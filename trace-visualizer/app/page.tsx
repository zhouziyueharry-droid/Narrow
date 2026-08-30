'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowRight,
  Check,
  CircleAlert,
  GitBranch,
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

type Stage = {
  name: string;
  label: string;
  count: number;
  targetRank: number | null;
  status: 'present' | 'absent';
  signal: Record<string, unknown> | null;
};

type Turn = {
  turn: number;
  userMessage: string;
  semanticQuery: string;
  constraints: Array<Record<string, unknown>>;
  evaluationActive: boolean;
  relaxed: boolean;
  latencyMs: number;
  diagnosis: string;
  reason: string;
  stages: Stage[];
};

type Session = {
  sampleId: string;
  scenario: string;
  hit: boolean;
  firstHitTurn: number | null;
  bestRank: number | null;
  diagnosis: string;
  diagnosisReason: string;
  target: {
    parentAsin: string;
    title: string;
    category: string;
    price: number | null;
    rating: number | null;
  };
  turns: Turn[];
};

type Diagnostics = {
  run: {
    id: string;
    model: string;
    workers: number;
    sampleCount: number;
    hitRate: number;
    mrr: number;
    technicalScore: number;
    diagnosisCounts: Record<string, number>;
  };
  sessions: Session[];
};

const diagnosisLabels: Record<string, string> = {
  hit: '已命中',
  recall: '召回漏失',
  fusion: '融合截断',
  filter: '硬过滤',
  rerank: '精排掉队',
  response: '输出丢失',
  gated: '等待覆盖',
};

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
      className={`stage-card ${present ? 'stage-present' : 'stage-absent'} ${active ? 'stage-active' : ''}`}
      aria-pressed={active}
    >
      <span className="stage-icon" aria-hidden="true">
        {present ? <Check /> : <X />}
      </span>
      <span className="min-w-0 text-left">
        <span className="stage-label">{stage.label}</span>
        <span className="stage-meta">
          {present ? `目标 #${stage.targetRank}` : '目标未出现'}
          <span aria-hidden="true"> · </span>
          {stage.count} 候选
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

  useEffect(() => {
    fetch('/diagnostics.json')
      .then((response) => {
        if (!response.ok) throw new Error('诊断数据加载失败');
        return response.json();
      })
      .then((payload: Diagnostics) => {
        setData(payload);
        const firstMiss = payload.sessions.find((session) => !session.hit);
        const initial = firstMiss ?? payload.sessions[0];
        setSelectedId(initial?.sampleId ?? '');
        setTurnNumber(initial?.turns.at(-1)?.turn ?? 1);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

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

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center bg-background p-6">
        <Card className="max-w-md border-red-300 bg-red-50">
          <CardContent className="flex gap-3 text-red-900">
            <CircleAlert className="mt-0.5 size-5" />
            <div><strong>无法打开诊断面板</strong><p className="mt-1 text-sm">{error}</p></div>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!data || !session || !turn || !stage) {
    return (
      <main className="loading-screen">
        <div className="loading-mark"><Target /></div>
        <p>正在重建目标商品路径…</p>
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
            <h1>标准答案流失诊断</h1>
          </div>
        </div>
        <div className="run-meta">
          <span>{data.run.model}</span>
          <span>{data.run.workers} workers</span>
          <span>{data.run.id}</span>
        </div>
        <div className="metric-strip">
          <div><span>样本</span><strong>{data.run.sampleCount}</strong></div>
          <div><span>Hit@10</span><strong>{(data.run.hitRate * 100).toFixed(1)}%</strong></div>
          <div><span>MRR</span><strong>{data.run.mrr.toFixed(3)}</strong></div>
          <div><span>技术分</span><strong>{data.run.technicalScore.toFixed(3)}</strong></div>
        </div>
      </header>

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
                  <Badge variant={stage.targetRank !== null ? 'default' : 'destructive'}>{stage.targetRank !== null ? `目标 #${stage.targetRank}` : '目标缺失'}</Badge>
                </div>
                <dl className="signal-list">
                  <div><dt>候选总数</dt><dd>{stage.count}</dd></div>
                  <div><dt>目标排名</dt><dd>{stage.targetRank ?? '未进入'}</dd></div>
                  {stage.signal && Object.entries(stage.signal).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{formatSignal(value)}</dd></div>)}
                </dl>
              </CardContent>
            </Card>

            <Card className="evidence-card query-card">
              <CardContent>
                <p className="eyebrow">TURN CONTEXT</p>
                <h3>本轮输入与结构化意图</h3>
                <blockquote>{turn.userMessage}</blockquote>
                <div className="query-block"><span>semantic_query</span><code>{turn.semanticQuery || '—'}</code></div>
                <div className="constraint-list">
                  {turn.constraints.map((constraint, index) => <span key={`${String(constraint.field)}-${index}`}>{String(constraint.field)} {String(constraint.operator)} {String(constraint.value)}</span>)}
                  {turn.constraints.length === 0 && <span>无结构化约束</span>}
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </section>
    </main>
  );
}
