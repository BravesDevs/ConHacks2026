import { ArrowRight } from 'lucide-react';
import type { ScanConfig } from '../pages/MainApp';

interface ConnectScreenProps {
  config: ScanConfig;
  onChange: (config: ScanConfig) => void;
  onAnalyze: () => void;
}

export default function ConnectScreen({ config, onChange, onAnalyze }: ConnectScreenProps) {
  const set = (key: keyof ScanConfig) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...config, [key]: e.target.value });

  return (
    <div className="flex min-h-[calc(900px-73px)] items-center justify-center px-8 py-16">
      <div className="w-full max-w-[640px]">
        <div className="mb-12 text-center">
          <h1 className="mb-3 text-3xl dark:text-white">Connect your infrastructure</h1>
          <p className="text-black/60 dark:text-white/60">
            Link your GitHub repository and DigitalOcean account to analyze your infrastructure costs
          </p>
        </div>

        <div className="space-y-8">
          <div>
            <h2 className="mb-4 text-lg dark:text-white">GitHub repository</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                  Repository URL
                </label>
                <input
                  type="text"
                  value={config.repoUrl}
                  onChange={set('repoUrl')}
                  placeholder="https://github.com/your-org/your-repo"
                  className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                    Branch
                  </label>
                  <input
                    type="text"
                    value={config.branch}
                    onChange={set('branch')}
                    placeholder="main"
                    className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                    Terraform path
                  </label>
                  <input
                    type="text"
                    value={config.terraformPath}
                    onChange={set('terraformPath')}
                    placeholder="/infra"
                    className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="h-px bg-black/10 dark:bg-white/10" />

          <div>
            <div className="mb-4 flex items-center gap-2">
              <h2 className="text-lg dark:text-white">DigitalOcean credentials</h2>
              <span className="rounded-full bg-[#1D9E75]/10 px-2.5 py-0.5 text-xs text-[#1D9E75]">
                encrypted
              </span>
            </div>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                  API Token
                </label>
                <input
                  type="password"
                  placeholder="••••••••••••••••••••••••••••"
                  className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                    Project (optional)
                  </label>
                  <input
                    type="text"
                    value={config.doProject}
                    onChange={set('doProject')}
                    placeholder=""
                    className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                    Region filter
                  </label>
                  <input
                    type="text"
                    value={config.regionFilter}
                    onChange={set('regionFilter')}
                    placeholder=""
                    className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 flex items-center justify-end gap-3">
          <button
            onClick={() => onChange({ repoUrl: '', branch: 'main', terraformPath: '/infra', doProject: '', regionFilter: '' })}
            className="rounded-lg px-5 py-2.5 text-black/60 dark:text-white/60 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
          >
            Clear
          </button>
          <button
            onClick={onAnalyze}
            className="flex items-center gap-2 rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90"
          >
            Analyze
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
