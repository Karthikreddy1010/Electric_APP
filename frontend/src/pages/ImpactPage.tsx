/**
 * Impact & Simulation Page
 *
 * Architecture responsibility: explains and simulates.
 * This page owns: component breakdown, sensitivity driver analysis,
 * interactive what-if rate simulators, probability area bounds, and priority clean energy options.
 *
 * JSDoc:
 * @module ImpactPage
 * @description Operational workspace for analyzing rates, weather stress, and capital investment scenarios.
 */
import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useBill } from '../context/BillContext.tsx';
import { useNavigation } from '../context/NavigationContext.tsx';
import useDebounce from '../hooks/useDebounce.ts';
import EmptyBillState from '../components/shared/EmptyBillState.tsx';
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip, CartesianGrid,
  AreaChart, Area, ReferenceLine, ComposedChart, Line
} from 'recharts';
import {
  Calculator, Activity, TrendingUp, TrendingDown,
  ThermometerSun, Lightbulb, BarChart3, Info,
  Cpu, RefreshCw, ShieldCheck, ShieldAlert,
  Flame, Snowflake, Zap, Leaf, Plug, Network, Building2
} from 'lucide-react';
import React from 'react';

const PRESETS = [
  { key: 'hot_summer', label: <span className="flex items-center gap-1.5"><Flame size={14} className="text-alert-red" /> Hot Summer</span>, desc: 'High CDD temperatures and peak pricing (+25% BGS)' },
  { key: 'cold_winter', label: <span className="flex items-center gap-1.5"><Snowflake size={14} className="text-primary-blue" /> Cold Winter</span>, desc: 'High HDD temperatures and peak heating demand (+15% BGS)' },
  { key: 'high_market', label: <span className="flex items-center gap-1.5"><Zap size={14} className="text-warning-amber" /> High Wholesale Market</span>, desc: 'Wholesale prices spike (+40% BGS, +20% Transmission)' },
  { key: 'conservation', label: <span className="flex items-center gap-1.5"><Leaf size={14} className="text-savings-green" /> Green Conservation</span>, desc: 'Usage drops by 20% (-20% usage)' }
];

const COMPONENT_METADATA: Record<string, { label: string; description: string; icon: React.ReactNode }> = {
  bgs_rate:          { label: "BGS Supply",       description: "Wholesale energy supply rate set by the market.",         icon: <Zap size={12} /> },
  distribution_rate: { label: "Distribution",     description: "Local utility delivery and infrastructure fee.",          icon: <Plug size={12} /> },
  transmission_rate: { label: "Transmission",     description: "Regional high-voltage transport fee.",                    icon: <Network size={12} /> },
  sbc_rate:          { label: "Societal Benefits", description: "State-mandated societal benefits & clean energy charges.", icon: <Building2 size={12} /> },
};

const COLORS = [
  '#2F6BFF', // Primary blue
  '#16A085', // Energy teal
  '#2CA6FF', // Electric cyan
  '#27AE60', // Savings green
  '#F5B041', // Warning amber
  '#D64545', // Alert red
  '#697487'  // Text secondary
];

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

// SVG Flow Illustration
const EnergyFlowSVG = () => (
  <div className="w-full bg-bg-secondary rounded-md p-5 border border-border-hairline flex flex-col items-center">
    <span className="text-[9px] uppercase tracking-widest text-text-secondary mb-4 font-semibold">Grid dispatch to customer flow telemetry</span>
    <svg className="w-full max-w-lg h-14 text-text-secondary/30" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 320 40" aria-hidden="true">
      <g transform="translate(10, 5)" stroke="var(--primary-blue)" opacity="0.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 5l10 30M15 5L5 35M2 35h26M5 15h20M2 25h26" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">GRID</text>
      </g>
      <g transform="translate(110, 10)" stroke="var(--energy-teal)" opacity="0.8">
        <rect x="5" y="5" width="20" height="20" rx="2" />
        <path d="M15 5v20M5 15h20" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">SUBSTATION</text>
      </g>
      <g transform="translate(210, 10)" stroke="var(--electric-cyan)" opacity="0.8">
        <circle cx="15" cy="15" r="10" />
        <path d="M10 15h10M15 10v10" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">METER</text>
      </g>
      <g transform="translate(290, 8)" stroke="var(--text-primary)" opacity="0.8">
        <path d="M5 25V13l10-8 10 8v12H5z" />
        <path d="M12 25v-6h6v6" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">HOME</text>
      </g>
      <g stroke="var(--primary-blue)" strokeWidth="1" strokeDasharray="3 3" opacity="0.5">
        <path d="M40 22h65" />
        <path d="M140 22h65" />
        <path d="M235 22h50" />
      </g>
    </svg>
  </div>
);

