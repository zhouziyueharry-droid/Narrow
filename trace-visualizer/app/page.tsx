'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowRight,
  Check,
  CircleAlert,
  GitBranch,
  FileJson,
  Search,
  Target,
  X,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';

import { parseTrace, type Diagnostics, type Session, type Stage } from '@/lib/trace';

const diagnosisLabels: Record<string, string> = {
  hit: '已命中',
  recall: '召回漏失',
  fusion: '融合截断',
  filter: '硬过滤',
  rerank: '精排掉队',
  response: '输出丢失',
  gated: '等待覆盖',
  unknown: '快照不足',
};

function rankLabel(stage: Stage) {
  if (stage.targetRank !== null) return `目标 #${stage.targetRank}`;
  if (stage.status === 'unknown') return stage.snapshotLimit ? `未见于前 ${stage.snapshotLimit}（排名未知）` : '未记录';
  return '目标未出现';
}

function formatSignal(value: unknown) {
  if (Array.isArray(value)) return value.join(' · ');
  if (typeof value === 'number') return Number(value.toFixed(5)).toString();
  return String(value);
}

function StageCard({
  stage,
  active,
  onClick,
}: {
  stage: Stage;
  active: boolean;
  onClick: () => void;
}) {
  const present = stage.targetRank !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`stage-card stage-${stage.status} ${active ? 'stage-active' : ''}`}
      aria-pressed={active}
    >
      <span className="stage-icon" aria-hidden="true">
        {present ? <Check /> : stage.status === 'unknown' ? <CircleAlert /> : <X />}
      </span>
      <span className="min-w-0 text-left">
        <span className="stage-label">{stage.label}</span>
        <span className="stage-meta">
          {rankLabel(stage)}
          <span aria-hidden="true"> · </span>
          {stage.count ?? '未知数量'} 候选
        </span>
      </span>
    </button>
  );
}

