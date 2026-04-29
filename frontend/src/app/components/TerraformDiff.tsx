import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface TerraformDiffProps {
  diff: string;
  file?: string;
}

export default function TerraformDiff({ diff, file }: TerraformDiffProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(diff);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const lines = diff.split('\n');

  return (
    <div className="overflow-hidden border border-white/07">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/07 bg-black/30 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#f87171]" />
          <span className="h-2 w-2 rounded-full bg-[#fbbf24]" />
          <span className="h-2 w-2 rounded-full bg-[#34d399]" />
          {file && (
            <span className="ml-2 font-['IBM_Plex_Mono'] text-[11px] text-white/30">{file}</span>
          )}
        </div>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 text-white/20 transition-colors hover:text-white/60"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-[#34d399]" /> : <Copy className="h-3.5 w-3.5" />}
          <span className="font-['Chakra_Petch'] text-[10px] tracking-[0.1em]">
            {copied ? 'COPIED' : 'COPY'}
          </span>
        </button>
      </div>

      {/* Diff lines */}
      <div className="overflow-x-auto bg-[#05070a] p-4">
        <pre className="font-['IBM_Plex_Mono'] text-xs leading-6">
          {lines.map((line, i) => {
            const isAdd = line.startsWith('+') && !line.startsWith('+++');
            const isRemove = line.startsWith('-') && !line.startsWith('---');
            const isHunk = line.startsWith('@');
            return (
              <div
                key={i}
                className={`px-1 ${
                  isAdd
                    ? 'bg-[#34d399]/08 text-[#34d399]'
                    : isRemove
                    ? 'bg-[#f87171]/08 text-[#f87171]'
                    : isHunk
                    ? 'text-[#22d3ee]/70'
                    : 'text-white/55'
                }`}
              >
                {line || '\u00A0'}
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
