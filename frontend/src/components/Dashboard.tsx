/**
 * Dashboard — tab switcher.
 *
 * Maps activeTab string to the correct page component.
 * Tab order follows the architecture plan (Rev 3):
 *   Overview → Bill Analysis → Impact & Simulation →
 *   Regional Insights → Forecast → Plans → Settings
 *
 * Each case comment documents the page's architectural responsibility.
 */
import BillPage from '../pages/BillPage.tsx';
import ForecastPage from '../pages/ForecastPage.tsx';
import PlansPage from '../pages/PlansPage.tsx';
import SettingsPage from '../pages/SettingsPage.tsx';
import OverviewPage from '../pages/OverviewPage.tsx';

import ImpactPage from '../pages/ImpactPage.tsx';

import RegionalPage from '../pages/RegionalPage.tsx';

interface DashboardProps {
  activeTab: string;
}

const Dashboard = ({ activeTab }: DashboardProps) => {
  switch (activeTab) {
    // Overview — summarizes (Phase A.6, complete ✅)
    case 'Overview':
      return <OverviewPage />;

    // Bill Analysis — ingests (Phase A.3, complete)
    case 'Bill Analysis':
      return <BillPage />;

    // Impact & Simulation — explains and simulates (Phase A.4, complete ✅)
    case 'Impact & Simulation':
      return <ImpactPage />;

    // Regional Insights — compares (Phase A.5, complete ✅)
    case 'Regional Insights':
      return <RegionalPage />;

    // Forecast — predicts (Phase A, complete)
    case 'Forecast':
      return <ForecastPage />;

    // Plans — recommends (Phase A, complete)
    case 'Plans':
      return <PlansPage />;

    // Settings — configures (Phase A, complete)
    case 'Settings':
      return <SettingsPage />;

    default:
      return <OverviewPage />;
  }
};

export default Dashboard;
