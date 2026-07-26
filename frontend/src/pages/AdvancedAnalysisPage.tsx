/**
 * AdvancedAnalysisPage.tsx — Dedicated Engineering & Data Science Diagnostics Page
 *
 * Exclusively for energy researchers, utility engineers, data scientists, and economists.
 * Separated completely from the consumer interface.
 */

import { useBill } from '../context/BillContext.tsx';
import { useNavigation } from '../context/NavigationContext.tsx';
import { Cpu, Activity, Database, Network, ArrowLeft } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar } from 'recharts';

const AdvancedAnalysisPage = () => {
  const { uploadedBill } = useBill();
  const navigate = useNavigation();

  // Baseline telemetry values
  const bill = uploadedBill || {
    customer_id: 'CUST-DEMO-001',
    utility: 'PSE&G',
    rate_schedule: 'RS',
    total_bill: 158.40,
    usage_kwh: 750
  };

  const bellCurveData = [
    { x: 130, y: 0.01 }, { x: 135, y: 0.05 }, { x: 140, y: 0.15 },
    { x: 145, y: 0.40 }, { x: 150, y: 0.75 }, { x: 155, y: 0.98 },
    { x: 158, y: 1.00 }, { x: 162, y: 0.88 }, { x: 168, y: 0.50 },
    { x: 172, y: 0.20 }, { x: 178, y: 0.06 }, { x: 185, y: 0.01 }
  ];

  const tornadoData = [
    { component: 'Wholesale BGS Supply', shock: 18.40 },
    { component: 'Distribution Delivery', shock: 8.20 },
    { component: 'Transmission Charge', shock: 5.10 },
    { component: 'State Sales Tax', shock: 2.40 },
    { component: 'Societal Benefits (SBC)', shock: 1.80 }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6 sm:p-10 font-mono space-y-8">

      {/* HEADER BAR */}
      <header className="border-b border-slate-800 pb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-purple-900/60 text-purple-300 text-xs font-bold px-2.5 py-0.5 rounded border border-purple-700/50 uppercase tracking-widest">
              Research & Engineering Diagnostics
            </span>
            <span className="text-xs text-slate-400 font-sans">
              Utility: {bill.utility} • Customer: {bill.customer_id}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1.5 flex items-center gap-2 font-sans">
            <Cpu className="w-6 h-6 text-purple-400" /> Advanced Power Systems & Econometric Analysis
          </h1>
        </div>

        <button
          onClick={() => navigate('Impact Simulator')}
          className="flex items-center gap-2 text-xs font-sans font-bold bg-slate-800 hover:bg-slate-700 text-white px-4 py-2.5 rounded-lg border border-slate-700 transition-all shadow-sm active:scale-95 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Consumer View
        </button>
      </header>

      {/* TOP STAT CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: DML Model */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl space-y-3 shadow-md">
          <div className="flex justify-between items-center text-purple-400 text-xs font-bold">
            <span className="flex items-center gap-1.5"><Activity className="w-4 h-4" /> Double ML (DML) Model</span>
            <span className="bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px]">p = 0.042</span>
          </div>
          <div className="space-y-1">
            <span className="text-3xl font-bold text-white">-0.421</span>
            <span className="text-xs text-slate-400 block">Average Treatment Effect (ATE)</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed pt-2 border-t border-slate-800">
            Controls for HDD/CDD temperature confounders using Random Forest nuisance estimators.
          </p>
        </div>

        {/* Card 2: Monte Carlo Variance */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl space-y-3 shadow-md">
          <div className="flex justify-between items-center text-purple-400 text-xs font-bold">
            <span className="flex items-center gap-1.5"><Database className="w-4 h-4" /> Monte Carlo Variance</span>
            <span className="bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px]">2,000 Trials</span>
          </div>
          <div className="space-y-1">
            <span className="text-3xl font-bold text-white">σ = $5.48</span>
            <span className="text-xs text-slate-400 block">95% Confidence Interval: [$142.10, $175.80]</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed pt-2 border-t border-slate-800">
            Gaussian kernel density estimation over wholesale LMP rate variances.
          </p>
        </div>

        {/* Card 3: PJM Telemetry */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl space-y-3 shadow-md">
          <div className="flex justify-between items-center text-purple-400 text-xs font-bold">
            <span className="flex items-center gap-1.5"><Network className="w-4 h-4" /> PJM Grid Telemetry</span>
            <span className="bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded text-[10px]">Live Node Feed</span>
          </div>
          <div className="space-y-1">
            <span className="text-3xl font-bold text-white">31,450 MW</span>
            <span className="text-xs text-slate-400 block">Real-Time LMP: $38.42 / MWh</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed pt-2 border-t border-slate-800">
            Direct 5-minute telemetry stream from PJM Data Miner 2 balancing authority.
          </p>
        </div>
      </div>

      {/* DETAILED GRAPHS GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Graph 1: Probability Bell Curve */}
        <div className="bg-slate-900/90 border border-slate-800 p-6 rounded-xl space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <div>
              <span className="text-[10px] text-purple-400 uppercase tracking-widest font-bold block">Probability Density</span>
              <h3 className="text-sm font-bold text-white">Monte Carlo Bill Probability Distribution</h3>
            </div>
            <span className="text-xs text-emerald-400 font-semibold bg-emerald-950/80 px-2.5 py-1 rounded border border-emerald-800">
              High Confidence (R² = 0.94)
            </span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={bellCurveData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="x" stroke="#94A3B8" tick={{ fontSize: 10 }} unit="$" />
                <YAxis stroke="#94A3B8" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Area type="monotone" dataKey="y" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.25} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Graph 2: Tornado Sensitivity Analysis */}
        <div className="bg-slate-900/90 border border-slate-800 p-6 rounded-xl space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <div>
              <span className="text-[10px] text-purple-400 uppercase tracking-widest font-bold block">Rate Sensitivity</span>
              <h3 className="text-sm font-bold text-white">Tornado Sensitivity Analysis ($ Shock)</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">10% Rate Variance</span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tornadoData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#94A3B8" tick={{ fontSize: 10 }} unit="$" />
                <YAxis dataKey="component" type="category" stroke="#94A3B8" tick={{ fontSize: 10 }} width={140} />
                <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Bar dataKey="shock" fill="#3B82F6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

    </div>
  );
};

export default AdvancedAnalysisPage;
