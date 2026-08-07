import React from 'react';
import type { ForecastOutlookData, ForecastHorizon } from './types';

interface ForecastOutlookProps {
  data: ForecastOutlookData;
  sectionNumber?: number | string;
}

export const ForecastOutlook: React.FC<ForecastOutlookProps> = React.memo(({
  data,
  sectionNumber = 5,
}) => {
  const { shortTerm, mediumTerm, longTerm } = data;

  const renderCard = (horizonData: ForecastHorizon) => {
    if (!horizonData) return null;
    const assumptionsArr = Array.isArray(horizonData.assumptions)
      ? horizonData.assumptions
      : horizonData.assumptions ? [horizonData.assumptions] : [];

    return (
      <div className="forecast-card" key={horizonData.horizon}>
        <div className="forecast-header">{horizonData.horizon}</div>
        <div className="forecast-content">
          <p>
            <strong>Confidence Level:</strong> {horizonData.confidence}
          </p>
          <p>
            <strong>Change:</strong> {horizonData.change}
          </p>
          <p>
            <strong>Assumptions:</strong>
          </p>
          <ul>
            {assumptionsArr.map((assumption, idx) => (
              <li key={idx}>{assumption}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  };

  return (
    <section className="sec-5">
      <h2 className="serif-title">
        <span className="section-label" style={{ fontSize: '24px', fontFamily: 'Arial, sans-serif' }}>
          SECTION {sectionNumber}.
        </span>{' '}
        Multi-Horizon Forecast Outlook
      </h2>

      <div className="forecast-grid">
        {shortTerm && renderCard(shortTerm)}
        {mediumTerm && renderCard(mediumTerm)}
        {longTerm && renderCard(longTerm)}
      </div>
    </section>
  );
});

ForecastOutlook.displayName = 'ForecastOutlook';
export default ForecastOutlook;
