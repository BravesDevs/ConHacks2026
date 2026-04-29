import { Check, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ScanningScreenProps {
  onComplete: () => void;
}

export default function ScanningScreen({ onComplete }: ScanningScreenProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 500);
          return 100;
        }
        return prev + 1;
      });
    }, 30);

    return () => clearInterval(interval);
  }, [onComplete]);

  const steps = [
    { id: 1, label: 'Clone repo', completed: progress > 20 },
    { id: 2, label: 'Parse TF', completed: progress > 40 },
    { id: 3, label: 'Fetch DO', completed: progress > 60, active: progress >= 40 && progress <= 60 },
    { id: 4, label: 'AI model', completed: progress > 80, active: progress > 60 && progress <= 80 },
    { id: 5, label: 'Report', completed: progress > 95, active: progress > 80 && progress <= 95 }
  ];

  return (
    <div className="flex min-h-[calc(900px-73px)] items-center justify-center px-8 py-16">
      <div className="w-full max-w-[640px]">
        <div className="mb-12 text-center">
          <h1 className="mb-3 text-3xl dark:text-white">Scanning your infrastructure</h1>
          <p className="text-black/60 dark:text-white/60">
            Fetching repository data and analyzing your DigitalOcean resources
          </p>
        </div>

        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-8">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-black/5 dark:bg-white/5">
              <svg className="h-5 w-5 dark:text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.164 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
              </svg>
            </div>
            <div>
              <div className="font-medium dark:text-white">acme-corp/infra-prod</div>
              <div className="flex items-center gap-2 text-sm text-black/60 dark:text-white/60">
                <span className="rounded-full bg-black/5 dark:bg-white/5 px-2 py-0.5">main</span>
                <span className="rounded-full bg-black/5 dark:bg-white/5 px-2 py-0.5">terraform</span>
                <span className="rounded-full bg-black/5 dark:bg-white/5 px-2 py-0.5">digitalocean</span>
              </div>
            </div>
          </div>

          <div className="mb-3">
            <div className="h-2 w-full overflow-hidden rounded-full bg-black/5 dark:bg-white/5">
              <div
                className="h-full rounded-full bg-[#1D9E75] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            {steps.map(step => (
              <div key={step.id} className="flex flex-col items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border ${
                    step.completed
                      ? 'border-[#1D9E75] bg-[#1D9E75] text-white'
                      : step.active
                      ? 'border-[#1D9E75] bg-white dark:bg-gray-700 text-[#1D9E75]'
                      : 'border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 text-black/20 dark:text-white/20'
                  }`}
                >
                  {step.completed ? (
                    <Check className="h-4 w-4" />
                  ) : step.active ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <div className="h-1.5 w-1.5 rounded-full bg-current" />
                  )}
                </div>
                <span
                  className={`text-xs ${
                    step.completed || step.active ? 'text-black dark:text-white' : 'text-black/40 dark:text-white/40'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
