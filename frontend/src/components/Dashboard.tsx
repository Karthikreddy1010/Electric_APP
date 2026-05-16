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
  return (
    <div className="space-y-6">
      {activeTab === 'Overview' && <OverviewTab />}
      {activeTab === 'Forecast' && <ForecastTab />}
      {activeTab === 'Impact' && <ImpactTab />}
      {activeTab === 'Benchmark' && <BenchmarkTab />}
      {activeTab === 'Geo Insights' && <GeoTab />}
      {activeTab === 'Plans' && <PlansTab />}
    </div>
  );
};

export default Dashboard;
