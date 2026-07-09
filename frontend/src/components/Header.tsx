import { Activity } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  uploadedBill?: any;
}

const Header = ({ activeTab, setActiveTab, uploadedBill }: HeaderProps) => {
  const tabs = [
    'Overview', 
    'Bill Analysis', 
    'Forecast', 
    'Impact & Simulation', 
    'Benchmark', 
    'Geo Insights', 
    'Plans', 
    'Utility Intelligence', 
    'Settings'
  ];

  // Utility Load Strip configuration
  const minRate = 0.10;
  const maxRate = 0.25;
  const getPct = (val: number) => {
    return Math.min(100, Math.max(0, ((val - minRate) / (maxRate - minRate)) * 100));
  };

  const curRate = uploadedBill?.effective_rate || 0.1852;
  const stateAvg = 0.1780;
  const natAvg = 0.1648;

  const curPct = getPct(curRate);
  const statePct = getPct(stateAvg);
  const natPct = getPct(natAvg);

  return (
    <header className="bg-bg-surface border-b border-border-hairline text-text-primary sticky top-0 z-50 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-[6px] flex items-center justify-center bg-bg-primary border border-border-hairline text-primary-blue">
            <Activity size={16} />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight font-sans text-text-primary">ElectricAI</span>
            <span className="text-[8px] tracking-wider uppercase font-mono text-text-secondary">Operational Intelligence</span>
          </div>
        </div>

        {/* Header Metadata Context (Always visible if bill exists) */}
        {uploadedBill && (
          <div className="hidden lg:flex items-center gap-4 border-l border-border-hairline pl-4 text-xs">
            <div className="flex flex-col">
              <span className="text-[9px] text-text-secondary uppercase">Current Utility</span>
              <span className="font-mono-numbers text-text-primary font-bold">{uploadedBill.utility}</span>
            </div>
            <div className="flex flex-col border-l border-border-hairline pl-4">
              <span className="text-[9px] text-text-secondary uppercase">Billing Cycle</span>
              <span className="font-mono-numbers text-text-primary">{uploadedBill.bill_date || uploadedBill.billing_period}</span>
            </div>
            <div className="flex flex-col border-l border-border-hairline pl-4">
              <span className="text-[9px] text-text-secondary uppercase">Current Effective Rate</span>
              <span className="font-mono-numbers text-primary-blue font-bold">${uploadedBill.effective_rate?.toFixed(4)}/kWh</span>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <nav className="hidden md:flex items-center gap-1 overflow-x-auto py-1">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-semibold transition-all shrink-0 ${
                activeTab === tab 
                  ? 'bg-bg-primary text-primary-blue border border-border-hairline' 
                  : 'text-text-secondary border border-transparent hover:text-text-primary hover:bg-bg-primary/50'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>

        {/* Persistent Utility Load Strip */}
        <div className="flex flex-col w-[180px] shrink-0">
          <div className="flex justify-between items-center text-[8px] font-mono-numbers leading-none text-text-secondary">
            <span>$0.10</span>
            <span className="uppercase tracking-wider">Load Strip</span>
            <span>$0.25</span>
          </div>
          <div className="relative h-1.5 border rounded-full mt-1 bg-bg-primary border-border-hairline">
            {/* National Average Marker */}
            <div 
              className="absolute top-0 bottom-0 w-0.5 bg-text-secondary opacity-60"
              style={{ left: `${natPct}%` }}
            />
            {/* State Average Marker */}
            <div 
              className="absolute top-0 bottom-0 w-0.5 bg-warning-amber"
              style={{ left: `${statePct}%` }}
            />
            {/* Current Rate Marker (animating) */}
            <div 
              className="absolute -top-[3px] w-2 h-3 bg-primary-blue transition-all duration-350 ease-out rounded-sm"
              style={{ left: `calc(${curPct}% - 4px)` }}
            />
          </div>
          <div className="relative h-2.5 text-[7px] text-text-secondary mt-0.5 font-mono-numbers leading-none">
            <span className="absolute" style={{ left: `${natPct}%`, transform: 'translateX(-50%)' }}>NAT</span>
            <span className="absolute text-warning-amber" style={{ left: `${statePct}%`, transform: 'translateX(-50%)' }}>STATE</span>
            <span className="absolute text-primary-blue font-bold" style={{ left: `${curPct}%`, transform: 'translateX(-50%)', transition: 'left 350ms ease-out' }}>CUR</span>
          </div>
        </div>

      </div>
    </header>
  );
};

export default Header;
