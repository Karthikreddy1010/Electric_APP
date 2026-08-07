import React from 'react';
import type { ExecutiveSummaryData } from './types';

interface ExecutiveSummaryProps {
  data: ExecutiveSummaryData;
  sectionNumber?: number | string;
}

export const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = React.memo(({
  data,
  sectionNumber = 1,
}) => {
  const { primaryFinding, briefing } = data;

  return (
    <section className="sec-1">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Executive Summary</h2>
      <div className="primary-finding">
        PRIMARY FINDING: <span>{primaryFinding}</span>
      </div>
      <p className="section-text">{briefing}</p>
    </section>
  );
});

ExecutiveSummary.displayName = 'ExecutiveSummary';
export default ExecutiveSummary;
