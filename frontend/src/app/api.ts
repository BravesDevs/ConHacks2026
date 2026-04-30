import type { AnalysisResult, ScanConfig } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function parseRepoUrl(repoUrl: string): { owner: string; name: string } {
  const clean = repoUrl.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '');
  const [owner = '', name = ''] = clean.split('/');
  return { owner, name };
}

export async function fetchAnalysis(_config: ScanConfig): Promise<AnalysisResult> {
  const res = await fetch(`${BASE_URL}/api/recommendations`);
  if (!res.ok) throw new Error(`fetchAnalysis failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(message: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: message }),
  });
  if (!res.ok) throw new Error(`chat failed: ${res.status}`);
  const data = await res.json();
  return data.answer ?? '';
}

export async function runPipeline(
  config?: Pick<ScanConfig, 'githubToken' | 'repoUrl' | 'branch'>
): Promise<{ runId: string; steps: string[]; errors: string[]; completedAt: string }> {
  const { owner, name } = parseRepoUrl(config?.repoUrl ?? '');
  const res = await fetch(`${BASE_URL}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      github_token: config?.githubToken ?? '',
      repo_owner: owner,
      repo_name: name,
      branch: config?.branch ?? 'main',
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`runPipeline failed: ${res.status} — ${body}`);
  }
  return res.json();
}

export async function approveRecommendation(
  _resourceId: string,
  config: Pick<ScanConfig, 'repoUrl' | 'branch'>
): Promise<{ prUrl: string }> {
  const [owner, repo] = config.repoUrl
    .replace(/^https?:\/\/github\.com\//, '')
    .split('/');
  const res = await fetch(`${BASE_URL}/github/pull-requests`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${(window as any).__githubToken ?? ''}`,
    },
    body: JSON.stringify({
      repo_owner: owner,
      repo_name: repo,
      base_branch: config.branch || 'main',
      file_path: 'terraform.tfvars',
      content: `# Updated by InfraLens\n`,
    }),
  });
  if (!res.ok) throw new Error(`approveRecommendation failed: ${res.status}`);
  const data = await res.json();
  return { prUrl: data.pr_url };
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
  'We found a cost savings opportunity in your cloud setup.';

export async function fetchSavingsSummary(): Promise<string> {
  try {
    const result = await fetchAnalysis({} as ScanConfig);
    const sorted = [...result.resources].sort(
      (a, b) => (b.currentCost - b.optimizedCost) - (a.currentCost - a.optimizedCost)
    );
    const top = sorted[0];
    if (!top) return DEMO_SAVINGS_SUMMARY;

    const saved = Math.round(top.currentCost - top.optimizedCost);
    const reason = top.recommendation?.trim() || `downsize ${top.name}`;
    return `${reason} (about ${saved} dollars per month).`;
  } catch (err) {
    console.warn('fetchSavingsSummary fell back to demo:', err);
    return DEMO_SAVINGS_SUMMARY;
  }
}

export async function triggerSavingsCall(args: {
  phoneNumber: string;
  summary: string;
  customerName?: string;
  githubToken?: string;
  repoUrl?: string;
  branch?: string;
}): Promise<{ call_id: string; call_sid: string }> {
  const res = await fetch(`${API_BASE}/voice/call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: args.phoneNumber,
      savings_summary: args.summary,
      customer_name: args.customerName,
      github_token: args.githubToken,
      repo_url: args.repoUrl,
      branch: args.branch,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`call failed: ${res.status} ${text}`);
  }
  return res.json();
}
