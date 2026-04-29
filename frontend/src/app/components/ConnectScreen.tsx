import { useState } from 'react';
import { Eye, EyeOff, ArrowRight, Github, Lock, Server } from 'lucide-react';
import type { ScanConfig } from '../types';

interface ConnectScreenProps {
  config: ScanConfig;
  onChange: (config: ScanConfig) => void;
  onAnalyze: () => void;
}

function SecretField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div>
      <label className="mb-1.5 block font-['Chakra_Petch'] text-[11px] tracking-[0.14em] text-white/40">
        {label}
      </label>
      <div className="relative flex items-center border border-white/08 bg-white/[0.03] transition-colors focus-within:border-[#f97316]/50 focus-within:bg-[#f97316]/[0.03]">
        <input
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent px-4 py-3 font-['IBM_Plex_Mono'] text-sm text-white/80 placeholder:text-white/15 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          className="mr-3 flex-shrink-0 text-white/20 hover:text-white/50 transition-colors"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  hint?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block font-['Chakra_Petch'] text-[11px] tracking-[0.14em] text-white/40">
        {label}
        {hint && <span className="ml-2 font-['IBM_Plex_Mono'] normal-case tracking-normal text-white/20">{hint}</span>}
      </label>
      <div className="border border-white/08 bg-white/[0.03] transition-colors focus-within:border-[#f97316]/50 focus-within:bg-[#f97316]/[0.03]">
        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent px-4 py-3 font-['IBM_Plex_Mono'] text-sm text-white/80 placeholder:text-white/15 focus:outline-none"
        />
      </div>
    </div>
  );
}

export default function ConnectScreen({ config, onChange, onAnalyze }: ConnectScreenProps) {
  const set = (key: keyof ScanConfig) => (v: string) => onChange({ ...config, [key]: v });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const canAnalyze = config.githubToken.trim() && config.repoUrl.trim() && config.doApiKey.trim();

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center px-6 py-12">
      <div className="w-full max-w-[560px] animate-fade-up">

        {/* Header */}
        <div className="mb-10">
          <div className="mb-3 flex items-center gap-2">
            <div className="h-px w-8 bg-[#f97316]/60" />
            <span className="font-['Chakra_Petch'] text-[11px] tracking-[0.18em] text-[#f97316]/70">SYSTEM INITIALIZATION</span>
          </div>
          <h1 className="font-['Chakra_Petch'] text-3xl font-700 tracking-tight text-white">
            Connect your infrastructure
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-white/40">
            Provide access credentials to begin the infrastructure scan. Tokens are used only for this session.
          </p>
        </div>

        {/* Form panel */}
        <div className="tech-bracket relative border border-white/08 bg-white/[0.02]">
          <div className="space-y-6 p-7">

            {/* GitHub section */}
            <div>
              <div className="mb-4 flex items-center gap-2.5">
                <Github className="h-4 w-4 text-white/40" />
                <span className="font-['Chakra_Petch'] text-[11px] font-600 tracking-[0.16em] text-white/50">GITHUB</span>
                <div className="h-px flex-1 bg-white/06" />
              </div>
              <div className="space-y-4">
                <SecretField
                  label="PERSONAL ACCESS TOKEN"
                  value={config.githubToken}
                  onChange={set('githubToken')}
                  placeholder="ghp_••••••••••••••••••••••••••"
                />
                <TextField
                  label="REPOSITORY"
                  value={config.repoUrl}
                  onChange={set('repoUrl')}
                  placeholder="your-org/infra-repo"
                />
              </div>
            </div>

            <div className="h-px bg-white/05" />

            {/* DigitalOcean section */}
            <div>
              <div className="mb-4 flex items-center gap-2.5">
                <Server className="h-4 w-4 text-white/40" />
                <span className="font-['Chakra_Petch'] text-[11px] font-600 tracking-[0.16em] text-white/50">DIGITALOCEAN</span>
                <div className="h-px flex-1 bg-white/06" />
                <div className="flex items-center gap-1 border border-[#34d399]/20 bg-[#34d399]/05 px-2 py-0.5">
                  <Lock className="h-2.5 w-2.5 text-[#34d399]/60" />
                  <span className="font-['Chakra_Petch'] text-[9px] tracking-[0.12em] text-[#34d399]/60">ENCRYPTED</span>
                </div>
              </div>
              <SecretField
                label="API KEY"
                value={config.doApiKey}
                onChange={set('doApiKey')}
                placeholder="dop_v1_••••••••••••••••••••••••••"
              />
            </div>

            {/* Advanced / optional */}
            <button
              type="button"
              onClick={() => setShowAdvanced(v => !v)}
              className="flex items-center gap-2 text-[11px] font-['Chakra_Petch'] tracking-[0.1em] text-white/25 hover:text-white/50 transition-colors"
            >
              <span>{showAdvanced ? '▲' : '▼'}</span>
              ADVANCED OPTIONS
            </button>

            {showAdvanced && (
              <div className="space-y-4 border-t border-white/05 pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <TextField
                    label="BRANCH"
                    value={config.branch}
                    onChange={set('branch')}
                    placeholder="main"
                  />
                  <TextField
                    label="DO PROJECT"
                    hint="(optional)"
                    value={config.doProject ?? ''}
                    onChange={set('doProject')}
                    placeholder="my-project"
                  />
                </div>
                <TextField
                  label="REGION FILTER"
                  hint="(optional)"
                  value={config.regionFilter ?? ''}
                  onChange={set('regionFilter')}
                  placeholder="nyc3, sfo3"
                />
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-8 flex items-center justify-between">
          <button
            type="button"
            onClick={() => onChange({ githubToken: '', repoUrl: '', branch: 'main', doApiKey: '', doProject: '', regionFilter: '' })}
            className="font-['Chakra_Petch'] text-[11px] tracking-[0.12em] text-white/25 hover:text-white/50 transition-colors"
          >
            CLEAR FIELDS
          </button>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={!canAnalyze}
            className={`group flex items-center gap-3 border px-6 py-3 font-['Chakra_Petch'] text-sm font-600 tracking-[0.1em] transition-all ${
              canAnalyze
                ? 'border-[#f97316] bg-[#f97316]/10 text-[#f97316] hover:bg-[#f97316]/20'
                : 'cursor-not-allowed border-white/08 text-white/20'
            }`}
          >
            INITIALIZE SCAN
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
