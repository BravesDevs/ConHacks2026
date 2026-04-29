import { AlertTriangle, RotateCw, Sparkles } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';

interface DashboardScreenProps {
  onRescan: () => void;
}

export default function DashboardScreen({ onRescan }: DashboardScreenProps) {
  const spendData = [
    { name: 'Droplets', value: 899 },
    { name: 'Databases', value: 251 },
    { name: 'Storage', value: 98 }
  ];

  const trendData = [
    { month: 'Nov', value: 980 },
    { month: 'Dec', value: 1050 },
    { month: 'Jan', value: 1100 },
    { month: 'Feb', value: 1150 },
    { month: 'Mar', value: 1200 },
    { month: 'Apr', value: 1248 }
  ];

  const recommendations = [
    {
      icon: AlertTriangle,
      title: 'Downsize 3 over-provisioned droplets',
      description: 'These droplets are consistently using less than 30% CPU and memory',
      savings: 180
    },
    {
      icon: AlertTriangle,
      title: 'Remove unused reserved IP',
      description: 'Reserved IP not attached to any active resource for 45+ days',
      savings: 6
    },
    {
      icon: Sparkles,
      title: 'Switch managed DB to smaller tier',
      description: 'Database shows low query volume and can be optimized to a lower tier',
      savings: 161
    }
  ];

  return (
    <div className="min-h-[calc(900px-73px)] px-8 py-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="mb-2 text-3xl dark:text-white">Cost insights</h1>
            <p className="text-sm text-black/60 dark:text-white/60">
              acme-corp/infra-prod · Last scanned April 29, 2026 at 2:34 PM
            </p>
          </div>
          <button
            onClick={onRescan}
            className="flex items-center gap-2 rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 text-sm transition-colors hover:bg-black/5 dark:hover:bg-white/5"
          >
            <RotateCw className="h-4 w-4" />
            Re-scan
          </button>
        </div>

        <div className="mb-8 grid grid-cols-3 gap-6">
          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6">
            <div className="mb-2 text-sm text-black/60 dark:text-white/60">Monthly spend</div>
            <div className="mb-1 text-3xl dark:text-white">$1,248</div>
            <div className="flex items-center gap-1 text-sm text-red-600">
              <span>↑ 12%</span>
              <span className="text-black/40 dark:text-white/40">vs last month</span>
            </div>
          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6">
            <div className="mb-2 text-sm text-black/60 dark:text-white/60">Potential savings</div>
            <div className="mb-1 text-3xl text-[#1D9E75]">$347</div>
            <div className="flex items-center gap-1 text-sm text-[#1D9E75]">
              <span>↓ 28%</span>
              <span className="text-black/40 dark:text-white/40">reduction possible</span>
            </div>
          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6">
            <div className="mb-2 text-sm text-black/60 dark:text-white/60">Resources flagged</div>
            <div className="mb-1 text-3xl dark:text-white">7/24</div>
            <div className="text-sm text-black/40 dark:text-white/40">resources need attention</div>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-2 gap-6">
          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6">
            <h3 className="mb-6 text-lg dark:text-white">Spend by resource type</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={spendData} layout="vertical" margin={{ left: 20, right: 20 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 14 }} width={80} />
                <Bar dataKey="value" radius={6}>
                  {spendData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill="#1D9E75" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 flex items-center justify-between border-t border-black/10 dark:border-white/10 pt-4">
              {spendData.map(item => (
                <div key={item.name} className="text-center">
                  <div className="text-sm text-black/60 dark:text-white/60">{item.name}</div>
                  <div className="font-medium dark:text-white">${item.value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6">
            <h3 className="mb-6 text-lg dark:text-white">Spend over time (6 months)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={trendData} margin={{ left: 0, right: 0 }}>
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis hide />
                <Bar dataKey="value" radius={6}>
                  {trendData.map((entry, index) => {
                    const opacity = 0.5 + (index / trendData.length) * 0.5;
                    return (
                      <Cell
                        key={`cell-${index}`}
                        fill="#1D9E75"
                        fillOpacity={opacity}
                      />
                    );
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div>
          <div className="mb-4 flex items-center gap-2">
            <h3 className="text-lg dark:text-white">AI recommendations</h3>
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs text-amber-700">
              3 quick wins
            </span>
          </div>

          <div className="space-y-4">
            {recommendations.map((rec, index) => (
              <div
                key={index}
                className="flex items-start gap-4 rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-6"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
                  <rec.icon className="h-5 w-5 text-amber-700 dark:text-amber-500" />
                </div>
                <div className="flex-1">
                  <h4 className="mb-1 font-medium dark:text-white">{rec.title}</h4>
                  <p className="text-sm text-black/60 dark:text-white/60">{rec.description}</p>
                </div>
                <div className="shrink-0 text-right">
                  <div className="mb-2 font-medium text-[#1D9E75]">
                    Save ~${rec.savings}/mo
                  </div>
                  <button className="rounded-lg border border-black/10 dark:border-white/10 px-4 py-2 text-sm dark:text-white transition-colors hover:bg-black/5 dark:hover:bg-white/5">
                    Apply fix
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
