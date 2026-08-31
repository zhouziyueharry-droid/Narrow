"""Local HTTP adapter for demo-frontend; uses final's agent and evaluation CLIs."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from shopping_agent.application.service import ShoppingAgent
from shopping_agent.web_results import iter_rows, product, read_json, result_payload, simulator_trace

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
BUNDLE = ROOT/"models/lambdamart_synthetic_2000"
ARCHIVE = ROOT/"evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800"
LIMITS = {"native": 200, "simulator-techjam": 200, "simulator-realistic": 100}
ACTIVE = {"queued", "running", "finalizing_diagnostics"}
ORIGINS = {f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (5173, 3000, 8000)}


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path: Path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["local", "deepseek"] = "local"
    model: str = Field(default="deepseek-v4-pro", min_length=1, max_length=120)
    realistic_verbalizer: Literal["template", "deepseek"] = "template"
    reranker: Literal["precise", "lambdamart"] = "precise"


class Settings(Options):
    base_url: str = "https://api.deepseek.com"


class Evaluation(Options):
    mode: Literal["native", "simulator-techjam", "simulator-realistic"]
    count: int = Field(default=10, ge=1, le=200)
    seed: Literal[42] = 42


class Message(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=10, ge=1, le=10)


class Deletion(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


class ApiFailure(Exception):
    def __init__(self, code: str, status=400):
        self.code, self.status = code, status


def environment(options: dict) -> dict[str, str]:
    return {"SHOPPING_AGENT_ENABLE_LLM": "true" if options["provider"] == "deepseek" else "false",
            "DEEPSEEK_MODEL": options["model"], "SHOPPING_UI_RERANKER": options["reranker"],
            "SHOPPING_DENSE_BACKEND": "local", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}


def create_agent(catalog_path):
    """Callable accepted by the unchanged simulator's --agent-class option."""
    ranker = None
    if os.getenv("SHOPPING_UI_RERANKER", "precise") == "lambdamart":
        from shopping_agent.ranking.lambdamart import LambdaMARTReranker
        ranker = LambdaMARTReranker(BUNDLE)
    return ShoppingAgent(catalog_path, reranker=ranker)


