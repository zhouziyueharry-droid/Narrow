export type Stage = {
  name: string; label: string; count: number | null; targetRank: number | null;
  status: 'present' | 'absent' | 'unknown'; snapshotLimit?: number;
  signal: Record<string, unknown> | null;
};
export type Turn = {
  turn: number; userMessage: string; agentMessage?: string; recommendedAsins?: string[];
  semanticQuery: string; constraints: Array<Record<string, unknown>>;
  evaluationActive: boolean; relaxed: boolean; latencyMs: number;
  diagnosis: string; reason: string; stages: Stage[]; error?: string | null;
  nodeTrace?: Array<{ names: string[]; updates: Record<string, unknown>; step?: number | null; createdAt?: string | null }>;
};
export type Session = {
  sampleId: string; scenario: string; hit: boolean; firstHitTurn: number | null;
  bestRank: number | null; diagnosis: string; diagnosisReason: string;
  target: { parentAsin: string; title: string; category: string; price: number | null; rating: number | null };
  turns: Turn[];
};
export type Diagnostics = {
  diagnosticMode?: 'target' | 'agent';
  schema?: 'shopping-agent.trace'; schemaVersion?: 1;
  run: {
    id: string; model: string; workers: number; sampleCount: number;
    expectedSampleCount?: number; incompleteSampleCount?: number; partial?: boolean;
    snapshotMode?: boolean; reranker?: { mode: string; model_name?: string } | null;
    llmEnabled?: boolean | null; denseBackend?: string; mttc?: number;
    hitRate: number; mrr: number; technicalScore: number; diagnosisCounts: Record<string, number>;
  };
  sessions: Session[];
};

const stageNames = ['lexical', 'dense', 'attribute', 'fusion', 'filter', 'rerank', 'response'];
function check(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}
function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function text(value: unknown): value is string { return typeof value === 'string'; }
function number(value: unknown): value is number { return typeof value === 'number' && Number.isFinite(value); }
function integer(value: unknown): value is number { return number(value) && Number.isInteger(value) && value >= 0; }
function nullableNumber(value: unknown) { return value === null || number(value); }
function rank(value: unknown) { return value === null || (integer(value) && value > 0); }

/** Validate files before replacing the current view; legacy diagnostics remain readable. */
export function parseTrace(source: string): Diagnostics {
  let data: unknown;
  try { data = JSON.parse(source.replace(/^\uFEFF/, '')); }
  catch { throw new Error('JSON 无法解析，请选择完整的 trace.json 文件。'); }
  check(object(data), 'Trace 必须是 JSON 对象。');
  if (data.schema !== undefined || data.schemaVersion !== undefined) {
    check(data.schema === 'shopping-agent.trace' && data.schemaVersion === 1,
      '不支持此 Trace 格式或版本；当前支持 shopping-agent.trace v1。');
  }
  check(object(data.run) && Array.isArray(data.sessions),
    '请选择评测生成的 trace.json（或旧 diagnostics.json）；summary.json、results.json 不含完整 Trace。');
  const run = data.run;
  check(text(run.id) && text(run.model) && integer(run.workers), 'Trace 的运行信息不完整。');
  check(integer(run.sampleCount) && run.sampleCount === data.sessions.length, '样本数量与 Trace 内容不一致。');
  for (const key of ['hitRate', 'mrr', 'technicalScore']) {
    check(number(run[key]) && run[key] >= 0 && run[key] <= 1, `无效的评分字段：${key}`);
  }
  check(object(run.diagnosisCounts) && Object.values(run.diagnosisCounts).every(integer), '诊断计数无效。');
  for (const key of ['partial', 'snapshotMode', 'llmEnabled']) {
    check(run[key] == null || typeof run[key] === 'boolean', `无效的运行状态：${key}`);
  }
  for (const key of ['expectedSampleCount', 'incompleteSampleCount']) {
    check(run[key] === undefined || integer(run[key]), `无效的样本数量：${key}`);
  }
  check(run.reranker == null || (object(run.reranker) && text(run.reranker.mode)), '精排配置无效。');
  const ids = new Set<string>();
  for (const session of data.sessions) {
    check(object(session), '样本记录无效。');
    check(text(session.sampleId) && session.sampleId.length > 0 && !ids.has(session.sampleId), '样本 ID 缺失或重复。');
    ids.add(session.sampleId);
    const prefix = `样本 ${session.sampleId}`;
    check(text(session.scenario) && typeof session.hit === 'boolean' && rank(session.firstHitTurn) && rank(session.bestRank), `${prefix} 的评测结果无效。`);
    check(text(session.diagnosis) && text(session.diagnosisReason), `${prefix} 缺少诊断说明。`);
    const target = session.target;
    check(object(target) && text(target.parentAsin) && text(target.title) && text(target.category)
      && nullableNumber(target.price) && nullableNumber(target.rating), `${prefix} 的目标商品信息无效。`);
    check(Array.isArray(session.turns) && session.turns.length > 0, `${prefix} 没有对话 Trace。`);
    const turns = new Set<number>();
    for (const turn of session.turns) {
      check(object(turn) && integer(turn.turn) && turn.turn > 0 && !turns.has(turn.turn), `${prefix} 的轮次无效或重复。`);
      turns.add(turn.turn);
      check(text(turn.userMessage) && text(turn.semanticQuery) && text(turn.diagnosis) && text(turn.reason)
        && number(turn.latencyMs) && turn.latencyMs >= 0 && typeof turn.evaluationActive === 'boolean'
        && typeof turn.relaxed === 'boolean', `${prefix} 第 ${turn.turn} 轮的信息不完整。`);
      check(Array.isArray(turn.constraints) && turn.constraints.every(object), `${prefix} 的约束格式无效。`);
      check(turn.agentMessage === undefined || text(turn.agentMessage), `${prefix} 的回复格式无效。`);
      check(turn.error == null || text(turn.error), `${prefix} 的错误信息格式无效。`);
      check(turn.recommendedAsins === undefined || (Array.isArray(turn.recommendedAsins) && turn.recommendedAsins.every(text)), `${prefix} 的推荐列表格式无效。`);
      check(Array.isArray(turn.stages) && turn.stages.length === stageNames.length, `${prefix} 缺少排序阶段。`);
      for (const [i, stage] of turn.stages.entries()) {
        check(object(stage) && stage.name === stageNames[i] && text(stage.label)
          && (stage.count === null || integer(stage.count)) && rank(stage.targetRank)
          && ['present', 'absent', 'unknown'].includes(String(stage.status))
          && (stage.signal === null || object(stage.signal))
          && (stage.snapshotLimit === undefined || integer(stage.snapshotLimit)), `${prefix} 的阶段数据无效。`);
        check((stage.status === 'present') === (stage.targetRank !== null), `${prefix} 的目标排名与状态矛盾。`);
      }
      check(turn.nodeTrace === undefined || (Array.isArray(turn.nodeTrace) && turn.nodeTrace.every(node =>
        object(node) && Array.isArray(node.names) && node.names.every(text) && object(node.updates))), `${prefix} 的节点更新格式无效。`);
    }
  }
  return data as Diagnostics;
}
