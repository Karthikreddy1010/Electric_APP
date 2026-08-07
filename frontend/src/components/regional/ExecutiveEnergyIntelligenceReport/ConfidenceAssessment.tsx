import React from 'react';
import type { ConfidenceAssessmentData } from './types';

interface ConfidenceAssessmentProps {
  data: ConfidenceAssessmentData;
  sectionNumber?: number | string;
}

export const ConfidenceAssessment: React.FC<ConfidenceAssessmentProps> = React.memo(({
  data,
  sectionNumber = 13,
}) => {
  const {
    overallConfidencePct,
    dataCompletenessPct,
    modelAgreementPct,
    qualityScore,
    availableDatasets = [],
    missingDatasets = [],
  } = data;

  return (
    <section className="sec-13 space-y-3">
      <div className="section-label">SECTION {sectionNumber}</div>
      <h2 className="serif-title">AI Confidence &amp; Model Data Quality Assessment</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div className="bg-gray-50 border border-gray-200 p-3 rounded text-center">
          <span className="text-gray-500 uppercase font-bold text-[10px] block">Overall AI Confidence</span>
          <span className="text-xl font-bold text-[#2a4b7c] mt-0.5 block">{overallConfidencePct}%</span>
        </div>

        <div className="bg-gray-50 border border-gray-200 p-3 rounded text-center">
          <span className="text-gray-500 uppercase font-bold text-[10px] block">Data Completeness</span>
          <span className="text-xl font-bold text-[#27ae60] mt-0.5 block">{dataCompletenessPct}%</span>
        </div>

        <div className="bg-gray-50 border border-gray-200 p-3 rounded text-center">
          <span className="text-gray-500 uppercase font-bold text-[10px] block">Model Agreement</span>
          <span className="text-xl font-bold text-[#d35400] mt-0.5 block">{modelAgreementPct}%</span>
        </div>

        <div className="bg-gray-50 border border-gray-200 p-3 rounded text-center">
          <span className="text-gray-500 uppercase font-bold text-[10px] block">Quality Grade</span>
          <span className="text-xl font-bold text-gray-900 mt-0.5 block">{qualityScore}</span>
        </div>
      </div>

      <div className="market-analysis-grid">
        <div className="analysis-box">
          <div className="analysis-header">INCLUDED DATASETS ({availableDatasets.length})</div>
          <div className="analysis-content">
            <ul className="list-disc pl-4 space-y-1">
              {availableDatasets.map((ds, idx) => (
                <li key={idx} className="text-xs text-gray-800">
                  <span className="text-green-600 font-bold">✓</span> {ds}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="analysis-box">
          <div className="analysis-header">DATASET LIMITATIONS &amp; GAPS</div>
          <div className="analysis-content">
            {missingDatasets.length > 0 ? (
              <ul className="list-disc pl-4 space-y-1">
                {missingDatasets.map((ds, idx) => (
                  <li key={idx} className="text-xs text-gray-600">
                    <span className="text-amber-600 font-bold">•</span> {ds}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-green-700 font-medium">No critical data gaps detected. Full historical telemetry validated.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
});

ConfidenceAssessment.displayName = 'ConfidenceAssessment';
export default ConfidenceAssessment;
