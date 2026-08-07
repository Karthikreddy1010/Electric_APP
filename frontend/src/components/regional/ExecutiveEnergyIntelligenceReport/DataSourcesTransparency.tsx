import React from 'react';
import type { DataSourcesData } from './types';

interface DataSourcesTransparencyProps {
  data: DataSourcesData;
  sectionNumber?: number | string;
}

export const DataSourcesTransparency: React.FC<DataSourcesTransparencyProps> = React.memo(({
  data,
  sectionNumber = 14,
}) => {
  const { sources = [], limitations } = data;

  return (
    <section className="sec-14 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">Data Sources &amp; Transparency Manifest</h2>

      <div className="overflow-x-auto border border-gray-300">
        <table className="risk-matrix">
          <thead>
            <tr>
              <th style={{ width: '25%' }}>Dataset Name</th>
              <th style={{ width: '25%' }}>Date Range</th>
              <th style={{ width: '20%' }}>Update Cadence</th>
              <th style={{ width: '30%' }}>Analytical Model / Engine</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((src, idx) => (
              <tr key={idx}>
                <td>{src.name}</td>
                <td>{src.dateRange}</td>
                <td>{src.updateFrequency}</td>
                <td>{src.model}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="root-cause">
        <div className="analysis-header">METHODOLOGICAL ASSUMPTIONS &amp; LIMITATIONS</div>
        <div className="analysis-content">
          {limitations}
        </div>
      </div>
    </section>
  );
});

DataSourcesTransparency.displayName = 'DataSourcesTransparency';
export default DataSourcesTransparency;
