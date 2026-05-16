import OverviewTab from './tabs/OverviewTab.tsx';
import ForecastTab from './tabs/ForecastTab.tsx';
import ImpactTab from './tabs/ImpactTab.tsx';
import BenchmarkTab from './tabs/BenchmarkTab.tsx';
import GeoTab from './tabs/GeoTab.tsx';
import PlansTab from './tabs/PlansTab.tsx';

interface DashboardProps {
  activeTab: string;
}

const Dashboard = ({ activeTab }: DashboardProps) => {
  switch (activeTab) {
    case 'Overview': return <OverviewTab />;
    case 'Forecast': return <ForecastTab />;
    case 'Impact': return <ImpactTab />;
    case 'Benchmark': return <BenchmarkTab />;
    case 'Geo Insights': return <GeoTab />;
    case 'Plans': return <PlansTab />;
    default: return <OverviewTab />;
  }
};

export default Dashboard;
