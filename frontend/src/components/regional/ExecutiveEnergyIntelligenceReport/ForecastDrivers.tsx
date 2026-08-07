import React from 'react';
import type { ForecastDriversData } from './types';

interface ForecastDriversProps {
  data: ForecastDriversData;
  sectionNumber?: number | string;
}

export const ForecastDrivers: React.FC<ForecastDriversProps> = React.memo(({
  data,
  sectionNumber = 11,
}) => {
  const { drivers = [] } = data;

  return (
    <section className="sec-11 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Forecast Drivers &amp; Regression Evidence</h2>

      <div className="overflow-x-auto border border-gray-300">
        <table className="risk-matrix">
          <thead>
            <tr>
              <th style={{ width: '25%' }}>Forecast Driver</th>
              <th style={{ width: '15%' }}>Contribution</th>
              <th style={{ width: '15%' }}>Model Confidence</th>
              <th style={{ width: '45%' }}>Supporting Telemetry &amp; Evidence</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d, idx) => (
              <tr key={idx}>
                <td>{d.factor}</td>
                <td className="font-bold text-[#2a4b7c]">{d.contributionPct}%</td>
                <td>
                  <span className="badge low" style={{ width: '70px', fontSize: '11px' }}>
                    {d.confidencePct}%
                  </span>
                </td>
                <td>{d.supportingEvidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

ForecastDrivers.displayName = 'ForecastDrivers';
export default ForecastDrivers;
