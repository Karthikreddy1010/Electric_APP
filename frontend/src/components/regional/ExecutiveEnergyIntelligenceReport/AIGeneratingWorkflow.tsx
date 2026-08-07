import React from 'react';
import { Loader2, CheckCircle2, Cpu, Sparkles, Layers } from 'lucide-react';

export interface WorkflowStep {
  id: string;
  label: string;
  sectionKey?: string;
}

export const GENERATION_STEPS: WorkflowStep[] = [
  { id: 'init', label: 'Initializing AI Intelligence Engine...' },
  { id: 'profile', label: 'Customer Profile Loaded & Validated' },
  { id: 'usage', label: 'Analyzing Electricity Usage & Interval Telemetry...' },
  { id: 'sec1', label: 'Drafting Executive Summary & Briefing...', sectionKey: 'summary' },
  { id: 'sec2', label: 'Calculating Regional Market Telemetry & Benchmarks...', sectionKey: 'market' },
  { id: 'sec3', label: 'Building Cost Breakdown & Rate Structure...', sectionKey: 'cost' },
  { id: 'sec4', label: 'Performing Regional Risk Vulnerability Matrix...', sectionKey: 'risk' },
  { id: 'sec5', label: 'Computing Multi-Horizon Forecast Outlook...', sectionKey: 'forecast' },
  { id: 'sec6', label: 'Analyzing Macro Drivers Behind the Trend...', sectionKey: 'drivers' },
  { id: 'sec7', label: 'Synthesizing Geographic & Spatial Intelligence...', sectionKey: 'geo' },
  { id: 'sec8', label: 'Evaluating Customer Load Factor & Consumption Patterns...', sectionKey: 'consumption' },
  { id: 'sec9', label: 'Calculating Sector Economic Impact Analysis...', sectionKey: 'economic' },
  { id: 'sec10', label: 'Correlating Weather & Climate Regressions (NOAA)...', sectionKey: 'weather' },
  { id: 'sec11', label: 'Validating Forecast Driver Contributions...', sectionKey: 'f_drivers' },
  { id: 'sec12', label: 'Formulating Actionable Stakeholder Recommendations...', sectionKey: 'recommendations' },
  { id: 'sec13', label: 'Evaluating AI Confidence & Data Quality Score...', sectionKey: 'confidence' },
  { id: 'sec14', label: 'Generating Data Sources & Transparency Manifest...', sectionKey: 'sources' },
  { id: 'finalizing', label: 'Finalizing Executive Intelligence Report...' },
];

export interface UnlockedSectionsState {
  summary: boolean;
  market: boolean;
  cost: boolean;
  risk: boolean;
  forecast: boolean;
  drivers: boolean;
  geo: boolean;
  consumption: boolean;
  economic: boolean;
  weather: boolean;
  f_drivers: boolean;
  recommendations: boolean;
  confidence: boolean;
  sources: boolean;
}

interface AIGeneratingWorkflowProps {
  currentStepIndex: number;
  unlockedSections: UnlockedSectionsState;
}

export const AIGeneratingWorkflow: React.FC<AIGeneratingWorkflowProps> = ({
  currentStepIndex,
  unlockedSections,
}) => {
  const totalSteps = GENERATION_STEPS.length;
  const progressPct = Math.min(100, Math.round(((currentStepIndex + 1) / totalSteps) * 100));

  return (
    <div className="max-w-[900px] mx-auto space-y-6 font-sans">
      {/* Header Container */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-md space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#2a4b7c] flex items-center justify-center text-white shadow-xs shrink-0">
              <Cpu size={22} className="animate-pulse" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <span>AI Analyst is Generating Your Executive Intelligence Report</span>
                <Sparkles size={16} className="text-amber-500 fill-amber-400" />
              </h2>
              <p className="text-xs text-gray-500">
                Synthesizing multi-page intelligence across 14 comprehensive executive sections...
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-xs font-bold text-[#2a4b7c] bg-blue-50 px-2.5 py-1 rounded border border-blue-200 inline-block">
              Progress: {progressPct}%
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-100 h-2.5 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-[#2a4b7c] via-blue-600 to-amber-500 h-full transition-all duration-300 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
          {GENERATION_STEPS.map((step, idx) => {
            const isDone = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] transition-all border ${
                  isDone
                    ? 'bg-green-50/60 border-green-200 text-gray-800'
                    : isCurrent
                    ? 'bg-blue-50 border-blue-300 text-[#2a4b7c] font-bold shadow-xs'
                    : 'bg-gray-50/50 border-gray-100 text-gray-400'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 size={14} className="text-green-600 shrink-0" />
                ) : isCurrent ? (
                  <Loader2 size={14} className="animate-spin text-[#2a4b7c] shrink-0" />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-gray-300 shrink-0" />
                )}

                <span className="truncate">{step.label}</span>
              </div>
            );
          })}
        </div>

        {/* Streaming Section Indicators */}
        <div className="pt-2 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-gray-600">
          <span className="font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1">
            <Layers size={13} />
            <span>Multi-Page Sections:</span>
          </span>

          <div className="flex flex-wrap items-center gap-1.5 font-medium text-[10px]">
            {Object.entries(unlockedSections).map(([secKey, isUnlocked], idx) => (
              <span
                key={secKey}
                className={`px-2 py-0.5 rounded border ${
                  isUnlocked
                    ? 'bg-green-50 border-green-300 text-green-700 font-bold'
                    : 'bg-gray-50 border-gray-200 text-gray-400'
                }`}
              >
                {isUnlocked ? `✓ Sec ${idx + 1}` : `Sec ${idx + 1}`}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIGeneratingWorkflow;
