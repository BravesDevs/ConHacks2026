# Sample DigitalOcean Droplet Metrics (Downsize Candidate)

This is a **sample** metrics snapshot for a single droplet that likely needs downsizing due to consistently low utilization.

## Droplet
- `resource_type`: `droplet`
- `resource_id`: `123456789`
- `name`: `web-prod-01`
- `region`: `nyc3`
- `current_size_slug`: `s-4vcpu-8gb`
- `vcpus`: 4
- `memory_mb`: 8192
- `disk_gb`: 160
- `price_monthly_usd` (approx): 48

## Time window
- `start`: `2026-04-22T00:00:00Z`
- `end`: `2026-04-29T00:00:00Z`
- `step`: `300s` (5m)

## Metrics summary (7d)

### CPU (percent)
- `cpu.usage`:
  - `avg`: **3.2%**
  - `p95`: **9.1%**
  - `max`: **22.4%**
  - Notes: No sustained CPU pressure; spikes are short-lived.

### Memory (bytes)
- `memory.available` (higher is better; indicates free memory):
  - `avg_available_gib`: **6.9 GiB** of 8.0 GiB
  - `p95_available_gib`: **6.2 GiB**
- `memory.used`:
  - `avg_used_gib`: **1.1 GiB**
  - `p95_used_gib`: **1.8 GiB**
  - Notes: Memory use stays low; no evidence of swapping/pressure.

### Disk (percent)
- `disk.usage`:
  - `avg`: **12%**
  - `p95`: **16%**
  - Notes: Plenty of headroom; disk is not a constraint.

### Network (bytes/sec)
- `net.bytes_in`:
  - `avg`: **25 KB/s**
  - `p95`: **110 KB/s**
- `net.bytes_out`:
  - `avg`: **30 KB/s**
  - `p95`: **140 KB/s**
  - Notes: Low steady traffic; no significant bandwidth bursts.

## Heuristic recommendation
- Current size `s-4vcpu-8gb` appears oversized.
- Suggested new size (example): **`s-2vcpu-2gb`** or **`s-2vcpu-4gb`**
  - Rationale:
    - `cpu p95 < 10%` on 4 vCPUs
    - `memory p95 ~ 1.8 GiB` with large free memory throughout the week
    - Disk and network are low

## Example “raw-style” JSON payload (what we’d upload to Snowflake)

```json
{
  "resource_type": "droplet",
  "resource_id": "123456789",
  "name": "web-prod-01",
  "region": "nyc3",
  "current_size_slug": "s-4vcpu-8gb",
  "window": {
    "start": "2026-04-22T00:00:00Z",
    "end": "2026-04-29T00:00:00Z",
    "step_seconds": 300
  },
  "metrics": {
    "cpu_usage_percent": { "avg": 3.2, "p95": 9.1, "max": 22.4 },
    "memory_used_gib": { "avg": 1.1, "p95": 1.8, "max": 2.4 },
    "disk_usage_percent": { "avg": 12.0, "p95": 16.0, "max": 20.0 },
    "net_in_kbps": { "avg": 200.0, "p95": 880.0, "max": 1400.0 },
    "net_out_kbps": { "avg": 240.0, "p95": 1120.0, "max": 1600.0 }
  },
  "recommendation": {
    "suggested_size_slug": "s-2vcpu-4gb",
    "reason": "Consistently low utilization over 7d: CPU p95 < 10%, memory p95 < 2GiB on 8GiB."
  }
}
```
