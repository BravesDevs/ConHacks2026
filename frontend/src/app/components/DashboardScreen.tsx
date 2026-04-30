import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  FileCode2,
  RefreshCw,
  Search,
  Server,
  Sparkles,
  ArrowDownRight,
  ArrowUpRight,
  ArrowLeftRight,
  Filter,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {
  DashboardTab,
  Provider,
  ResourceType,
  ChartType,
  TimeRange,
  ScanConfig,
} from '../types';
import { MONTH_LABELS_12 } from '../mockData';
import { fetchAnalysis, runPipeline } from '../api';
import type { AnalysisResult } from '../types';
import RecommendationCard from './RecommendationCard';
import TerraformDiff from './TerraformDiff';

interface DashboardScreenProps {
  config: ScanConfig;
  onRescan: () => void;
}

type RecFilter = 'all' | 'with-diff' | 'pending';

const PROVIDER_COLORS: Record<string, string> = {
  DigitalOcean: '#22d3ee',
  AWS: '#fbbf24',
  Snowflake: '#a78bfa',
};

const TYPE_COLORS: Record<string, string> = {
  Droplet: '#f97316',
  'EC2 Instance': '#fbbf24',
  'Managed Database': '#22d3ee',
  'RDS Instance': '#22d3ee',
  Kubernetes: '#a78bfa',
  'EKS Cluster': '#a78bfa',
  Storage: '#34d399',
  'S3 Bucket': '#34d399',
  'Data Warehouse': '#f87171',
};

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-[#f87171]',
  high:     'bg-[#fbbf24]',
  medium:   'bg-[#f97316]',
  low:      'bg-[#34d399]',
};

const NAV_ITEMS: { id: DashboardTab; label: string; icon: React.ElementType }[] = [
  { id: 'overview',        label: 'OVERVIEW',        icon: BarChart3 },
  { id: 'resources',       label: 'RESOURCES',       icon: Server },
  { id: 'recommendations', label: 'RECOMMENDATIONS', icon: Sparkles },
  { id: 'terraform',       label: 'TERRAFORM',       icon: FileCode2 },
];

function DarkTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-white/10 bg-[#0c1018] p-3 shadow-lg">
      <p className="mb-2 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] text-white/40">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 font-['IBM_Plex_Mono'] text-xs">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: p.color }} />
          <span className="text-white/40">{p.name}</span>
          <span className="text-white/80">${p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardScreen({ config, onRescan }: DashboardScreenProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [providerFilter, setProviderFilter] = useState<'All' | Provider>('All');
  const [typeFilter, setTypeFilter] = useState<'All' | ResourceType>('All');
  const [query, setQuery] = useState('');
  const [selectedResourceId, setSelectedResourceId] = useState('');
  const [chartType, setChartType] = useState<ChartType>('area');
  const [timeRange, setTimeRange] = useState<TimeRange>('6M');
  const [recFilter, setRecFilter] = useState<RecFilter>('all');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  useEffect(() => {
    fetchAnalysis(config)
      .then(result => {
        setAnalysisResult(result);
        if (result.resources.length > 0) setSelectedResourceId(result.resources[0].id);
      })
      .catch(err => {
        console.error('fetchAnalysis failed:', err);
        setFetchError(String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  function handleRunPipeline() {
    setPipelineRunning(true);
    setFetchError(null);
    runPipeline()
      .then(pipelineResult => {
        if (pipelineResult.errors?.length) {
          setFetchError(`Pipeline errors: ${pipelineResult.errors.join(' | ')}`);
        }
        return fetchAnalysis(config);
      })
      .then(result => {
        setAnalysisResult(result);
        if (result.resources.length > 0) setSelectedResourceId(result.resources[0].id);
      })
      .catch(err => setFetchError(String(err)))
      .finally(() => setPipelineRunning(false));
  }

  const allResources = analysisResult?.resources ?? [];

  const filteredResources = useMemo(() => {
    return allResources.filter(r => {
      const pMatch = providerFilter === 'All' || r.provider === providerFilter;
      const tMatch = typeFilter === 'All' || r.type === typeFilter;
      const qMatch = !query.trim() || `${r.name} ${r.provider} ${r.type} ${r.region}`.toLowerCase().includes(query.toLowerCase());
      return pMatch && tMatch && qMatch;
    });
  }, [allResources, providerFilter, typeFilter, query]);

  const selectedResource = filteredResources.find(r => r.id === selectedResourceId) ?? filteredResources[0] ?? null;

  const totals = useMemo(() => {
    const current = filteredResources.reduce((s, r) => s + r.currentCost, 0);
    const optimized = filteredResources.reduce((s, r) => s + r.optimizedCost, 0);
    return { current, optimized, savings: current - optimized, count: filteredResources.length };
  }, [filteredResources]);

  const rangeCount = { '1M': 2, '3M': 3, '6M': 6, '1Y': 12 }[timeRange];
  const monthSlice = MONTH_LABELS_12.slice(-rangeCount);

  const trendData = useMemo(() => {
    return monthSlice.map((month, i) => {
      const idx = 12 - rangeCount + i;
      return {
        month,
        Current: filteredResources.reduce((s, r) => s + (r.trendCurrent[idx] ?? 0), 0),
        Optimized: filteredResources.reduce((s, r) => s + (r.trendOptimized[idx] ?? 0), 0),
      };
    });
  }, [filteredResources, monthSlice, rangeCount]);

  const typeBreakdown = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of filteredResources) {
      map.set(r.type, (map.get(r.type) ?? 0) + r.currentCost);
    }
    return Array.from(map.entries())
      .map(([type, value]) => ({ type, value }))
      .sort((a, b) => b.value - a.value);
  }, [filteredResources]);

  const topRecommendations = useMemo(() => {
    return [...filteredResources]
      .sort((a, b) => (b.currentCost - b.optimizedCost) - (a.currentCost - a.optimizedCost))
      .slice(0, 5);
  }, [filteredResources]);

  const recommendationsList = useMemo(() => {
    let list = [...allResources].sort(
      (a, b) => (b.currentCost - b.optimizedCost) - (a.currentCost - a.optimizedCost)
    );
    if (recFilter === 'with-diff') list = list.filter(r => r.terraformDiff);
    if (recFilter === 'pending') list = list.filter(r => r.approvalStatus === 'pending');
    return list;
  }, [allResources, recFilter]);

  const terraformResources = useMemo(() => allResources.filter(r => r.terraformDiff), [allResources]);

  // ── Render helpers ──────────────────────────────────────────────────────────

  const CostChart = () => {
    const chartProps = {
      data: trendData,
      margin: { left: 0, right: 4, top: 4, bottom: 0 },
    };
    const axis = (
      <>
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
        <YAxis tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
        <Tooltip content={<DarkTooltip />} />
      </>
    );

    if (chartType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart {...chartProps}>
            {axis}
            <Bar dataKey="Current" fill="#f97316" fillOpacity={0.7} radius={[2,2,0,0]} />
            <Bar dataKey="Optimized" fill="#34d399" fillOpacity={0.7} radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }
    if (chartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart {...chartProps}>
            {axis}
            <Line type="monotone" dataKey="Current" stroke="#f97316" strokeWidth={2} dot={{ r: 3, fill: '#f97316' }} />
            <Line type="monotone" dataKey="Optimized" stroke="#34d399" strokeWidth={2} dot={{ r: 3, fill: '#34d399' }} />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    return (
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart {...chartProps}>
          <defs>
            <linearGradient id="gCurrent" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f97316" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="gOptimized" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          {axis}
          <Area type="monotone" dataKey="Current" stroke="#f97316" strokeWidth={2} fill="url(#gCurrent)" />
          <Area type="monotone" dataKey="Optimized" stroke="#34d399" strokeWidth={2} fill="url(#gOptimized)" />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  const resourceById = (id?: string) => allResources.find(r => r.id === id);

  // ── Overview tab ────────────────────────────────────────────────────────────
  const OverviewContent = () => (
    <div className="space-y-5">
      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: 'CURRENT COST', value: `$${totals.current}`, sub: 'per month', color: '#f97316', icon: ArrowUpRight },
          { label: 'OPTIMIZED COST', value: `$${totals.optimized}`, sub: 'per month', color: '#34d399', icon: ArrowDownRight },
          { label: 'TOTAL SAVINGS', value: `$${totals.savings}`, sub: `${Math.round(totals.savings / totals.current * 100)}% reduction`, color: '#34d399', icon: Sparkles },
          { label: 'RESOURCES', value: String(totals.count), sub: `${allResources.filter(r => r.equivalentResourceId).length / 2 | 0} cross-cloud pairs`, color: '#22d3ee', icon: Server },
        ].map(card => (
          <div key={card.label} className="tech-bracket border border-white/07 bg-[#0c1018] p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-['Chakra_Petch'] text-[10px] tracking-[0.14em] text-white/30">{card.label}</span>
              <card.icon className="h-3.5 w-3.5" style={{ color: card.color, opacity: 0.6 }} />
            </div>
            <div className="font-['IBM_Plex_Mono'] text-2xl font-500 tabular-nums" style={{ color: card.color }}>
              {card.value}
            </div>
            <div className="mt-1 font-['IBM_Plex_Mono'] text-[11px] text-white/25">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Cost trend + controls */}
      <div className="border border-white/07 bg-[#0c1018]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/07 px-5 py-3">
          <div>
            <span className="font-['Chakra_Petch'] text-sm text-white/80">COST TREND</span>
            <div className="mt-0.5 flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-4 rounded-full bg-[#f97316]/70" />
                <span className="font-['IBM_Plex_Mono'] text-[11px] text-white/30">Current</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-4 rounded-full bg-[#34d399]/70" />
                <span className="font-['IBM_Plex_Mono'] text-[11px] text-white/30">Optimized</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Chart type */}
            <div className="flex border border-white/07">
              {(['area', 'bar', 'line'] as ChartType[]).map(t => (
                <button
                  key={t}
                  onClick={() => setChartType(t)}
                  className={`px-3 py-1.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] transition-colors ${
                    chartType === t ? 'bg-[#f97316]/15 text-[#f97316]' : 'text-white/25 hover:text-white/50'
                  }`}
                >
                  {t.toUpperCase()}
                </button>
              ))}
            </div>
            {/* Time range */}
            <div className="flex border border-white/07">
              {(['1M', '3M', '6M', '1Y'] as TimeRange[]).map(r => (
                <button
                  key={r}
                  onClick={() => setTimeRange(r)}
                  className={`px-3 py-1.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] transition-colors ${
                    timeRange === r ? 'bg-[#f97316]/15 text-[#f97316]' : 'text-white/25 hover:text-white/50'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="p-5">
          <CostChart />
        </div>
      </div>

      {/* Bottom row: spend breakdown + top recommendations */}
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        {/* Spend by type */}
        <div className="border border-white/07 bg-[#0c1018]">
          <div className="border-b border-white/07 px-5 py-3">
            <span className="font-['Chakra_Petch'] text-sm text-white/80">SPEND BY RESOURCE TYPE</span>
          </div>
          <div className="p-5">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={typeBreakdown} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.04)" />
                <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <YAxis type="category" dataKey="type" tickLine={false} axisLine={false} width={130} tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <Tooltip content={<DarkTooltip />} />
                <Bar dataKey="value" radius={[0, 2, 2, 0]}>
                  {typeBreakdown.map(entry => (
                    <Cell key={entry.type} fill={TYPE_COLORS[entry.type] ?? '#64748b'} fillOpacity={0.7} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top recommendations */}
        <div className="border border-white/07 bg-[#0c1018]">
          <div className="border-b border-white/07 px-5 py-3">
            <span className="font-['Chakra_Petch'] text-sm text-white/80">TOP SAVINGS OPPORTUNITIES</span>
          </div>
          <div className="divide-y divide-white/04">
            {topRecommendations.map((r, i) => {
              const savings = r.currentCost - r.optimizedCost;
              return (
                <button
                  key={r.id}
                  onClick={() => { setSelectedResourceId(r.id); setActiveTab('recommendations'); }}
                  className="flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-white/[0.02]"
                >
                  <span className="w-5 font-['IBM_Plex_Mono'] text-xs text-white/20">{String(i + 1).padStart(2, '0')}</span>
                  <div className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[r.severity]}`} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-['IBM_Plex_Mono'] text-sm text-white/80">{r.name}</div>
                    <div className="font-['Chakra_Petch'] text-[10px] tracking-[0.08em]" style={{ color: PROVIDER_COLORS[r.provider] }}>
                      {r.provider.toUpperCase()} · {r.type.toUpperCase()}
                    </div>
                  </div>
                  <span className="flex-shrink-0 font-['IBM_Plex_Mono'] text-sm font-500 text-[#34d399]">−${savings}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );

  // ── Resources tab ────────────────────────────────────────────────────────────
  const ResourcesContent = () => (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      {/* Resource table */}
      <div className="border border-white/07 bg-[#0c1018]">
        <div className="border-b border-white/07 px-5 py-3">
          <div className="flex items-center justify-between">
            <span className="font-['Chakra_Petch'] text-sm text-white/80">
              RESOURCES <span className="ml-2 font-['IBM_Plex_Mono'] text-xs text-white/25">{filteredResources.length} visible</span>
            </span>
            <div className="flex items-center gap-1">
              <ArrowLeftRight className="h-3 w-3 text-white/20" />
              <span className="font-['Chakra_Petch'] text-[10px] tracking-[0.08em] text-white/20">
                {allResources.filter(r => r.equivalentResourceId).length / 2 | 0} CROSS-CLOUD PAIRS
              </span>
            </div>
          </div>
        </div>

        {/* Column headers */}
        <div className="hidden grid-cols-[minmax(0,1.8fr)_120px_90px_90px_80px_32px] gap-3 border-b border-white/05 px-5 py-2 lg:grid">
          {['RESOURCE', 'TYPE / REGION', 'CURRENT', 'OPTIMIZED', 'SAVINGS', ''].map(h => (
            <div key={h} className="font-['Chakra_Petch'] text-[9px] tracking-[0.16em] text-white/25">{h}</div>
          ))}
        </div>

        <div>
          {filteredResources.map(r => {
            const savings = r.currentCost - r.optimizedCost;
            const pColor = PROVIDER_COLORS[r.provider] ?? '#64748b';
            const isSelected = selectedResource?.id === r.id;
            const equiv = r.equivalentResourceId ? resourceById(r.equivalentResourceId) : null;

            return (
              <button
                key={r.id}
                onClick={() => setSelectedResourceId(r.id)}
                className={`grid w-full gap-3 border-b border-white/04 px-5 py-3 text-left transition-all lg:grid-cols-[minmax(0,1.8fr)_120px_90px_90px_80px_32px] ${
                  isSelected ? 'border-l-2 border-l-[#f97316]/60 bg-[#f97316]/04' : 'hover:bg-white/[0.02]'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className="flex h-7 w-7 flex-shrink-0 items-center justify-center border text-[10px] font-['Chakra_Petch'] font-600"
                    style={{ borderColor: `${pColor}30`, color: pColor, background: `${pColor}10` }}
                  >
                    {r.provider.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate font-['IBM_Plex_Mono'] text-sm text-white/80">{r.name}</div>
                    {equiv && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <ArrowLeftRight className="h-2.5 w-2.5 text-white/20" />
                        <span className="font-['IBM_Plex_Mono'] text-[10px] text-white/25">{equiv.name} ({equiv.provider})</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="font-['IBM_Plex_Mono'] text-xs text-white/40">
                  <div>{r.type}</div>
                  <div className="text-white/25">{r.region}</div>
                </div>
                <div className="font-['IBM_Plex_Mono'] text-sm tabular-nums text-white/60">${r.currentCost}</div>
                <div className="font-['IBM_Plex_Mono'] text-sm tabular-nums text-white/60">${r.optimizedCost}</div>
                <div className="font-['IBM_Plex_Mono'] text-sm tabular-nums text-[#34d399]">−${savings}</div>
                <div className={`flex h-2 w-2 items-center justify-center rounded-full ${SEVERITY_DOT[r.severity]}`} />
              </button>
            );
          })}
          {filteredResources.length === 0 && (
            <div className="px-5 py-10 text-center font-['IBM_Plex_Mono'] text-xs text-white/20">
              No resources match the current filters
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      <div className="border border-white/07 bg-[#0c1018]">
        {selectedResource ? (
          <>
            <div className="border-b border-white/07 px-5 py-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-['IBM_Plex_Mono'] text-sm text-white/80">{selectedResource.name}</div>
                  <div className="mt-0.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em]" style={{ color: PROVIDER_COLORS[selectedResource.provider] }}>
                    {selectedResource.provider.toUpperCase()}
                  </div>
                </div>
                <span className={`border px-2 py-0.5 font-['Chakra_Petch'] text-[9px] tracking-[0.12em] uppercase severity-${selectedResource.severity}`}
                  style={{ borderColor: 'currentColor', opacity: 0.7 }}>
                  {selectedResource.severity}
                </span>
              </div>
              <div className="mt-1 font-['IBM_Plex_Mono'] text-xs text-white/25">
                {selectedResource.type} · {selectedResource.region}
              </div>
            </div>

            <div className="p-5 space-y-4">
              {/* Metrics */}
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'CPU', value: `${selectedResource.cpuUsage}%`, show: selectedResource.cpuUsage > 0 },
                  { label: 'MEMORY', value: `${selectedResource.memoryUsage}%`, show: selectedResource.memoryUsage > 0 },
                  { label: 'NETWORK', value: `${selectedResource.networkUsageGb} GB`, show: true },
                  { label: 'UTIL SCORE', value: String(selectedResource.utilizationScore), show: true },
                ].filter(m => m.show).map(m => (
                  <div key={m.label} className="border border-white/06 bg-white/[0.02] p-3">
                    <div className="font-['Chakra_Petch'] text-[9px] tracking-[0.14em] text-white/25">{m.label}</div>
                    <div className="mt-1 font-['IBM_Plex_Mono'] text-lg tabular-nums text-white/70">{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Savings */}
              <div className="border border-[#34d399]/15 bg-[#34d399]/04 p-3">
                <div className="font-['Chakra_Petch'] text-[9px] tracking-[0.14em] text-[#34d399]/50">POTENTIAL SAVINGS</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-['IBM_Plex_Mono'] text-2xl font-500 tabular-nums text-[#34d399]">
                    −${selectedResource.currentCost - selectedResource.optimizedCost}
                  </span>
                  <span className="font-['Chakra_Petch'] text-[10px] text-[#34d399]/40">/ MONTH</span>
                </div>
              </div>

              {/* Mini trend chart */}
              <div className="border border-white/06 bg-black/20 p-3">
                <div className="mb-2 font-['Chakra_Petch'] text-[9px] tracking-[0.12em] text-white/25">COST TRACE (6M)</div>
                <ResponsiveContainer width="100%" height={80}>
                  <AreaChart
                    data={MONTH_LABELS_12.slice(-6).map((month, i) => ({
                      month,
                      Current: selectedResource.trendCurrent[6 + i],
                      Optimized: selectedResource.trendOptimized[6 + i],
                    }))}
                    margin={{ left: 0, right: 0, top: 2, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="mCurrent" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f97316" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="Current" stroke="#f97316" strokeWidth={1.5} fill="url(#mCurrent)" />
                    <Area type="monotone" dataKey="Optimized" stroke="#34d399" strokeWidth={1.5} fill="none" strokeDasharray="3 2" />
                    <Tooltip content={<DarkTooltip />} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Recommendation text */}
              <div className="border-l-2 border-[#f97316]/30 pl-4">
                <div className="mb-1 font-['Chakra_Petch'] text-[10px] tracking-[0.12em] text-[#f97316]/50">RECOMMENDATION</div>
                <p className="text-xs leading-relaxed text-white/40">{selectedResource.recommendation}</p>
              </div>

              {/* Cross-provider equivalent */}
              {selectedResource.equivalentResourceId && (() => {
                const equiv = resourceById(selectedResource.equivalentResourceId);
                if (!equiv) return null;
                return (
                  <div className="border border-white/06 bg-white/[0.02] p-3">
                    <div className="mb-1 flex items-center gap-1.5">
                      <ArrowLeftRight className="h-3 w-3 text-white/20" />
                      <span className="font-['Chakra_Petch'] text-[9px] tracking-[0.12em] text-white/30">
                        CROSS-PROVIDER EQUIVALENT ({selectedResource.equivalentCategory.toUpperCase()})
                      </span>
                    </div>
                    <div className="font-['IBM_Plex_Mono'] text-xs text-white/60">
                      {equiv.name} <span className="text-white/25">on {equiv.provider}</span>
                    </div>
                    <div className="mt-1 font-['IBM_Plex_Mono'] text-xs text-white/30">
                      ${equiv.currentCost}/mo → ${equiv.optimizedCost}/mo
                    </div>
                  </div>
                );
              })()}

              {/* Quick action */}
              <button
                onClick={() => setActiveTab('recommendations')}
                className="w-full border border-[#f97316]/30 bg-[#f97316]/06 py-2.5 font-['Chakra_Petch'] text-[11px] tracking-[0.12em] text-[#f97316] transition-colors hover:bg-[#f97316]/12"
              >
                VIEW RECOMMENDATION →
              </button>
            </div>
          </>
        ) : (
          <div className="p-6 font-['IBM_Plex_Mono'] text-xs text-white/20">Select a resource to view details</div>
        )}
      </div>
    </div>
  );

  // ── Recommendations tab ──────────────────────────────────────────────────────
  const RecommendationsContent = () => (
    <div className="space-y-4">
      {/* Filter pills */}
      <div className="flex items-center gap-2">
        {([
          { id: 'all', label: 'ALL' },
          { id: 'with-diff', label: 'WITH DIFF' },
          { id: 'pending', label: 'PENDING APPROVAL' },
        ] as { id: RecFilter; label: string }[]).map(f => (
          <button
            key={f.id}
            onClick={() => setRecFilter(f.id)}
            className={`border px-4 py-1.5 font-['Chakra_Petch'] text-[10px] tracking-[0.12em] transition-colors ${
              recFilter === f.id
                ? 'border-[#f97316]/50 bg-[#f97316]/10 text-[#f97316]'
                : 'border-white/08 text-white/30 hover:text-white/60'
            }`}
          >
            {f.label}
            <span className="ml-2 font-['IBM_Plex_Mono'] opacity-50">
              {f.id === 'all' ? allResources.length : f.id === 'with-diff' ? allResources.filter(r => r.terraformDiff).length : allResources.filter(r => r.approvalStatus === 'pending').length}
            </span>
          </button>
        ))}
      </div>

      {recommendationsList.map((r, i) => (
        <RecommendationCard
          key={r.id}
          resource={r}
          config={{ repoUrl: config.repoUrl, branch: config.branch }}
          rank={i + 1}
        />
      ))}
    </div>
  );

  // ── Terraform tab ────────────────────────────────────────────────────────────
  const TerraformContent = () => (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-['IBM_Plex_Mono'] text-xs text-white/30">
            {terraformResources.length} resources with pending changes · estimated −${terraformResources.reduce((s, r) => s + r.currentCost - r.optimizedCost, 0)}/month
          </p>
        </div>
      </div>

      {terraformResources.map(r => {
        const savings = r.currentCost - r.optimizedCost;
        const pColor = PROVIDER_COLORS[r.provider] ?? '#64748b';
        return (
          <div key={r.id} className="border border-white/07 bg-[#0c1018]">
            <div className="flex items-center justify-between border-b border-white/07 px-5 py-3">
              <div className="flex items-center gap-3">
                <div
                  className="flex h-6 w-6 items-center justify-center border font-['Chakra_Petch'] text-[9px]"
                  style={{ borderColor: `${pColor}30`, color: pColor, background: `${pColor}10` }}
                >
                  {r.provider.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <span className="font-['IBM_Plex_Mono'] text-sm text-white/80">{r.name}</span>
                  <span className="ml-3 font-['Chakra_Petch'] text-[10px] tracking-[0.08em] text-white/25">{r.terraformFile}</span>
                </div>
              </div>
              <span className="font-['IBM_Plex_Mono'] text-sm tabular-nums text-[#34d399]">−${savings}/mo</span>
            </div>
            <div className="p-5">
              <TerraformDiff diff={r.terraformDiff!} file={r.terraformFile} />
            </div>
          </div>
        );
      })}
    </div>
  );

  // ── Main render ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
        <span className="font-['IBM_Plex_Mono'] text-sm text-white/40">Loading recommendations...</span>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
        <span className="font-['IBM_Plex_Mono'] text-sm text-red-400">Error: {fetchError}</span>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-56px)]">
      <div className="flex h-full">
        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0 border-r border-white/06 bg-[#060810]">
          <div className="sticky top-0 flex h-[calc(100vh-56px)] flex-col overflow-y-auto p-4">
            {/* Workspace */}
            <div className="mb-5 border border-white/06 bg-white/[0.02] p-3">
              <div className="font-['Chakra_Petch'] text-[10px] tracking-[0.1em] text-white/25">WORKSPACE</div>
              <div className="mt-1 truncate font-['IBM_Plex_Mono'] text-xs text-white/70">
                {config.repoUrl || 'acme-corp / prod'}
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {[
                  { label: 'DO', color: PROVIDER_COLORS.DigitalOcean },
                  { label: 'TF', color: '#94a3b8' },
                  { label: 'SF', color: PROVIDER_COLORS.Snowflake },
                ].map(s => (
                  <span
                    key={s.label}
                    className="border px-1.5 py-0.5 font-['Chakra_Petch'] text-[9px] tracking-[0.1em]"
                    style={{ borderColor: `${s.color}30`, color: s.color }}
                  >
                    {s.label}
                  </span>
                ))}
              </div>
            </div>

            {/* Nav */}
            <nav className="mb-auto space-y-0.5">
              {NAV_ITEMS.map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                    activeTab === item.id
                      ? 'border-l-2 border-[#f97316] bg-[#f97316]/08 text-[#f97316]'
                      : 'border-l-2 border-transparent text-white/30 hover:text-white/60'
                  }`}
                >
                  <item.icon className="h-3.5 w-3.5 flex-shrink-0" />
                  <span className="font-['Chakra_Petch'] text-[11px] tracking-[0.1em]">{item.label}</span>
                </button>
              ))}
            </nav>

            {/* Footer */}
            <div className="mt-4 space-y-2 border-t border-white/05 pt-4">
              <button
                onClick={handleRunPipeline}
                disabled={pipelineRunning}
                className={`flex w-full items-center gap-2 border px-3 py-2 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] transition-colors ${
                  pipelineRunning
                    ? 'border-[#f97316]/30 text-[#f97316]/50 cursor-not-allowed'
                    : 'border-[#f97316]/40 text-[#f97316]/70 hover:border-[#f97316]/70 hover:text-[#f97316]'
                }`}
              >
                <Sparkles className={`h-3 w-3 ${pipelineRunning ? 'animate-pulse' : ''}`} />
                {pipelineRunning ? 'RUNNING...' : 'RUN ANALYSIS'}
              </button>
              <button
                onClick={onRescan}
                className="flex w-full items-center gap-2 border border-white/08 px-3 py-2 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] text-white/30 transition-colors hover:border-white/16 hover:text-white/60"
              >
                <RefreshCw className="h-3 w-3" />
                RE-SCAN
              </button>
              <div className="px-1 font-['IBM_Plex_Mono'] text-[10px] text-white/15">
                Scanned {analysisResult ? new Date(analysisResult.scannedAt).toLocaleTimeString() : '—'}
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1 overflow-auto">
          {/* Filter bar */}
          <div className="sticky top-0 z-10 border-b border-white/06 bg-[#07090d]/95 backdrop-blur-sm">
            <div className="flex flex-wrap items-center gap-3 px-6 py-3">
              {/* Provider filters */}
              <div className="flex items-center gap-1.5">
                <Filter className="h-3 w-3 text-white/20" />
                {(['All', 'DigitalOcean', 'AWS', 'Snowflake'] as ('All' | Provider)[]).map(p => (
                  <button
                    key={p}
                    onClick={() => setProviderFilter(p)}
                    className={`border px-2.5 py-1 font-['Chakra_Petch'] text-[10px] tracking-[0.08em] transition-colors ${
                      providerFilter === p
                        ? 'border-[#f97316]/50 bg-[#f97316]/10 text-[#f97316]'
                        : 'border-white/08 text-white/30 hover:text-white/60'
                    }`}
                  >
                    {p === 'DigitalOcean' ? 'DO' : p.toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="h-4 w-px bg-white/08" />

              {/* Type filters */}
              <div className="flex flex-wrap items-center gap-1">
                {(['All', 'Droplet', 'Managed Database', 'Kubernetes', 'Storage', 'Data Warehouse'] as ('All' | ResourceType)[]).map(t => (
                  <button
                    key={t}
                    onClick={() => setTypeFilter(t)}
                    className={`border px-2.5 py-1 font-['Chakra_Petch'] text-[10px] tracking-[0.08em] transition-colors ${
                      typeFilter === t
                        ? 'border-[#22d3ee]/50 bg-[#22d3ee]/10 text-[#22d3ee]'
                        : 'border-white/08 text-white/30 hover:text-white/60'
                    }`}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="ml-auto flex items-center gap-2 border border-white/08 bg-white/[0.02] px-3 py-1.5">
                <Search className="h-3.5 w-3.5 text-white/20" />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search resources..."
                  className="w-40 bg-transparent font-['IBM_Plex_Mono'] text-xs text-white/70 placeholder:text-white/15 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Tab content */}
          <div className="p-6">
            {activeTab === 'overview'        && <OverviewContent />}
            {activeTab === 'resources'       && <ResourcesContent />}
            {activeTab === 'recommendations' && <RecommendationsContent />}
            {activeTab === 'terraform'       && <TerraformContent />}
          </div>
        </main>
      </div>
    </div>
  );
}
