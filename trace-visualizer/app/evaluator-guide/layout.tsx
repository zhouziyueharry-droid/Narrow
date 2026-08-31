import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Evaluator 使用指南 · Shopping Eval Lab',
  description:
    '理解商品池、会话 JSONL 与购物 Agent 评测报告之间的关系。',
};

export default function EvaluatorGuideLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
