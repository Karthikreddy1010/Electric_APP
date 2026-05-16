import { clsx } from 'clsx';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const tabs = ['Overview', 'Forecast', 'Impact', 'Benchmark', 'Geo Insights', 'Plans'];

const Header = ({ activeTab, setActiveTab }: HeaderProps) => {
  return (
    <header className="bg-white border-b border-border h-16 flex items-center px-8 sticky top-0 z-50">
      <div className="flex items-center gap-8 w-full max-w-7xl mx-auto">
        <span className="text-xl font-bold text-slate-900 tracking-tight">ElectricAI</span>
        
        <nav className="flex items-center gap-2 h-full ml-4">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                "nav-link text-sm h-16 flex items-center",
                activeTab === tab && "active"
              )}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Header;
