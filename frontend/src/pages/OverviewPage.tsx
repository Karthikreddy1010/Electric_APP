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
import { useBill } from '../context/BillContext.tsx';
import OnboardingHero from './overview/OnboardingHero.tsx';
import MissionControlDashboard from './overview/MissionControlDashboard.tsx';

const OverviewPage = () => {
  const { hasBill } = useBill();
  return hasBill ? <MissionControlDashboard /> : <OnboardingHero />;
};

export default OverviewPage;
