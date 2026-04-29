import { Settings, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router';

interface NavbarProps {
  currentStep: number;
  onChatOpen: () => void;
}

const steps = [
  { number: 1, label: 'CONNECT' },
  { number: 2, label: 'SCAN' },
  { number: 3, label: 'INSIGHTS' },
];

export default function Navbar({ currentStep, onChatOpen }: NavbarProps) {
  const navigate = useNavigate();

  return (
    <nav className="relative z-40 border-b border-white/[0.06] bg-[#060810]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-6">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center border border-[#f97316]/40 bg-[#f97316]/10">
            <span className="font-['Chakra_Petch'] text-xs font-700 tracking-widest text-[#f97316]">IL</span>
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-['Chakra_Petch'] text-sm font-600 tracking-[0.12em] text-white">INFRALENS</span>
            <span className="mt-0.5 text-[10px] tracking-[0.08em] text-[#f97316]/85">INFRASTRUCTURE INTELLIGENCE</span>
          </div>
        </div>

        {/* Step indicators... */}
        <div className="flex items-center gap-0">
          {steps.map((step, index) => {
            const completed = step.number < currentStep;
            const active = step.number === currentStep;

            return (
              <div key={step.number} className="flex items-center">
                <div className="flex items-center gap-2 px-4 py-1">
                  <div
                    className={`flex h-5 w-5 items-center justify-center border text-[10px] font-['IBM_Plex_Mono'] transition-colors ${
                      active
                        ? 'border-[#f97316] bg-[#f97316]/15 text-[#f97316]'
                        : completed
                        ? 'border-[#f97316]/50 bg-[#f97316]/5 text-[#f97316]/60'
                        : 'border-white/10 bg-transparent text-white/25'
                    }`}
                  >
                    {completed ? '✓' : step.number}
                  </div>
                  <span
                    className={`text-[11px] font-['Chakra_Petch'] tracking-[0.1em] transition-colors ${
                      active ? 'text-white' : completed ? 'text-white/40' : 'text-white/20'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div className={`h-px w-8 transition-colors ${completed ? 'bg-[#f97316]/30' : 'bg-white/08'}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onChatOpen}
            className="flex h-8 w-8 items-center justify-center border border-white/08 text-white/30 transition-colors hover:border-white/40 hover:text-[#f97316]/60"
            title="AI Assistant"
          >
            <MessageSquare className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => navigate('/settings')}
            className="flex h-8 w-8 items-center justify-center border border-white/08 text-white/30 transition-colors hover:border-white/40 hover:text-[#f97316]/60"
            title="Settings"
          >
            <Settings className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Active step accent line */}
      <div className="absolute bottom-0 left-0 right-0 h-px">
        <div className="h-full bg-[#f97316]/20" />
      </div>
    </nav>
  );
}
