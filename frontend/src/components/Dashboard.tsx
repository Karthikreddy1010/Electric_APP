import OverviewTab from './tabs/OverviewTab.tsx';
import ForecastTab from './tabs/ForecastTab.tsx';
import ImpactTab from './tabs/ImpactTab.tsx';
import WhatIfTab from './tabs/WhatIfTab.tsx';
import CausalTab from './tabs/CausalTab.tsx';
import BenchmarkTab from './tabs/BenchmarkTab.tsx';
import GeoTab from './tabs/GeoTab.tsx';
import PlansTab from './tabs/PlansTab.tsx';
import UtilityTab from './tabs/UtilityTab.tsx';

interface DashboardProps {
  activeTab: string;
}

const Dashboard = ({ activeTab }: DashboardProps) => {
  switch (activeTab) {
    case 'Overview': return <OverviewTab />;
    case 'Forecast': return <ForecastTab />;
    case 'Impact': return <ImpactTab />;
    case 'What-If Scenario': return <WhatIfTab />;
    case 'Causal Analysis': return <CausalTab />;
    case 'Benchmark': return <BenchmarkTab />;
    case 'Geo Insights': return <GeoTab />;
    case 'Plans': return <PlansTab />;
    case 'Utility Intelligence': return <UtilityTab />;
    default: return <OverviewTab />;
  }
};

export default Dashboard;
