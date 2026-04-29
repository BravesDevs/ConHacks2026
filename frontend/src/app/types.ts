export type Provider = 'DigitalOcean' | 'AWS' | 'Snowflake';

export type ResourceType =
  | 'Droplet'
  | 'Managed Database'
  | 'Kubernetes'
  | 'Storage'
  | 'Data Warehouse'
  | 'EC2 Instance'
  | 'RDS Instance'
  | 'EKS Cluster'
  | 'S3 Bucket';

export type EquivalentCategory =
  | 'Compute'
  | 'Database'
  | 'Kubernetes'
  | 'Object Storage'
  | 'Data Warehouse';

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected';
export type ChartType = 'area' | 'bar' | 'line';
export type TimeRange = '1M' | '3M' | '6M' | '1Y';
export type DashboardTab = 'overview' | 'resources' | 'recommendations' | 'terraform';

export interface ResourceRecord {
  id: string;
  name: string;
  provider: Provider;
  type: ResourceType;
  equivalentCategory: EquivalentCategory;
  equivalentResourceId?: string;
  region: string;
  currentCost: number;
  optimizedCost: number;
  cpuUsage: number;
  memoryUsage: number;
  networkUsageGb: number;
  utilizationScore: number;
  trendCurrent: number[];   // 12 months, oldest first
  trendOptimized: number[];
  recommendation: string;
  terraformDiff?: string;
  terraformFile?: string;
  severity: Severity;
  approvalStatus: ApprovalStatus;
}

export interface ScanConfig {
  githubToken: string;
  repoUrl: string;
  branch: string;
  doApiKey: string;
  doProject?: string;
  regionFilter?: string;
}

export interface AnalysisResult {
  scannedAt: string;
  resources: ResourceRecord[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}
