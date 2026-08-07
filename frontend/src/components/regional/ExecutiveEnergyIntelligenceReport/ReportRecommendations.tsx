import React from 'react';
import type { ReportRecommendationsData } from './types';

interface ReportRecommendationsProps {
  data: ReportRecommendationsData;
  sectionNumber?: number | string;
}

export const ReportRecommendations: React.FC<ReportRecommendationsProps> = React.memo(({
  data,
  sectionNumber = 12,
}) => {
  const { recommendations = [] } = data;

  return (
    <section className="sec-12 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Actionable Executive Recommendations</h2>

      <div className="overflow-x-auto border border-gray-300">
        <table className="risk-matrix">
          <thead>
            <tr>
              <th style={{ width: '20%' }}>Target Stakeholder</th>
              <th style={{ width: '45%' }}>Recommended Strategic Action</th>
              <th style={{ width: '35%' }}>Expected Quantifiable Outcome</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((rec, idx) => (
              <tr key={idx}>
                <td>{rec.target}</td>
                <td>{rec.action}</td>
                <td className="font-bold text-[#27ae60]">{rec.expectedOutcome}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

ReportRecommendations.displayName = 'ReportRecommendations';
export default ReportRecommendations;
