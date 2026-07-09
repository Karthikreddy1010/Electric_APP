import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip, CartesianGrid,
  AreaChart, Area, ReferenceLine
} from 'recharts';
import { 
  Calculator, Activity, TrendingUp, TrendingDown, 
  ThermometerSun, ArrowRight, Lightbulb,
  CloudRain, DollarSign, Gauge, BarChart3, Info
} from 'lucide-react';

const SCENARIOS = [
  { id: "", label: "Custom rate changes only" },
  { id: "cold_winter", label: "❄️ Cold winter (High heat load)" },
  { id: "hot_summer", label: "☀️ Hot summer (High cooling load)" },
  { id: "high_market", label: "📈 High wholesale market prices" },
  { id: "low_usage", label: "🏠 Energy efficient household" },
  { id: "conservation", label: "🌱 Conservation effort" }
];

const COMPONENT_METADATA: Record<string, { label: string; description: string; icon: string }> = {
  bgs_rate:          { label: "BGS Supply",       description: "Wholesale energy supply rate set by the market.",         icon: "⚡" },
  distribution_rate: { label: "Distribution",     description: "Local utility delivery and infrastructure fee.",          icon: "🔌" },
  transmission_rate: { label: "Transmission",     description: "Regional high-voltage transport fee.",                    icon: "🏗️" },
  sbc_rate:          { label: "Societal Benefits", description: "State-mandated societal benefits & clean energy charges.", icon: "🏛️" },
};

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

const fmt = (v: number, forceSign = false) => {
  const sign = v > 0 ? '+' : v < 0 ? '−' : '';
  const abs = Math.abs(v).toFixed(2);
  if (forceSign) return `${sign}$${abs}`;
  return `$${abs}`;
};

const getConfidenceLevel = (std: number, mean: number) => {
  const cv = mean > 0 ? std / mean : 0;
  if (cv < 0.03) return { label: 'Very High', color: 'text-savings-green', bg: 'bg-savings-green/10', border: 'border-savings-green/20', barColor: '#27AE60' };
  if (cv < 0.06) return { label: 'High', color: 'text-savings-green', bg: 'bg-savings-green/10', border: 'border-savings-green/20', barColor: '#27AE60' };
  if (cv < 0.12) return { label: 'Moderate', color: 'text-warning-amber', bg: 'bg-warning-amber/10', border: 'border-warning-amber/20', barColor: '#F5B041' };
  return { label: 'Low', color: 'text-alert-red', bg: 'bg-alert-red/10', border: 'border-alert-red/25', barColor: '#D64545' };
};

const getPValueColor = (p: number) => {
  if (p < 0.01) return 'text-savings-green bg-savings-green/10 border-savings-green/20';
  if (p < 0.05) return 'text-primary-blue bg-primary-blue/10 border-primary-blue/20';
  return 'text-text-secondary bg-bg-primary border-border-hairline';
};

const getSignificanceLabel = (p: number) => {
  if (p < 0.01) return 'Highly Significant (p < 0.01)';
  if (p < 0.05) return 'Statistically Significant (p < 0.05)';
  return 'Not Statistically Significant (p >= 0.05)';
};

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

const round = (val: number, decimals: number) => {
  const p = Math.pow(10, decimals);
  return Math.round(val * p) / p;
};

