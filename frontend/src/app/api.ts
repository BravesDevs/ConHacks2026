import type { AnalysisResult, ScanConfig, TerraformFileMap, PipelineChange, ResourceRecord } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const GITHUB_API = 'https://api.github.com';

function parseRepoUrl(repoUrl: string): { owner: string; name: string } {
  const clean = repoUrl.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '');
  const [owner = '', name = ''] = clean.split('/');
  return { owner, name };
}

function githubHeaders(token: string) {
  return {
    Authorization: `token ${token}`,
    Accept: 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
  };
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

const HARDCODED_TF_PATH = 'terraform/sample/main_hardcoded.tf';

// Fetch only the hardcoded terraform sample file from the GitHub repo.
export async function fetchTerraformFiles(config: ScanConfig): Promise<TerraformFileMap> {
  const { owner, name } = parseRepoUrl(config.repoUrl);
  const headers = githubHeaders(config.githubToken);
  const branch = config.branch || 'main';

  const files: TerraformFileMap['files'] = {};

  const contentRes = await fetch(
    `${GITHUB_API}/repos/${owner}/${name}/contents/${HARDCODED_TF_PATH}?ref=${branch}`,
    { headers }
  );
  if (!contentRes.ok) throw new Error(`GitHub fetch failed for ${HARDCODED_TF_PATH}: ${contentRes.status}`);
  const data = await contentRes.json();
  files[HARDCODED_TF_PATH] = {
    path: HARDCODED_TF_PATH,
    content: atob(data.content.replace(/\n/g, '')),
    sha: data.sha,
  };

  return { files };
}

export async function runPipeline(
  config: Pick<ScanConfig, 'githubToken' | 'repoUrl' | 'branch'>
): Promise<{ runId: string; steps: string[]; errors: string[]; completedAt: string; changes?: PipelineChange[] }> {
  const { owner, name } = parseRepoUrl(config.repoUrl ?? '');
  const res = await fetch(`${BASE_URL}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      github_token: config.githubToken ?? '',
      repo_owner: owner,
      repo_name: name,
      branch: config.branch ?? 'main',
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`runPipeline failed: ${res.status} — ${body}`);
  }
  return res.json();
}

// Commit each changed file to a new branch via the backend, then open a PR.
export async function createPipelinePR(
  config: ScanConfig,
  changes: PipelineChange[]
): Promise<{ prUrl: string }> {
  const { owner, name } = parseRepoUrl(config.repoUrl);
  const base = config.branch || 'main';
  const bearerHeaders = {
    'Authorization': `Bearer ${config.githubToken}`,
    'Content-Type': 'application/json',
  };

  // Commit the first changed file — backend creates an infrabott/* branch automatically
  const first = changes[0];
  const fileRes = await fetch(`${BASE_URL}/github/repos/${owner}/${name}/files/${first.filePath}`, {
    method: 'PUT',
    headers: bearerHeaders,
    body: JSON.stringify({
      content: first.content,
      message: `InfraLens: ${first.description || 'Apply cost optimization recommendations'}`,
    }),
  });
  if (!fileRes.ok) {
    const err = await fileRes.text().catch(() => '');
    throw new Error(`Failed to commit file: ${fileRes.status} — ${err}`);
  }
  const { branch: head } = await fileRes.json();

  // Open the PR via the backend
  const prRes = await fetch(`${BASE_URL}/github/pull-requests`, {
    method: 'POST',
    headers: bearerHeaders,
    body: JSON.stringify({ owner, repo: name, head, base }),
  });
  if (!prRes.ok) {
    const err = await prRes.text().catch(() => '');
    throw new Error(`Failed to create PR: ${prRes.status} — ${err}`);
  }
  return { prUrl: (await prRes.json()).pr_url };
}

// Parse a backend-generated diff ("# file\n-old\n+new") into its parts.
function parseTerraformDiff(diff: string): { file: string; remove: string; add: string } | null {
  const lines = diff.split('\n');
  const fileLine = lines.find(l => l.startsWith('# '));
  const removeLine = lines.find(l => l.startsWith('-'));
  const addLine = lines.find(l => l.startsWith('+'));
  if (!fileLine || !removeLine || !addLine) return null;
  return {
    file: fileLine.slice(2).trim(),
    remove: removeLine.slice(1).trim(),
    add: addLine.slice(1).trim(),
  };
}

// Build PipelineChange[] from analysis resources by fetching the actual files from
// GitHub and applying each diff as a line-level text replacement.
export async function buildChangesFromResources(
  config: ScanConfig,
  resources: ResourceRecord[]
): Promise<PipelineChange[]> {
  // Extract old→new replacements from each resource diff
  const replacements: Array<{ remove: string; add: string; label: string }> = [];
  for (const r of resources) {
    if (!r.terraformDiff) continue;
    const parsed = parseTerraformDiff(r.terraformDiff);
    if (parsed) replacements.push({ remove: parsed.remove, add: parsed.add, label: `${r.name}: ${parsed.remove} → ${parsed.add}` });
  }
  if (replacements.length === 0) return [];

  // Walk the whole repo and check every .tf / .tfvars file line by line
  const { owner, name } = parseRepoUrl(config.repoUrl);
  const headers = githubHeaders(config.githubToken);
  const branch = config.branch || 'main';

  const treeRes = await fetch(
    `${GITHUB_API}/repos/${owner}/${name}/git/trees/${branch}?recursive=1`,
    { headers }
  );
  if (!treeRes.ok) throw new Error(`GitHub tree fetch failed: ${treeRes.status}`);
  const entries = ((await treeRes.json()).tree as Array<{ path: string; type: string }>)
    .filter(f => f.type === 'blob' && (f.path.endsWith('.tf') || f.path.endsWith('.tfvars')));

  const changes: PipelineChange[] = [];
  await Promise.all(entries.map(async entry => {
    const res = await fetch(
      `${GITHUB_API}/repos/${owner}/${name}/contents/${entry.path}?ref=${branch}`,
      { headers }
    ).catch(() => null);
    if (!res?.ok) return;
    const original = atob((await res.json()).content.replace(/\n/g, ''));

    const labels: string[] = [];
    const updatedLines = original.split('\n').map(line => {
      for (const rep of replacements) {
        if (line.includes(rep.remove)) {
          labels.push(rep.label);
          return line.replace(rep.remove, rep.add);
        }
      }
      return line;
    });

    const updated = updatedLines.join('\n');
    if (updated !== original) {
      changes.push({ filePath: entry.path, content: updated, description: labels.join('; ') });
    }
  }));

  return changes;
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
