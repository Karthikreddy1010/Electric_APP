import React from 'react';
import type { MarketAnalysisData } from './types';

interface RegionalMarketAnalysisProps {
  data: MarketAnalysisData;
  sectionNumber?: number | string;
}

export const RegionalMarketAnalysis: React.FC<RegionalMarketAnalysisProps> = React.memo(({
  data,
  sectionNumber = 2,
}) => {
  const { pricesTrajectory, consumptionSeasonality, rootCauseAttribution } = data;

  return (
    <section className="sec-2">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Regional Market Analysis</h2>
      
      <div className="market-analysis-grid">
        <div className="analysis-box">
          <div className="analysis-header">PRICES &amp; TRAJECTORY</div>
          <div className="analysis-content">
            {pricesTrajectory}
          </div>
        </div>
        <div className="analysis-box">
          <div className="analysis-header">CONSUMPTION &amp; SEASONALITY</div>
          <div className="analysis-content">
            {consumptionSeasonality}
          </div>
        </div>
      </div>

      <div className="root-cause">
        <div className="analysis-header">ROOT CAUSE ATTRIBUTION</div>
        <div className="analysis-content">
          {rootCauseAttribution}
        </div>
      </div>
    </section>
  );
});

RegionalMarketAnalysis.displayName = 'RegionalMarketAnalysis';
export default RegionalMarketAnalysis;