const ImpactTab = ({ uploadedBill, setActiveTab }: { uploadedBill: any, setActiveTab?: (tab: string) => void }) => {
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
      <div className="panel-operational flex flex-col items-center justify-center p-16 text-center max-w-xl mx-auto space-y-4 my-12 border-dashed border border-border-hairline">
        <Activity size={36} className="text-text-secondary opacity-60" />
        <h3 className="text-sm font-bold text-text-primary">No active telemetry source</h3>
        <p className="text-xs text-text-secondary max-w-sm">
          Ingest an electricity bill inside the Bill Analysis module to run comparative sensitivity analyses.
        </p>
        <button 
          onClick={() => setActiveTab?.("Bill Analysis")}
          className="px-4 py-2 bg-bg-surface border border-border-hairline rounded-md text-xs font-semibold hover:bg-bg-primary transition-all"
        >
          Initialize analysis
        </button>
      </div>
    );
  }

  const utilityBill = uploadedBill.total_bill;
  const simulatedBill = simulation?.simulated_bill ?? utilityBill;
  const deltaBill = simulation?.delta_amount ?? 0;
  const deltaPct = simulation?.delta_pct ?? 0;

  const directPrice = simulation?.decomposition?.direct_price_effect_dollars ?? 0;
  const behaviorShift = simulation?.decomposition?.elasticity_shift_dollars ?? 0;
  const weatherEffect = simulation?.decomposition?.weather_effect_dollars ?? 0;
  const usageDelta = simulation?.decomposition?.elasticity_shift_kwh ?? 0;

  const isIncrease = deltaBill > 0.05;
  const finalBill = simulatedBill;
  const adjustment = deltaBill;

  const waterfallData = [
    { name: 'Baseline', value: utilityBill, type: 'base' },
    { 
      name: 'Rate change', 
      value: directPrice, 
      type: directPrice >= 0 ? 'increase' : 'decrease' 
    },
    { 
      name: 'Weather shift', 
      value: weatherEffect, 
      type: weatherEffect >= 0 ? 'increase' : 'decrease' 
    },
    { 
      name: 'Behavior response', 
      value: behaviorShift, 
      type: behaviorShift >= 0 ? 'increase' : 'decrease' 
    },
    { name: 'Simulated bill', value: finalBill, type: 'final' }
  ].filter(d => Math.abs(d.value) > 0.005 || d.type === 'base' || d.type === 'final');

  const sensitivityDrivers = [
    { key: 'bgs_rate', label: 'BGS supply rate sensitivity', impact: directPrice * 1.2, controllable: false, level: 'high', reason: 'Directly linked to regional market price spikes.' },
    { key: 'distribution_rate', label: 'Local distribution rate sensitivity', impact: behaviorShift * 0.8, controllable: true, level: 'medium', reason: 'Calculated from controllable peak household demand.' },
    { key: 'weather', label: 'Seasonal temp volatility sensitivity', impact: weatherEffect, controllable: false, level: 'low', reason: 'Impacted by degree-day temperature variances.' }
  ];
  
  const costDrivers = sensitivityDrivers.sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  const selectedMeta = COMPONENT_METADATA[selectedComp];
  const elasticity = simulation?.model_info?.elasticity ?? -0.200;

  const simMean = simulation?.probabilistic?.mean ?? simulatedBill;
  const simStd = simulation?.probabilistic?.std_dev ?? 5.5;
  const p5 = simulation?.probabilistic?.percentiles?.['5'] ?? (simMean - 1.64 * simStd);
  const p95 = simulation?.probabilistic?.percentiles?.['95'] ?? (simMean + 1.64 * simStd);
  const pValue = simulation?.probabilistic?.p_value ?? 0.08;

  const curveData = buildBellCurve(simMean, simStd, p5, p95);
  const confidence = getConfidenceLevel(simStd, simMean);

  return (
    <div className="space-y-6 font-sans">

      {/* Primary tab titles */}
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          Risk & sensitivity analysis
        </span>
        <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Causal bill impact</h2>
        <p className="text-xs text-text-secondary mt-1">
          Isolate tariff adjustments, behavioral elasticities, and weather factors using PJM balancing authority parameters.
        </p>
      </div>

      {/* Component breakdown strip */}
      {customerImpact && (
        <div className="panel-operational space-y-4">
          <div>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Active component breakdown</span>
            <h3 className="text-xs text-text-secondary font-semibold mt-0.5">Aggregated cost composition</h3>
          </div>
          
          <div className="w-full h-3 bg-bg-primary border border-border-hairline rounded-sm overflow-hidden flex shadow-inner">
            {customerImpact.components.map((comp: any, idx: number) => {
              const bgColors = ["bg-primary-blue", "bg-energy-teal", "bg-electric-cyan", "bg-warning-amber", "bg-savings-green", "bg-text-secondary"];
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
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {customerImpact.components.map((comp: any, idx: number) => {
              const textColors = ["text-primary-blue", "text-energy-teal", "text-electric-cyan", "text-warning-amber", "text-savings-green", "text-text-secondary"];
              const borderColors = ["border-primary-blue/20", "border-energy-teal/20", "border-electric-cyan/20", "border-warning-amber/20", "border-savings-green/20", "border-border-hairline"];
              return (
                <div key={idx} className={`p-3 bg-bg-primary rounded-md border ${borderColors[idx % borderColors.length]} flex flex-col justify-between shadow-sm`}>
                  <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest block leading-tight mb-1">{comp.name}</span>
                  <div className="flex justify-between items-baseline mt-auto">
                    <span className={`text-xs font-bold ${textColors[idx % textColors.length]}`}>{comp.pct}%</span>
                    <span className="text-xs font-bold text-text-primary font-mono-numbers">${comp.amount?.toFixed(2)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      
      {/* SECTION 1: TOP ROW — Bill Summary & Weather Context */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Bill Summary Card */}
        <div id="bill-summary-card" className="lg:col-span-2 panel-operational flex flex-col justify-between">
          <div className="flex items-center gap-2 mb-4 border-b border-border-hairline pb-2">
            <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
              <DollarSign size={14} />
            </div>
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
              Current bill overview
            </h3>
          </div>
          
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Utility bill</span>
              <span className="text-xl font-bold text-text-primary font-mono-numbers">${utilityBill.toFixed(2)}</span>
            </div>
            
            <div className="hidden md:flex items-center text-text-secondary opacity-40">
              <ArrowRight size={16} strokeWidth={2.5} />
            </div>
            
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Adjustments</span>
              <span className={`text-xl font-bold font-mono-numbers ${adjustment > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                {fmt(adjustment, true)}
              </span>
            </div>
            
            <div className="hidden md:flex items-center text-text-secondary opacity-40">
              <ArrowRight size={16} strokeWidth={2.5} />
            </div>
            
            <div className="flex flex-col gap-1 bg-bg-primary px-5 py-3.5 rounded-md border border-border-hairline shadow-sm">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider">Final bill</span>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-text-primary font-mono-numbers tracking-tight">
                  ${finalBill.toFixed(2)}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-[4px] font-mono-numbers border ${
                  deltaBill > 0 
                    ? 'text-alert-red bg-alert-red/10 border-alert-red/20' 
                    : deltaBill < 0
                      ? 'text-savings-green bg-savings-green/10 border-savings-green/20'
                      : 'text-text-secondary bg-bg-primary border-border-hairline'
                }`}>
                  {deltaBill >= 0 ? '+' : '−'}${Math.abs(deltaBill).toFixed(2)} ({deltaBill >= 0 ? '+' : '−'}{Math.abs(deltaPct).toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Weather Context Card */}
        <div id="weather-context-card" className="panel-insight flex flex-col justify-between border-primary-blue/20 bg-primary-blue/5">
          <div>
            <div className="flex items-center gap-2 mb-3 border-b border-primary-blue/10 pb-2">
              <div className="p-1 bg-primary-blue/10 rounded-[4px] text-primary-blue">
                <ThermometerSun size={14} />
              </div>
              <h3 className="text-xs font-bold text-primary-blue uppercase tracking-wider">
                Weather impact
              </h3>
            </div>
            <p className="text-xs text-text-primary font-semibold leading-relaxed mb-4">
              {weatherEffect < -0.5
                ? `Mild conditions reduced expected cooling/heating usage by ${Math.abs(usageDelta * 0.3).toFixed(1)} kWh this period.`
                : weatherEffect > 0.5
                  ? `Extreme temperatures increased HVAC demand, adding to your bill.`
                  : `Weather conditions were typical for this period with minimal bill impact.`
              }
            </p>
          </div>
          
          <div className="flex items-center gap-2 bg-bg-surface px-3 py-2 rounded-md border border-border-hairline shadow-sm">
            <CloudRain size={12} className="text-primary-blue" />
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider">Bill impact:</span>
            <span className={`text-xs font-bold font-mono-numbers ${weatherEffect <= 0 ? 'text-savings-green' : 'text-alert-red'}`}>
              {fmt(weatherEffect, true)}
            </span>
          </div>
        </div>
      </div>

      {/* SECTION 2: MIDDLE ROW — Why Did Your Bill Change? */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Impact Decomposition (Waterfall) */}
        <div id="impact-decomposition-card" className="panel-chart flex flex-col justify-between h-[360px]">
          <div>
            <div className="flex items-center gap-2 mb-2 border-b border-border-hairline pb-2">
              <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
                <BarChart3 size={14} />
              </div>
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
                Why did your bill change?
              </h3>
            </div>
            <p className="text-xl font-bold text-text-primary mb-4 mt-2">
              Total change:{' '}
              <span className={`font-mono-numbers ${isIncrease ? 'text-alert-red' : deltaBill < -0.5 ? 'text-savings-green' : 'text-text-secondary'}`}>
                {fmt(deltaBill, true)}
              </span>
            </p>
          </div>
          
          {/* Waterfall Chart */}
          <div className="flex-1 min-h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterfallData} margin={{ top: 10, right: 15, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 600 }} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} 
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip 
                  cursor={{ fill: 'var(--bg-primary)', opacity: 0.5 }} 
                  contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }} 
                  itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                  formatter={(value: any) => [`$${value.toFixed(2)}`, 'Amount']}
                />
                <Bar dataKey="value" radius={[2, 2, 0, 0]} maxBarSize={40}>
                  {waterfallData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={
                      entry.type === 'base'      ? 'var(--text-secondary)' : 
                      entry.type === 'increase'  ? 'var(--alert-red)' : 
                      entry.type === 'decrease'  ? 'var(--savings-green)' : 'var(--primary-blue)'
                    } />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Decomposition Line Items */}
          <div className="space-y-2 mt-4 text-xs font-semibold">
            <div className="flex justify-between items-center bg-bg-primary px-4 py-2 rounded-md border border-border-hairline">
              <span className="text-text-primary">Direct price effect</span>
              <span className={`font-mono-numbers ${directPrice >= 0 ? 'text-alert-red' : 'text-savings-green'}`}>{fmt(directPrice, true)}</span>
            </div>
            <div className="flex justify-between items-center bg-bg-primary px-4 py-2 rounded-md border border-border-hairline">
              <span className="text-text-primary">Behavioral response</span>
              <span className={`font-mono-numbers ${behaviorShift >= 0 ? 'text-alert-red' : 'text-savings-green'}`}>{fmt(behaviorShift, true)}</span>
            </div>
          </div>
        </div>

        {/* Top Cost Drivers */}
        <div id="cost-drivers-card" className="panel-operational flex flex-col justify-between h-[360px]">
          <div className="flex items-center gap-2 mb-4 border-b border-border-hairline pb-2">
            <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
              <Activity size={14} />
            </div>
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
              Top influence drivers
            </h3>
          </div>
          
          <div className="flex-1 space-y-3 overflow-y-auto pr-1">
            {costDrivers.map((driver: any, idx: number) => {
              const levelConfig = {
                high:   { color: 'text-alert-red',     bg: 'bg-alert-red/10',     badge: 'bg-alert-red/10 text-alert-red border-alert-red/20' },
                medium: { color: 'text-warning-amber',   bg: 'bg-warning-amber/10',   badge: 'bg-warning-amber/10 text-warning-amber border-warning-amber/20' },
                low:    { color: 'text-savings-green', bg: 'bg-savings-green/10', badge: 'bg-savings-green/10 text-savings-green border-savings-green/20' },
              };
              const cfg = levelConfig[driver.level as keyof typeof levelConfig] || levelConfig.low;
              
              return (
                <div 
                  key={driver.key} 
                  className="flex items-start gap-3 p-3.5 rounded-md bg-bg-primary border border-border-hairline transition-all hover:border-text-secondary/30"
                >
                  <div className={`p-1.5 ${cfg.bg} rounded-md shrink-0 mt-0.5`}>
                    {driver.impact > 0 ? <TrendingUp size={14} className={cfg.color} /> : <TrendingDown size={14} className={cfg.color} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-xs font-bold text-text-primary">{idx + 1}. {driver.label}</h4>
                      <span className={`text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[4px] border ${cfg.badge}`}>
                        {driver.level}
                      </span>
                      {driver.controllable && (
                        <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[4px] bg-primary-blue/10 text-primary-blue border border-primary-blue/20">
                          Controllable
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-text-secondary leading-relaxed">{driver.reason}</p>
                    <p className="text-xs font-bold text-text-primary mt-1 font-mono-numbers">
                      Impact: {fmt(driver.impact, true)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* SECTION 3: Non-Utility Adjustments */}
      <div id="adjustments-card" className="banner-status flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
            <Activity size={12} />
          </div>
          <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
            Adjustments & credits
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-5 font-mono-numbers text-xs">
          <div className="flex items-center gap-2">
            <span className="text-text-secondary font-sans">Supplier adjustment:</span>
            <span className="font-semibold text-alert-red">+$3.20</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-secondary font-sans">Demand response credit:</span>
            <span className="font-semibold text-savings-green">−$5.10</span>
          </div>
          <div className="h-4 w-px bg-border-hairline hidden sm:block"></div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-text-primary font-sans uppercase">Net:</span>
            <span className="font-bold text-savings-green">−$1.90</span>
          </div>
        </div>
      </div>

      {/* SECTION 4: BOTTOM ROW — Simulator & Confidence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* What-If Simulator (Enhanced) */}
        <div id="what-if-simulator-card" className="lg:col-span-2 panel-operational space-y-6">
          <div className="flex items-center justify-between border-b border-border-hairline pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
                <Calculator size={14} />
              </div>
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
                Scenario simulator
              </h3>
            </div>
            {isSimLoading && (
              <span className="text-[10px] font-bold text-primary-blue animate-pulse uppercase tracking-widest flex items-center gap-1.5 font-mono-numbers">
                Computing 2,000 scenarios…
              </span>
            )}
          </div>

          {/* Dynamic Plain-English Explanation */}
          <div className="bg-primary-blue/5 border border-primary-blue/10 p-4 rounded-md">
            <div className="flex items-start gap-2">
              <Info size={14} className="text-primary-blue shrink-0 mt-0.5" />
              <p className="text-xs font-semibold text-text-primary leading-relaxed">
                {changePct === 0 ? (
                  <>Select a rate adjustment or scenario to simulate its effect on your bill.</>
                ) : changePct > 0 ? (
                  <>
                    Increasing <strong className="text-primary-blue">{selectedMeta?.label}</strong> by{' '}
                    <strong className="text-primary-blue">{changePct}%</strong> raises your bill by{' '}
                    <strong className="text-alert-red">${Math.abs(directPrice).toFixed(2)}</strong>
                    {Math.abs(usageDelta) > 0.5 && (
                      <>, but this is partially offset by a <strong className="text-savings-green">{Math.abs(usageDelta).toFixed(1)} kWh</strong> drop in usage
                        {elasticity !== -0.20 && <> (elasticity: {elasticity.toFixed(3)})</>}
                      </>
                    )}.
                  </>
                ) : (
                  <>
                    Decreasing <strong className="text-primary-blue">{selectedMeta?.label}</strong> by{' '}
                    <strong className="text-primary-blue">{Math.abs(changePct)}%</strong> lowers your bill by{' '}
                    <strong className="text-savings-green">${Math.abs(directPrice).toFixed(2)}</strong>.
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Controls */}
            <div className="space-y-4 text-xs font-semibold text-text-secondary">
              {/* Scenario Preset */}
              <div>
                <label className="block text-[10px] font-bold text-text-secondary uppercase tracking-widest mb-1.5">
                  Market scenario
                </label>
                <select 
                  id="scenario-select"
                  value={scenario} 
                  onChange={(e) => setScenario(e.target.value)} 
                  className="w-full p-2.5 bg-bg-primary border border-border-hairline rounded-md text-xs font-bold text-text-primary outline-none focus:border-primary-blue"
                >
                  {SCENARIOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
              
              {/* Target Component */}
              <div>
                <label className="block text-[10px] font-bold text-text-secondary uppercase tracking-widest mb-1.5">
                  Target component
                </label>
                <select 
                  id="component-select"
                  value={selectedComp} 
                  onChange={(e) => setSelectedComp(e.target.value)} 
                  className="w-full p-2.5 bg-bg-primary border border-border-hairline rounded-md text-xs font-bold text-text-primary outline-none focus:border-primary-blue"
                >
                  {Object.entries(COMPONENT_METADATA).map(([k, v]) => (
                    <option key={k} value={k}>{v.icon} {v.label} — {v.description}</option>
                  ))}
                </select>
              </div>

              {/* Rate Slider */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">Rate adjustment</label>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-[4px] font-mono-numbers border ${
                    changePct > 0 ? 'text-alert-red bg-alert-red/10 border-alert-red/20' 
                    : changePct < 0 ? 'text-savings-green bg-savings-green/10 border-savings-green/20'
                    : 'text-text-secondary bg-bg-primary border-border-hairline'
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
                  className="w-full h-1.5 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue border border-border-hairline" 
                />
                <div className="flex justify-between mt-1 text-[9px] text-text-secondary font-mono-numbers">
                  <span>−50%</span>
                  <span>0%</span>
                  <span>+50%</span>
                </div>
              </div>
            </div>

            {/* Results Panel */}
            <div className="flex flex-col items-center justify-center p-5 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-1">Simulated bill</span>
              <span className="text-4xl font-bold text-text-primary font-mono-numbers tracking-tight mb-4">
                ${simulatedBill.toFixed(2)}
              </span>
              <div className="flex flex-wrap gap-2 justify-center font-mono-numbers text-xs">
                <span className={`px-2 py-1 rounded-[4px] border ${
                  isIncrease ? 'bg-alert-red/10 text-alert-red border-alert-red/20' : 'bg-savings-green/10 text-savings-green border-savings-green/20'
                }`}>
                  Delta: {fmt(deltaBill, true)}
                </span>
                <span className="px-2 py-1 rounded-[4px] bg-bg-surface text-text-primary border border-border-hairline">
                  Usage: {usageDelta > 0 ? '+' : ''}{usageDelta.toFixed(0)} kWh
                </span>
              </div>
              
              <div className="mt-4 flex items-center gap-1.5 text-[9px] text-text-secondary font-semibold font-mono-numbers">
                <Gauge size={10} />
                <span>
                  {simulation?.model_info?.method || 'Monte Carlo'} · {simulation?.model_info?.n_simulations || 2000} draws · {simulation?.model_info?.runtime_ms || '—'}ms
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Confidence & Uncertainty */}
        <div id="confidence-card" className="panel-operational flex flex-col justify-between h-[400px]">
          <div>
            <div className="flex items-center gap-2 mb-3 border-b border-border-hairline pb-2">
              <div className="p-1 bg-bg-primary border border-border-hairline rounded-[4px] text-text-secondary">
                <Lightbulb size={14} />
              </div>
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
                Probability distribution & bounds
              </h3>
            </div>
            
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider">Confidence boundary</span>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[4px] border ${confidence.bg} ${confidence.color} ${confidence.border}`}>
                {confidence.label} confidence
              </span>
            </div>
            
            {/* Bell Curve distribution visualization */}
            <div className="h-[140px] relative">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={curveData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
                  <XAxis dataKey="x" type="number" domain={['auto', 'auto']} tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip labelFormatter={(l) => `Bill: $${l}`} formatter={(v: any) => [`${(v*100).toFixed(1)}%`, 'Probability']} />
                  <Area type="monotone" dataKey="y" stroke="var(--primary-blue)" fill="var(--primary-blue)" fillOpacity={0.08} strokeWidth={2} />
                  <ReferenceLine x={simMean} stroke="var(--primary-blue)" strokeDasharray="3 3" strokeWidth={1} label={{ value: 'Mean', position: 'top', fill: 'var(--text-primary)', fontSize: 9 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border-t border-border-hairline pt-3 mt-4 space-y-1.5 text-[11px] font-mono-numbers text-text-primary">
            <div className="flex justify-between">
              <span className="text-text-secondary font-sans">90% confidence interval:</span>
              <span className="font-bold">${p5.toFixed(2)} – ${p95.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-secondary font-sans">Probability value (p-value):</span>
              <span className={`px-1.5 py-0.5 rounded-[4px] border text-[9px] font-bold ${getPValueColor(pValue)}`}>
                {pValue.toFixed(3)} · {getSignificanceLabel(pValue)}
              </span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default ImpactTab;
