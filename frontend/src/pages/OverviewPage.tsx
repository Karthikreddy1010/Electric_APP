/**
 * Overview Page — adaptive shell.
 *
 * Architecture rule: Overview summarizes.
 *
 * State A (hasBill === false): Onboarding Hero — premium landing experience
 *   with animated SVG illustration, feature highlights, and onboarding timeline.
 *
 * State B (hasBill === true): Mission Control — summary KPI dashboard
 *   with deep-links to all other pages. No detailed charts or analysis here.
 */
import MissionControlDashboard from './overview/MissionControlDashboard.tsx';

const OverviewPage = () => {
  return <MissionControlDashboard />;
};

export default OverviewPage;