class Runtime:
    def __init__(self, catalog: Path, runs: Path, archive: Path = ARCHIVE):
        self.catalog, self.runs, self.archive = catalog.resolve(), runs.resolve(), archive.resolve()
        self.settings = Settings(base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        self.revision = 0
        self.sessions, self.jobs, self.processes, self.tasks = {}, {}, {}, set()
        self.lock = asyncio.Lock()  # ponytail: one chat/settings operation at a time; isolate runtimes if concurrent users are needed.
        self.agent = None
        self.products = None
        if runs.exists():
            for path in runs.glob("*/job.json"):
                job = read_json(path)
                if job["status"] in ACTIVE:
                    job.update(status="interrupted", code="job.interrupted", finished_at=now())
                self.jobs[job["id"]] = job
        if (archive/"summary.json").exists():
            summary = read_json(archive/"summary.json")
            self.jobs[archive.name] = {"id": archive.name, "mode": "native", "status": "completed", "code": "job.completed",
                "protected": True, "created_at": "2026-08-30T21:17:51+08:00", "finished_at": "2026-08-30T21:29:50+08:00",
                "config": {"count": summary["sample_count"], "provider": "deepseek", "model": summary["model"],
                    "reranker": "lambdamart", "realistic_verbalizer": "template", "seed": 20260830},
                "progress": {"completed": summary["sample_count"], "total": summary["sample_count"]}, "metrics": summary}

    def catalog_products(self):
        if self.products is None:
            self.products = {row["parent_asin"]: product(row) for row in iter_rows(self.catalog)}
        return self.products

    def settings_payload(self):
        return self.settings.model_dump() | {"revision": self.revision,
            "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
            "model_presets": ["deepseek-v4-flash", "deepseek-v4-pro"]}

    def active(self):
        return any(job["status"] in ACTIVE for job in self.jobs.values())

    def get_job(self, job_id):
        if job_id not in self.jobs:
            raise ApiFailure("job.not_found", 404)
        return self.jobs[job_id]

    def job_root(self, job):
        path = (self.runs/job["id"]).resolve()
        if path.parent != self.runs or path.is_symlink():
            raise ApiFailure("job.delete_unsafe_path", 409)
        return path

    def artifact_dir(self, job):
        if job.get("protected"):
            return self.archive
        base = self.job_root(job)
        if job["mode"] != "native":
            return base
        matches = sorted((base/"evaluation").glob("*/run_config.json"))
        return matches[-1].parent if matches else base/"evaluation"

    def persist(self, job):
        dump(self.job_root(job)/"job.json", job)

    def check_options(self, options):
        if not self.catalog.is_file():
            raise ApiFailure("data.catalog_missing", 503)
        needs_key = options.provider == "deepseek" or options.realistic_verbalizer == "deepseek"
        if needs_key and not os.getenv("DEEPSEEK_API_KEY", "").strip():
            raise ApiFailure("deepseek.not_configured", 422)

    def result(self, job):
        return result_payload(self.artifact_dir(job), job, self.catalog_products())

    async def start_job(self, options: Evaluation):
        if self.active():
            raise ApiFailure("job.already_running", 409)
        if options.count > LIMITS[options.mode] or (options.mode != "simulator-realistic" and options.realistic_verbalizer != "template"):
            raise ApiFailure("request.validation_failed", 422)
        self.check_options(options)
        job_id = f"{options.mode}_{uuid.uuid4().hex}"
        job = {"id": job_id, "mode": options.mode, "status": "queued", "code": "job.queued", "created_at": now(),
            "config": options.model_dump(exclude={"mode"}), "progress": {"completed": 0, "total": options.count}}
        self.job_root(job).mkdir(parents=True)
        self.jobs[job_id] = job
        self.persist(job)
        task = asyncio.create_task(self.run_job(job))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return job

    def command(self, job):
        cfg, folder = job["config"], self.job_root(job)
        if job["mode"] == "native":
            command = [sys.executable, str(ROOT/"scripts/evaluate_with_traces.py"), "--catalog", str(self.catalog),
                "--dataset", str(ROOT/"data/public_set.jsonl"), "--max-samples", str(cfg["count"]),
                "--candidate-limit", "0", "--output-root", str(folder/"evaluation"),
                "--llm" if cfg["provider"] == "deepseek" else "--no-llm"]
            if cfg["reranker"] == "lambdamart":
                command += ["--ltr-model-dir", str(BUNDLE), "--ltr-ranker", "lambdamart"]
            return command
        return [sys.executable, "-m", "user_simulator.cli", "run", "--preset", job["mode"].removeprefix("simulator-"),
            "--catalog-path", str(self.catalog), "--sessions-path", str(ROOT/"data/public_set.jsonl"),
            "--agent-class", "shopping_agent.web:create_agent", "--limit", str(cfg["count"]),
            "--verbalizer", cfg["realistic_verbalizer"], "--output", str(folder/"result.json"),
            "--session-output", str(folder/"sessions.jsonl"), "--event-output", str(folder/"events.jsonl"),
            "--report-output", str(folder/"report.md")]

    async def run_job(self, job):
        try:
            if job["status"] == "cancelled":
                return
            job.update(status="running", code="job.running", started_at=now())
            env = os.environ | environment(job["config"]) | {"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join(map(str, [ROOT/"src", ROOT, REPO/"user-simulator/src"]))}
            with (self.job_root(job)/"worker.log").open("wb") as log:
                process = subprocess.Popen(self.command(job), cwd=ROOT, env=env, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                self.processes[job["id"]] = process
                while process.poll() is None:
                    job["progress"]["completed"] = sum(1 for _ in iter_rows(self.artifact_dir(job)/"sessions.jsonl"))
                    self.persist(job)
                    await asyncio.sleep(1)
                if job["status"] == "cancelled":
                    return
                if process.returncode:
                    raise RuntimeError("worker failed")
            result = self.result(job)
            if len(result["sessions"]) != job["config"]["count"]:
                raise RuntimeError("incomplete result")
            job.update(status="completed", code="job.completed", finished_at=now(), metrics=result["metrics"])
            job["progress"]["completed"] = len(result["sessions"])
        except Exception:
            job.update(status="failed", code="job.failed", finished_at=now(), error={"code": "evaluation.runner_failed"})
        finally:
            self.processes.pop(job["id"], None)
            self.persist(job)

    async def cancel(self, job):
        if job["status"] in ACTIVE:
            job.update(status="cancelled", code="job.cancelled", finished_at=now())
            process = self.processes.get(job["id"])
            if process and process.poll() is None:
                process.terminate()  # Both existing CLIs run in this child, without launching descendant workers.
                await asyncio.to_thread(process.wait)
            self.persist(job)
        return job


def create_app(catalog: Path | None = None, runs: Path | None = None, archive: Path = ARCHIVE):
    runtime = Runtime(catalog or ROOT/"data/catalog.jsonl", runs or REPO/"demo_runs", archive)

    @asynccontextmanager
    async def lifespan(app):
        yield
        for job in list(runtime.jobs.values()):
            await runtime.cancel(job)
        if runtime.tasks:
            await asyncio.gather(*runtime.tasks)

    async def api(request: Request):
        if request.method != "GET":
            origin = request.headers.get("origin")
            if (origin and origin not in ORIGINS) or request.headers.get("sec-fetch-site") == "cross-site":
                raise ApiFailure("request.forbidden_origin", 403)
        path, method = request.path_params["path"].strip("/"), request.method
        data = {}
        if method in {"POST", "PUT", "DELETE"}:
            body = await request.body()
            if len(body) > 32768:
                raise ApiFailure("request.validation_failed", 413)
            data = json.loads(body) if body else {}
        if path == "health":
            return {"status": "ok", "code": "api.ready"}
        if path == "capabilities":
            return {"catalog": {"available": runtime.catalog.is_file(), "product_count": len(runtime.catalog_products()),
                "bytes": runtime.catalog.stat().st_size if runtime.catalog.is_file() else 0},
                "public_set": {"available": (ROOT/"data/public_set.jsonl").is_file(), "session_count": 200},
                "deepseek_configured": runtime.settings_payload()["deepseek_configured"],
                "trace_url": "http://127.0.0.1:3000/?runId=" + runtime.archive.name, "limits": LIMITS}
        if path == "settings":
            if method == "PUT":
                settings = Settings.model_validate(data)
                if settings.base_url != runtime.settings.base_url:
                    raise ApiFailure("settings.base_url_locked", 422)
                if settings.provider == "deepseek" and not runtime.settings_payload()["deepseek_configured"]:
                    raise ApiFailure("deepseek.not_configured", 422)
                async with runtime.lock:
                    if runtime.active():
                        raise ApiFailure("settings.locked_by_active_job", 409)
                    if runtime.agent:
                        for sid in runtime.sessions:
                            runtime.agent.release_session(sid)
                    runtime.agent, runtime.sessions = None, {}
                    runtime.settings = settings
                    runtime.revision += 1
            return runtime.settings_payload()
        if path == "settings/deepseek/test" and method == "POST":
            if not runtime.settings_payload()["deepseek_configured"]:
                raise ApiFailure("deepseek.not_configured", 422)
            from openai import OpenAI
            async with runtime.lock:
                started = time.perf_counter()
                try:
                    with OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=runtime.settings.base_url, timeout=20) as client:
                        await asyncio.to_thread(client.chat.completions.create, model=runtime.settings.model,
                            messages=[{"role": "user", "content": "Reply OK"}], max_tokens=8)
                except Exception:
                    raise ApiFailure("deepseek.connection_failed", 502)
            return {"code": "deepseek.connection_ok", "model": runtime.settings.model, "latency_ms": round((time.perf_counter()-started)*1000)}
        if path == "chat/sessions":
            if method == "GET":
                return {"sessions": [{k: v for k, v in session.items() if k != "messages"} | {"message_count": len(session["messages"])}
                    for session in sorted(runtime.sessions.values(), key=lambda s: s["updated_at"], reverse=True)]}
            if method == "POST":
                runtime.check_options(runtime.settings)
                sid = uuid.uuid4().hex
                session = {"id": sid, "title": "New chat", "created_at": now(), "updated_at": now(),
                    "settings_revision": runtime.revision, "messages": []}
                runtime.sessions[sid] = session
                return session
        parts = path.split("/")
        if parts[:2] == ["chat", "sessions"] and len(parts) in {3, 4}:
            sid = parts[2]
            async with runtime.lock:
                if sid not in runtime.sessions:
                    raise ApiFailure("chat.session_not_found", 404)
                session = runtime.sessions[sid]
                if method == "DELETE" and len(parts) == 3:
                    if runtime.agent:
                        runtime.agent.release_session(sid)
                    del runtime.sessions[sid]
                    return Response(status_code=204)
                if method == "GET" and len(parts) == 3:
                    return session
                if method == "POST" and parts[-1] == "messages":
                    message = Message.model_validate(data)
                    if not message.message.strip():
                        raise ApiFailure("request.validation_failed", 422)
                    runtime.check_options(runtime.settings)
                    os.environ.update(environment(runtime.settings.model_dump()))
                    if runtime.agent is None:
                        runtime.agent = await asyncio.to_thread(create_agent, runtime.catalog)
                    if not session["messages"]:
                        runtime.agent.start_session(sid)
                    started = time.perf_counter()
                    try:
                        response = await asyncio.to_thread(runtime.agent.chat, sid, message.message, top_k=message.top_k)
                        intent = runtime.agent.get_intent_state(sid)
                    except Exception:
                        raise ApiFailure("chat.agent_failed", 502)
                    stamp = now()
                    answer = {"role": "assistant", "content": response["message"], "created_at": stamp,
                        "ask_attribute": response.get("ask_attribute"), "usage": response.get("usage", {}), "intent": intent,
                        "latency_ms": round((time.perf_counter()-started)*1000), "provider": runtime.settings.provider,
                        "model": runtime.settings.model if runtime.settings.provider == "deepseek" else "local",
                        "recommendations": [runtime.catalog_products().get(item["parent_asin"], {"title": "", "categories": [], "features": []}) | item
                                            for item in response["recommendations"]]}
                    session["messages"].extend([{"role": "user", "content": message.message, "created_at": stamp}, answer])
                    session.update(title=message.message[:60] if len(session["messages"]) == 2 else session["title"], updated_at=stamp)
                    return answer
        if path == "evaluations":
            if method == "GET":
                return {"runs": sorted(runtime.jobs.values(), key=lambda j: j["created_at"], reverse=True)}
            if method == "POST":
                options = Evaluation.model_validate(data)
                if "reranker" not in data:
                    options.reranker = runtime.settings.reranker
                async with runtime.lock:
                    return await runtime.start_job(options)
            if method == "DELETE":
                ids = Deletion.model_validate(data).ids
                async with runtime.lock:
                    jobs = [runtime.jobs[sid] for sid in set(ids) if sid in runtime.jobs]
                    if any(job.get("protected") for job in jobs):
                        raise ApiFailure("job.archive_protected", 409)
                    if any(job["status"] in ACTIVE or job["id"] in runtime.processes for job in jobs):
                        raise ApiFailure("job.active_cannot_delete", 409)
                    paths = [(job, runtime.job_root(job)) for job in jobs]
                    for job, folder in paths:
                        shutil.rmtree(folder)
                        del runtime.jobs[job["id"]]
                return {"deleted": [job["id"] for job in jobs], "not_found": [sid for sid in ids if sid not in {j["id"] for j in jobs}]}
        if parts[0] == "evaluations" and len(parts) >= 2:
            job = runtime.get_job(parts[1])
            if len(parts) == 2 and method == "GET":
                return job
            action = parts[2] if len(parts) > 2 else ""
            if action == "cancel" and method == "POST":
                return await runtime.cancel(job)
            if action == "events" and method == "GET":
                async def events():
                    while True:
                        payload = {"status": job["status"], "code": job["code"], "progress": job["progress"], "timestamp": now()}
                        yield "event: snapshot\ndata: " + json.dumps(payload) + "\n\n"
                        if job["status"] not in ACTIVE:
                            break
                        await asyncio.sleep(1)
                return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
            if action in {"result", "live-result"} and method == "GET":
                if action == "result" and job["status"] != "completed":
                    raise ApiFailure("job.result_not_ready", 409)
                result = await asyncio.to_thread(runtime.result, job)
                return {"result": result} if action == "live-result" else result
            if action == "diagnostics" and method == "GET":
                if job["status"] != "completed":
                    raise ApiFailure("job.diagnostics_not_ready", 409)
                run = runtime.artifact_dir(job)
                if job["mode"] == "native":
                    return FileResponse(run/"trace.json", media_type="application/json")
                return await asyncio.to_thread(simulator_trace, run, job, runtime.catalog_products())
        raise ApiFailure("request.not_found", 404)

    async def dispatch(request):
        try:
            result = await api(request)
            return result if isinstance(result, Response) else JSONResponse(result)
        except ApiFailure as exc:
            return JSONResponse({"error": {"code": exc.code}}, status_code=exc.status)
        except (ValidationError, json.JSONDecodeError):
            return JSONResponse({"error": {"code": "request.validation_failed"}}, status_code=422)
        except Exception:
            return JSONResponse({"error": {"code": "api.unavailable"}}, status_code=500)

    routes = [Route("/api/{path:path}", dispatch, methods=["GET", "POST", "PUT", "DELETE"])]
    dist = REPO/"demo-frontend/dist"
    if dist.exists():
        class SPA(StaticFiles):
            async def get_response(self, path, scope):
                from starlette.exceptions import HTTPException
                try:
                    return await super().get_response(path, scope)
                except HTTPException as exc:
                    if exc.status_code == 404 and "." not in Path(path).name:
                        return await super().get_response("index.html", scope)
                    raise
        routes.append(Mount("/", app=SPA(directory=dist, html=True)))
    app = Starlette(routes=routes, lifespan=lifespan, middleware=[
        Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]),
        Middleware(CORSMiddleware, allow_origins=list(ORIGINS), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])])
    app.state.runtime = runtime
    return app


def main():
    from dotenv import load_dotenv
    import uvicorn
    load_dotenv(ROOT/".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path(os.getenv("SHOPPING_CATALOG_PATH", ROOT/"data/catalog.jsonl")))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(args.catalog), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
