import { Activity } from 'lucide-react';
import { useNavigation } from '../../context/NavigationContext.tsx';

interface EmptyBillStateProps {
  title?: string;
  description?: string;
  ctaLabel?: string;
  /** Tab name to navigate to when CTA is clicked */
  ctaTab?: string;
}

/**
 * Reusable "no bill uploaded" empty state.
 * Replaces 4 duplicate implementations across ImpactTab, OverviewTab,
 * PlansTab, and RegionalInsights.
 */
const EmptyBillState = ({
  title = 'No active telemetry source',
  description = 'Upload an electricity bill in the Bill Analysis module to unlock this feature.',
  ctaLabel = 'Go to Bill Analysis',
  ctaTab = 'Bill Analysis',
}: EmptyBillStateProps) => {
  const navigate = useNavigation();

  return (
    <div className="panel-operational flex flex-col items-center justify-center p-16 text-center max-w-xl mx-auto space-y-4 my-12 border-dashed border border-border-hairline">
      <Activity size={36} className="text-text-secondary opacity-60" />
      <h3 className="text-sm font-bold text-text-primary">{title}</h3>
      <p className="text-xs text-text-secondary max-w-sm">{description}</p>
      <button
        onClick={() => navigate(ctaTab)}
        className="px-4 py-2.5 bg-bg-surface border border-border-hairline rounded-md text-xs font-semibold hover:bg-bg-primary transition-all shadow-sm"
      >
        {ctaLabel}
      </button>
    </div>
  );
};

export default EmptyBillState;