export default function Home() {
  const [data, setData] = useState<Diagnostics | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [resultFilter, setResultFilter] = useState('miss');
  const [scenarioFilter, setScenarioFilter] = useState('all');
  const [selectedId, setSelectedId] = useState('');
  const [turnNumber, setTurnNumber] = useState(1);
  const [selectedStage, setSelectedStage] = useState('rerank');
  const [sourceName, setSourceName] = useState('');
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  const installData = useCallback((payload: Diagnostics, source: string, sample?: string | null) => {
    const firstMiss = payload.sessions.find((item) => !item.hit);
    const initial = payload.sessions.find((item) => item.sampleId === sample) ?? firstMiss ?? payload.sessions[0];
    setData(payload);
    setSourceName(source);
    setError('');
    setQuery('');
    setScenarioFilter('all');
    setResultFilter(initial?.hit ? 'all' : 'miss');
    setSelectedId(initial?.sampleId ?? '');
    setTurnNumber(initial?.turns.at(-1)?.turn ?? 1);
    setSelectedStage(initial?.hit ? 'response' : 'rerank');
  }, []);

  useEffect(() => {
    const id = ++requestId.current;
    const controller = new AbortController();
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('data');
    const filename = requested && /^[a-zA-Z0-9][\w.-]*\.json$/.test(requested) ? requested : 'diagnostics.json';
    const runId = params.get('runId');
    const endpoint = runId
      ? `http://127.0.0.1:8000/api/evaluations/${encodeURIComponent(runId)}/diagnostics`
      : `/${filename}`;
    fetch(endpoint, { cache: 'no-store', signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`无法加载 ${filename}，可以直接选择本地 trace.json。`);
        return response.text();
      })
      .then((source) => {
        if (id === requestId.current) {
          const payload = parseTrace(source);
          const sample = params.get('session') ?? params.get('sample');
          installData(payload, runId ?? filename, sample);
          const selected = payload.sessions.find(item => item.sampleId === sample);
          const requestedTurn = Number(params.get('turn'));
          if (selected?.turns.some(item => item.turn === requestedTurn)) setTurnNumber(requestedTurn);
        }
      })
      .catch((reason: Error) => {
        if (id === requestId.current && reason.name !== 'AbortError') setError(reason.message);
      })
      .finally(() => { if (id === requestId.current) setLoading(false); });
    return () => controller.abort();
  }, [installData]);

  async function importFile(file: File) {
    const id = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      if (file.size > 100 * 1024 * 1024) throw new Error('文件超过 100 MB，请选择精简的 trace.json，而不是原始 node_traces.jsonl。');
      const source = await file.text();
      if (id === requestId.current) installData(parseTrace(source), file.name);
    } catch (reason) {
      if (id === requestId.current) setError(reason instanceof Error ? reason.message : '读取文件失败');
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }

  const fileToolbar = <section className="trace-file-bar" aria-label="Trace 数据来源">
    <FileJson aria-hidden="true" />
    <div className="trace-file-copy">
      <strong>{sourceName || '选择评测结果'}</strong>
      <span>{loading ? '正在读取 Trace…' : data ? `运行 ${data.run.id} · ${data.schemaVersion ? `Trace v${data.schemaVersion}` : '兼容旧诊断格式'}` : '导入 testing 生成的 trace.json'}</span>
    </div>
    <label className="trace-file-picker">
      <span>选择 Trace JSON</span>
      <Input type="file" accept=".json,application/json" aria-label="选择 Trace JSON"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = '';
          if (file) void importFile(file);
        }} />
    </label>
    <span className="trace-privacy">仅在浏览器本地读取，不上传</span>
  </section>;

  const filteredSessions = useMemo(() => {
    if (!data) return [];
    const normalized = query.trim().toLowerCase();
    return data.sessions.filter((session) => {
      const resultMatch =
        resultFilter === 'all' ||
        (resultFilter === 'hit' && session.hit) ||
        (resultFilter === 'miss' && !session.hit) ||
        session.diagnosis === resultFilter;
      const scenarioMatch =
        scenarioFilter === 'all' || session.scenario === scenarioFilter;
      const queryMatch =
        !normalized ||
        session.sampleId.toLowerCase().includes(normalized) ||
        session.target.parentAsin.toLowerCase().includes(normalized) ||
        session.target.title.toLowerCase().includes(normalized);
      return resultMatch && scenarioMatch && queryMatch;
    });
  }, [data, query, resultFilter, scenarioFilter]);

  const session =
    data?.sessions.find((item) => item.sampleId === selectedId) ??
    filteredSessions[0] ??
    data?.sessions[0];
  const turn =
    session?.turns.find((item) => item.turn === turnNumber) ??
    session?.turns.at(-1);
  const stage =
    turn?.stages.find((item) => item.name === selectedStage) ?? turn?.stages[0];
  const routes = turn?.stages.slice(0, 3) ?? [];
  const downstream = turn?.stages.slice(3) ?? [];

  function selectSession(next: Session) {
    setSelectedId(next.sampleId);
    setTurnNumber(next.turns.at(-1)?.turn ?? 1);
    setSelectedStage(next.diagnosis === 'hit' ? 'response' : next.diagnosis);
  }

  if (!data || !session || !turn || !stage) {
    return (
      <main className="app-shell">
        {fileToolbar}
        <section className="trace-empty" aria-live="polite">
          <Target aria-hidden="true" />
          <h1>{error ? '未能读取 Trace' : loading ? '正在读取评测结果…' : '还没有可展示的样本'}</h1>
          <p role={error ? 'alert' : undefined}>{error || '请选择评测生成的 trace.json，也支持旧 diagnostics.json。'}</p>
          <p>summary.json 只有评分，不能用于展示逐轮 Trace。</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><GitBranch /></span>
          <div>
            <p className="eyebrow">RANKING TRACE LAB</p>
            <h1>{data.diagnosticMode === 'agent' ? 'Agent 路径诊断（保存的快照）' : '标准答案流失诊断'}</h1>
          </div>
        </div>
        <div className="run-meta">
          <a href="http://127.0.0.1:5173/runs">返回 Shopping Copilot</a>
          <span>{data.run.model}</span>
          {data.run.reranker && <span>{data.run.reranker.mode}</span>}
          <span>{data.run.workers} workers</span>
          <span>{data.run.id}</span>
        </div>
        <div className="metric-strip">
          <div><span>{data.run.partial ? '已完成 / 计划' : '样本'}</span><strong>{data.run.sampleCount}{data.run.partial && ` / ${data.run.expectedSampleCount}`}</strong></div>
          <div><span>{data.diagnosticMode === 'agent' ? '成功率' : data.run.partial ? '部分 Hit@10' : 'Hit@10'}</span><strong>{(data.run.hitRate * 100).toFixed(1)}%</strong></div>
          <div><span>MRR</span><strong>{data.run.mrr.toFixed(3)}</strong></div>
          <div><span>{data.run.partial ? '部分技术分' : '技术分'}</span><strong>{data.diagnosticMode === 'agent' ? '不适用' : data.run.technicalScore.toFixed(3)}</strong></div>
        </div>
      </header>

      {fileToolbar}
      {error && <div className="trace-file-error" role="alert"><CircleAlert aria-hidden="true" /><span>{error} 当前结果保持不变。</span></div>}

      <section className="workspace">
        <aside className="sample-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">SAMPLE EXPLORER</p><h2>评测样本</h2></div>
            <Badge variant="outline">{filteredSessions.length}</Badge>
          </div>
          <div className="filters">
            <label className="search-box">
              <Search aria-hidden="true" />
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ID、ASIN 或商品名" aria-label="搜索样本" />
            </label>
            <div className="filter-row">
              <NativeSelect value={resultFilter} onChange={(event) => setResultFilter(event.target.value)} aria-label="结果筛选">
                <NativeSelectOption value="miss">仅未命中</NativeSelectOption>
                <NativeSelectOption value="all">全部结果</NativeSelectOption>
                <NativeSelectOption value="hit">仅命中</NativeSelectOption>
                <NativeSelectOption value="recall">召回漏失</NativeSelectOption>
                <NativeSelectOption value="filter">硬过滤</NativeSelectOption>
                <NativeSelectOption value="rerank">精排掉队</NativeSelectOption>
              </NativeSelect>
              <NativeSelect value={scenarioFilter} onChange={(event) => setScenarioFilter(event.target.value)} aria-label="场景筛选">
                <NativeSelectOption value="all">全部场景</NativeSelectOption>
                <NativeSelectOption value="buying">Buying</NativeSelectOption>
                <NativeSelectOption value="browsing">Browsing</NativeSelectOption>
                <NativeSelectOption value="boundary">Boundary</NativeSelectOption>
                <NativeSelectOption value="intent_override">Override</NativeSelectOption>
              </NativeSelect>
            </div>
          </div>
          <div className="sample-list">
            {filteredSessions.map((item) => (
              <button type="button" key={item.sampleId} onClick={() => selectSession(item)} className={`sample-row ${item.sampleId === session.sampleId ? 'selected' : ''}`}>
                <span className={`result-dot ${item.hit ? 'hit' : 'miss'}`} />
                <span className="sample-copy">
                  <span className="sample-id">{item.sampleId}</span>
                  <span className="sample-title">{item.target.title}</span>
                  <span className="sample-tags"><span>{item.scenario}</span><span>{diagnosisLabels[item.diagnosis] ?? item.diagnosis}</span></span>
                </span>
              </button>
            ))}
            {filteredSessions.length === 0 && <p className="empty-copy">没有符合条件的样本</p>}
          </div>
        </aside>

        <section className="trace-panel">
          {data.run.snapshotMode && <div className="snapshot-notice" role="note">
            <strong>{data.run.partial ? '中断运行 · 部分结果' : '日志快照模式'}</strong>
            <p>仅展示已完成的 {data.run.sampleCount} 个样本；另有 {data.run.incompleteSampleCount ?? 0} 个未完成样本保留在原始日志中。指标仅基于已完成样本。</p>
            <p>直接读取保存的 Trace，未重跑模型。未见于已保存的候选快照不代表未召回；灰色节点表示排名未知。</p>
          </div>}
          <div className="target-header">
            <div className="target-icon"><Target /></div>
            <div className="target-copy">
              <div className="target-line">
                <Badge variant={session.hit ? 'default' : 'destructive'}>{session.hit ? `第 ${session.firstHitTurn} 轮命中` : '最终未命中'}</Badge>
                <span>{session.target.parentAsin}</span>
              </div>
              <h2>{session.target.title}</h2>
              <p>{session.target.category || '未标注类目'}</p>
            </div>
            <div className="target-facts">
              <span>价格<strong>{session.target.price == null ? '—' : `$${session.target.price}`}</strong></span>
              <span>评分<strong>{session.target.rating ?? '—'}</strong></span>
            </div>
          </div>

          <div className="turn-bar">
            <span className="turn-label">对话轮次</span>
            <div className="turn-buttons">
              {session.turns.map((item) => (
                <Button key={item.turn} size="sm" variant={item.turn === turn.turn ? 'default' : 'outline'} onClick={() => setTurnNumber(item.turn)} aria-label={`查看第 ${item.turn} 轮`}>
                  {item.turn}<span className={`mini-dot ${item.diagnosis}`} />
                </Button>
              ))}
            </div>
            <span className="latency">{(turn.latencyMs / 1000).toFixed(2)}s</span>
          </div>

          <div className={`diagnosis-banner diagnosis-${turn.diagnosis}`}>
            <span>{turn.diagnosis === 'hit' ? <Check /> : <CircleAlert />}</span>
            <div><strong>{diagnosisLabels[turn.diagnosis] ?? turn.diagnosis}</strong><p>{turn.reason}</p></div>
            {!turn.evaluationActive && <Badge variant="outline">评测门控未开启</Badge>}
          </div>

          <section className="flow-section" aria-label="目标商品流转流程图">
            <div className="flow-caption">
              <div><p className="eyebrow">TARGET SURVIVAL PATH</p><h3>目标商品存活路径</h3></div>
              <p>点击任一节点查看目标商品在该阶段的分数和排名。</p>
            </div>
            <div className="flow-canvas">
              <div className="recall-group">
                <span className="group-label">并行粗召回</span>
                <div className="recall-grid">
                  {routes.map((item) => <StageCard key={item.name} stage={item} active={stage.name === item.name} onClick={() => setSelectedStage(item.name)} />)}
                </div>
              </div>
              <div className="flow-arrow"><ArrowDown /></div>
              <div className="downstream-flow">
                {downstream.map((item, index) => (
                  <div className="downstream-item" key={item.name}>
                    <StageCard stage={item} active={stage.name === item.name} onClick={() => setSelectedStage(item.name)} />
                    {index < downstream.length - 1 && <ArrowRight className="connector" aria-hidden="true" />}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <div className="evidence-grid">
            <Card className="evidence-card">
              <CardContent>
                <p className="eyebrow">NODE EVIDENCE</p>
                <div className="evidence-title">
                  <h3>{stage.label}</h3>
                  <Badge variant={stage.status === 'unknown' ? 'outline' : stage.targetRank !== null ? 'default' : 'destructive'}>{rankLabel(stage)}</Badge>
                </div>
                <dl className="signal-list">
                  <div><dt>候选总数</dt><dd>{stage.count ?? '未记录'}</dd></div>
                  <div><dt>目标排名</dt><dd>{rankLabel(stage)}</dd></div>
                  {stage.signal && Object.entries(stage.signal).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{formatSignal(value)}</dd></div>)}
                </dl>
              </CardContent>
            </Card>

            <Card className="evidence-card query-card">
              <CardContent>
                <p className="eyebrow">TURN CONTEXT</p>
                <h3>本轮输入与结构化意图</h3>
                <blockquote>{turn.userMessage}</blockquote>
                {turn.agentMessage && <p className="text-xs">Agent：{turn.agentMessage}</p>}
                {turn.recommendedAsins && <details className="mt-3 text-xs"><summary>本轮推荐 Top 10</summary><ol className="mt-2 list-decimal pl-5">{turn.recommendedAsins.map((asin) => <li key={asin}>{asin}</li>)}</ol></details>}
                <div className="query-block"><span>semantic_query</span><code>{turn.semanticQuery || '—'}</code></div>
                <div className="constraint-list">
                  {turn.constraints.map((constraint, index) => <span key={`${String(constraint.field)}-${index}`}>{String(constraint.field)} {String(constraint.operator)} {String(constraint.value)}</span>)}
                  {turn.constraints.length === 0 && <span>无结构化约束</span>}
                </div>
              </CardContent>
            </Card>
          </div>
          {turn.error && <p className="trace-file-error" role="alert">本轮执行错误：{turn.error}</p>}
          {turn.nodeTrace && <section className="node-trace-details" aria-label="节点 Trace">
            <h3>本轮节点 Trace</h3>
            <p>直接来自评测日志。候选池显示目标商品的快照证据，完整候选保留在原始 JSONL 日志。</p>
            {turn.nodeTrace.map((node, index) => <details key={`${turn.turn}-${index}`}>
              <summary>{node.names.join(' / ')} <span>step {node.step ?? index + 1}</span></summary>
              <pre>{JSON.stringify(node.updates, null, 2)}</pre>
            </details>)}
          </section>}
        </section>
      </section>
    </main>
  );
}
