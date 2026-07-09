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
  <div className="card p-8 bg-white border border-slate-200 rounded-2xl max-w-2xl mx-auto space-y-6">
    <div>
      <h2 className="text-2xl font-black text-slate-900">System Settings</h2>
      <p className="text-slate-500 text-xs mt-1">Configure your AI Electricity Bill Assistant environment</p>
    </div>
    <div className="space-y-4 pt-4 border-t border-slate-100">
      <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
        <div>
          <h4 className="text-sm font-bold text-slate-800">Double Machine Learning (DML)</h4>
          <p className="text-xs text-slate-500">Enable causal impact modeling using EconML/DoWhy estimators</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 text-primary bg-slate-100 border-slate-300 rounded focus:ring-primary" />
      </div>
      <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
        <div>
          <h4 className="text-sm font-bold text-slate-800">Local LLM Acceleration</h4>
          <p className="text-xs text-slate-500">Redirect bill explanations to local Ollama server running qwen3:4b</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 text-primary bg-slate-100 border-slate-300 rounded focus:ring-primary" />
      </div>
      <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
        <div>
          <h4 className="text-sm font-bold text-slate-800">OCR Scanner Animation</h4>
          <p className="text-xs text-slate-500">Show sweeping scanline and typing logger during bill parsing</p>
        </div>
        <input type="checkbox" defaultChecked className="w-4 h-4 text-primary bg-slate-100 border-slate-300 rounded focus:ring-primary" />
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