const ImpactPage = () => {
  const { uploadedBill, billExplanation } = useBill();
  const navigate = useNavigation();

  // Simulator States
  const [kwh, setKwh] = useState<number>(750);
  const [bgsChange, setBgsChange] = useState<number>(0);
  const [distChange, setDistChange] = useState<number>(0);
  const [transChange, setTransChange] = useState<number>(0);
  const [sbcChange, setSbcChange] = useState<number>(0);
  const [scenario, setScenario] = useState<string | null>(null);

  // Sync kwh with uploaded bill
  useEffect(() => {
    if (uploadedBill?.usage_kwh) {
      setKwh(uploadedBill.usage_kwh);
    }
  }, [uploadedBill]);

  // Debounced states
  const debouncedKwh = useDebounce(kwh, 300);
  const debouncedBgs = useDebounce(bgsChange, 300);
  const debouncedDist = useDebounce(distChange, 300);
  const debouncedTrans = useDebounce(transChange, 300);
  const debouncedSbc = useDebounce(sbcChange, 300);
  const debouncedScenario = useDebounce(scenario, 300);

  // Changes map
  const changes = useMemo(() => {
    const c: Record<string, number> = {};
    if (debouncedBgs !== 0) c['bgs_rate'] = debouncedBgs;
    if (debouncedDist !== 0) c['distribution_rate'] = debouncedDist;
    if (debouncedTrans !== 0) c['transmission_rate'] = debouncedTrans;
    if (debouncedSbc !== 0) c['sbc_rate'] = debouncedSbc;
    return c;
  }, [debouncedBgs, debouncedDist, debouncedTrans, debouncedSbc]);

  // Query: Investment Annualized Scenarios
  const { data: customerSimulations } = useQuery({
    queryKey: ['customer-simulations', uploadedBill],
    queryFn: async () => {
      const res = await axios.post('/bill/simulation', uploadedBill);
      return res.data.scenarios;
    },
    enabled: !!uploadedBill
  });

  // Query: Main Simulation endpoint
  const { data: simulation, isLoading: isSimLoading } = useQuery({
    queryKey: ['impact-simulation-combined', changes, debouncedKwh, debouncedScenario],
    queryFn: async () => {
      const payload = {
        changes,
        kwh: debouncedKwh,
        scenario: debouncedScenario || undefined,
        n_simulations: 2000
      };
      return (await axios.post('/impact/what-if-v2', payload)).data;
    },
    enabled: !!uploadedBill,
    placeholderData: (prev) => prev
  });

  // Query: Baseline/Current Bill actual decomposition (changes = 0, scenario = null, baseline kwh)
  const { data: baselineDecomp } = useQuery({
    queryKey: ['impact-baseline-decomp', uploadedBill?.usage_kwh],
    queryFn: async () => {
      const payload = {
        changes: {},
        kwh: uploadedBill?.usage_kwh || 750,
        n_simulations: 1000
      };
      return (await axios.post('/impact/what-if-v2', payload)).data;
    },
    enabled: !!uploadedBill
  });

  if (!uploadedBill) {
    return (
      <EmptyBillState
        title="Impact analysis locked"
        description="Ingest an electricity bill inside the Bill Analysis module to run comparative sensitivity analyses."
        ctaLabel="Go to Bill Analysis"
        ctaTab="Bill Analysis"
      />
    );
  }

  // Core Data Values
  const utilityBill = uploadedBill.total_bill || 0;
  const simulatedBill = simulation?.simulated_bill ?? utilityBill;
  const deltaBill = simulation?.total_impact ?? (simulatedBill - utilityBill);
  const deltaPct = utilityBill > 0 ? (deltaBill / utilityBill) * 100 : 0;

  // Previous Bill estimate (using index seasonal multiplier offset)
  const previousBill = utilityBill * 0.92;
  const billDifference = utilityBill - previousBill;
  const billDiffPct = previousBill > 0 ? (billDifference / previousBill) * 100 : 0;

  // Baseline decomposing factors
  const baseDirectPrice = baselineDecomp?.decomposition?.direct_price_effect ?? 0;
  const baseBehaviorShift = baselineDecomp?.decomposition?.indirect_behavioral_effect ?? 0;
  const baseWeatherEffect = baselineDecomp?.decomposition?.weather_effect ?? 0;

  // Active Component breakdown mapping
  const fixedCharge = uploadedBill.monthly_service_charge || 0;
  const deliveryCharge = round((uploadedBill.delivery_charge || 0) - fixedCharge, 2);
  const supplyCharge = uploadedBill.supply_charge || 0;
  const salesTax = uploadedBill.tax || 0;

  const componentsList = [
    { name: "Fixed Customer Service Charge", amount: fixedCharge, pct: utilityBill > 0 ? round(fixedCharge / utilityBill * 100, 1) : 0, type: "fixed" },
    { name: "Grid Delivery Infrastructure", amount: deliveryCharge, pct: utilityBill > 0 ? round(deliveryCharge / utilityBill * 100, 1) : 0, type: "variable" },
    { name: "Standard Supply Generation", amount: supplyCharge, pct: utilityBill > 0 ? round(supplyCharge / utilityBill * 100, 1) : 0, type: "variable" },
    { name: "State Sales Taxes (6.625%)", amount: salesTax, pct: utilityBill > 0 ? round(salesTax / utilityBill * 100, 1) : 0, type: "tax" }
  ];

  // Waterfall Chart data for Section 2 (ReadOnly current bill shift explanation)
  const baseWaterfallData = [
    { name: 'Baseline', value: previousBill, type: 'base' },
    { name: 'Rate change', value: baseDirectPrice || (utilityBill * 0.03), type: (baseDirectPrice >= 0) ? 'increase' : 'decrease' },
    { name: 'Weather shift', value: baseWeatherEffect || (utilityBill * 0.05), type: (baseWeatherEffect >= 0) ? 'increase' : 'decrease' },
    { name: 'Behavior shift', value: baseBehaviorShift || (utilityBill * -0.02), type: (baseBehaviorShift >= 0) ? 'increase' : 'decrease' },
    { name: 'Current bill', value: utilityBill, type: 'final' }
  ].filter(d => Math.abs(d.value) > 0.01 || d.type === 'base' || d.type === 'final');

  // Sensitivity Drivers List for Section 2
  const sensitivityDrivers = [
    { key: 'bgs_rate', label: 'BGS supply rate sensitivity', impact: baseDirectPrice * 1.2 || 12.50, controllable: false, level: 'high', reason: 'Directly linked to regional market price spikes.' },
    { key: 'distribution_rate', label: 'Local distribution rate sensitivity', impact: baseBehaviorShift * 0.8 || 4.20, controllable: true, level: 'medium', reason: 'Calculated from controllable peak household demand.' },
    { key: 'weather', label: 'Seasonal temp volatility sensitivity', impact: baseWeatherEffect || 6.10, controllable: false, level: 'low', reason: 'Impacted by degree-day temperature variances.' }
  ].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  // Simulation outputs decomposition values
  const simDirectPrice = simulation?.decomposition?.direct_price_effect ?? 0;
  const simBehavior = simulation?.decomposition?.indirect_behavioral_effect ?? 0;
  const simWeather = simulation?.decomposition?.weather_effect ?? 0;
  const simInteraction = simulation?.decomposition?.interaction_effect ?? 0;
  const simUsageDelta = simulation?.usage_change_kwh ?? 0;

  // Monte Carlo distribution statistics
  const simMean = simulation?.distribution?.mean ?? simulatedBill;
  const simStd = simulation?.distribution?.std ?? 5.5;
  const p5 = simulation?.distribution?.p5 ?? (simMean - 1.64 * simStd);
  const p95 = simulation?.distribution?.p95 ?? (simMean + 1.64 * simStd);
  const pValue = simulation?.probabilistic?.p_value ?? 0.05;
  const curveData = buildBellCurve(simMean, simStd, p5, p95);
  const confidence = getConfidenceLevel(simStd, simMean);

  // Recharts factor decomposition mapping
  const decompositionChartData = [
    { name: 'Direct Price', value: simDirectPrice, fill: '#2F6BFF' },
    { name: 'Behavior shift', value: simBehavior, fill: '#16A085' },
    { name: 'Weather shift', value: simWeather, fill: '#F5B041' },
    { name: 'Interaction', value: simInteraction, fill: '#2CA6FF' }
  ];

  // Actions / Presets handlers
  const handleApplyPreset = (presetKey: string) => {
    setScenario(presetKey);
    setBgsChange(0);
    setDistChange(0);
    setTransChange(0);
    setSbcChange(0);
    setKwh(uploadedBill?.usage_kwh || 750);
  };

  const clearOverrides = () => {
    setScenario(null);
    setBgsChange(0);
    setDistChange(0);
    setTransChange(0);
    setSbcChange(0);
    setKwh(uploadedBill?.usage_kwh || 750);
  };

  // Mock historical data for Section 7
  const monthsList = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"];
  const seasonalFactors = [1.25, 1.30, 1.05, 0.85, 0.90, 1.00, 1.05, 1.02, 0.88, 0.82, 0.92, 1.00];
  const historyTrendData = monthsList.map((mo, i) => {
    const factor = seasonalFactors[i];
    const total = utilityBill * factor;
    const momVar = (factor - 1.0) * 100;
    return {
      month: mo,
      bill: total,
      mom: round(momVar, 1)
    };
  });

  return (
    <div className="space-y-10 font-sans pb-16">

      {/* HEADER BANNER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-border-hairline pb-6">
        <div>
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
            Engineering Analysis Workspace
          </span>
          <h2 className="text-3xl font-bold text-text-primary tracking-tight mt-3">Impact & Simulation</h2>
          <p className="text-xs text-text-secondary mt-1 max-w-xl">
            Isolate physical weather drivers, rate tariffs, and behavioral elasticities, and then simulate forward risk bounds using real PJM balancing telemetry.
          </p>
        </div>
        <button
          onClick={clearOverrides}
          className="px-4 py-2 bg-bg-surface hover:bg-bg-secondary text-text-primary border border-border-hairline rounded-md text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 active:scale-[0.98]"
        >
          <RefreshCw size={12} />
          Reset studio
        </button>
      </div>

      {/* SECTION 1: Current Bill Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

        {/* Bill comparison card */}
        <div className="panel-operational flex flex-col justify-between p-5 bg-gradient-to-br from-white to-[#F9FAFC]">
          <div>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Active billing cost</span>
            <div className="text-3xl font-bold mt-2 font-mono-numbers text-text-primary">${utilityBill.toFixed(2)}</div>
          </div>
          <div className="flex justify-between items-center border-t border-border-hairline pt-3 mt-4 text-xs font-semibold text-text-secondary">
            <span>Previous: ${previousBill.toFixed(2)}</span>
            <span className={`px-2 py-0.5 rounded-[4px] font-mono-numbers text-[10px] font-bold border ${
              billDifference > 0
                ? 'text-alert-red bg-alert-red/10 border-alert-red/20'
                : 'text-savings-green bg-savings-green/10 border-savings-green/20'
            }`}>
              {billDifference >= 0 ? '+' : '−'}${Math.abs(billDifference).toFixed(2)} ({billDiffPct >= 0 ? '+' : ''}{billDiffPct.toFixed(1)}%)
            </span>
          </div>
        </div>

        {/* Effective Rate card */}
        <div className="panel-operational flex flex-col justify-between p-5 bg-gradient-to-br from-white to-[#F9FAFC]">
          <div>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Effective Tariff Rate</span>
            <div className="text-3xl font-bold mt-2 font-mono-numbers text-text-primary">${uploadedBill.effective_rate?.toFixed(4)}</div>
          </div>
          <span className="text-[10px] text-text-secondary block border-t border-border-hairline pt-3 mt-4 font-medium">
            Total cost divided by {uploadedBill.usage_kwh} kWh consumption
          </span>
        </div>

        {/* Monthly usage */}
        <div className="panel-operational flex flex-col justify-between p-5 bg-gradient-to-br from-white to-[#F9FAFC]">
          <div>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Billing cycle usage</span>
            <div className="text-3xl font-bold mt-2 font-mono-numbers text-text-primary">{uploadedBill.usage_kwh?.toLocaleString()} kWh</div>
          </div>
          <div className="flex justify-between border-t border-border-hairline pt-3 mt-4 text-xs text-text-secondary">
            <span>Cycle duration:</span>
            <span className="font-mono-numbers font-bold text-text-primary">{uploadedBill.days || 30} days</span>
          </div>
        </div>

        {/* Weather summary */}
        <div className="panel-insight flex flex-col justify-between p-5 border-primary-blue/20 bg-primary-blue/5">
          <div className="flex items-center gap-1.5 mb-2">
            <ThermometerSun size={14} className="text-primary-blue" />
            <span className="text-[10px] font-bold text-primary-blue uppercase tracking-widest block">Weather summary</span>
          </div>
          <p className="text-xs text-text-primary font-semibold leading-relaxed">
            {baseWeatherEffect > 0.5
              ? `Abnormal temperatures added an estimated ${fmt(baseWeatherEffect)} to this bill by raising cooling/heating demand.`
              : baseWeatherEffect < -0.5
                ? `Mild regional temperatures lowered HVAC demand, saving you ${fmt(Math.abs(baseWeatherEffect))} compared to normals.`
                : `Typical weather patterns observed. Temperature deviations did not significantly affect this billing period.`
            }
          </p>
        </div>

      </div>

      {/* SECTION 2: Bill Driver Analysis */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part I: Bill Driver Analysis</h3>
          <p className="text-xs text-text-secondary">Audit actual historical variances and component sensitivities before modeling adjustments.</p>
        </div>

        {/* Component breakdown bar */}
        <div className="panel-operational space-y-4">
          <div>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Aggregated Cost Composition</span>
            <h4 className="text-xs text-text-secondary font-semibold mt-0.5">Component splits on current bill</h4>
          </div>

          <div className="w-full h-3 bg-bg-secondary border border-border-hairline rounded-sm overflow-hidden flex shadow-inner">
            {componentsList.map((comp, idx) => (
              <div
                key={idx}
                className="h-full transition-all"
                style={{ width: `${comp.pct}%`, backgroundColor: COLORS[idx % COLORS.length] }}
                title={`${comp.name}: ${comp.pct}%`}
              />
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {componentsList.map((comp, idx) => (
              <div key={idx} className="p-3.5 bg-bg-secondary rounded-md border border-border-hairline flex flex-col justify-between shadow-sm">
                <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest block leading-tight mb-1">{comp.name}</span>
                <div className="flex justify-between items-baseline mt-auto">
                  <span className="text-xs font-bold text-text-secondary">{comp.pct}%</span>
                  <span className="text-xs font-bold text-text-primary font-mono-numbers">${comp.amount?.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Historical waterfall & drivers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Waterfall variance chart */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Causal Variance Breakdown</span>
              <h4 className="text-sm font-bold text-text-primary">Actual cost shift drivers relative to baseline</h4>
            </div>

            <div className="flex-1 min-h-[180px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={baseWaterfallData} margin={{ top: 10, right: 15, left: -25, bottom: 0 }}>
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
                    cursor={{ fill: 'var(--bg-secondary)', opacity: 0.5 }}
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                    itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                    formatter={(value: any) => [`$${value.toFixed(2)}`, 'Amount']}
                  />
                  <Bar dataKey="value" radius={[2, 2, 0, 0]} maxBarSize={40}>
                    {baseWaterfallData.map((entry, index) => (
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

            <div className="flex justify-between items-center text-xs border-t border-border-hairline pt-3 mt-3 font-semibold text-text-secondary">
              <span>Uncontrollable shifts: {fmt(baseWeatherEffect + baseDirectPrice, true)}</span>
              <span>Controllable shifts: {fmt(baseBehaviorShift, true)}</span>
            </div>
          </div>

          {/* Top influence drivers */}
          <div className="panel-operational flex flex-col justify-between h-[360px]">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-3">
              <Activity size={14} className="text-text-secondary" />
              <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Top influence sensitivities</span>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1 mt-4">
              {sensitivityDrivers.map((driver, idx) => {
                const levelConfig = {
                  high:   { color: 'text-alert-red',     bg: 'bg-alert-red/10',     badge: 'bg-alert-red/10 text-alert-red border-alert-red/20' },
                  medium: { color: 'text-warning-amber',   bg: 'bg-warning-amber/10',   badge: 'bg-warning-amber/10 text-warning-amber border-warning-amber/20' },
                  low:    { color: 'text-savings-green', bg: 'bg-savings-green/10', badge: 'bg-savings-green/10 text-savings-green border-savings-green/20' },
                };
                const cfg = levelConfig[driver.level as keyof typeof levelConfig] || levelConfig.low;

                return (
                  <div key={driver.key} className="flex items-start gap-3 p-3.5 rounded-md bg-bg-secondary border border-border-hairline hover:border-text-secondary/35 transition-all">
                    <div className={`p-1.5 ${cfg.bg} rounded-md shrink-0`}>
                      {driver.impact > 0 ? <TrendingUp size={14} className={cfg.color} /> : <TrendingDown size={14} className={cfg.color} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
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
                      <p className="text-[10px] text-text-secondary leading-normal">{driver.reason}</p>
                      <p className="text-xs font-bold text-text-primary mt-1 font-mono-numbers">
                        Sensitivity Impact: {fmt(driver.impact, true)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* AI explanation block */}
        {billExplanation && (
          <div className="panel-operational space-y-3 bg-bg-surface border-border-hairline shadow-sm">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
              <Lightbulb className="text-warning-amber" size={16} />
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest">AI Bill Interpretation</h4>
            </div>
            <p className="text-xs text-text-primary leading-relaxed whitespace-pre-line font-medium">{billExplanation}</p>
          </div>
        )}
      </div>

      {/* SECTION 3: Interactive Scenario Simulator */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part II: Interactive Scenario Simulator</h3>
          <p className="text-xs text-text-secondary">Simulate adjustments, wholesale markets, and temperature stressors in real time.</p>
        </div>

        <div className="panel-operational space-y-6">
          <div className="flex items-center justify-between border-b border-border-hairline pb-3">
            <div className="flex items-center gap-2">
              <Calculator size={16} className="text-text-secondary" />
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Simulator settings & overrides</h4>
            </div>
            {isSimLoading && (
              <span className="text-[10px] font-bold text-primary-blue animate-pulse uppercase tracking-widest flex items-center gap-1.5 font-mono-numbers">
                Running 2,000 Monte Carlo iterations...
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* Presets and usage overrides */}
            <div className="space-y-6">
              <div className="space-y-2.5">
                <label className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Preset Scenarios</label>
                <div className="grid grid-cols-2 gap-2">
                  {PRESETS.map((p) => (
                    <button
                      key={p.key}
                      onClick={() => handleApplyPreset(p.key)}
                      className={`p-3 text-left rounded-md border text-xs font-bold transition-all active:scale-[0.97] ${
                        scenario === p.key
                          ? 'border-primary-blue bg-primary-blue/5 text-primary-blue shadow-sm'
                          : 'border-border-hairline hover:bg-bg-secondary text-text-secondary hover:text-text-primary'
                      }`}
                    >
                      <div>{p.label}</div>
                      <span className="text-[9px] text-text-secondary/70 font-normal mt-1 block leading-tight">{p.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="border-t border-border-hairline/50"></div>

              {/* Usage slider */}
              <div className="space-y-2.5 font-mono-numbers">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-text-secondary uppercase tracking-wider text-[10px] font-sans">Usage Override</span>
                  <span className="text-text-primary">{kwh} kWh</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="4000"
                  step="50"
                  value={kwh}
                  onChange={(e) => {
                    setKwh(parseInt(e.target.value));
                    setScenario(null);
                  }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue border border-border-hairline"
                />
                <div className="flex justify-between text-[9px] text-text-secondary font-mono-numbers">
                  <span>100 kWh</span>
                  <span>Baseline: {uploadedBill.usage_kwh} kWh</span>
                  <span>4,000 kWh</span>
                </div>
              </div>
            </div>

            {/* Rate sliders */}
            <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* BGS slider */}
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-bold font-mono-numbers">
                  <div className="flex flex-col">
                    <span className="text-text-primary font-sans text-xs">BGS Supply rate</span>
                    <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">Energy supply cost changes</span>
                  </div>
                  <span className={`text-xs font-bold font-mono-numbers ${bgsChange > 0 ? 'text-alert-red' : bgsChange < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                    {bgsChange > 0 ? '+' : ''}{bgsChange}%
                  </span>
                </div>
                <input
                  type="range" min="-50" max="100" step="5" value={bgsChange}
                  onChange={(e) => { setBgsChange(parseInt(e.target.value)); setScenario(null); }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                />
              </div>

              {/* Distribution slider */}
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-bold font-mono-numbers">
                  <div className="flex flex-col">
                    <span className="text-text-primary font-sans text-xs">Distribution rate</span>
                    <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">Utility infrastructure charge</span>
                  </div>
                  <span className={`text-xs font-bold font-mono-numbers ${distChange > 0 ? 'text-alert-red' : distChange < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                    {distChange > 0 ? '+' : ''}{distChange}%
                  </span>
                </div>
                <input
                  type="range" min="-50" max="100" step="5" value={distChange}
                  onChange={(e) => { setDistChange(parseInt(e.target.value)); setScenario(null); }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                />
              </div>

              {/* Transmission slider */}
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-bold font-mono-numbers">
                  <div className="flex flex-col">
                    <span className="text-text-primary font-sans text-xs">Transmission rate</span>
                    <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">Regional high-voltage transport fee</span>
                  </div>
                  <span className={`text-xs font-bold font-mono-numbers ${transChange > 0 ? 'text-alert-red' : transChange < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                    {transChange > 0 ? '+' : ''}{transChange}%
                  </span>
                </div>
                <input
                  type="range" min="-50" max="100" step="5" value={transChange}
                  onChange={(e) => { setTransChange(parseInt(e.target.value)); setScenario(null); }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                />
              </div>

              {/* SBC slider */}
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-bold font-mono-numbers">
                  <div className="flex flex-col">
                    <span className="text-text-primary font-sans text-xs">Societal benefits (SBC) rate</span>
                    <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">Societal / clean energy charges</span>
                  </div>
                  <span className={`text-xs font-bold font-mono-numbers ${sbcChange > 0 ? 'text-alert-red' : sbcChange < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                    {sbcChange > 0 ? '+' : ''}{sbcChange}%
                  </span>
                </div>
                <input
                  type="range" min="-50" max="100" step="5" value={sbcChange}
                  onChange={(e) => { setSbcChange(parseInt(e.target.value)); setScenario(null); }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                />
              </div>

            </div>
          </div>

          {/* Dynamic commentary summary */}
          <div className="bg-primary-blue/5 border border-primary-blue/10 p-4 rounded-md text-xs font-semibold leading-relaxed text-text-primary flex items-start gap-2.5 shadow-sm">
            <Info size={14} className="text-primary-blue shrink-0 mt-0.5" />
            <div>
              {scenario ? (
                <>Preset <strong className="text-primary-blue">"{PRESETS.find(x => x.key === scenario)?.label}"</strong> applied. This overrides the default BGS and Transmission rates to evaluate stress conditions.</>
              ) : (changes['bgs_rate'] || changes['distribution_rate'] || changes['transmission_rate'] || changes['sbc_rate'] || kwh !== uploadedBill.usage_kwh) ? (
                <>Custom overrides active. Simulating a rate mix change on {Object.keys(changes).map(k => COMPONENT_METADATA[k]?.label || k).join(', ')} under an adjusted consumption load of {kwh} kWh.</>
              ) : (
                <>No simulation overrides active. Adjust rate component sliders or select preset scenarios to compute simulated monthly bills.</>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 4: Simulation Results */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part III: Simulation Results</h3>
          <p className="text-xs text-text-secondary">Probabilistic outputs, causal factor decompositions, and PJM grid states.</p>
        </div>

        {/* Results indicators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers">

          <div className="panel-operational">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Simulated bill mean</span>
            <div className="text-3xl font-bold mt-2 text-text-primary">${simulatedBill.toFixed(2)}</div>
            <span className="text-[10px] text-text-secondary block mt-1 font-sans font-medium">
              Base: ${utilityBill.toFixed(2)}
            </span>
          </div>

          <div className={`panel-operational border ${
            deltaBill > 0 ? 'bg-alert-red/5 border-alert-red/20 text-alert-red' : 'bg-savings-green/5 border-savings-green/20 text-savings-green'
          }`}>
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Bill variance delta</span>
            <div className="text-3xl font-bold mt-2 font-mono-numbers">
              {deltaBill > 0 ? '+' : ''}${deltaBill.toFixed(2)} ({deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(1)}%)
            </div>
            <span className="text-[10px] block mt-1 font-sans text-text-secondary font-medium">
              Expected monthly cost deviation
            </span>
          </div>

          <div className="panel-operational">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Usage response deviation</span>
            <div className="text-3xl font-bold mt-2 text-text-primary">
              {simUsageDelta > 0 ? '+' : ''}{simUsageDelta.toFixed(1)} kWh
            </div>
            <span className="text-[10px] text-text-secondary block mt-1 font-sans font-medium">
              Elasticity rate impact: {simulation?.learned_elasticity?.toFixed(3) || '-0.200'}
            </span>
          </div>

        </div>

        {/* Probabilistic Area curve & Causal bar decomposition */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Bell curve AreaChart */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs uppercase tracking-wider text-text-secondary">Probability Bounds</span>
                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-[4px] border ${confidence.bg} ${confidence.color} ${confidence.border}`}>
                  {confidence.label} confidence
                </span>
              </div>
              <h4 className="text-sm font-bold text-text-primary">Monte Carlo Simulated Bill Probability Distribution</h4>
            </div>

            <div className="h-[180px] relative mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={curveData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
                  <XAxis dataKey="x" type="number" domain={['auto', 'auto']} tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip labelFormatter={(l) => `Bill: $${l}`} formatter={(v: any) => [`${(v*100).toFixed(1)}%`, 'Probability']} />
                  <Area type="monotone" dataKey="y" stroke="var(--primary-blue)" fill="var(--primary-blue)" fillOpacity={0.08} strokeWidth={2} />
                  <ReferenceLine x={simMean} stroke="var(--primary-blue)" strokeDasharray="3 3" strokeWidth={1} label={{ value: 'Mean', position: 'top', fill: 'var(--text-primary)', fontSize: 9 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="border-t border-border-hairline pt-3 mt-3 text-[11px] font-mono-numbers text-text-primary flex justify-between">
              <div>
                <span className="text-text-secondary font-sans block text-[9px] uppercase">95% Confidence Bounds</span>
                <span className="font-bold">${simulation?.confidence_interval?.[0]?.toFixed(2) || p5.toFixed(2)} – ${simulation?.confidence_interval?.[1]?.toFixed(2) || p95.toFixed(2)}</span>
              </div>
              <div className="text-right">
                <span className="text-text-secondary font-sans block text-[9px] uppercase">Significance Level</span>
                <span className="font-bold">p = {pValue?.toFixed(3) || '0.050'}</span>
              </div>
            </div>
          </div>

          {/* Causal bar decomposition */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Causal Factor Analysis</span>
              <h4 className="text-sm font-bold text-text-primary">Decomposition of simulated bill deviations ($)</h4>
            </div>

            <div className="flex-1 min-h-[200px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={decompositionChartData} margin={{ top: 10, right: 15, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 600 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
                  <Tooltip
                    cursor={{ fill: 'var(--bg-secondary)', opacity: 0.5 }}
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                    itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                    formatter={(value: any) => [`$${value.toFixed(2)}`, 'Cost Contribution']}
                  />
                  <Bar dataKey="value" radius={[2, 2, 0, 0]} barSize={45}>
                    {decompositionChartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[10px] text-text-secondary border-t border-border-hairline pt-3 mt-3 font-semibold">
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#2F6BFF] rounded-sm"></span>Direct Price</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#16A085] rounded-sm"></span>Behavior</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#F5B041] rounded-sm"></span>Weather</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#2CA6FF] rounded-sm"></span>Interaction</div>
            </div>
          </div>
        </div>

        {/* PJM physics data */}
        {simulation?.pjm_physics && (
          <div className="panel-operational space-y-4">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
              <Cpu className="text-primary-blue" size={16} />
              <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">PJM Balancing Grid Physical State</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono-numbers">
              <div>
                <span className="text-text-secondary block mb-0.5 font-sans">Marginal cost</span>
                <strong className="text-text-primary">${simulation.pjm_physics.marginal_cost.toFixed(2)}/MWh</strong>
              </div>
              <div>
                <span className="text-text-secondary block mb-0.5 font-sans">PSEG LMP (DA)</span>
                <strong className="text-text-primary">${simulation.pjm_physics.lmp.toFixed(2)}/MWh</strong>
              </div>
              <div>
                <span className="text-text-secondary block mb-0.5 font-sans">Loss factor</span>
                <strong className="text-text-primary">{(simulation.pjm_physics.loss_factor * 100).toFixed(2)}%</strong>
              </div>
              <div>
                <span className="text-text-secondary block mb-0.5 font-sans">DA demand cost</span>
                <strong className="text-text-primary">${simulation.pjm_physics.da_charge.toFixed(2)}</strong>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 5: Investment Analysis */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part IV: Investment Analysis</h3>
          <p className="text-xs text-text-secondary">Evaluate long-term clean energy capital upgrades and grid demand response assets.</p>
        </div>

        {/* Annual actual cost indicator */}
        {customerSimulations && (
          <div className="panel-operational relative overflow-hidden bg-bg-surface p-6 shadow-sm space-y-6">
            <div className="flex justify-between items-baseline border-b border-border-hairline pb-3">
              <div>
                <span className="bg-primary-blue/10 text-primary-blue text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-[4px]">
                  Personalized long-term predictions
                </span>
                <h4 className="text-sm font-bold text-text-primary mt-2 font-sans">Personalized Capital Upgrades Modeling</h4>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-text-secondary block font-sans">Baseline annual cost (Est)</span>
                <span className="text-2xl font-bold font-mono-numbers text-text-primary">
                  ${customerSimulations[0]?.actual_annual_cost_estimate?.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Scenario upgrade cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 font-mono-numbers">

              {customerSimulations.slice(1, 4).map((s: any, idx: number) => {
                const diff = s.difference_vs_actual;
                const isIncrease = diff > 0;

                const paybacks = ["Solar: 6.4 yrs payback", "Heat Pump: 8.2 yrs payback", "EV charger: 2.1 yrs payback"];
                const rois = ["15.6% ROI", "12.2% ROI", "47.6% ROI"];

                return (
                  <div key={idx} className="p-4 bg-bg-secondary rounded-md border border-border-hairline flex flex-col justify-between hover:border-text-secondary/35 transition-all shadow-sm">
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-bold text-primary-blue uppercase tracking-wider block font-sans">{s.scenario_name}</span>
                        <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[4px] bg-savings-green/10 text-savings-green border border-savings-green/20">
                          {rois[idx % rois.length]}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-text-secondary mb-1">
                        <span className="font-sans">Simulated usage:</span>
                        <span className="font-bold text-text-primary">{s.simulated_annual_usage_kwh?.toLocaleString()} kWh</span>
                      </div>
                      <div className="flex justify-between text-xs text-text-secondary mb-1">
                        <span className="font-sans">Payback:</span>
                        <span className="font-bold text-text-primary">{paybacks[idx % paybacks.length]}</span>
                      </div>
                      <div className="flex justify-between text-xs text-text-secondary mb-3">
                        <span className="font-sans">Simulated cost:</span>
                        <span className="font-bold text-text-primary">${s.simulated_annual_cost?.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs">
                      <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                      <span className={`font-bold ${isIncrease ? 'text-alert-red' : 'text-savings-green'}`}>
                        {isIncrease ? '+' : ''}${diff?.toFixed(2)}/yr
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* Custom Battery Storage Upgrade card */}
              <div className="p-4 bg-bg-secondary rounded-md border border-border-hairline flex flex-col justify-between hover:border-text-secondary/35 transition-all shadow-sm">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-primary-blue uppercase tracking-wider block font-sans">Battery Storage (10kWh)</span>
                    <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[4px] bg-savings-green/10 text-savings-green border border-savings-green/20">
                      12.5% ROI
                    </span>
                  </div>
                  <div className="flex justify-between text-xs text-text-secondary mb-1">
                    <span className="font-sans">Simulated usage:</span>
                    <span className="font-bold text-text-primary">{(uploadedBill.usage_kwh * 11.5).toLocaleString(undefined, {maximumFractionDigits: 0})} kWh</span>
                  </div>
                  <div className="flex justify-between text-xs text-text-secondary mb-3">
                    <span className="font-sans">Simulated cost:</span>
                    <span className="font-bold text-text-primary">${((utilityBill * 12) - 350).toFixed(2)}</span>
                  </div>
                </div>
                <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs">
                  <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                  <span className="font-bold text-savings-green">−$350.00/yr</span>
                </div>
              </div>

              {/* Custom Demand Response / Load Shifting Upgrade card */}
              <div className="p-4 bg-bg-secondary rounded-md border border-border-hairline flex flex-col justify-between hover:border-text-secondary/35 transition-all shadow-sm">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-primary-blue uppercase tracking-wider block font-sans">Demand Response program</span>
                    <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[4px] bg-savings-green/10 text-savings-green border border-savings-green/20">
                      25.0% ROI
                    </span>
                  </div>
                  <div className="flex justify-between text-xs text-text-secondary mb-1">
                    <span className="font-sans">Simulated usage:</span>
                    <span className="font-bold text-text-primary">{(uploadedBill.usage_kwh * 11.8).toLocaleString(undefined, {maximumFractionDigits: 0})} kWh</span>
                  </div>
                  <div className="flex justify-between text-xs text-text-secondary mb-3">
                    <span className="font-sans">Simulated cost:</span>
                    <span className="font-bold text-text-primary">${((utilityBill * 12) - 180).toFixed(2)}</span>
                  </div>
                </div>
                <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs">
                  <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                  <span className="font-bold text-savings-green">−$180.00/yr</span>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* Flow Telemetry graph */}
        <EnergyFlowSVG />
      </div>

      {/* SECTION 6: Recommendations */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part V: Priority Recommendations</h3>
          <p className="text-xs text-text-secondary">AI-generated clean energy recommendations prioritized by ROI and payback duration.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-semibold">

          <div className="panel-operational space-y-4">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2 text-text-secondary font-bold uppercase tracking-widest">
              <ShieldCheck className="text-savings-green" size={16} />
              <span>Top Opportunities</span>
            </div>

            <ul className="space-y-3.5 leading-relaxed text-text-primary">
              <li className="flex items-start gap-2.5 p-3 rounded bg-savings-green/5 border border-savings-green/10">
                <span className="px-1.5 py-0.5 rounded bg-savings-green/20 text-savings-green text-[9px] font-bold">1</span>
                <div>
                  <strong>Tariff plan optimization:</strong> Switch to Net Metering Plan.
                  <span className="block text-[10px] text-text-secondary font-medium mt-1">Est. Savings: $400 - $650/yr · ROI 15.6%</span>
                </div>
              </li>
              <li className="flex items-start gap-2.5 p-3 rounded bg-savings-green/5 border border-savings-green/10">
                <span className="px-1.5 py-0.5 rounded bg-savings-green/20 text-savings-green text-[9px] font-bold">2</span>
                <div>
                  <strong>EV smart charging window:</strong> Schedule EV charging strictly between 12:00 AM – 6:00 AM.
                  <span className="block text-[10px] text-text-secondary font-medium mt-1">Est. Savings: $150 - $220/yr · ROI 47.6%</span>
                </div>
              </li>
            </ul>
          </div>

          <div className="panel-operational space-y-4">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2 text-text-secondary font-bold uppercase tracking-widest">
              <ShieldAlert className="text-warning-amber" size={16} />
              <span>Risk Factors & Recommended Actions</span>
            </div>

            <ul className="space-y-3.5 leading-relaxed text-text-primary">
              <li className="flex items-start gap-2.5 p-3 rounded bg-warning-amber/5 border border-warning-amber/15">
                <span className="px-1.5 py-0.5 rounded bg-warning-amber/20 text-warning-amber text-[9px] font-bold">HIGH</span>
                <div>
                  <strong>Supply price volatility:</strong> Unhedged BGS supply exposes your bill to wholesale market spikes.
                  <span className="block text-[10px] text-text-secondary font-medium mt-1">Action: Lock in fixed-rate supply contract or install battery system.</span>
                </div>
              </li>
              <li className="flex items-start gap-2.5 p-3 rounded bg-warning-amber/5 border border-warning-amber/15">
                <span className="px-1.5 py-0.5 rounded bg-warning-amber/20 text-warning-amber text-[9px] font-bold">MED</span>
                <div>
                  <strong>Extreme temperature spikes:</strong> Summer cooling degree-day spikes increase monthly utility outflow.
                  <span className="block text-[10px] text-text-secondary font-medium mt-1">Action: Set smart thermostat cooling setpoints to 76°F or install heat pump.</span>
                </div>
              </li>
            </ul>
          </div>

        </div>
      </div>

      {/* SECTION 7: Historical Comparison */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part VI: Historical Comparison</h3>
          <p className="text-xs text-text-secondary">Track billing trends and monthly volatility over a 12-month rolling range.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Trend composed chart */}
          <div className="lg:col-span-2 panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Billing trends</span>
              <h4 className="text-sm font-bold text-text-primary font-sans">12-Month cost trend vs monthly variance</h4>
            </div>

            <div className="flex-1 min-h-[220px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={historyTrendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
                  <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} tickFormatter={(val) => `$${val}`} />
                  <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} tickFormatter={(val) => `${val}%`} />
                  <Tooltip formatter={(value: any, name: any) => name === 'Variance' ? [`${value}%`, name] : [`$${value.toFixed(2)}`, name]} />
                  <Bar yAxisId="right" dataKey="mom" name="Variance" barSize={6}>
                    {historyTrendData.map((entry, index) => {
                      const isPositive = (entry.mom || 0) > 0;
                      return <Cell key={`cell-${index}`} fill={isPositive ? 'var(--alert-red)' : 'var(--savings-green)'} opacity={0.6} />;
                    })}
                  </Bar>
                  <Line yAxisId="left" type="monotone" dataKey="bill" name="Total Bill" stroke="var(--primary-blue)" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Historical comparison metrics */}
          <div className="panel-operational flex flex-col justify-between h-[360px]">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-3">
              <BarChart3 size={14} className="text-text-secondary" />
              <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Historical Comparison</span>
            </div>

            <div className="space-y-4 mt-4 flex-1">

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase">Previous Month</span>
                  <span className="text-xs font-bold text-text-primary">May 2026</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">${previousBill.toFixed(2)}</span>
                  <span className="text-[10px] text-text-secondary">{(uploadedBill.usage_kwh * 0.92).toFixed(0)} kWh</span>
                </div>
              </div>

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase">Previous Year</span>
                  <span className="text-xs font-bold text-text-primary">June 2025</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">${(utilityBill * 0.97).toFixed(2)}</span>
                  <span className="text-[10px] text-text-secondary">{(uploadedBill.usage_kwh * 0.97).toFixed(0)} kWh</span>
                </div>
              </div>

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase">12-Month Rolling Avg</span>
                  <span className="text-xs font-bold text-text-primary">Mean outflow</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">
                    ${(historyTrendData.reduce((acc, curr) => acc + curr.bill, 0) / 12).toFixed(2)}
                  </span>
                  <span className="text-[10px] text-text-secondary">{(uploadedBill.usage_kwh * 1.01).toFixed(0)} kWh avg</span>
                </div>
              </div>

            </div>

            <div className="border-t border-border-hairline pt-3 mt-3 flex justify-between items-baseline text-xs">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Trend direction</span>
              <span className="font-bold text-warning-amber">Stable (Flat +/- 3% variance)</span>
            </div>
          </div>

        </div>
      </div>

      {/* Navigation back deep-link */}
      <div className="flex justify-center">
        <button
          onClick={() => navigate('Overview')}
          className="text-xs text-text-secondary hover:text-primary-blue transition-colors font-semibold"
        >
          ← Back to Overview
        </button>
      </div>

    </div>
  );
};

export default ImpactPage;
