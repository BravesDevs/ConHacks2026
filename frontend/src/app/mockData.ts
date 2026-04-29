import type { AnalysisResult, ResourceRecord } from './types';

const resources: ResourceRecord[] = [
  {
    id: 'do-web-prod',
    name: 'web-prod-01',
    provider: 'DigitalOcean',
    type: 'Droplet',
    equivalentCategory: 'Compute',
    equivalentResourceId: 'aws-ec2-web',
    region: 'nyc3',
    currentCost: 148,
    optimizedCost: 92,
    cpuUsage: 26,
    memoryUsage: 61,
    networkUsageGb: 142,
    utilizationScore: 42,
    trendCurrent:   [128,131,134,137,139,141,143,144,145,146,147,148],
    trendOptimized: [112,109,107,105,103,102,100,98,96,95,93,92],
    recommendation: 'web-prod-01 is provisioned with a 4vCPU/8GB droplet but shows consistent CPU utilization below 30% and memory at 61%. Peak utilization correlates with scheduled batch jobs that could be offloaded to the background worker pool. Downsizing to s-2vcpu-4gb will reduce monthly cost by $56 while accommodating current sustained load patterns.',
    terraformDiff: `resource "digitalocean_droplet" "web_prod_01" {
  name   = "web-prod-01"
  region = "nyc3"
  image  = "ubuntu-22-04-x64"
- size   = "s-4vcpu-8gb"
+ size   = "s-2vcpu-4gb"
  tags   = ["production", "web"]
}`,
    terraformFile: 'infra/compute.tf',
    severity: 'high',
    approvalStatus: 'pending',
  },
  {
    id: 'aws-ec2-web',
    name: 'ec2-web-prod',
    provider: 'AWS',
    type: 'EC2 Instance',
    equivalentCategory: 'Compute',
    equivalentResourceId: 'do-web-prod',
    region: 'us-east-1',
    currentCost: 165,
    optimizedCost: 108,
    cpuUsage: 22,
    memoryUsage: 58,
    networkUsageGb: 189,
    utilizationScore: 38,
    trendCurrent:   [148,151,154,157,159,161,162,163,163,164,165,165],
    trendOptimized: [125,122,119,117,115,113,112,111,110,110,109,108],
    recommendation: 'ec2-web-prod mirrors the DigitalOcean web-prod-01 workload with near-identical traffic patterns. The m5.large instance is over-provisioned by the same margin. Migrating to t3.medium with Compute Savings Plan pricing reduces cost by 35% and aligns provisioning with measured utilization.',
    terraformDiff: `resource "aws_instance" "web_prod" {
  ami           = "ami-0c55b159cbfafe1f0"
- instance_type = "m5.large"
+ instance_type = "t3.medium"
  tags = {
    Name        = "ec2-web-prod"
    Environment = "production"
  }
}`,
    terraformFile: 'infra/aws-compute.tf',
    severity: 'high',
    approvalStatus: 'pending',
  },
  {
    id: 'do-worker-prod',
    name: 'worker-prod-02',
    provider: 'DigitalOcean',
    type: 'Droplet',
    equivalentCategory: 'Compute',
    region: 'tor1',
    currentCost: 88,
    optimizedCost: 64,
    cpuUsage: 18,
    memoryUsage: 39,
    networkUsageGb: 44,
    utilizationScore: 28,
    trendCurrent:   [78,79,80,81,82,83,84,85,85,86,87,88],
    trendOptimized: [70,69,69,68,68,67,67,66,66,65,65,64],
    recommendation: 'The background worker pool autoscaler floor is set to 3 nodes but median active capacity is 1.8 nodes over the last 90 days. Reducing the minimum node count and right-sizing the remaining instances will save $24/month without affecting job throughput at current queue depths.',
    severity: 'medium',
    approvalStatus: 'pending',
  },
  {
    id: 'do-pg-main',
    name: 'pg-main',
    provider: 'DigitalOcean',
    type: 'Managed Database',
    equivalentCategory: 'Database',
    equivalentResourceId: 'aws-rds-backup',
    region: 'nyc3',
    currentCost: 122,
    optimizedCost: 94,
    cpuUsage: 34,
    memoryUsage: 57,
    networkUsageGb: 28,
    utilizationScore: 49,
    trendCurrent:   [116,117,118,119,119,120,120,121,121,121,122,122],
    trendOptimized: [102,101,101,100,100,99,98,97,97,96,95,94],
    recommendation: 'pg-main is running on db-s-4vcpu-8gb but p95 query times are under 12ms and CPU stays below 40% outside of scheduled backup windows. Enabling connection pooling (PgBouncer) and stepping down to db-s-2vcpu-4gb will save $28/month. The backup window should be rescheduled to avoid the recommendation inference job.',
    terraformDiff: `resource "digitalocean_database_cluster" "pg_main" {
  name       = "pg-main"
  engine     = "pg"
  version    = "15"
  region     = "nyc3"
- size       = "db-s-4vcpu-8gb"
+ size       = "db-s-2vcpu-4gb"
  node_count = 1
}

resource "digitalocean_database_connection_pool" "pg_main_pool" {
+ name     = "pg-main-pool"
+ cluster_id = digitalocean_database_cluster.pg_main.id
+ mode     = "transaction"
+ size     = 25
+ db_name  = "defaultdb"
+ user     = "doadmin"
}`,
    terraformFile: 'infra/databases.tf',
    severity: 'high',
    approvalStatus: 'pending',
  },
  {
    id: 'aws-rds-backup',
    name: 'rds-backup',
    provider: 'AWS',
    type: 'RDS Instance',
    equivalentCategory: 'Database',
    equivalentResourceId: 'do-pg-main',
    region: 'us-east-1',
    currentCost: 89,
    optimizedCost: 61,
    cpuUsage: 12,
    memoryUsage: 44,
    networkUsageGb: 8,
    utilizationScore: 31,
    trendCurrent:   [82,83,84,85,86,86,87,87,88,88,89,89],
    trendOptimized: [67,66,65,65,64,64,63,63,62,62,61,61],
    recommendation: 'rds-backup operates as a cross-cloud replica of pg-main and shows consistently low utilization — 12% CPU and 44% memory. Since this instance is read-only disaster recovery, migrating from db.r5.large to db.t3.medium and using Reserved Instance pricing (1yr, no-upfront) reduces cost by 31%.',
    terraformDiff: `resource "aws_db_instance" "rds_backup" {
  identifier        = "rds-backup"
  engine            = "postgres"
  engine_version    = "15"
- instance_class    = "db.r5.large"
+ instance_class    = "db.t3.medium"
  allocated_storage = 100
  multi_az          = false
}`,
    terraformFile: 'infra/aws-databases.tf',
    severity: 'medium',
    approvalStatus: 'pending',
  },
  {
    id: 'do-edge-k8s',
    name: 'edge-k8s',
    provider: 'DigitalOcean',
    type: 'Kubernetes',
    equivalentCategory: 'Kubernetes',
    equivalentResourceId: 'aws-eks-staging',
    region: 'sfo3',
    currentCost: 176,
    optimizedCost: 133,
    cpuUsage: 47,
    memoryUsage: 54,
    networkUsageGb: 312,
    utilizationScore: 58,
    trendCurrent:   [158,161,163,165,167,168,170,171,172,174,175,176],
    trendOptimized: [147,145,144,143,142,141,140,139,138,137,136,133],
    recommendation: 'DOKS cluster edge-k8s has 3 node pools with an average utilization score of 58%. The baseline node pool floor is configured at 3 nodes but the 30-day average active node count is 1.8. Reducing the minimum to 2 nodes and right-sizing the default pool from s-4vcpu-8gb to s-2vcpu-4gb saves $43/month while maintaining headroom for traffic bursts.',
    terraformDiff: `resource "digitalocean_kubernetes_cluster" "edge_k8s" {
  name    = "edge-k8s"
  region  = "sfo3"
  version = "1.29.1-do.0"

  node_pool {
    name       = "default"
-   size       = "s-4vcpu-8gb"
+   size       = "s-2vcpu-4gb"
    node_count = 2
    auto_scale = true
-   min_nodes  = 3
+   min_nodes  = 2
    max_nodes  = 8
  }
}`,
    terraformFile: 'infra/kubernetes.tf',
    severity: 'high',
    approvalStatus: 'pending',
  },
  {
    id: 'aws-eks-staging',
    name: 'eks-staging',
    provider: 'AWS',
    type: 'EKS Cluster',
    equivalentCategory: 'Kubernetes',
    equivalentResourceId: 'do-edge-k8s',
    region: 'us-west-2',
    currentCost: 143,
    optimizedCost: 98,
    cpuUsage: 31,
    memoryUsage: 48,
    networkUsageGb: 221,
    utilizationScore: 44,
    trendCurrent:   [128,130,132,134,135,136,137,138,140,141,142,143],
    trendOptimized: [112,110,109,108,107,106,105,104,103,101,100,98],
    recommendation: 'eks-staging node group is running m5.xlarge on-demand instances with a 44% utilization score. Switching to Spot Instances for the worker node group (with on-demand fallback) and reducing min node count from 3 to 1 for this non-production cluster will cut costs by 31%.',
    severity: 'medium',
    approvalStatus: 'pending',
  },
  {
    id: 'do-spaces-assets',
    name: 'spaces-assets',
    provider: 'DigitalOcean',
    type: 'Storage',
    equivalentCategory: 'Object Storage',
    equivalentResourceId: 'aws-s3-media',
    region: 'ams3',
    currentCost: 41,
    optimizedCost: 28,
    cpuUsage: 0,
    memoryUsage: 0,
    networkUsageGb: 890,
    utilizationScore: 36,
    trendCurrent:   [32,33,33,34,35,36,37,38,39,40,40,41],
    trendOptimized: [31,30,30,30,30,29,29,29,29,28,28,28],
    recommendation: 'spaces-assets holds 890GB of static assets with a wide access distribution. Analysis of object access logs shows 61% of stored data has not been accessed in 90+ days. Enabling lifecycle policies to transition cold objects to the lower-cost archival tier reduces monthly storage cost by $13 with no impact on active content delivery.',
    severity: 'low',
    approvalStatus: 'pending',
  },
  {
    id: 'aws-s3-media',
    name: 's3-media',
    provider: 'AWS',
    type: 'S3 Bucket',
    equivalentCategory: 'Object Storage',
    equivalentResourceId: 'do-spaces-assets',
    region: 'us-east-1',
    currentCost: 57,
    optimizedCost: 38,
    cpuUsage: 0,
    memoryUsage: 0,
    networkUsageGb: 1240,
    utilizationScore: 29,
    trendCurrent:   [46,47,48,50,51,52,53,54,55,55,56,57],
    trendOptimized: [43,43,42,42,41,41,40,40,40,39,39,38],
    recommendation: 'S3 media bucket contains 1.2TB with Intelligent-Tiering disabled. Enabling S3 Intelligent-Tiering and archiving objects with access dates older than 120 days to Glacier Instant Retrieval will save $19/month. Cross-cloud duplication with spaces-assets should be reviewed after Snowflake ingestion confirms both buckets hold the same content.',
    severity: 'low',
    approvalStatus: 'pending',
  },
  {
    id: 'snowflake-wh',
    name: 'finops_wh',
    provider: 'Snowflake',
    type: 'Data Warehouse',
    equivalentCategory: 'Data Warehouse',
    region: 'aws_us_east_1',
    currentCost: 194,
    optimizedCost: 138,
    cpuUsage: 0,
    memoryUsage: 0,
    networkUsageGb: 0,
    utilizationScore: 44,
    trendCurrent:   [148,154,158,163,167,171,174,178,182,186,190,194],
    trendOptimized: [148,147,146,145,145,144,143,142,141,140,139,138],
    recommendation: 'The FinOps warehouse is configured with LARGE size and 10-minute auto-suspend, but query history shows a bimodal distribution: short recommendation reads (avg 3.2s) run at 23% warehouse utilization. Reducing to MEDIUM, enabling auto-resume, and setting auto-suspend to 60 seconds will cut Snowflake credit consumption by ~29% with negligible latency impact on read workloads.',
    terraformDiff: `resource "snowflake_warehouse" "finops_wh" {
  name    = "FINOPS_WH"
  comment = "FinOps cost optimization inference warehouse"
- warehouse_size    = "LARGE"
+ warehouse_size    = "MEDIUM"
- auto_suspend      = 600
+ auto_suspend      = 60
+ auto_resume       = true
  initially_suspended = false
}`,
    terraformFile: 'infra/snowflake.tf',
    severity: 'critical',
    approvalStatus: 'pending',
  },
];

export const analysisResult: AnalysisResult = {
  scannedAt: new Date().toISOString(),
  resources,
};

export const MONTH_LABELS_12 = ['May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr'];
