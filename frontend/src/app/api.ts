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

// Create a GitHub PR with the pipeline's suggested changes.
// Uses the Git Data API to create a commit on a new branch, then opens a PR.
export async function createPipelinePR(
  config: ScanConfig,
  changes: PipelineChange[]
): Promise<{ prUrl: string }> {
  const { owner, name } = parseRepoUrl(config.repoUrl);
  const headers = githubHeaders(config.githubToken);
  const base = config.branch || 'main';
  const head = `infralens/recommendations-${Date.now()}`;

  // Get base branch tip SHA
  const refRes = await fetch(
    `${GITHUB_API}/repos/${owner}/${name}/git/ref/heads/${base}`,
    { headers }
  );
  if (!refRes.ok) throw new Error(`Failed to resolve branch ${base}: ${refRes.status}`);
  const baseSha: string = (await refRes.json()).object.sha;

  // Get base tree SHA from the tip commit
  const commitRes = await fetch(
    `${GITHUB_API}/repos/${owner}/${name}/git/commits/${baseSha}`,
    { headers }
  );
  if (!commitRes.ok) throw new Error(`Failed to fetch commit: ${commitRes.status}`);
  const baseTreeSha: string = (await commitRes.json()).tree.sha;

  // Create a new tree with changed files
  const treeRes = await fetch(`${GITHUB_API}/repos/${owner}/${name}/git/trees`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      base_tree: baseTreeSha,
      tree: changes.map(c => ({
        path: c.filePath,
        mode: '100644',
        type: 'blob',
        content: c.content,
      })),
    }),
  });
  if (!treeRes.ok) throw new Error(`Failed to create tree: ${treeRes.status}`);
  const newTreeSha: string = (await treeRes.json()).sha;

  // Create the commit
  const newCommitRes = await fetch(`${GITHUB_API}/repos/${owner}/${name}/git/commits`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message: 'InfraLens: Apply cost optimization recommendations',
      tree: newTreeSha,
      parents: [baseSha],
    }),
  });
  if (!newCommitRes.ok) throw new Error(`Failed to create commit: ${newCommitRes.status}`);
  const newCommitSha: string = (await newCommitRes.json()).sha;

  // Push as a new branch
  const branchRes = await fetch(`${GITHUB_API}/repos/${owner}/${name}/git/refs`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ref: `refs/heads/${head}`, sha: newCommitSha }),
  });
  if (!branchRes.ok) throw new Error(`Failed to create branch: ${branchRes.status}`);

  // Open the pull request
  const prBody = [
    '## InfraLens Cost Optimization',
    '',
    'Automatically generated by [InfraLens](https://github.com) based on your infrastructure analysis.',
    '',
    '### Changed files',
    ...changes.map(c => `- **${c.filePath}**${c.description ? `: ${c.description}` : ''}`),
    '',
    '> Review carefully before merging.',
  ].join('\n');

  const prRes = await fetch(`${GITHUB_API}/repos/${owner}/${name}/pulls`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      title: 'InfraLens: Cost optimization recommendations',
      body: prBody,
      head,
      base,
    }),
  });
  if (!prRes.ok) {
    const err = await prRes.text().catch(() => '');
    throw new Error(`Failed to create PR: ${prRes.status} — ${err}`);
  }
  return { prUrl: (await prRes.json()).html_url };
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
  // Collect old→new string replacements from all diffs
  const replacements: Array<{ remove: string; add: string; label: string }> = [];
  for (const r of resources) {
    if (!r.terraformDiff) continue;
    const parsed = parseTerraformDiff(r.terraformDiff);
    if (parsed) replacements.push({ remove: parsed.remove, add: parsed.add, label: `${r.name}: ${parsed.remove} → ${parsed.add}` });
  }
  if (replacements.length === 0) return [];

  // Walk the whole repo and grep every .tf / .tfvars file for the old string
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

    let updated = original;
    const labels: string[] = [];
    for (const rep of replacements) {
      if (updated.includes(rep.remove)) {
        updated = updated.replaceAll(rep.remove, rep.add);
        labels.push(rep.label);
      }
    }
    if (updated !== original) changes.push({ filePath: entry.path, content: updated, description: labels.join('; ') });
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
