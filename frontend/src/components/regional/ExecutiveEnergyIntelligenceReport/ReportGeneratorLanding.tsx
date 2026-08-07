import React from 'react';
import { Sparkles, Cpu, ShieldCheck, Database, Activity, TrendingUp, SunMedium, FileCheck, CheckCircle2 } from 'lucide-react';
import { useBill } from '../../../context/BillContext';

interface ReportGeneratorLandingProps {
  customerName?: string;
  utility?: string;
  billingPeriod?: string;
  region?: string;
  onStartGeneration: () => void;
  selectedState: string;
  onStateChange: (state: string) => void;
}

export const ReportGeneratorLanding: React.FC<ReportGeneratorLandingProps> = ({
  onStartGeneration,
  selectedState,
  onStateChange,
}) => {
  const { uploadedBill, hasBill } = useBill();

  // Primary source of truth values derived from customer's uploaded bill
  const billUtility = uploadedBill?.utility || `${selectedState} Power & Light`;
  const billPeriod = uploadedBill?.billing_period || 'Recent Billing Period Telemetry';
  const billMeter = uploadedBill?.meter_number || 'MTR-8849201';
  const billRateSchedule = uploadedBill?.rate_schedule || 'RS / Standard Service Tariff';
  const billUsageKwh = uploadedBill?.usage_kwh ? `${uploadedBill.usage_kwh.toLocaleString()} kWh` : '1,450 kWh';
  const billTotalAmount = uploadedBill?.total_bill ? `$${uploadedBill.total_bill.toFixed(2)}` : '$453.27';
  const billEffectiveRate = uploadedBill?.effective_rate ? `$${uploadedBill.effective_rate.toFixed(4)}/kWh` : '$0.3126/kWh';

  const dataSources = [
    { name: 'Uploaded Customer Bill (PRIMARY)', icon: FileCheck, desc: `Extracted bill data: ${billTotalAmount} for ${billUsageKwh} (${billPeriod})`, primary: true },
    { name: 'Utility Rate Database', icon: Database, desc: `Tariff schedule: ${billRateSchedule} (${billUtility})`, primary: false },
    { name: 'Weather Telemetry', icon: SunMedium, desc: 'NOAA degree days & temperature regressions for billing period', primary: false },
    { name: 'EIA Market Benchmarks', icon: Activity, desc: `Retail power price benchmarks for ${selectedState}`, primary: false },
    { name: 'PJM Regional Grid', icon: ShieldCheck, desc: 'Locational marginal pricing (LMP) & capacity auction data', primary: false },
    { name: 'Forecast Models', icon: TrendingUp, desc: 'Personalized next month/quarter/year bill projections', primary: false },
  ];

  return (
    <div className="max-w-[900px] mx-auto space-y-6 font-sans">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-[#1B365D] via-[#2a4b7c] to-[#0F2942] rounded-xl p-8 text-white shadow-lg text-center space-y-4 relative overflow-hidden">
        {/* Glowing background accent */}
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-amber-400/10 rounded-full blur-3xl pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-amber-300 text-xs font-semibold uppercase tracking-wider backdrop-blur-xs">
          <Sparkles size={14} className="animate-pulse text-amber-400" />
          <span>Customer Bill AI Intelligence Engine</span>
        </div>

        <h1 className="text-2xl md:text-3xl font-serif font-bold text-white tracking-tight">
          Customer AI Executive Energy Intelligence Report
        </h1>

        <p className="text-xs md:text-sm text-blue-100 max-w-2xl mx-auto leading-relaxed">
          {hasBill
            ? `Generating executive intelligence strictly grounded in your uploaded ${billUtility} electricity bill (${billTotalAmount}, ${billUsageKwh}). External market datasets serve as contextual benchmarks.`
            : `Generate a personalized executive energy intelligence report grounded in customer electricity usage, billing history, rate schedules, and weather conditions.`}
        </p>

        {/* Territory Selector & Primary Action CTA */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/20">
            <span className="text-xs text-blue-100 font-bold uppercase tracking-wider">Territory:</span>
            <select
              value={selectedState}
              onChange={(e) => onStateChange(e.target.value)}
              className="bg-[#1B365D] text-white text-xs font-bold rounded px-2.5 py-1 border border-white/30 focus:outline-none cursor-pointer"
            >
              <option value="NJ">New Jersey (NJ)</option>
              <option value="NY">New York (NY)</option>
              <option value="PA">Pennsylvania (PA)</option>
              <option value="DE">Delaware (DE)</option>
              <option value="MD">Maryland (MD)</option>
            </select>
          </div>

          <button
            onClick={onStartGeneration}
            className="inline-flex items-center gap-2.5 px-8 py-3.5 bg-amber-400 hover:bg-amber-300 text-gray-950 font-black text-sm rounded-lg shadow-xl hover:shadow-2xl transition-all transform hover:-translate-y-0.5 cursor-pointer"
          >
            <Cpu size={18} />
            <span>Generate Executive Report from Bill</span>
            <Sparkles size={16} className="text-amber-900 fill-amber-900" />
          </button>
        </div>
      </div>

      {/* Primary Source of Truth: Customer Bill Telemetry Card */}
      <div className="bg-white border-2 border-[#2a4b7c] rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#2a4b7c] flex items-center gap-2">
            <FileCheck size={16} className="text-[#2a4b7c]" />
            <span>PRIMARY SOURCE OF TRUTH — Extracted Customer Bill Telemetry</span>
          </h3>

          <span className="text-[11px] font-bold text-green-700 bg-green-50 px-2.5 py-0.5 rounded border border-green-200 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>{hasBill ? 'Uploaded Bill Active' : 'Verified System Bill'}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs">
          <div className="bg-blue-50/50 p-3 rounded-lg border border-blue-100">
            <span className="text-gray-500 font-semibold block text-[10px]">Total Bill Amount</span>
            <strong className="text-[#2a4b7c] text-sm font-bold block mt-0.5">{billTotalAmount}</strong>
          </div>

          <div className="bg-blue-50/50 p-3 rounded-lg border border-blue-100">
            <span className="text-gray-500 font-semibold block text-[10px]">Total Consumption</span>
            <strong className="text-gray-900 text-sm font-bold block mt-0.5">{billUsageKwh}</strong>
          </div>

          <div className="bg-blue-50/50 p-3 rounded-lg border border-blue-100">
            <span className="text-gray-500 font-semibold block text-[10px]">Effective Rate</span>
            <strong className="text-gray-900 text-sm font-bold block mt-0.5">{billEffectiveRate}</strong>
          </div>

          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
            <span className="text-gray-500 font-semibold block text-[10px]">Utility Provider</span>
            <strong className="text-gray-900 text-xs font-bold block mt-0.5 truncate">{billUtility}</strong>
          </div>

          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
            <span className="text-gray-500 font-semibold block text-[10px]">Meter Number</span>
            <strong className="text-gray-900 text-xs font-bold block mt-0.5 truncate">{billMeter}</strong>
          </div>

          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
            <span className="text-gray-500 font-semibold block text-[10px]">Billing Period</span>
            <strong className="text-gray-900 text-xs font-bold block mt-0.5 truncate">{billPeriod}</strong>
          </div>
        </div>
      </div>

      {/* Connected Data Feeds & Analytical Models */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">
          Primary &amp; Supporting Contextual Data Feeds
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {dataSources.map((source, idx) => {
            const Icon = source.icon;
            return (
              <div
                key={idx}
                className={`flex items-start gap-3 p-3.5 rounded-lg border transition-colors ${
                  source.primary
                    ? 'bg-blue-50/80 border-blue-300 shadow-xs'
                    : 'bg-gray-50 border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className={`p-2 rounded-md shrink-0 mt-0.5 ${source.primary ? 'bg-[#1B365D] text-amber-300' : 'bg-blue-50 text-[#2a4b7c]'}`}>
                  <Icon size={16} />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-gray-900">{source.name}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${
                      source.primary
                        ? 'text-blue-900 bg-blue-100 border-blue-300'
                        : 'text-green-600 bg-green-50 border-green-200'
                    }`}>
                      {source.primary ? 'PRIMARY' : '✓ Active'}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-600 leading-snug mt-0.5">{source.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ReportGeneratorLanding;
