import React from 'react';
import type { DriversBehindTrendData } from './types';

interface DriversBehindTrendProps {
  data: DriversBehindTrendData;
  sectionNumber?: number | string;
}

export const DriversBehindTrend: React.FC<DriversBehindTrendProps> = React.memo(({
  data,
  sectionNumber = 6,
}) => {
  const { drivers = [] } = data;

  return (
    <section className="sec-6">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Drivers Behind the Trend</h2>

      <div className="market-analysis-grid">
        {drivers.map((driver, idx) => (
          <div key={idx} className="analysis-box">
            <div className="analysis-header flex justify-between items-center">
              <span>{driver.title}</span>
              <span className="text-[11px] font-normal text-text-secondary bg-primary-blue/10 px-2 py-0.5 rounded border border-primary-blue/20">
                {driver.impact}
              </span>
            </div>
            <div className="analysis-content">
              {driver.description}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
});

DriversBehindTrend.displayName = 'DriversBehindTrend';
export default DriversBehindTrend;
