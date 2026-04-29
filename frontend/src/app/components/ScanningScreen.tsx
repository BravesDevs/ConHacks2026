import { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import type { ScanConfig } from '../types';

interface ScanningScreenProps {
  config: ScanConfig;
  onComplete: () => void;
}

interface ScanStep {
  id: number;
  label: string;
  detail: string;
  threshold: number;
}

const SCAN_STEPS: ScanStep[] = [
  { id: 1, label: 'INIT',  detail: 'Repository cloned',               threshold: 18 },
  { id: 2, label: 'PARSE', detail: 'Terraform files analyzed',         threshold: 36 },
  { id: 3, label: 'FETCH', detail: 'DigitalOcean API queried',         threshold: 54 },
  { id: 4, label: 'MODEL', detail: 'Snowflake recommendation engine',  threshold: 78 },
  { id: 5, label: 'REPORT',detail: 'Optimization report generated',    threshold: 96 },
];

function buildLogMessages(repoUrl: string) {
  const repo = repoUrl || 'infra-repo';
  return [
    { at: 2,  text: `> Initialized scan for ${repo}` },
    { at: 6,  text: `> Cloning repository (branch: main)...` },
    { at: 14, text: `> Repository cloned — 127 files, 23 directories` },
    { at: 19, text: `> Parsing Terraform configuration...` },
    { at: 25, text: `> Found 8 resource definitions in infra/compute.tf` },
    { at: 30, text: `> Found 3 resource definitions in infra/databases.tf` },
    { at: 35, text: `> Found 2 resource definitions in infra/snowflake.tf` },
    { at: 40, text: `> Fetching DigitalOcean resource metrics...` },
    { at: 44, text: `> Connected to DigitalOcean API v2` },
    { at: 50, text: `> Retrieved metrics for 7 resources across 3 regions` },
    { at: 56, text: `> Running Snowflake optimization model...` },
    { at: 62, text: `> Analyzing utilization patterns (90-day window)` },
    { at: 70, text: `> Cross-provider equivalency mapping: 4 pairs identified` },
    { at: 78, text: `> Generated 7 optimization recommendations` },
    { at: 84, text: `> Estimated savings: $234/month (28.3% reduction)` },
    { at: 90, text: `> Generating infrastructure report...` },
    { at: 96, text: `> Report generation complete` },
    { at: 99, text: `> Transferring to dashboard...` },
  ];
}

export default function ScanningScreen({ config, onComplete }: ScanningScreenProps) {
  const [progress, setProgress] = useState(0);
  const [visibleLogs, setVisibleLogs] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const logMessages = buildLogMessages(config.repoUrl);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 600);
          return 100;
        }
        const next = prev + 0.8;

        // Reveal log messages as progress crosses thresholds
        const revealed = logMessages.filter(m => m.at <= next && m.at > prev);
        if (revealed.length > 0) {
          setVisibleLogs(logs => [...logs, ...revealed.map(m => m.text)]);
        }

        return next;
      });
    }, 40);
    return () => clearInterval(interval);
  }, [onComplete]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [visibleLogs]);

  const repoDisplay = config.repoUrl || 'acme-corp/infra-prod';

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center px-6 py-12">
      <div className="w-full max-w-[640px] animate-fade-up">

        {/* Header */}
        <div className="mb-8">
          <div className="mb-3 flex items-center gap-2">
            <div className="h-px w-8 bg-[#f97316]/60" />
            <span className="font-['Chakra_Petch'] text-[11px] tracking-[0.18em] text-[#f97316]/70">INFRASTRUCTURE SCAN</span>
          </div>
          <h1 className="font-['Chakra_Petch'] text-2xl font-700 text-white">
            Scanning your infrastructure
          </h1>
        </div>

        {/* Main scan panel */}
        <div className="tech-bracket border border-white/08 bg-white/[0.02]">
          <div className="p-6">

            {/* Repo indicator */}
            <div className="mb-5 flex items-center gap-3 border-b border-white/05 pb-5">
              <div className="flex h-8 w-8 items-center justify-center border border-white/10 bg-white/05">
                <svg className="h-4 w-4 text-white/60" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.164 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="font-['IBM_Plex_Mono'] text-sm text-white/80">{repoDisplay}</div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-white/30">
                  <span className="border border-white/10 px-1.5 py-0.5 font-['IBM_Plex_Mono'] text-[10px]">
                    {config.branch || 'main'}
                  </span>
                  <span className="border border-white/10 px-1.5 py-0.5 font-['IBM_Plex_Mono'] text-[10px]">
                    terraform
                  </span>
                  <span className="border border-white/10 px-1.5 py-0.5 font-['IBM_Plex_Mono'] text-[10px]">
                    digitalocean
                  </span>
                </div>
              </div>
              <div className="ml-auto font-['IBM_Plex_Mono'] text-sm tabular-nums text-[#f97316]">
                {Math.floor(progress)}%
              </div>
            </div>

            {/* Progress bar */}
            <div className="mb-6 h-1 w-full bg-white/05">
              <div
                className="h-full bg-[#f97316] transition-all duration-100"
                style={{ width: `${progress}%`, boxShadow: '0 0 8px rgba(249,115,22,0.5)' }}
              />
            </div>

            {/* Step indicators */}
            <div className="mb-6 grid grid-cols-5 gap-2">
              {SCAN_STEPS.map(step => {
                const completed = progress > step.threshold;
                const active = !completed && progress >= (step.threshold - 18);
                return (
                  <div key={step.id} className="flex flex-col items-center gap-2">
                    <div
                      className={`flex h-8 w-8 items-center justify-center border text-xs transition-all ${
                        completed
                          ? 'border-[#34d399]/60 bg-[#34d399]/10 text-[#34d399]'
                          : active
                          ? 'border-[#f97316]/60 bg-[#f97316]/10 text-[#f97316]'
                          : 'border-white/08 bg-transparent text-white/20'
                      }`}
                    >
                      {completed ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : active ? (
                        <span className="inline-block h-1.5 w-1.5 animate-pulse-dot rounded-full bg-[#f97316]" />
                      ) : (
                        <span className="inline-block h-1 w-1 rounded-full bg-white/15" />
                      )}
                    </div>
                    <span
                      className={`font-['Chakra_Petch'] text-[9px] tracking-[0.1em] transition-colors ${
                        completed ? 'text-[#34d399]/70' : active ? 'text-[#f97316]/80' : 'text-white/20'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Log output */}
            <div
              ref={logRef}
              className="h-40 overflow-y-auto border border-white/05 bg-black/30 p-4 font-['IBM_Plex_Mono'] text-xs"
            >
              {visibleLogs.map((line, i) => (
                <div key={i} className={`mb-1 leading-5 ${i === visibleLogs.length - 1 ? 'text-white/70' : 'text-white/30'}`}>
                  {line}
                  {i === visibleLogs.length - 1 && progress < 100 && (
                    <span className="ml-0.5 animate-cursor text-[#f97316]">_</span>
                  )}
                </div>
              ))}
              {visibleLogs.length === 0 && (
                <span className="text-white/20">Initializing scan engine<span className="animate-cursor text-[#f97316]">_</span></span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
