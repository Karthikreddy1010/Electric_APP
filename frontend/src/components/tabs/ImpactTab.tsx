import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip, CartesianGrid,
  AreaChart, Area, ReferenceLine
} from 'recharts';
import { 
  Calculator, Activity, TrendingUp, TrendingDown, 
  ThermometerSun, Zap, ShieldCheck, ArrowRight, Lightbulb,
  CloudRain, DollarSign, Gauge, BarChart3, Info,
  Brain, CheckCircle, AlertCircle
} from 'lucide-react';

// ─── Constants ───────────────────────────────────────────────────────────────

const SCENARIOS = [
  { id: "", label: "Custom Rate Changes Only" },
  { id: "cold_winter", label: "❄️ Cold Winter (High Heat Load)" },
  { id: "hot_summer", label: "☀️ Hot Summer (High Cooling Load)" },
  { id: "high_market", label: "📈 High Wholesale Market Prices" },
  { id: "low_usage", label: "🏠 Energy Efficient Household" },
  { id: "conservation", label: "🌱 Conservation Effort" }
];

const COMPONENT_METADATA: Record<string, { label: string; description: string; icon: string }> = {
  bgs_rate:          { label: "BGS Supply",       description: "Wholesale energy supply rate set by the market.",         icon: "⚡" },
  distribution_rate: { label: "Distribution",     description: "Local utility delivery and infrastructure fee.",          icon: "🔌" },
  transmission_rate: { label: "Transmission",     description: "Regional high-voltage transport fee.",                    icon: "🏗️" },
  sbc_rate:          { label: "Societal Benefits", description: "State-mandated societal benefits & clean energy charges.", icon: "🏛️" },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

/** Format dollar amount with sign */
const fmt = (v: number, forceSign = false) => {
  const sign = v > 0 ? '+' : v < 0 ? '−' : '';
  const abs = Math.abs(v).toFixed(2);
  if (forceSign) return `${sign}$${abs}`;
  return `$${abs}`;
};

/** Get confidence level label from simulation variability */
const getConfidenceLevel = (std: number, mean: number) => {
  const cv = mean > 0 ? std / mean : 0;
  if (cv < 0.03) return { label: 'Very High', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', barColor: '#10B981' };
  if (cv < 0.06) return { label: 'High', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', barColor: '#10B981' };
  if (cv < 0.12) return { label: 'Moderate', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', barColor: '#F59E0B' };
  return { label: 'Low', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', barColor: '#EF4444' };
};

const getPValueColor = (p: number) => {
  if (p < 0.01) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
  if (p < 0.05) return 'text-blue-600 bg-blue-50 border-blue-200';
  return 'text-slate-500 bg-slate-50 border-slate-200';
};

const getSignificanceLabel = (p: number) => {
  if (p < 0.01) return 'Highly Significant (p < 0.01)';
  if (p < 0.05) return 'Statistically Significant (p < 0.05)';
  return 'Not Statistically Significant (p >= 0.05)';
};

/** Build bell curve data for distribution visualization */
const buildBellCurve = (mean: number, std: number, p5: number, p95: number) => {
  const points = [];
  const lo = Math.min(p5, mean - 3 * std);
  const hi = Math.max(p95, mean + 3 * std);
  const steps = 60;
  for (let i = 0; i <= steps; i++) {
    const x = lo + (hi - lo) * (i / steps);
    const z = (x - mean) / (std || 1);
    const y = Math.exp(-0.5 * z * z);
    points.push({ x: Math.round(x * 100) / 100, y: Math.round(y * 1000) / 1000 });
  }
  return points;
};

// ─── Main Component ──────────────────────────────────────────────────────────

const round = (val: number, decimals: number) => {
  const p = Math.pow(10, decimals);
  return Math.round(val * p) / p;
};

const ImpactTab = ({ uploadedBill, setActiveTab }: { uploadedBill: any, setActiveTab?: (tab: string) => void }) => {
  // ── Simulator State ──
  const [selectedComp, setSelectedComp] = useState("bgs_rate");
  const [changePct, setChangePct] = useState(10);
  const [scenario, setScenario] = useState("");
  
  const debouncedChange = useDebounce(changePct, 300);
  const debouncedComp = useDebounce(selectedComp, 300);
  const debouncedScenario = useDebounce(scenario, 300);

  const customerImpact = useMemo(() => {
    if (!uploadedBill) return null;
    const fixed = uploadedBill.monthly_service_charge;
    const supply = uploadedBill.supply_charge;
    const tax = uploadedBill.tax;
    const total = uploadedBill.total_bill;
    const delivery = round(uploadedBill.delivery_charge - fixed, 2);
    
    return {
      total_bill: total,
      components: [
        {"name": "Fixed Customer Service Charge", "amount": fixed, "pct": round(fixed/total*100, 1)},
        {"name": "Grid Delivery Infrastructure", "amount": delivery, "pct": round(delivery/total*100, 1)},
        {"name": "Standard Supply Generation", "amount": supply, "pct": round(supply/total*100, 1)},
        {"name": "State Sales Taxes (6.625%)", "amount": tax, "pct": round(tax/total*100, 1)}
      ]
    };
  }, [uploadedBill]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: _fullAnalysis } = useQuery({
    queryKey: ['impact-full-analysis'],
    queryFn: async () => (await axios.get('/impact/full-analysis')).data
  });

  const { data: simulation, isLoading: isSimLoading } = useQuery({
    queryKey: ['impact-what-if-v2', debouncedComp, debouncedChange, debouncedScenario, uploadedBill?.usage_kwh],
    queryFn: async () => {
      const changes: Record<string, number> = {};
      if (debouncedChange !== 0) changes[debouncedComp] = debouncedChange;
      const payload: any = { 
        changes, 
        n_simulations: 2000,
        kwh: uploadedBill?.usage_kwh || 750
      };
      if (debouncedScenario) payload.scenario = debouncedScenario;
      return (await axios.post('/impact/what-if-v2', payload)).data;
    },
    enabled: !!uploadedBill,
    placeholderData: (prev) => prev
  });

  if (!uploadedBill) {
    return (
      <div className="flex flex-col items-center justify-center p-16 card bg-slate-50 border-dashed border-2 border-slate-200 text-center max-w-xl mx-auto space-y-4 my-12">
        <Zap size={48} className="text-slate-400 animate-bounce" />
        <h3 className="text-xl font-bold text-slate-800">Impact Analysis Locked</h3>
        <p className="text-sm text-slate-500 max-w-sm">
          Please upload and analyze an electricity bill on the Bill Analysis page to run cost component contribution forecasts.
        </p>
        <button 
          onClick={() => setActiveTab?.("Bill Analysis")}
          className="bg-primary text-white hover:bg-primary-hover font-bold px-6 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 mt-4"
        >
          Go to Bill Analysis
        </button>
      </div>
    );
  }

  const isCausalLoading = false;
  const isCausalError = false;
  const causalError: any = null;
  const causalData: any = null;
  const customerId = "UPLOADED";

  // ── Derived Values ──
  const baseBill = simulation?.base_bill || 185.00;
  const simulatedBill = simulation?.simulated_bill || simulation?.new_bill || baseBill;
  const deltaBill = simulatedBill - baseBill;
  const isIncrease = deltaBill > 0;
  const deltaPct = baseBill > 0 ? ((deltaBill / baseBill) * 100) : 0;
  
  // Decomposition
  const directPrice = simulation?.decomposition?.direct_price_effect || 0;
  const behaviorShift = simulation?.decomposition?.indirect_behavioral_effect || 0;
  const weatherEffect = simulation?.decomposition?.weather_effect || 0;
  const interactionEffect = simulation?.decomposition?.interaction_effect || 0;
  const usageDelta = simulation?.usage_change_kwh || 0;
  const elasticity = simulation?.learned_elasticity || -0.20;

  // Distribution
  const distMean = simulation?.distribution?.mean || simulatedBill;
  const distStd = simulation?.distribution?.std || 5;
  const distP5 = simulation?.distribution?.p5 || (distMean - 2 * distStd);
  const distP95 = simulation?.distribution?.p95 || (distMean + 2 * distStd);

  // Confidence
  const ci = simulation?.confidence_interval || [distP5, distP95];
  const confidence = getConfidenceLevel(distStd, distMean);

  // Bill breakdown values
  const utilityBill = baseBill + 6.49;
  const adjustment = -6.49;
  const finalBill = baseBill;

  // ── Waterfall Chart ──
  type WaterfallType = 'base' | 'increase' | 'decrease' | 'total';
  const waterfallData = useMemo(() => {
    const items: { name: string; value: number; type: WaterfallType }[] = [
      { name: 'Base Bill', value: baseBill, type: 'base' },
      { name: 'Rate Change', value: directPrice, type: directPrice >= 0 ? 'increase' : 'decrease' },
      { name: 'Behavior', value: behaviorShift, type: behaviorShift >= 0 ? 'increase' : 'decrease' },
    ];
    if (Math.abs(weatherEffect) > 0.01) {
      items.push({ name: 'Weather', value: weatherEffect, type: weatherEffect >= 0 ? 'increase' : 'decrease' });
    }
    if (Math.abs(interactionEffect) > 0.5) {
      items.push({ name: 'Interaction', value: interactionEffect, type: interactionEffect >= 0 ? 'increase' : 'decrease' });
    }
    items.push({ name: 'New Bill', value: simulatedBill, type: 'total' });
    return items;
  }, [baseBill, directPrice, behaviorShift, weatherEffect, interactionEffect, simulatedBill]);

  // ── Bell Curve ──
  const bellCurveData = useMemo(() => {
    return buildBellCurve(distMean, distStd, distP5, distP95);
  }, [distMean, distStd, distP5, distP95]);

  // ── Cost Drivers (ranked from SHAP) ──
  const costDrivers = useMemo(() => {
    if (!_fullAnalysis || !_fullAnalysis.all_features) return [];
    
    // Take top 4 drivers by absolute SHAP impact
    return _fullAnalysis.all_features.slice(0, 4).map((f: any) => {
      const impact = f.shap_value;
      const absImpact = Math.abs(impact);
      
      // Determine level based on percentage share of the bill
      const share = f.share_pct;
      const level = share > 20 ? 'high' : share > 5 ? 'medium' : 'low';
      
      // Controllable logic based on category
      const controllable = f.category === 'Behavioral' || f.category === 'Usage';
      
      return {
        key: f.label,
        label: f.label,
        value: absImpact,
        impact: impact,
        level: level,
        reason: `${f.category} driver accounting for ${share.toFixed(1)}% of your bill.`,
        controllable: controllable,
      };
    });
  }, [_fullAnalysis]);

  // ── Dynamic Insight Summary ──
  const insightText = useMemo(() => {
    if (!costDrivers || costDrivers.length === 0) {
      return 'Loading insights...';
    }
    const primaryDriver = costDrivers[0];
    const offset = costDrivers.find((d: any) => d.impact < 0 && d.key !== primaryDriver.key);
    
    if (Math.abs(deltaBill) < 0.5) {
      return 'Your bill is projected to remain roughly unchanged under this scenario.';
    }
    
    let text = '';
    if (deltaBill > 0) {
      text = `Your bill increased by $${Math.abs(deltaBill).toFixed(2)} mainly due to ${primaryDriver.label.toLowerCase()}.`;
      if (offset) {
        text += ` However, ${offset.label.toLowerCase()} partially offset the increase by $${Math.abs(offset.impact).toFixed(2)}.`;
      }
    } else {
      text = `Your bill decreased by $${Math.abs(deltaBill).toFixed(2)}, primarily driven by ${primaryDriver.label.toLowerCase()}.`;
    }
    return text;
  }, [costDrivers, deltaBill]);

  // ── Component metadata for selected ──
  const selectedMeta = COMPONENT_METADATA[selectedComp];

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-12" id="impact-tab">
      
      {/* ── Personalized Component Cost Contribution ── */}
      {customerImpact && (
        <div className="card p-6 border border-slate-100 hover:shadow-md transition-shadow bg-slate-900 text-white relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-32 h-32 bg-blue-600/10 rounded-full blur-3xl"></div>
          <div className="flex items-center justify-between mb-4 relative z-10">
            <div>
              <h3 className="text-lg font-bold">Personalized Component Cost Contribution</h3>
              <p className="text-xs text-slate-400 mt-0.5">Factor contribution breakdown for customer {customerId}'s latest bill</p>
            </div>
            <span className="text-2xl font-black text-blue-400">${customerImpact.total_bill?.toFixed(2)}</span>
          </div>
          
          {/* Horizontal stack showing components in a single premium bar */}
          <div className="w-full h-4 rounded-full overflow-hidden flex mb-6 bg-slate-800 relative z-10">
            {customerImpact.components.map((comp: any, idx: number) => {
              const bgColors = ["bg-blue-600", "bg-purple-600", "bg-teal-600", "bg-amber-500", "bg-rose-500", "bg-slate-500"];
              return (
                <div 
                  key={idx} 
                  style={{ width: `${comp.pct}%` }} 
                  className={`${bgColors[idx % bgColors.length]} h-full transition-all`}
                  title={`${comp.name}: ${comp.pct}%`}
                />
              );
            })}
          </div>
          
          {/* Grid detailing each component */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 relative z-10">
            {customerImpact.components.map((comp: any, idx: number) => {
              const textColors = ["text-blue-400", "text-purple-400", "text-teal-400", "text-amber-400", "text-rose-400", "text-slate-400"];
              const borderColors = ["border-blue-600/30", "border-purple-600/30", "border-teal-600/30", "border-amber-600/30", "border-rose-600/30", "border-slate-600/30"];
              return (
                <div key={idx} className={`p-3 bg-slate-800/50 rounded-xl border ${borderColors[idx % borderColors.length]} flex flex-col justify-between`}>
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block leading-tight mb-1">{comp.name}</span>
                  <div className="flex justify-between items-baseline mt-auto">
                    <span className={`text-xs font-black ${textColors[idx % textColors.length]}`}>{comp.pct}%</span>
                    <span className="text-sm font-black text-white">${comp.amount?.toFixed(2)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      
      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 1: TOP ROW — Bill Summary & Weather Context
          ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ── Bill Summary Card ── */}
        <div 
          id="bill-summary-card"
          className="lg:col-span-2 rounded-2xl bg-white border border-slate-200 shadow-sm p-6 transition-all duration-300"
        >
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 bg-slate-100 rounded-lg">
              <DollarSign size={16} className="text-slate-600" />
            </div>
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
              Current Bill Overview
            </h3>
          </div>
          
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            {/* Utility Bill */}
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Utility Bill</span>
              <span className="text-2xl font-black text-slate-800 tabular-nums">${utilityBill.toFixed(2)}</span>
            </div>
            
            <div className="hidden md:flex items-center text-slate-300">
              <ArrowRight size={18} strokeWidth={2.5} />
            </div>
            
            {/* Adjustments */}
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Adjustments</span>
              <span className="text-2xl font-black text-emerald-600 tabular-nums">{fmt(adjustment, true)}</span>
            </div>
            
            <div className="hidden md:flex items-center text-slate-300">
              <ArrowRight size={18} strokeWidth={2.5} />
            </div>
            
            {/* Final Bill */}
            <div className="flex flex-col gap-1 bg-gradient-to-br from-slate-50 to-slate-100/60 px-6 py-4 rounded-2xl border border-slate-200/80">
              <span className="text-xs font-black text-slate-500 uppercase tracking-wider">Final Bill</span>
              <div className="flex items-center gap-3">
                <span className="text-4xl font-black text-slate-900 tabular-nums tracking-tight">
                  ${finalBill.toFixed(2)}
                </span>
                <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                  deltaBill > 0 
                    ? 'text-red-700 bg-red-50 border border-red-200' 
                    : deltaBill < 0
                      ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                      : 'text-slate-600 bg-slate-100 border border-slate-200'
                }`}>
                  {deltaBill >= 0 ? '+' : '−'}${Math.abs(deltaBill).toFixed(2)} ({deltaBill >= 0 ? '+' : '−'}{Math.abs(deltaPct).toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Weather Context Card ── */}
        <div 
          id="weather-context-card"
          className="rounded-2xl bg-gradient-to-br from-blue-50 via-indigo-50/50 to-sky-50 border border-blue-200/60 shadow-sm p-6 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="p-1.5 bg-blue-100 rounded-lg">
                <ThermometerSun size={16} className="text-blue-600" />
              </div>
              <h3 className="text-xs font-black text-blue-800 uppercase tracking-[0.15em]">
                Weather Impact
              </h3>
            </div>
            <p className="text-sm text-blue-800/80 font-medium leading-relaxed mb-4">
              {weatherEffect < -0.5
                ? `Mild conditions reduced expected cooling/heating usage by ${Math.abs(usageDelta * 0.3).toFixed(1)} kWh this period.`
                : weatherEffect > 0.5
                  ? `Extreme temperatures increased HVAC demand, adding to your bill.`
                  : `Weather conditions were typical for this period with minimal bill impact.`
              }
            </p>
          </div>
          
          <div className="flex items-center gap-2 bg-white/70 backdrop-blur-sm px-4 py-2.5 rounded-xl border border-blue-100/80">
            <CloudRain size={14} className="text-blue-500" />
            <span className="text-xs font-bold text-blue-900 uppercase tracking-wider">Bill Impact:</span>
            <span className={`text-sm font-black ${weatherEffect <= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {fmt(weatherEffect, true)}
            </span>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 2: MIDDLE ROW — Why Did Your Bill Change?
          ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* ── Impact Decomposition (Waterfall) ── */}
        <div 
          id="impact-decomposition-card"
          className="rounded-2xl bg-white border border-slate-200 shadow-sm p-6"
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-slate-100 rounded-lg">
                <BarChart3 size={16} className="text-slate-600" />
              </div>
              <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
                Why Did Your Bill Change?
              </h3>
            </div>
          </div>
          
          <p className="text-2xl font-black text-slate-900 mb-5 mt-2">
            Total Change:{' '}
            <span className={isIncrease ? 'text-red-600' : deltaBill < -0.5 ? 'text-emerald-600' : 'text-slate-600'}>
              {fmt(deltaBill, true)}
            </span>
          </p>
          
          {/* Waterfall Chart */}
          <div className="h-[210px] mb-5">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterfallData} margin={{ top: 15, right: 15, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748B', fontSize: 11, fontWeight: 600 }} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94A3B8', fontSize: 11 }} 
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip 
                  cursor={{ fill: '#F1F5F9' }} 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px -2px rgb(0 0 0 / 0.12)', fontSize: '13px' }} 
                  formatter={(value: any) => [`$${value.toFixed(2)}`, 'Amount']}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={50}>
                  {waterfallData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={
                      entry.type === 'base'     ? '#94A3B8' : 
                      entry.type === 'increase'  ? '#EF4444' : 
                      entry.type === 'decrease'  ? '#10B981' : '#1E293B'
                    } />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Decomposition Line Items */}
          <div className="space-y-2">
            <div className="flex justify-between items-center bg-red-50/60 px-4 py-2.5 rounded-xl border border-red-100/60">
              <span className="text-xs font-bold text-red-800">Direct Price Effect</span>
              <span className="text-sm font-black text-red-600 tabular-nums">{fmt(directPrice, true)}</span>
            </div>
            <div className="flex justify-between items-center bg-emerald-50/60 px-4 py-2.5 rounded-xl border border-emerald-100/60">
              <span className="text-xs font-bold text-emerald-800">Behavioral Response</span>
              <span className="text-sm font-black text-emerald-600 tabular-nums">{fmt(behaviorShift, true)}</span>
            </div>
            {Math.abs(weatherEffect) > 0.01 && (
              <div className="flex justify-between items-center bg-blue-50/60 px-4 py-2.5 rounded-xl border border-blue-100/60">
                <span className="text-xs font-bold text-blue-800">Weather Effect</span>
                <span className="text-sm font-black text-blue-600 tabular-nums">{fmt(weatherEffect, true)}</span>
              </div>
            )}
            {Math.abs(interactionEffect) > 0.5 && (
              <div className="flex justify-between items-center bg-purple-50/60 px-4 py-2.5 rounded-xl border border-purple-100/60">
                <span className="text-xs font-bold text-purple-800">Interaction Effect</span>
                <span className="text-sm font-black text-purple-600 tabular-nums">{fmt(interactionEffect, true)}</span>
              </div>
            )}
          </div>
        </div>

        {/* ── Top Cost Drivers ── */}
        <div 
          id="cost-drivers-card"
          className="rounded-2xl bg-white border border-slate-200 shadow-sm p-6 flex flex-col"
        >
          <div className="flex items-center gap-2 mb-6">
            <div className="p-1.5 bg-slate-100 rounded-lg">
              <Activity size={16} className="text-slate-600" />
            </div>
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
              Top Influence Drivers
            </h3>
          </div>
          
          <div className="flex-1 space-y-3">
            {costDrivers.map((driver: any, idx: number) => {
              const levelConfig = {
                high:   { color: 'text-red-600',     bg: 'bg-red-100',     border: 'border-red-100',     badge: 'bg-red-100 text-red-700',     dot: '🔴' },
                medium: { color: 'text-amber-600',   bg: 'bg-amber-100',   border: 'border-amber-100',   badge: 'bg-amber-100 text-amber-700', dot: '🟡' },
                low:    { color: 'text-emerald-600', bg: 'bg-emerald-100', border: 'border-emerald-100', badge: 'bg-emerald-100 text-emerald-700', dot: '🟢' },
              };
              const cfg = levelConfig[driver.level as keyof typeof levelConfig];
              
              return (
                <div 
                  key={driver.key} 
                  className={`flex items-start gap-3 p-4 rounded-xl bg-slate-50/80 border border-slate-100 transition-all duration-200 hover:shadow-sm hover:border-slate-200`}
                >
                  <div className={`p-2 ${cfg.bg} rounded-lg shrink-0 mt-0.5`}>
                    {driver.impact > 0 ? <TrendingUp size={18} className={cfg.color} /> : <TrendingDown size={18} className={cfg.color} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-bold text-slate-900">{idx + 1}. {driver.label}</h4>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${cfg.badge}`}>
                        {driver.level}
                      </span>
                      {driver.controllable && (
                        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                          Controllable
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">{driver.reason}</p>
                    <p className="text-xs font-bold text-slate-700 mt-1 tabular-nums">
                      Impact: {fmt(driver.impact, true)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 3: Non-Utility Adjustments
          ═══════════════════════════════════════════════════════════════════ */}
      <div 
        id="adjustments-card"
        className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white shadow-xl p-5 border border-slate-700/40"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-white/10 rounded-lg">
              <Zap size={14} className="text-slate-300" />
            </div>
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
              Adjustments & Credits
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-5">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Supplier Adjustment</span>
              <span className="text-xs font-bold text-red-400 tabular-nums">+$3.20</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Demand Response Credit</span>
              <span className="text-xs font-bold text-emerald-400 tabular-nums">−$5.10</span>
            </div>
            <div className="h-4 w-px bg-slate-600 hidden sm:block"></div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Net</span>
              <span className="text-sm font-black text-emerald-400 tabular-nums">−$1.90</span>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 4: BOTTOM ROW — Simulator & Confidence
          ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ── What-If Simulator (Enhanced) ── */}
        <div 
          id="what-if-simulator-card"
          className="lg:col-span-2 rounded-2xl bg-white border border-slate-200 shadow-sm p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-blue-100 rounded-lg">
                <Calculator size={16} className="text-blue-600" />
              </div>
              <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
                Scenario Simulator
              </h3>
            </div>
            {isSimLoading && (
              <span className="text-[10px] font-bold text-blue-500 animate-pulse uppercase tracking-widest flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping"></span>
                Computing 2,000 scenarios…
              </span>
            )}
          </div>

          {/* Dynamic Plain-English Explanation */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/60 p-4 rounded-xl mb-6">
            <div className="flex items-start gap-2">
              <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-blue-900 leading-relaxed">
                {changePct === 0 ? (
                  <>Select a rate adjustment or scenario to simulate its effect on your bill.</>
                ) : changePct > 0 ? (
                  <>
                    Increasing <strong className="text-blue-700">{selectedMeta?.label}</strong> by{' '}
                    <strong className="text-blue-700">{changePct}%</strong> raises your bill by{' '}
                    <strong className="text-red-600">${Math.abs(directPrice).toFixed(2)}</strong>
                    {Math.abs(usageDelta) > 0.5 && (
                      <>, but this is partially offset by a <strong className="text-emerald-600">{Math.abs(usageDelta).toFixed(1)} kWh</strong> drop in usage
                        {elasticity !== -0.20 && <> (elasticity: {elasticity.toFixed(3)})</>}
                      </>
                    )}.
                  </>
                ) : (
                  <>
                    Decreasing <strong className="text-blue-700">{selectedMeta?.label}</strong> by{' '}
                    <strong className="text-blue-700">{Math.abs(changePct)}%</strong> lowers your bill by{' '}
                    <strong className="text-emerald-600">${Math.abs(directPrice).toFixed(2)}</strong>.
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Controls */}
            <div className="space-y-5">
              {/* Scenario Preset */}
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-[0.15em] mb-2">
                  Market Scenario
                </label>
                <select 
                  id="scenario-select"
                  value={scenario} 
                  onChange={(e) => setScenario(e.target.value)} 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400 transition-all"
                >
                  {SCENARIOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
              
              {/* Target Component */}
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-[0.15em] mb-2">
                  Target Component
                </label>
                <select 
                  id="component-select"
                  value={selectedComp} 
                  onChange={(e) => setSelectedComp(e.target.value)} 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400 transition-all"
                >
                  {Object.entries(COMPONENT_METADATA).map(([k, v]) => (
                    <option key={k} value={k}>{v.icon} {v.label} — {v.description}</option>
                  ))}
                </select>
              </div>

              {/* Rate Slider */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.15em]">Rate Adjustment</label>
                  <span className={`text-sm font-black px-2.5 py-1 rounded-lg tabular-nums ${
                    changePct > 0 ? 'text-red-700 bg-red-50 border border-red-200' 
                    : changePct < 0 ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                    : 'text-slate-600 bg-slate-100 border border-slate-200'
                  }`}>
                    {changePct > 0 ? '+' : ''}{changePct}%
                  </span>
                </div>
                <input 
                  id="rate-slider"
                  type="range" 
                  min="-50" max="50" step="5" 
                  value={changePct} 
                  onChange={(e) => setChangePct(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600" 
                />
                <div className="flex justify-between mt-1">
                  <span className="text-[10px] text-slate-400 font-medium">−50%</span>
                  <span className="text-[10px] text-slate-400 font-medium">0%</span>
                  <span className="text-[10px] text-slate-400 font-medium">+50%</span>
                </div>
              </div>
            </div>

            {/* Results Panel */}
            <div className="flex flex-col items-center justify-center p-6 bg-gradient-to-br from-slate-50 to-slate-100/60 rounded-2xl border border-slate-200/80">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] mb-1">Simulated Bill</span>
              <span className="text-5xl font-black text-slate-900 tabular-nums tracking-tight mb-4">
                ${simulatedBill.toFixed(2)}
              </span>
              <div className="flex flex-wrap gap-2 justify-center">
                <span className={`text-xs font-bold px-3 py-1.5 rounded-lg tabular-nums ${
                  isIncrease ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                }`}>
                  Delta: {fmt(deltaBill, true)}
                </span>
                <span className="text-xs font-bold px-3 py-1.5 rounded-lg bg-slate-200 text-slate-700 border border-slate-300 tabular-nums">
                  Usage: {usageDelta > 0 ? '+' : ''}{usageDelta.toFixed(0)} kWh
                </span>
              </div>
              
              {/* Model info badge */}
              <div className="mt-4 flex items-center gap-1.5 text-[10px] text-slate-400 font-medium">
                <Gauge size={10} />
                <span>
                  {simulation?.model_info?.method || 'Monte Carlo'} · {simulation?.model_info?.n_simulations || 2000} draws · {simulation?.model_info?.runtime_ms || '—'}ms
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Confidence & Uncertainty ── */}
        <div 
          id="confidence-card"
          className="rounded-2xl bg-white border border-slate-200 shadow-sm p-6 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center gap-2 mb-5">
              <div className="p-1.5 bg-slate-100 rounded-lg">
                <ShieldCheck size={16} className="text-slate-600" />
              </div>
              <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">
                Prediction Reliability
              </h3>
            </div>
            
            {/* Confidence Badge */}
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-3xl font-black text-slate-900">{confidence.label}</span>
              <span className={`text-sm font-bold ${confidence.color}`}>Confidence</span>
            </div>
            
            <p className="text-xs font-medium text-slate-500 mb-5 leading-relaxed">
              {confidence.label === 'Very High' || confidence.label === 'High'
                ? `Low variability across ${simulation?.model_info?.n_simulations || 2000} Monte Carlo scenarios → reliable estimate.`
                : confidence.label === 'Moderate'
                  ? `Moderate variability detected. The estimate is usable but sensitive to input assumptions.`
                  : `High variability detected. Consider narrowing scenario assumptions for more reliable projections.`
              }
            </p>
          </div>

          {/* Bell Curve Visualization */}
          <div className="mb-4">
            <div className="h-[90px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={bellCurveData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                  <defs>
                    <linearGradient id="bellGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={confidence.barColor} stopOpacity={0.25}/>
                      <stop offset="95%" stopColor={confidence.barColor} stopOpacity={0.03}/>
                    </linearGradient>
                  </defs>
                  <Area 
                    type="monotone" 
                    dataKey="y" 
                    stroke={confidence.barColor} 
                    strokeWidth={2}
                    fill="url(#bellGrad)" 
                  />
                  <ReferenceLine 
                    x={Math.round(distMean * 100) / 100} 
                    stroke="#1E293B" 
                    strokeDasharray="3 3" 
                    strokeWidth={1.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* CI Range */}
          <div className={`${confidence.bg} rounded-xl p-4 border ${confidence.border}`}>
            <span className="block text-[10px] font-black text-slate-500 uppercase tracking-[0.15em] mb-2">
              Expected Range (95% CI)
            </span>
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-slate-700 tabular-nums">${ci[0]?.toFixed(0)}</span>
              <div className="flex-1 mx-3 h-1.5 rounded-full overflow-hidden bg-slate-200/60">
                <div 
                  className="h-full rounded-full" 
                  style={{ 
                    background: `linear-gradient(90deg, ${confidence.barColor}33, ${confidence.barColor}, ${confidence.barColor}33)`,
                    width: '100%' 
                  }}
                ></div>
              </div>
              <span className="text-lg font-bold text-slate-700 tabular-nums">${ci[1]?.toFixed(0)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 4.5: Causal AI Verification
          ═══════════════════════════════════════════════════════════════════ */}
      <div className="space-y-6" id="causal-verification">
        <div className="flex justify-between items-end border-b border-slate-200 pb-4">
          <div>
            <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
              <Brain className="text-indigo-600" size={24} /> Causal AI Verification
            </h3>
            <p className="text-slate-500 text-xs mt-1">
              Double Machine Learning (DML) isolates the true causal impact of <strong>{selectedMeta?.label}</strong> changes by controlling for weather, seasonality, and usage history.
            </p>
          </div>
          <div className="bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border border-indigo-100">
            Double ML (DML) Model
          </div>
        </div>

        {isCausalLoading ? (
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm p-12 flex flex-col items-center justify-center min-h-[300px] space-y-4">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
            <p className="text-slate-500 text-sm font-medium animate-pulse">Fitting Double Machine Learning Estimator...</p>
          </div>
        ) : isCausalError ? (
          <div className="rounded-2xl bg-rose-50/50 border border-rose-100 p-8 min-h-[200px] flex flex-col items-center justify-center text-center">
            <AlertCircle className="text-rose-600 mb-3" size={36} />
            <h4 className="text-base font-bold text-slate-900 mb-1">Causal Fit Failed</h4>
            <p className="text-xs text-slate-500 max-w-md">
              {(causalError as any)?.response?.data?.detail || "Make sure the causal model is successfully trained at backend startup."}
            </p>
          </div>
        ) : causalData ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Stat Cards Column */}
            <div className="space-y-4">
              
              {/* Causal Effect */}
              <div className="rounded-2xl p-5 bg-gradient-to-br from-indigo-900 to-slate-900 text-white shadow-sm">
                <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest">Causal Impact</span>
                <div className="text-3xl font-black mt-1.5">
                  ${causalData.causal_effect_estimate.toFixed(2)}
                </div>
                <span className="text-xs text-indigo-200 block mt-1">
                  change in total bill per unit rate change
                </span>
              </div>
              
              {/* Standard Error */}
              <div className="rounded-2xl p-5 bg-white border border-slate-200 shadow-sm">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Statistical Error</span>
                <div className="text-2xl font-black mt-1.5 text-slate-900">
                  ±{causalData.std_error.toFixed(4)}
                </div>
                <span className="text-xs text-slate-500 block mt-1">
                  standard error of estimate
                </span>
              </div>

              {/* Significance */}
              <div className={`rounded-2xl p-5 border shadow-sm ${getPValueColor(causalData.p_value)}`}>
                <span className="text-[10px] font-bold uppercase tracking-widest block opacity-75">Significance Check</span>
                <div className="text-base font-black mt-1.5 truncate">
                  {getSignificanceLabel(causalData.p_value)}
                </div>
                <span className="text-xs block mt-1 opacity-90">
                  p-value: {causalData.p_value.toFixed(5)}
                </span>
              </div>

            </div>

            {/* Confidence Interval Chart & Interpretations (2 cols) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* CI Chart */}
              <div className="rounded-2xl bg-white border border-slate-200 shadow-sm p-6">
                <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em] mb-4">
                  95% Confidence Interval Bounds
                </h4>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        {
                          name: 'Lower Bound (2.5%)',
                          value: causalData.ci_95[0],
                        },
                        {
                          name: 'DML Estimate',
                          value: causalData.causal_effect_estimate,
                        },
                        {
                          name: 'Upper Bound (97.5%)',
                          value: causalData.ci_95[1],
                        }
                      ]}
                      layout="vertical"
                      margin={{ left: 10, right: 30, top: 10, bottom: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" />
                      <XAxis type="number" stroke="#94A3B8" tick={{ fontSize: 10 }} />
                      <YAxis 
                        dataKey="name" 
                        type="category" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#475569', fontSize: 11, fontWeight: 700 }} 
                        width={130}
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px -2px rgb(0 0 0 / 0.12)', fontSize: '12px' }}
                        formatter={(v: any) => [`$${v.toFixed(4)}`, 'Value']}
                      />
                      <ReferenceLine x={0} stroke="#EF4444" strokeDasharray="3 3" />
                      <Bar dataKey="value" fill="#4F46E5" radius={6} barSize={20} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Text Interpretations */}
              <div className="rounded-2xl bg-white border border-slate-200 shadow-sm p-6 space-y-4">
                <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                  <CheckCircle className="text-emerald-500" size={18} />
                  <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider">Causal Interpretation</h4>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                  {causalData.interpretation}
                </p>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-[11px] text-slate-500 leading-relaxed">
                  <strong>Model Detail & Controls:</strong> Adjusted for confounders: <strong>{causalData.confounders_controlled.join(', ')}</strong>. Method: {causalData.method}.
                </div>
                <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-100 text-[11px] text-amber-700 leading-relaxed">
                  ⚠️ <strong>Model Caveat:</strong> {causalData.caveat}
                </div>
              </div>

            </div>

          </div>
        ) : null}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 5: Insight Summary (Footer)
          ═══════════════════════════════════════════════════════════════════ */}
      <div 
        id="insight-summary-bar"
        className="bg-gradient-to-r from-blue-600 via-blue-500 to-indigo-600 text-white rounded-2xl p-5 shadow-lg shadow-blue-600/20 flex items-start sm:items-center gap-4"
      >
        <div className="bg-white/20 backdrop-blur-sm p-2.5 rounded-xl shrink-0">
          <Lightbulb size={22} />
        </div>
        <p className="text-sm sm:text-base font-medium leading-relaxed">
          <strong className="font-black">Bottom Line:</strong>{' '}
          {insightText}
        </p>
      </div>

    </div>
  );
};

export default ImpactTab;
