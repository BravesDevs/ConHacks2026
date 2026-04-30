import type { AnalysisResult, ScanConfig } from './types';
import { analysisResult } from './mockData';

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms));
}

export async function fetchAnalysis(_config: ScanConfig): Promise<AnalysisResult> {
  await delay(200);
  return analysisResult;
}

export async function sendChatMessage(message: string): Promise<string> {
  const res = await fetch('/api/snowflake/v2/cortex/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer Lorem-proident-sint-et',
    },
    body: JSON.stringify({ question: message }),
  });
  if (!res.ok) throw new Error(`Chat error: ${res.status}`);
  const data = await res.json();
  return data.answer ?? 'No response from Cortex.';
}

export async function approveRecommendation(
  resourceId: string,
  config: Pick<ScanConfig, 'repoUrl' | 'branch'>
): Promise<{ prUrl: string }> {
  await delay(1500);
  const prNumber = Math.floor(Math.random() * 100) + 1;
  const base = config.repoUrl.replace(/^https?:\/\/github\.com\//, '');
  return { prUrl: `https://github.com/${base}/pull/${prNumber}` };
}

const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE_URL ?? 'http://localhost:8000';

interface CortexSummaryRow {
  RESOURCE_ID?: string;
  EXPLANATION?: string;
  resource_id?: string;
  explanation?: string;
}

const DEMO_SAVINGS_SUMMARY =
  'We found that two of your DigitalOcean droplets in NYC3 have averaged ' +
  'about 12 percent CPU usage over the past 30 days. Downsizing them from ' +
  '4-vCPU to 2-vCPU would save you roughly 240 dollars per month with no ' +
  'expected impact on performance.';

export async function fetchSavingsSummary(_maxItems = 3): Promise<string> {
  // Demo: skip Cortex (auth-gated) and return a canned summary.
  return DEMO_SAVINGS_SUMMARY;
}

export async function triggerSavingsCall(args: {
  phoneNumber: string;
  summary: string;
  customerName?: string;
}): Promise<{ call_id: string; call_sid: string }> {
  const res = await fetch(`${API_BASE}/voice/call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: args.phoneNumber,
      savings_summary: args.summary,
      customer_name: args.customerName,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`call failed: ${res.status} ${text}`);
  }
  return res.json();
}
