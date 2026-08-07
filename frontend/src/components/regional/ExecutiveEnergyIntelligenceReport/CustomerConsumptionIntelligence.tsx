import React from 'react';
import type { CustomerConsumptionData } from './types';

interface CustomerConsumptionIntelligenceProps {
  data: CustomerConsumptionData;
  sectionNumber?: number | string;
}

export const CustomerConsumptionIntelligence: React.FC<CustomerConsumptionIntelligenceProps> = React.memo(({
  data,
  sectionNumber = 8,
}) => {
  const {
    monthlyUsageKwh,
    peakDemandKw,
    loadFactorPct,
    seasonalBehavior,
    peerComparison,
    anomaliesObserved,
  } = data;

  return (
    <section className="sec-8 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Customer Consumption Intelligence</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="analysis-box">
          <div className="analysis-header">MONTHLY USAGE</div>
          <div className="analysis-content">
            <span className="text-xl font-bold text-[#2a4b7c] block">{monthlyUsageKwh.toLocaleString()} kWh</span>
            <p className="text-xs text-gray-600 mt-1">Average monthly energy throughput</p>
          </div>
        </div>

        <div className="analysis-box">
          <div className="analysis-header">PEAK DEMAND</div>
          <div className="analysis-content">
            <span className="text-xl font-bold text-[#d35400] block">{peakDemandKw} kW</span>
            <p className="text-xs text-gray-600 mt-1">Coincident peak demand interval</p>
          </div>
        </div>

        <div className="analysis-box">
          <div className="analysis-header">LOAD FACTOR</div>
          <div className="analysis-content">
            <span className="text-xl font-bold text-[#27ae60] block">{loadFactorPct}%</span>
            <p className="text-xs text-gray-600 mt-1">Grid utilization efficiency index</p>
          </div>
        </div>
      </div>

      <div className="market-analysis-grid">
        <div className="analysis-box">
          <div className="analysis-header">SEASONAL BEHAVIOR &amp; PEER COMPARISON</div>
          <div className="analysis-content space-y-2">
            <p><strong>Seasonal Patterns:</strong> {seasonalBehavior}</p>
            <p><strong>Benchmark vs Peers:</strong> {peerComparison}</p>
          </div>
        </div>

        <div className="root-cause">
          <div className="analysis-header">ANOMALIES &amp; UNUSUAL CONSUMPTION</div>
          <div className="analysis-content">
            {anomaliesObserved}
          </div>
        </div>
      </div>
    </section>
  );
});

CustomerConsumptionIntelligence.displayName = 'CustomerConsumptionIntelligence';
export default CustomerConsumptionIntelligence;
