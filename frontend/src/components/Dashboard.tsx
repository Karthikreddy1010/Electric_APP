import OverviewTab from './tabs/OverviewTab.tsx';
import BillAnalysisTab from './tabs/BillAnalysisTab.tsx';
import ForecastTab from './tabs/ForecastTab.tsx';
import ImpactTab from './tabs/ImpactTab.tsx';
import WhatIfTab from './tabs/WhatIfTab.tsx';
import BenchmarkTab from './tabs/BenchmarkTab.tsx';
import GeoTab from './tabs/GeoTab.tsx';
import PlansTab from './tabs/PlansTab.tsx';
import UtilityTab from './tabs/UtilityTab.tsx';

interface DashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  uploadedBill: any;
  setUploadedBill: (bill: any) => void;
  ocrRuns: any[] | null;
  setOcrRuns: (runs: any[] | null) => void;
  billExplanation: string | null;
  setBillExplanation: (explanation: string | null) => void;
}

const SettingsTab = () => (
  <div className="panel-operational max-w-2xl mx-auto space-y-6 bg-bg-surface border border-border-hairline shadow-sm">
    <div>
      <h2 className="text-xl font-bold text-text-primary">System settings</h2>
      <p className="text-text-secondary text-xs mt-1">Configure your AI Electricity Bill Assistant environment</p>
    </div>
    <div className="space-y-4 pt-4 border-t border-border-hairline">
      <div className="flex items-center justify-between p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
        <div>
          <h4 className="text-sm font-bold text-text-primary">Double machine learning (DML)</h4>
          <p className="text-xs text-text-secondary">Enable causal impact modeling using EconML/DoWhy estimators</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 accent-primary-blue rounded focus:ring-primary-blue bg-bg-surface border-border-hairline" aria-label="Toggle DML" />
      </div>
      <div className="flex items-center justify-between p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
        <div>
          <h4 className="text-sm font-bold text-text-primary">Local LLM acceleration</h4>
          <p className="text-xs text-text-secondary">Redirect bill explanations to local Ollama server running qwen3:4b</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 accent-primary-blue rounded focus:ring-primary-blue bg-bg-surface border-border-hairline" aria-label="Toggle Local LLM Acceleration" />
      </div>
      <div className="flex items-center justify-between p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
        <div>
          <h4 className="text-sm font-bold text-text-primary">OCR scanner animation</h4>
          <p className="text-xs text-text-secondary">Show sweeping scanline and typing logger during bill parsing</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 accent-primary-blue rounded focus:ring-primary-blue bg-bg-surface border-border-hairline" aria-label="Toggle OCR Scanner Animation" />
      </div>
    </div>
  </div>
);

const Dashboard = ({ 
  activeTab, 
  setActiveTab,
  uploadedBill, 
  setUploadedBill,
  ocrRuns,
  setOcrRuns,
  billExplanation,
  setBillExplanation
}: DashboardProps) => {
  switch (activeTab) {
    case 'Bill Analysis': 
      return (
        <BillAnalysisTab 
          uploadedBill={uploadedBill} 
          setUploadedBill={setUploadedBill}
          ocrRuns={ocrRuns}
          setOcrRuns={setOcrRuns}
          billExplanation={billExplanation}
          setBillExplanation={setBillExplanation}
          setActiveTab={setActiveTab}
        />
      );
    case 'Overview': return <OverviewTab uploadedBill={uploadedBill} setActiveTab={setActiveTab} />;
    case 'Forecast': return <ForecastTab />;
    case 'Bill Impact': return <ImpactTab uploadedBill={uploadedBill} setActiveTab={setActiveTab} />;
    case 'What-If Simulator': return <WhatIfTab uploadedBill={uploadedBill} setActiveTab={setActiveTab} />;
    case 'Benchmark': return <BenchmarkTab uploadedBill={uploadedBill} setActiveTab={setActiveTab} />;
    case 'Geo Insights': return <GeoTab />;
    case 'Plans': return <PlansTab uploadedBill={uploadedBill} setActiveTab={setActiveTab} />;
    case 'Utility Intelligence': return <UtilityTab />;
    case 'Settings': return <SettingsTab />;
    default: 
      return (
        <BillAnalysisTab 
          uploadedBill={uploadedBill} 
          setUploadedBill={setUploadedBill}
          ocrRuns={ocrRuns}
          setOcrRuns={setOcrRuns}
          billExplanation={billExplanation}
          setBillExplanation={setBillExplanation}
          setActiveTab={setActiveTab}
        />
      );
  }
};

export default Dashboard;
// Force IDE typescript language server refresh
