import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import Navbar from '../components/Navbar';
import ConnectScreen from '../components/ConnectScreen';
import ScanningScreen from '../components/ScanningScreen';
import DashboardScreen from '../components/DashboardScreen';
import type { ScanConfig } from '../types';

export type { ScanConfig };

export default function MainApp() {
  const [searchParams, setSearchParams] = useSearchParams();
  const stepParam = searchParams.get('step');
  const [currentStep, setCurrentStep] = useState(stepParam ? parseInt(stepParam) : 1);
  const [scanConfig, setScanConfig] = useState<ScanConfig>({
    githubToken: '',
    repoUrl: '',
    branch: 'main',
    doApiKey: '',
    doProject: '',
    regionFilter: '',
  });

  useEffect(() => {
    if (stepParam) {
      const step = parseInt(stepParam);
      if (step >= 1 && step <= 3) setCurrentStep(step);
    }
  }, [stepParam]);

  const goToStep = (step: number) => {
    setCurrentStep(step);
    setSearchParams({ step: step.toString() });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar currentStep={currentStep} />

      {currentStep === 1 && (
        <ConnectScreen
          config={scanConfig}
          onChange={setScanConfig}
          onAnalyze={() => goToStep(2)}
        />
      )}

      {currentStep === 2 && (
        <ScanningScreen
          config={scanConfig}
          onComplete={() => goToStep(3)}
        />
      )}

      {currentStep === 3 && (
        <DashboardScreen
          config={scanConfig}
          onRescan={() => goToStep(2)}
        />
      )}
    </div>
  );
}
