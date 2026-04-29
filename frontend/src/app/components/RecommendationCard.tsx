import { useState } from 'react';
import { ExternalLink, CheckCircle2, Loader2, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import TerraformDiff from './TerraformDiff';
import type { ResourceRecord, ScanConfig } from '../types';
import { approveRecommendation } from '../api';

interface RecommendationCardProps {
  resource: ResourceRecord;
  config: Pick<ScanConfig, 'repoUrl' | 'branch'>;
  rank: number;
}

const SEVERITY_STYLES = {
  critical: { border: 'border-[#f87171]/25', label: 'text-[#f87171]', bg: 'bg-[#f87171]/08' },
  high:     { border: 'border-[#fbbf24]/20', label: 'text-[#fbbf24]', bg: 'bg-[#fbbf24]/08' },
  medium:   { border: 'border-[#f97316]/20', label: 'text-[#f97316]', bg: 'bg-[#f97316]/08' },
  low:      { border: 'border-[#34d399]/15', label: 'text-[#34d399]', bg: 'bg-[#34d399]/08' },
};

const PROVIDER_COLORS: Record<string, string> = {
  DigitalOcean: '#22d3ee',
  AWS: '#fbbf24',
  Snowflake: '#a78bfa',
};

type ApproveState = 'idle' | 'confirming' | 'approving' | 'approved';

export default function RecommendationCard({ resource, config, rank }: RecommendationCardProps) {
  const [approveState, setApproveState] = useState<ApproveState>('idle');
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [diffExpanded, setDiffExpanded] = useState(true);
  const savings = resource.currentCost - resource.optimizedCost;
  const severityStyle = SEVERITY_STYLES[resource.severity];
  const providerColor = PROVIDER_COLORS[resource.provider] ?? '#64748b';

  const githubUrl = resource.terraformFile && config.repoUrl
    ? `https://github.com/${config.repoUrl.replace(/^https?:\/\/github\.com\//, '')}/blob/${config.branch || 'main'}/${resource.terraformFile}`
    : null;

  const handleApprove = async () => {
    if (approveState === 'idle') {
      setApproveState('confirming');
      return;
    }
    if (approveState === 'confirming') {
      setApproveState('approving');
      try {
        const result = await approveRecommendation(resource.id, config);
        setPrUrl(result.prUrl);
        setApproveState('approved');
      } catch {
        setApproveState('idle');
      }
    }
  };

  return (
    <div className={`tech-bracket border ${severityStyle.border} bg-[#0a0d12] transition-all`}>
      <div className="p-5">
        {/* Header row */}
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 font-['IBM_Plex_Mono'] text-xs text-white/20">
              {String(rank).padStart(2, '0')}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-['Chakra_Petch'] text-base font-600 text-white">
                  {resource.name}
                </span>
                <span
                  className="border px-2 py-0.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em]"
                  style={{ borderColor: `${providerColor}30`, color: `${providerColor}` }}
                >
                  {resource.provider.toUpperCase()}
                </span>
                <span className="border border-white/08 px-2 py-0.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] text-white/40">
                  {resource.type.toUpperCase()}
                </span>
                <span className={`border px-2 py-0.5 font-['Chakra_Petch'] text-[10px] tracking-[0.1em] uppercase ${severityStyle.border} ${severityStyle.label}`}>
                  {resource.severity}
                </span>
              </div>
              <div className="mt-1 font-['IBM_Plex_Mono'] text-xs text-white/30">{resource.region}</div>
            </div>
          </div>

          {/* Savings badge */}
          <div className="flex-shrink-0 border border-[#34d399]/25 bg-[#34d399]/08 px-3 py-2 text-right">
            <div className="font-['IBM_Plex_Mono'] text-lg font-500 tabular-nums text-[#34d399]">
              −${savings}
            </div>
            <div className="font-['Chakra_Petch'] text-[9px] tracking-[0.1em] text-[#34d399]/50">PER MONTH</div>
          </div>
        </div>

        {/* Recommendation text */}
        <p className="mb-5 border-l-2 border-white/08 pl-4 text-sm leading-relaxed text-white/50">
          {resource.recommendation}
        </p>

        {/* Terraform diff */}
        {resource.terraformDiff ? (
          <div className="mb-4">
            <button
              onClick={() => setDiffExpanded(v => !v)}
              className="mb-2 flex items-center gap-2 font-['Chakra_Petch'] text-[10px] tracking-[0.14em] text-white/30 hover:text-white/60 transition-colors"
            >
              {diffExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              TERRAFORM DIFF
            </button>
            {diffExpanded && (
              <TerraformDiff diff={resource.terraformDiff} file={resource.terraformFile} />
            )}
          </div>
        ) : (
          <div className="mb-4 border border-white/05 bg-black/20 px-4 py-3">
            <span className="font-['IBM_Plex_Mono'] text-xs text-white/20">
              # Terraform diff available after backend integration
            </span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          {githubUrl && (
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 border border-white/10 px-4 py-2 font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-white/40 transition-colors hover:border-white/20 hover:text-white/70"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              VIEW ON GITHUB
            </a>
          )}

          {approveState === 'approved' ? (
            <div className="flex items-center gap-2 border border-[#34d399]/30 bg-[#34d399]/08 px-4 py-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-[#34d399]" />
              <span className="font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-[#34d399]">
                CHANGE APPROVED
              </span>
              {prUrl && (
                <a
                  href={prUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-1 font-['IBM_Plex_Mono'] text-[11px] text-[#34d399]/60 underline"
                >
                  PR →
                </a>
              )}
            </div>
          ) : approveState === 'confirming' ? (
            <div className="flex items-center gap-2">
              <span className="font-['IBM_Plex_Mono'] text-[11px] text-[#fbbf24]/60">
                Apply this change?
              </span>
              <button
                onClick={handleApprove}
                className="border border-[#34d399]/40 bg-[#34d399]/10 px-4 py-2 font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-[#34d399] transition-colors hover:bg-[#34d399]/20"
              >
                CONFIRM APPLY
              </button>
              <button
                onClick={() => setApproveState('idle')}
                className="border border-white/10 px-4 py-2 font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-white/30 transition-colors hover:text-white/60"
              >
                CANCEL
              </button>
            </div>
          ) : approveState === 'approving' ? (
            <div className="flex items-center gap-2 border border-[#f97316]/30 bg-[#f97316]/08 px-4 py-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-[#f97316]" />
              <span className="font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-[#f97316]">
                CREATING PR...
              </span>
            </div>
          ) : (
            <button
              onClick={handleApprove}
              className="flex items-center gap-2 border border-[#f97316]/40 bg-[#f97316]/08 px-4 py-2 font-['Chakra_Petch'] text-[11px] tracking-[0.1em] text-[#f97316] transition-colors hover:bg-[#f97316]/16"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              APPROVE CHANGE
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
