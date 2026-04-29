import type { AnalysisResult, ScanConfig } from './types';
import { analysisResult } from './mockData';

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms));
}

export async function fetchAnalysis(_config: ScanConfig): Promise<AnalysisResult> {
  await delay(200);
  return analysisResult;
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
