import React, { useMemo } from 'react';
import type { CostBreakdownData } from './types';

interface CostBreakdownProps {
  data: CostBreakdownData;
  stateCode?: string;
  sectionNumber?: number | string;
}

export const CostBreakdown: React.FC<CostBreakdownProps> = React.memo(({
  data,
  stateCode = 'NJ',
  sectionNumber = 3,
}) => {
  const {
    totalRatePerKwh,
    generationPct = 42.5,
    transmissionPct = 21.0,
    distributionPct = 24.5,
    taxesFeesPct = 12.0,
    currency = '$',
    unit = '/kWh'
  } = data;

  const totalPct = (generationPct + transmissionPct + distributionPct + taxesFeesPct) || 100;
  const barHeight = 70; // Pixel height matching Stitch preview

  const heights = useMemo(() => ({
    tax: Math.max(6, (taxesFeesPct / totalPct) * barHeight),
    dist: Math.max(6, (distributionPct / totalPct) * barHeight),
    trans: Math.max(6, (transmissionPct / totalPct) * barHeight),
    gen: Math.max(10, (generationPct / totalPct) * barHeight),
  }), [generationPct, transmissionPct, distributionPct, taxesFeesPct, totalPct]);

  const formattedRate = `${currency}${totalRatePerKwh.toFixed(4)}${unit}`;

  return (
    <section className="sec-3">
      <div className="cost-breakdown">
        <div>
          <div className="section-label">SECTION {sectionNumber}</div>
          <h2 className="serif-title">Cost Breakdown</h2>
        </div>
        
        <div className="chart-container">
          <div className="chart-stack-wrapper">
            <div className="stacked-bar" style={{ height: `${barHeight}px` }}>
              <div
                className="bar-segment seg-tax"
                style={{ height: `${heights.tax}px` }}
                title={`Taxes & Fees: ${taxesFeesPct}%`}
              />
              <div
                className="bar-segment seg-dist"
                style={{ height: `${heights.dist}px` }}
                title={`Distribution: ${distributionPct}%`}
              />
              <div
                className="bar-segment seg-trans"
                style={{ height: `${heights.trans}px` }}
                title={`Transmission: ${transmissionPct}%`}
              />
              <div
                className="bar-segment seg-gen"
                style={{ height: `${heights.gen}px` }}
                title={`Generation: ${generationPct}%`}
              />
            </div>
            <div className="chart-label">{stateCode} Regional Rate ({formattedRate})</div>
          </div>
          
          <div className="chart-legend">
            <div className="legend-item">
              <div className="legend-color seg-gen" /> Generation
            </div>
            <div className="legend-item">
              <div className="legend-color seg-trans" /> Transmission
            </div>
            <div className="legend-item">
              <div className="legend-color seg-dist" /> Distribution
            </div>
            <div className="legend-item">
              <div className="legend-color seg-tax" /> Taxes &amp; Fees
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});

CostBreakdown.displayName = 'CostBreakdown';
export default CostBreakdown;
