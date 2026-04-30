import type { AnalysisResult, ScanConfig } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

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
