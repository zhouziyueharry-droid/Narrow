[CmdletBinding()]
param(
    [int]$Workers = 0,
    [string]$Model = "deepseek-v4-pro",
    [int]$CandidateLimit = 20,
    [string]$OutputRoot = "evaluation_runs/parallel_pro_200",
    [switch]$SkipTests,
    [switch]$SkipEvaluation,
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AgentRoot = Join-Path $RepoRoot "techjam-conversational-search"
$FrontendRoot = Join-Path $RepoRoot "trace-visualizer"
$PythonExe = Join-Path $AgentRoot ".venv\Scripts\python.exe"

if ($Workers -le 0) {
    $Workers = [Environment]::ProcessorCount
}
if ($Workers -lt 1) {
    throw "Workers must be at least 1."
}
if (-not (Test-Path -LiteralPath $AgentRoot)) {
    throw "Agent project not found: $AgentRoot"
}
if (-not (Test-Path -LiteralPath $FrontendRoot)) {
    throw "Trace frontend not found: $FrontendRoot"
}

function Invoke-ProjectPython {
    param([string[]]$PythonArgs)
    if (Test-Path -LiteralPath $PythonExe) {
        & $PythonExe @PythonArgs
    }
    elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run python @PythonArgs
    }
    else {
        throw "Neither .venv Python nor uv is available. Run 'uv sync --extra deepseek --group dev' first."
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

Push-Location $AgentRoot
try {
    if (-not $SkipTests) {
        Write-Host "[1/4] Running unit, integration, and regression tests..."
        Invoke-ProjectPython @(
            "-m", "pytest", "tests", "-q",
            "--basetemp=.pytest_tmp\official_pipeline"
        )
    }

    if (-not $SkipEvaluation) {
        Write-Host "[2/4] Running official evaluator semantics with $Workers traced LLM workers..."
        Invoke-ProjectPython @(
            "scripts\evaluate_parallel_with_traces.py",
            "--workers", "$Workers",
            "--model", $Model,
            "--candidate-limit", "$CandidateLimit",
            "--output-root", $OutputRoot
        )
    }
    else {
        Write-Host "[2/4] Reusing the latest completed evaluation."
    }
}
finally {
    Pop-Location
}

$EvaluationRoot = if ([IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot
} else {
    Join-Path $AgentRoot $OutputRoot
}
$LatestFile = Join-Path $EvaluationRoot "LATEST.txt"
if (-not (Test-Path -LiteralPath $LatestFile)) {
    throw "Evaluation LATEST.txt not found: $LatestFile"
}
$RunDir = (Get-Content -LiteralPath $LatestFile -Raw).Trim()

Push-Location $FrontendRoot
try {
    Write-Host "[3/4] Replaying exact target ranks into frontend diagnostics..."
    Invoke-ProjectPython @(
        "scripts\build-diagnostics.py",
        "--project-root", $AgentRoot,
        "--evaluation-root", $EvaluationRoot,
        "--run-dir", $RunDir,
        "--output", (Join-Path $FrontendRoot "public\diagnostics.json")
    )

    if (-not $SkipFrontendBuild) {
        Write-Host "[4/4] Building the trace frontend..."
        & npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed with exit code $LASTEXITCODE."
        }
    }
    else {
        Write-Host "[4/4] Frontend build skipped."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Pipeline complete."
Write-Host "Evaluation: $RunDir"
Write-Host "Frontend data: $(Join-Path $FrontendRoot 'public\diagnostics.json')"
Write-Host "Preview: cd '$FrontendRoot'; npm run dev"
