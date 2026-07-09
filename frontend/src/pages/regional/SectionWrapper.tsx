import type { ReactNode } from 'react';

interface SectionWrapperProps {
  title: string;
  description: string;
  badge?: string;
  children: ReactNode;
}

/**
 * Enterprise section wrapper for Regional Insights sections.
 * Ensures consistent borders, headings, typography, and responsive padding.
 */
const SectionWrapper = ({ title, description, badge, children }: SectionWrapperProps) => {
  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1.5 border-b border-border-hairline pb-3">
        <div>
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">{title}</h3>
          <p className="text-[11px] text-text-secondary font-medium mt-0.5">{description}</p>
        </div>
        {badge && (
          <span className="self-start sm:self-auto bg-primary-blue/10 border border-primary-blue/20 text-primary-blue text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-[4px]">
            {badge}
          </span>
        )}
      </div>
      <div className="pt-2">{children}</div>
    </div>
  );
};

export default SectionWrapper;
