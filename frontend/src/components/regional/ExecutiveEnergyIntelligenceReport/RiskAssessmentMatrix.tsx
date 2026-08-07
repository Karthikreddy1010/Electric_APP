import React from 'react';
import type { RiskAssessmentData, RiskSeverity } from './types';

interface RiskAssessmentMatrixProps {
  data: RiskAssessmentData;
  sectionNumber?: number | string;
}

export const RiskAssessmentMatrix: React.FC<RiskAssessmentMatrixProps> = React.memo(({
  data,
  sectionNumber = 4,
}) => {
  const { risks = [] } = data;

  const getBadgeClass = (severity: RiskSeverity | string) => {
    const sev = (severity || 'low').toString().toLowerCase();
    if (sev.includes('high')) return 'badge high';
    if (sev.includes('medium') || sev.includes('med')) return 'badge medium';
    return 'badge low';
  };

  return (
    <section className="sec-4">
      <h2 className="serif-title">
        <span className="section-label" style={{ fontSize: '24px', fontFamily: 'Arial, sans-serif' }}>
          SECTION {sectionNumber}.
        </span>{' '}
        Regional Risk Assessment Matrix
      </h2>
      <table className="risk-matrix">
        <thead>
          <tr>
            <th style={{ width: '20%' }}>Risk Category</th>
            <th style={{ width: '20%' }}>Status &amp; Badge</th>
            <th style={{ width: '60%' }}>Justification</th>
          </tr>
        </thead>
        <tbody>
          {risks.map((item, idx) => (
            <tr key={`${item.category}-${idx}`}>
              <td>{item.category}</td>
              <td>
                <span className={getBadgeClass(item.severity)}>
                  {item.severity.endsWith('Risk') ? item.severity : `${item.severity} Risk`}
                </span>
              </td>
              <td>{item.justification}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
});

RiskAssessmentMatrix.displayName = 'RiskAssessmentMatrix';
export default RiskAssessmentMatrix;
