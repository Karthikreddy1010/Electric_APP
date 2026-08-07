import React from 'react';
import type { WeatherClimateData } from './types';

interface WeatherClimateImpactProps {
  data: WeatherClimateData;
  sectionNumber?: number | string;
}

export const WeatherClimateImpact: React.FC<WeatherClimateImpactProps> = React.memo(({
  data,
  sectionNumber = 10,
}) => {
  const { summary, metrics = [] } = data;

  return (
    <section className="sec-10 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Weather &amp; Climate Impact</h2>

      <p className="section-text">{summary}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {metrics.map((m, idx) => (
          <div key={idx} className="analysis-box">
            <div className="analysis-header">{m.metric}</div>
            <div className="analysis-content space-y-1">
              <span className="text-lg font-bold text-[#2a4b7c] block">{m.value}</span>
              <p className="text-xs text-gray-700"><strong>Bill Impact:</strong> {m.billImpact}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
});

WeatherClimateImpact.displayName = 'WeatherClimateImpact';
export default WeatherClimateImpact;
