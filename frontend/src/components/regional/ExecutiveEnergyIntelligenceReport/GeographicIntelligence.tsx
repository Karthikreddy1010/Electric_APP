import React from 'react';
import type { GeographicIntelligenceData } from './types';

interface GeographicIntelligenceProps {
  data: GeographicIntelligenceData;
  sectionNumber?: number | string;
}

export const GeographicIntelligence: React.FC<GeographicIntelligenceProps> = React.memo(({
  data,
  sectionNumber = 7,
}) => {
  const { summary, metrics = [] } = data;

  return (
    <section className="sec-7 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Geographic Intelligence</h2>

      <p className="section-text">{summary}</p>

      <div className="overflow-x-auto border border-gray-300">
        <table className="risk-matrix">
          <thead>
            <tr>
              <th style={{ width: '25%' }}>Municipality / Sub-Territory</th>
              <th style={{ width: '20%' }}>Average Rate</th>
              <th style={{ width: '20%' }}>Grid Status</th>
              <th style={{ width: '35%' }}>Benchmark Notes</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((item, idx) => (
              <tr key={idx}>
                <td>{item.location}</td>
                <td>{item.avgRate}</td>
                <td>
                  <span className="badge low" style={{ width: '80px', fontSize: '11px' }}>
                    {item.status}
                  </span>
                </td>
                <td>{item.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

GeographicIntelligence.displayName = 'GeographicIntelligence';
export default GeographicIntelligence;
