import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import Navbar from '../components/Navbar';
import ConnectScreen from '../components/ConnectScreen';
import ScanningScreen from '../components/ScanningScreen';
import DashboardScreen from '../components/DashboardScreen';
import { supabase } from '@/lib/supabase';
import { useAuth } from '../context/AuthContext';

export interface ScanConfig {
  repoUrl: string;
  branch: string;
  terraformPath: string;
  doProject: string;
  regionFilter: string;
}

export default function MainApp() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const stepParam = searchParams.get('step');
  const [currentStep, setCurrentStep] = useState(stepParam ? parseInt(stepParam) : 1);
  const [scanConfig, setScanConfig] = useState<ScanConfig>({
    repoUrl: '',
    branch: 'main',
    terraformPath: '/infra',
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

  const handleScanComplete = async () => {
    if (user) {
      await supabase.from('scan_history').insert({
        user_id: user.id,
        repo_url: scanConfig.repoUrl,
        branch: scanConfig.branch,
        terraform_path: scanConfig.terraformPath,
        do_project: scanConfig.doProject,
        region_filter: scanConfig.regionFilter,
        results: {
          monthly_spend: 1248,
          potential_savings: 347,
          resources_flagged: 7,
          total_resources: 24,
        },
      });
    }
    goToStep(3);
  };

  return (
    <div className="min-h-screen bg-[#F5F5F2] dark:bg-gray-900">
      <Navbar currentStep={currentStep} />

      {currentStep === 1 && (
        <ConnectScreen
          config={scanConfig}
          onChange={setScanConfig}
          onAnalyze={() => goToStep(2)}
        />
      )}

      {currentStep === 2 && (
        <ScanningScreen onComplete={handleScanComplete} />
      )}

      {currentStep === 3 && (
        <DashboardScreen onRescan={() => goToStep(2)} />
      )}
    </div>
  );
}
