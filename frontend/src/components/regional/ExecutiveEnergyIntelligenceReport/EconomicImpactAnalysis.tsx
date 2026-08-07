import React from 'react';
import type { EconomicImpactData } from './types';

interface EconomicImpactAnalysisProps {
  data: EconomicImpactData;
  sectionNumber?: number | string;
}

export const EconomicImpactAnalysis: React.FC<EconomicImpactAnalysisProps> = React.memo(({
  data,
  sectionNumber = 9,
}) => {
  const { impacts = [] } = data;

  return (
    <section className="sec-9 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Economic Impact Analysis</h2>

      <div className="overflow-x-auto border border-gray-300">
        <table className="risk-matrix">
          <thead>
            <tr>
              <th style={{ width: '20%' }}>Customer Sector</th>
              <th style={{ width: '20%' }}>Bill Impact</th>
              <th style={{ width: '35%' }}>Operational &amp; Grid Implications</th>
              <th style={{ width: '25%' }}>Savings Opportunity</th>
            </tr>
          </thead>
          <tbody>
            {impacts.map((item, idx) => (
              <tr key={idx}>
                <td>{item.sector}</td>
                <td>
                  <span className="font-bold text-[#2a4b7c]">{item.billImpact}</span>
                </td>
                <td>{item.operationalImpact}</td>
                <td className="text-[#27ae60] font-bold">{item.savingsOpportunity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

EconomicImpactAnalysis.displayName = 'EconomicImpactAnalysis';
export default EconomicImpactAnalysis;
