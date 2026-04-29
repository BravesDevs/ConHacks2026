import { Check, Settings } from 'lucide-react';
import { useNavigate } from 'react-router';

interface NavbarProps {
  currentStep: number;
}

export default function Navbar({ currentStep }: NavbarProps) {
  const navigate = useNavigate();
  const steps = [
    { number: 1, label: 'Connect' },
    { number: 2, label: 'Scan' },
    { number: 3, label: 'Insights' }
  ];

  return (
    <nav className="border-b border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 px-8 py-4">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-[#1D9E75]" />
          <span className="font-medium dark:text-white">InfraLens</span>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
          {steps.map((step, index) => (
            <div key={step.number} className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div
                  className={`flex h-6 w-6 items-center justify-center rounded-full border ${
                    step.number === currentStep
                      ? 'border-[#1D9E75] bg-[#1D9E75] text-white'
                      : step.number < currentStep
                      ? 'border-[#1D9E75] bg-[#1D9E75] text-white'
                      : 'border-black/20 dark:border-white/20 bg-white dark:bg-gray-700 text-black/40 dark:text-white/40'
                  }`}
                >
                  {step.number < currentStep ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <span className="text-sm">{step.number}</span>
                  )}
                </div>
                <span
                  className={`text-sm ${
                    step.number === currentStep
                      ? 'text-black dark:text-white'
                      : step.number < currentStep
                      ? 'text-black/60 dark:text-white/60'
                      : 'text-black/40 dark:text-white/40'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div className="h-px w-12 bg-black/10 dark:bg-white/10" />
              )}
            </div>
          ))}
          </div>

          <button
            onClick={() => navigate('/settings')}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-black/60 dark:text-white/60 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}
