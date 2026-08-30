'use client';
/* oxlint-disable next/no-html-link-for-pages -- Vinext beta currently breaks next/link hydration. */

import { useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Bot,
  Boxes,
  Braces,
  CheckCircle2,
  Clipboard,
  Clock3,
  Code2,
  Cpu,
  Database,
  FileJson2,
  Gauge,
  Layers3,
  ListChecks,
  MessageSquareText,
  Play,
  ShieldCheck,
  Target,
  Users,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const catalogModes = [
  {
    id: 'official',
    label: '官方模式',
    products: '50,000',
    sessions: '官方 200',
    source: 'TechJam kit · Amazon Reviews 2023',
    contract: '官方指标',
  },
  {
    id: '50k',
    label: '重抽样 50k',
    products: '50,000',
    sessions: '固定 1,400',
    source: 'Amazon Reviews 2023 · Clothing',
    contract: '兼容指标',
  },
  {
    id: '200k',
    label: '扩容 200k',
    products: '200,000',
    sessions: '同一批 1,400',
    source: 'Amazon Reviews 2023 · Clothing scale',
    contract: '兼容指标',
  },
  {
    id: '500k',
    label: '跨品类 500k',
    products: '500,000',
    sessions: '同一批 1,400',
    source: 'Amazon Reviews 2023 · Cross-category',
    contract: '兼容指标',
  },
];

const flowSteps = [
  { icon: Database, label: '商品目录', detail: 'Agent 能搜索的候选世界' },
  { icon: FileJson2, label: '会话 JSONL', detail: '每行定义一个隐藏购物任务' },
  { icon: MessageSquareText, label: 'Simulator', detail: '把任务变成动态多轮对话' },
  { icon: Bot, label: 'Shopping Agent', detail: '提问、检索并返回 Top-10' },
  { icon: Gauge, label: 'Evaluator', detail: '对答案、轮次、延迟和模型用量记分' },
];

const sessionSplits = [
  {
    id: 'smoke',
    count: 20,
    label: 'Smoke',
    purpose: '先确认路径、Agent 接口和报告结构能跑通。',
    mix: '8 Buying · 8 Browsing · 3 Override · 1 Boundary',
    color: '#78a8a1',
  },
  {
    id: 'dev',
    count: 200,
    label: 'Dev',
    purpose: '日常开发、调参和回归定位；允许反复使用。',
    mix: '80 Buying · 80 Browsing · 30 Override · 10 Boundary',
    color: '#087f8c',
  },
  {
    id: 'core',
    count: 1000,
    label: 'Core Eval',
    purpose: '固定主成绩集，用于比较不同 Agent 或不同商品规模。',
    mix: '400 Buying · 400 Browsing · 150 Override · 50 Boundary',
    color: '#164b57',
  },
  {
    id: 'challenge',
    count: 200,
    label: 'Challenge',
    purpose: '只看意图改写与边界条件；必须与 Core 分开报告。',
    mix: '100 Override · 100 Boundary · 全部 Hard',
    color: '#e56b55',
  },
];

const jsonFields = [
  {
    id: 'sample_id',
    label: 'sample_id',
    value: 'tcsv1_dev_0001',
    meaning: '这条测试任务的唯一编号，用于连接输入、逐轮 Trace 和最终成绩。',
    visibility: '双方可见的记录 ID',
  },
  {
    id: 'ground_truth',
    label: 'ground_truth.parent_asin',
    value: 'B00TEA446S',
    meaning: 'Evaluator 的标准答案。Simulator 知道它，但绝不能直接暴露给 Agent。',
    visibility: '只对 Simulator / Evaluator 可见',
  },
  {
    id: 'intent_card',
    label: 'intent_card',
    value: 'cotton · Brix · pink',
    meaning: '用户真实需求的结构化版本。它控制后续回答，但不是一次性全部说出来。',
    visibility: '隐藏状态；按对话逐步披露',
  },
  {
    id: 'behavior',
    label: 'behavior',
    value: '第 3 轮改成 brand: Brix',
    meaning: '定义什么时候改口、如何处理 boundary；因此 JSONL 是任务卡，不是固定台词。',
    visibility: 'Simulator 执行，Agent 只看到自然语言',
  },
  {
    id: 'generation_metadata',
    label: 'generation_metadata',
    value: 'official_metric_contract=false',
    meaning: '记录数据来源、split、难度和是否官方，避免把重构成绩写成官方成绩。',
    visibility: '审计与报告可见',
  },
];

const reportSections = [
  { icon: BarChart3, name: 'evaluation', detail: 'Hit@10、MRR、MTTC、Efficiency 与技术分' },
  { icon: ListChecks, name: 'turn_metrics', detail: '真实执行轮数、成功/失败轮数分布' },
  { icon: Clock3, name: 'latency', detail: 'Agent、用户生成和整场会话耗时' },
  { icon: Cpu, name: 'model_usage', detail: '模型、API 调用、tokens、fallback 与成本状态' },
  { icon: Layers3, name: 'mode_specific_metrics', detail: '按场景拆分或 realistic 约束满足情况' },
];

const jsonPreviewLines = [
  { field: 'sample_id', text: '"sample_id": "tcsv1_dev_0001"' },
  { field: null, text: '"scenario_type": "intent_override"' },
  { field: 'ground_truth', text: '"ground_truth": {"parent_asin": "B00TEA446S"}' },
  { field: 'intent_card', text: '"intent_card": {"hard_constraints": ["cotton", "Brix", "pink"]}' },
  { field: 'behavior', text: '"behavior": {"override": {"turn": 3}}' },
  { field: 'generation_metadata', text: '"generation_metadata": {"official_metric_contract": false}' },
];

const runCommand = [
  'uv run --project user-simulator user-simulator run `',
  '  --preset techjam_compatible_resampled_50k `',
  '  --sessions-path user-simulator/data/derived/techjam_compatible_scale_v1/sessions/smoke_20.jsonl `',
  '  --output runs/compatible_50k_smoke.json `',
  '  --report-output runs/compatible_50k_smoke.md',
].join('\n');

export default function EvaluatorGuidePage() {
  const [selectedMode, setSelectedMode] = useState('50k');
  const [selectedSplit, setSelectedSplit] = useState('core');
  const [selectedField, setSelectedField] = useState('ground_truth');
  const [copied, setCopied] = useState(false);
  const mode = catalogModes.find((item) => item.id === selectedMode)!;
  const split = sessionSplits.find((item) => item.id === selectedSplit)!;
  const field = jsonFields.find((item) => item.id === selectedField)!;

  async function copyCommand() {
    await navigator.clipboard.writeText(runCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <main className="guide-shell">
      <header className="guide-nav">
        <a href="/" className="guide-back">
          <ArrowLeft aria-hidden="true" />
          返回 Trace Lab
        </a>
        <div className="guide-wordmark">
          <span>SHOPPING EVAL LAB</span>
          <strong>Evaluator 使用指南</strong>
        </div>
        <Badge variant="outline">面向算法与 Agent 开发</Badge>
      </header>

      <section className="guide-hero">
        <div className="guide-hero-copy">
          <p className="guide-kicker">先建立一个正确的心智模型</p>
          <h1>
            JSONL 不是商品库，
            <span>它是一叠给模拟用户的“秘密任务卡”。</span>
          </h1>
          <p>
            商品目录决定 Agent 要从多大的候选世界里找答案；会话 JSONL
            决定模拟用户想买什么、什么时候透露条件；Evaluator 则观察 Agent
            是否在 Top-10 中找到正确商品，以及用了多少轮、多少时间和多少模型调用。
          </p>
          <div className="guide-principles">
            <span><Boxes /> 商品数量 ≠ 会话数量</span>
            <span><Target /> 一条 JSONL = 一个测试任务</span>
            <span><ShieldCheck /> 官方与兼容成绩分开</span>
          </div>
        </div>
        <Card className="guide-demo-card">
          <CardContent>
            <div className="guide-demo-head">
              <div>
                <p>选择候选商品规模</p>
                <strong>{mode.label}</strong>
              </div>
              <Database aria-hidden="true" />
            </div>
            <div className="guide-mode-tabs" role="tablist" aria-label="商品规模">
              {catalogModes.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={item.id === selectedMode ? 'default' : 'outline'}
                  onClick={() => setSelectedMode(item.id)}
                  role="tab"
                  aria-selected={item.id === selectedMode}
                >
                  {item.id === 'official' ? '官方' : item.id}
                </Button>
              ))}
            </div>
            <dl className="guide-mode-facts">
              <div><dt>商品候选数</dt><dd>{mode.products}</dd></div>
              <div><dt>测试会话</dt><dd>{mode.sessions}</dd></div>
              <div><dt>商品来源</dt><dd>{mode.source}</dd></div>
              <div><dt>成绩标签</dt><dd>{mode.contract}</dd></div>
            </dl>
            <div className="guide-mode-note">
              <CheckCircle2 aria-hidden="true" />
              {selectedMode === 'official'
                ? '用于核对官方 evaluator；保持官方 10 轮、Top-10 和精确 parent_asin 规则。'
                : '50k、200k、500k 使用同一批重构任务，便于单独观察商品池变大带来的检索难度。'}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="guide-section guide-flow-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">END-TO-END FLOW</p>
            <h2>一条会话如何变成一行成绩</h2>
          </div>
          <p>沿着箭头看：输入负责定义世界和任务，运行时产生对话，最后才计算指标。</p>
        </div>
        <div className="guide-flow" aria-label="Evaluator 完整数据流">
          {flowSteps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div className="guide-flow-unit" key={step.label}>
                <div className="guide-flow-card">
                  <span><Icon aria-hidden="true" /></span>
                  <strong>{step.label}</strong>
                  <p>{step.detail}</p>
                </div>
                {index < flowSteps.length - 1 && (
                  <ArrowRight className="guide-flow-arrow" aria-hidden="true" />
                )}
              </div>
            );
          })}
        </div>
        <div className="guide-terminology-note">
          <FileJson2 />
          <div><strong>准确说法</strong><p>Session generator 生成“输入会话 JSONL”；Evaluator 读取这些任务并生成“结果 JSON / Markdown”。Evaluator 本身不会把商品目录自动变成会话。</p></div>
        </div>
      </section>

      <section className="guide-section guide-concepts">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">TWO INDEPENDENT AXES</p>
            <h2>商品规模和会话规模，分别控制不同难度</h2>
          </div>
          <p>商品越多，检索和排序越难；会话越多，覆盖面和统计稳定性越高。两者不能互相替代。</p>
        </div>
        <div className="guide-axis-grid">
          <Card className="guide-axis-card catalog-axis">
            <CardContent>
              <div className="guide-axis-title"><Database /><div><span>候选世界</span><h3>Catalog 商品目录</h3></div></div>
              <div className="guide-scale-bars" aria-label="商品规模对比">
                {[50000, 200000, 500000].map((count) => (
                  <div key={count}>
                    <span>{count / 1000}k</span>
                    <i style={{ width: `${Math.max(18, (count / 500000) * 100)}%` }} />
                  </div>
                ))}
              </div>
              <p>同一条任务放入更大的目录，目标商品不变，但干扰候选更多。这样才能测出召回与精排是否能扩展。</p>
            </CardContent>
          </Card>
          <Card className="guide-axis-card session-axis">
            <CardContent>
              <div className="guide-axis-title"><Users /><div><span>测试覆盖</span><h3>Session 会话任务</h3></div></div>
              <div className="guide-session-number"><strong>1,400</strong><span>唯一主会话</span></div>
              <div className="guide-session-stack"><i style={{ width: '14.3%' }} /><i style={{ width: '71.4%' }} /><i style={{ width: '14.3%' }} /></div>
              <p>200 Dev + 1,000 Core + 200 Challenge。20 条 Smoke 来自 Dev，是快速子集，不应再加进 1,400。</p>
            </CardContent>
          </Card>
        </div>
        <div className="guide-warning-grid">
          <div><strong>50k 商品 + 1,000 会话</strong><span>运行 1,000 个目标任务，每次都从 50k 商品中检索。</span></div>
          <div><strong>500k 商品 + 同一 1,000 会话</strong><span>任务完全不变，只增加干扰商品，结果才可公平比较。</span></div>
        </div>
      </section>

      <section className="guide-section guide-splits-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">SESSION SUITE</p>
            <h2>先选“跑多少条”，再选“在哪个商品池跑”</h2>
          </div>
          <p>开发阶段从 Smoke 开始；确认流程正常后再跑 Dev、Core，最后单独跑 Challenge。</p>
        </div>
        <div className="guide-split-layout">
          <div className="guide-split-tabs" role="tablist" aria-label="会话集合">
            {sessionSplits.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={selectedSplit === item.id}
                onClick={() => setSelectedSplit(item.id)}
                className={selectedSplit === item.id ? 'active' : ''}
              >
                <span style={{ background: item.color }} />
                <strong>{item.label}</strong>
                <b>{item.count}</b>
              </button>
            ))}
          </div>
          <Card className="guide-split-detail">
            <CardContent>
              <div className="guide-split-top">
                <div><span>当前选择</span><h3>{split.label}</h3></div>
                <strong style={{ color: split.color }}>{split.count}</strong>
              </div>
              <p>{split.purpose}</p>
              <div className="guide-mix"><span>场景构成</span><strong>{split.mix}</strong></div>
              <div className="guide-file-path">
                <FileJson2 />
                <code>{split.id === 'core' ? 'eval_core_1000.jsonl' : split.id === 'challenge' ? 'eval_challenge_200.jsonl' : `${split.id}_${split.count}.jsonl`}</code>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="guide-section guide-json-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">JSONL ANATOMY</p>
            <h2>点击字段，看它在测试里负责什么</h2>
          </div>
          <p>JSONL 的每一行都是一个完整 JSON 对象；Evaluator 一行一行加载，所以可以稳定分片、并行与恢复。</p>
        </div>
        <div className="guide-json-grid">
          <Card className="guide-code-card">
            <CardContent>
              <div className="guide-code-head"><span><Braces /> dev_200.jsonl · line 1</span><Badge variant="outline">interactive goal card</Badge></div>
              <pre aria-label="一条会话 JSONL 示例"><code>{'{\n'}{jsonPreviewLines.map((line, index) => <span key={line.text}>  {line.field ? <button onClick={() => setSelectedField(line.field!)} className={selectedField === line.field ? 'active' : ''}>{line.text}</button> : line.text}{index < jsonPreviewLines.length - 1 ? ',' : ''}{'\n'}</span>)}{'}'}</code></pre>
            </CardContent>
          </Card>
          <div className="guide-field-panel">
            <div className="guide-field-tabs">
              {jsonFields.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedField(item.id)} className={selectedField === item.id ? 'active' : ''}>{item.label}</button>
              ))}
            </div>
            <Card className="guide-field-detail">
              <CardContent>
                <Badge>{field.label}</Badge>
                <h3>{field.meaning}</h3>
                <div><span>本条示例</span><code>{field.value}</code></div>
                <div><span>可见性</span><strong>{field.visibility}</strong></div>
              </CardContent>
            </Card>
            <div className="guide-secret-note"><ShieldCheck /><span><strong>防作弊边界：</strong>Agent 只收到当前用户话语、允许暴露的 profile 和 Top-K 设置；隐藏 target 与未披露约束留在 Simulator 内部。</span></div>
          </div>
        </div>
      </section>

      <section className="guide-section guide-runtime-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">RUNTIME LOOP</p>
            <h2>Evaluator 不是问一次就结束，而是逐轮观察</h2>
          </div>
          <p>每一轮都保存可见输入、Agent 输出、推荐列表、延迟与 Trace；命中后记录 first hit turn，未命中最多跑 10 轮。</p>
        </div>
        <div className="guide-loop">
          <div className="guide-loop-step"><span>1</span><div><strong>Simulator 发一句用户话语</strong><p>根据 intent card 和当前已披露状态动态生成。</p></div></div>
          <div className="guide-loop-step"><span>2</span><div><strong>Agent 回答并给 Top-10</strong><p>可继续追问，也可以返回推荐商品 parent_asin。</p></div></div>
          <div className="guide-loop-step"><span>3</span><div><strong>Evaluator 检查目标排名</strong><p>目标进入 Top-10 才算 hit；同时保存 rank 与 latency。</p></div></div>
          <div className="guide-loop-step"><span>4</span><div><strong>未命中则进入下一轮</strong><p>Simulator 根据提问、override 或 boundary 状态继续回答。</p></div></div>
        </div>
        <div className="guide-equation">
          <div><span>Hit@10</span><strong>命中会话数 ÷ 总会话数</strong></div>
          <div><span>MRR</span><strong>平均 1 ÷ 首次命中排名</strong></div>
          <div><span>MTTC</span><strong>平均首次命中轮次；miss 记 11</strong></div>
          <div><span>Technical Score</span><strong>0.50 Hit + 0.30 MRR + 0.20 Efficiency</strong></div>
        </div>
      </section>

      <section className="guide-section guide-report-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">UNIFIED OUTPUT</p>
            <h2>最终 JSON 报告必须能回答五类问题</h2>
          </div>
          <p>`sessions` 继续保存逐会话、逐轮证据；下面五个区块负责汇总，不能只留下一个总分。</p>
        </div>
        <div className="guide-report-grid">
          {reportSections.map((item, index) => {
            const Icon = item.icon;
            return <div key={item.name}><span>{String(index + 1).padStart(2, '0')}</span><Icon /><code>{item.name}</code><p>{item.detail}</p></div>;
          })}
        </div>
        <div className="guide-contract-compare">
          <div className="official"><Badge>官方 TechJam</Badge><strong>mode=techjam</strong><code>official_metric_contract=true</code><p>官方会话、官方目标、官方意义上的成绩。</p></div>
          <div className="compatible"><Badge variant="outline">重构兼容模式</Badge><strong>mode=techjam_compatible</strong><code>official_metric_contract=false</code><p>公式相似，但数据不是官方，必须写成扩展压力测试。</p></div>
        </div>
      </section>

      <section className="guide-section guide-run-section">
        <div className="guide-section-heading">
          <div>
            <p className="guide-kicker">FIRST SAFE RUN</p>
            <h2>队友第一次使用，照这个顺序</h2>
          </div>
          <p>先验证数据路径，再跑 20 条 Smoke。没有成功报告前，不要直接启动 1,000 条或 500k 商品池。</p>
        </div>
        <div className="guide-run-grid">
          <ol>
            <li><span>01</span><div><strong>准备 catalog</strong><p>从 Release 解压或运行 nested catalog builder；大 JSONL 不在 Git 中。</p></div></li>
            <li><span>02</span><div><strong>检查 preset 路径</strong><p>50k / 200k / 500k 配置分别指向对应目录，但会话可以保持同一份。</p></div></li>
            <li><span>03</span><div><strong>先跑 smoke_20</strong><p>确认 Agent 接口、Top-10、逐轮 Trace 和五段报告都存在。</p></div></li>
            <li><span>04</span><div><strong>保存并比较</strong><p>固定代码 commit、catalog hash、session hash、模型状态和运行参数。</p></div></li>
          </ol>
          <Card className="guide-command-card">
            <CardContent>
              <div><span><Code2 /> PowerShell · repo root</span><Button size="sm" variant="outline" onClick={copyCommand}><Clipboard />{copied ? '已复制' : '复制'}</Button></div>
              <pre><code>{runCommand}</code></pre>
              <p><Play /> 默认 template verbalizer 不会调用 DeepSeek。只有明确启用 LLM 时才应记录 provider、model、calls、tokens 和 fallback。</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="guide-section guide-checklist-section">
        <div className="guide-checklist-copy">
          <p className="guide-kicker">HANDOFF CHECKLIST</p>
          <h2>交给另一个 Agent 时，让它先确认这些文件</h2>
          <p>这组路径是当前仓库里的权威入口。Agent 不需要从聊天记录猜数据含义。</p>
        </div>
        <div className="guide-path-list">
          <code>user-simulator/data/.../sessions/README.md <span>数据用途与边界</span></code>
          <code>user-simulator/data/.../sessions/manifest.json <span>数量、分布与 SHA-256</span></code>
          <code>user-simulator/data/.../sessions/session_index.csv <span>1,400 条逐项索引</span></code>
          <code>user-simulator/configs/techjam_compatible_*.yaml <span>50k / 200k / 500k 入口</span></code>
          <code>user-simulator/src/user_simulator/metrics.py <span>Evaluator 公式与报告结构</span></code>
          <code>docs/TEST_TRACE_VISUALIZATION_RUNBOOK.md <span>Trace 生成与诊断</span></code>
        </div>
      </section>

      <footer className="guide-footer">
        <div><Target /><strong>记住：</strong>Catalog 定义“从哪里找”，JSONL 定义“找什么”，Evaluator 定义“怎么算找到”。</div>
        <a href="/">打开标准答案流失诊断 <ArrowRight /></a>
      </footer>
    </main>
  );
}
