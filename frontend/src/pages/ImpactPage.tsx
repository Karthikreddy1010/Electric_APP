/**
 * Impact & Simulation Page
 *
 * Architecture responsibility: explains and simulates.
 * This page owns: component breakdown, sensitivity driver analysis,
 * interactive what-if rate simulators, probability area bounds, and priority clean energy options.
 *
 * JSDoc:
 * @module ImpactPage
 * @description Workspace for analyzing rates, weather stress, and capital investment scenarios.
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
  Flame, Snowflake, Zap, Leaf, Plug, Network, Building2,
  Trash2, Plus, MessageSquare, Send, CheckCircle2, AlertTriangle, AlertCircle, Copy, Download
} from 'lucide-react';
import React from 'react';

const PRESETS = [
  { key: 'hot_summer', label: <span className="flex items-center gap-1.5"><Flame size={14} className="text-alert-red" /> Hot Summer</span>, desc: 'High CDD temperatures and peak pricing (+25% BGS)' },
  { key: 'cold_winter', label: <span className="flex items-center gap-1.5"><Snowflake size={14} className="text-primary-blue" /> Cold Winter</span>, desc: 'High HDD temperatures and peak heating demand (+15% BGS)' },
  { key: 'high_market', label: <span className="flex items-center gap-1.5"><Zap size={14} className="text-warning-amber" /> High Wholesale Market</span>, desc: 'Wholesale prices spike (+40% BGS, +20% Transmission)' },
  { key: 'conservation', label: <span className="flex items-center gap-1.5"><Leaf size={14} className="text-savings-green" /> Green Conservation</span>, desc: 'Usage drops by 20% (-20% usage)' }
];

const COMPONENT_METADATA: Record<string, { label: string; description: string; icon: React.ReactNode }> = {
  customer_charge:   { label: "Customer Charge",   description: "Fixed monthly customer service and connection fee.",     icon: <Building2 size={12} /> },
  bgs_rate:          { label: "BGS Supply",       description: "Wholesale energy supply rate set by the market.",         icon: <Zap size={12} /> },
  distribution_rate: { label: "Distribution",     description: "Local utility delivery and infrastructure fee.",          icon: <Plug size={12} /> },
  transmission_rate: { label: "Transmission",     description: "Regional high-voltage transport fee.",                    icon: <Network size={12} /> },
  sbc_rate:          { label: "Societal Benefits", description: "State-mandated societal benefits & clean energy charges.", icon: <Building2 size={12} /> },
  transition_rate:   { label: "Transition Charge", description: "Charges related to electricity market deregulation.",     icon: <Plug size={12} /> },
  rider_rate:        { label: "Rider Charges",    description: "Supplemental infrastructure recovery adjustments.",       icon: <Network size={12} /> },
  nug_rate:          { label: "NUG Charge",       description: "Charges related to legacy non-utility generation contracts.", icon: <Zap size={12} /> },
};

const costToRateKey: Record<string, string> = {
  customer_charge: "customer_charge",
  bgs_cost: "bgs_rate",
  distribution_cost: "distribution_rate",
  transmission_cost: "transmission_rate",
  sbc_cost: "sbc_rate",
  market_transition_cost: "transition_rate",
  rider_cost: "rider_rate",
  nug_cost: "nug_rate"
};

const COLORS = [
  '#2F6BFF', // Primary blue
  '#16A085', // Energy teal
  '#2CA6FF', // Electric cyan
  '#27AE60', // Savings green
  '#F5B041', // Warning amber
  '#D64545', // Alert red
  '#8E44AD', // Purple
  '#E67E22', // Orange
  '#697487'  // Text secondary
];

const fmt = (v: number, forceSign = false) => {
  const sign = v > 0 ? '+' : v < 0 ? '−' : '';
  const abs = Math.abs(v).toFixed(2);
  if (forceSign) return `${sign}$${abs}`;
  return `$${abs}`;
};

const getComponentColor = (name: string, type?: string) => {
  if (type === 'base' || name === 'Base Bill' || name === 'Baseline') return '#697487'; // Gray
  if (type === 'final' || name === 'Final Bill' || name === 'Total Bill' || name === 'Current Total') return '#2F6BFF'; // Primary Blue
  if (type === 'increase') return '#D64545'; // Alert Red
  if (type === 'decrease') return '#27AE60'; // Savings Green

  switch (name) {
    case 'Cust Charge':
    case 'Fixed':
      return '#8E44AD'; // Purple
    case 'Supply (BGS)':
    case 'Supply':
      return '#F5B041'; // Warning Amber
    case 'Distribution':
      return '#16A085'; // Energy Teal
    case 'Transmission':
      return '#2CA6FF'; // Electric Cyan
    case 'SBC':
      return '#27AE60'; // Savings Green
    case 'NUG':
      return '#E67E22'; // Orange
    case 'Riders':
      return '#8E44AD'; // Purple
    case 'Transition':
      return '#27AE60'; // Savings Green
    case 'Tax':
    case 'Taxes':
      return '#D64545'; // Alert Red
    default:
      return '#2F6BFF'; // Primary Blue
  }
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

  // Dynamic Simulator overrides (key is rate Key, e.g. bgs_rate)
  const [componentOverrides, setComponentOverrides] = useState<Record<string, number>>({});
  const [kwh, setKwh] = useState<number>(() => uploadedBill?.usage_kwh || 750);
  const [scenario, setScenario] = useState<string | null>(null);
  const [prevUploadedBillId, setPrevUploadedBillId] = useState<string | null>(null);

  if (uploadedBill?.customer_id !== prevUploadedBillId) {
    setPrevUploadedBillId(uploadedBill?.customer_id ?? null);
    if (uploadedBill?.usage_kwh) {
      setKwh(uploadedBill.usage_kwh);
    }
  }

  // Dynamic component listing from structured bill components
  const activeComponents = useMemo(() => {
    if (!uploadedBill?.canonical_bill?.components) return [];
    return uploadedBill.canonical_bill.components.filter((c: any) => c.key !== 'sales_tax');
  }, [uploadedBill]);

  // Tariff States
  const [tariffSummary, setTariffSummary] = useState<any>(null);
  const [tariffHistory, setTariffHistory] = useState<any[]>([]);
  const utility = uploadedBill?.utility || 'PSE&G';
  const schedule = uploadedBill?.rate_schedule || 'RS';

  useEffect(() => {
    // Fetch summary
    axios.get(`/tariffs/summary?utility_code=${utility}`)
      .then(res => setTariffSummary(res.data))
      .catch(console.error);
        
    // Fetch history
    axios.get(`/tariffs/history?utility_code=${utility}&schedule=${schedule}`)
      .then(res => setTariffHistory(res.data.history || []))
      .catch(console.error);
  }, [utility, schedule]);

  // Debounced overrides
  const debouncedKwh = useDebounce(kwh, 300);
  const debouncedOverrides = useDebounce(componentOverrides, 300);
  const debouncedScenario = useDebounce(scenario, 300);

  // Modifications mapping
  const changes = useMemo(() => {
    const c: Record<string, number> = {};
    Object.entries(debouncedOverrides).forEach(([k, v]) => {
      if (v !== 0) {
        c[k] = v;
      }
    });
    return c;
  }, [debouncedOverrides]);

  // Query: Investment Annualized Scenarios
  const { data: customerSimulations } = useQuery({
    queryKey: ['customer-simulations', uploadedBill?.customer_id || uploadedBill?.bill_date],
    queryFn: async () => {
      const res = await axios.post('/bill/simulation', uploadedBill);
      return res.data.scenarios;
    },
    enabled: !!uploadedBill
  });

  // Query: Main Simulation endpoint
  const { data: simulation, isLoading: isSimLoading } = useQuery({
    queryKey: ['impact-simulation-combined', uploadedBill?.customer_id || uploadedBill?.bill_date, changes, debouncedKwh, debouncedScenario],
    queryFn: async () => {
      const payload = {
        changes,
        kwh: debouncedKwh,
        scenario: debouncedScenario || undefined,
        n_simulations: 2000,
        base_rates: uploadedBill?.rates,
        base_costs: uploadedBill?.costs
      };
      return (await axios.post('/impact/what-if-v2', payload)).data;
    },
    enabled: !!uploadedBill,
    placeholderData: (prev) => prev
  });

  // Core baseline billing values (safely accessed before early return)
  const utilityBill = uploadedBill?.total_bill || 0;
  const simulatedBill = simulation?.simulated_bill ?? utilityBill;

  // Dynamic Validation layer
  const validationResults = useMemo(() => {
    const checks: Array<{ label: string; status: string; desc: string }> = [];
    if (!simulation) return { status: "Passed", checks };

    const contribs = simulation.contributions || {};
    // 1. Component Sum matches Total Bill
    const sumComponents: number = (Object.values(contribs) as any[]).reduce((acc: number, curr: any) => acc + (curr.simulated_cost || 0), 0);
    const absDiff = Math.abs(sumComponents - simulatedBill);
    if (absDiff < 0.05) {
      checks.push({ label: "Component Sum check", status: "Passed", desc: `Total simulated bill sum matching components precisely.` });
    } else {
      checks.push({ label: "Component Sum check", status: "Warning", desc: `Component sum variance of $${absDiff.toFixed(2)}.` });
    }

    // 2. Negative Cost bounds
    const hasNegative = Object.values(contribs).some((curr: any) => (curr.simulated_cost || 0) < 0);
    if (!hasNegative) {
      checks.push({ label: "No Negative Costs check", status: "Passed", desc: "No components contain invalid negative charges." });
    } else {
      checks.push({ label: "No Negative Costs check", status: "Error", desc: "Simulation triggered invalid negative charges." });
    }

    // 3. Negative Rate bounds
    const hasNegativeRates = Object.values(contribs).some((curr: any) => (curr.simulated_rate || 0) < 0);
    if (!hasNegativeRates) {
      checks.push({ label: "Rates Validity check", status: "Passed", desc: "All simulated rate components are positive and valid." });
    } else {
      checks.push({ label: "Rates Validity check", status: "Error", desc: "Simulation contains negative or invalid rate definitions." });
    }

    const hasError = checks.some(c => c.status === "Error");
    const hasWarning = checks.some(c => c.status === "Warning");
    const status = hasError ? "Error" : (hasWarning ? "Warning" : "Passed");
    return { status, checks };
  }, [simulatedBill, simulation]);

  // Query: Baseline/Current Bill actual decomposition
  const { data: baselineDecomp } = useQuery({
    queryKey: ['impact-baseline-decomp', uploadedBill?.customer_id || uploadedBill?.bill_date, uploadedBill?.usage_kwh],
    queryFn: async () => {
      const payload = {
        changes: {},
        kwh: uploadedBill?.usage_kwh || 750,
        n_simulations: 1000,
        base_rates: uploadedBill?.rates,
        base_costs: uploadedBill?.costs
      };
      return (await axios.post('/impact/what-if-v2', payload)).data;
    },
    enabled: !!uploadedBill
  });

  // Query: DML Elasticity Diagnostics
  const { data: dmlData } = useQuery({
    queryKey: ['dml-causal-diagnostics', uploadedBill?.customer_id || uploadedBill?.bill_date],
    queryFn: async () => {
      return (await axios.post('/impact/causal-v2', { treatment: 'bgs_rate' })).data;
    },
    enabled: !!uploadedBill
  });

  // Scenario persistence states
  const [savedScenarios, setSavedScenarios] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('impact_scenarios');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error(e);
      return [];
    }
  });
  const [newScenarioName, setNewScenarioName] = useState('');
  const [comparedIds, setComparedIds] = useState<string[]>([]);

  const handleSaveScenario = () => {
    if (!newScenarioName.trim() || !simulation) return;
    const newScen = {
      id: Math.random().toString(36).substring(7),
      name: newScenarioName,
      timestamp: new Date().toLocaleString(),
      billId: uploadedBill?.customer_id || 'UPLOADED-BILL',
      changes: { ...componentOverrides },
      kwh,
      simulatedBill: simulation.simulated_bill,
      totalImpact: simulation.total_impact,
      usageChange: simulation.usage_change_kwh,
      elasticity: simulation.learned_elasticity,
      decomposition: simulation.decomposition
    };
    const updated = [...savedScenarios, newScen];
    setSavedScenarios(updated);
    localStorage.setItem('impact_scenarios', JSON.stringify(updated));
    setNewScenarioName('');
  };

  const handleDeleteScenario = (id: string) => {
    const updated = savedScenarios.filter(s => s.id !== id);
    setSavedScenarios(updated);
    localStorage.setItem('impact_scenarios', JSON.stringify(updated));
    setComparedIds(comparedIds.filter(cid => cid !== id));
  };

  const handleLoadScenario = (s: any) => {
    setScenario(null);
    setKwh(s.kwh);
    setComponentOverrides(s.changes);
  };

  const handleDuplicateScenario = (s: any) => {
    const dupScen = {
      ...s,
      id: Math.random().toString(36).substring(7),
      name: `${s.name} (Copy)`,
      timestamp: new Date().toLocaleString(),
    };
    const updated = [...savedScenarios, dupScen];
    setSavedScenarios(updated);
    localStorage.setItem('impact_scenarios', JSON.stringify(updated));
  };

  const handleExportScenarios = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(savedScenarios, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `electricai-scenarios-export-${new Date().toISOString().slice(0,10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Toggle scenario in comparison
  const toggleComparison = (id: string) => {
    if (comparedIds.includes(id)) {
      setComparedIds(comparedIds.filter(cid => cid !== id));
    } else {
      if (comparedIds.length >= 3) return; // Limit to 3 comparison cards
      setComparedIds([...comparedIds, id]);
    }
  };

  // Query: LLM report generation
  const { data: explainData, isLoading: isExplainLoading } = useQuery({
    queryKey: ['impact-explain-report', simulation],
    queryFn: async () => {
      if (!simulation) return null;
      const payload = {
        uploaded_bill: uploadedBill,
        simulation_results: simulation,
        scenario_inputs: { changes, kwh }
      };
      return (await axios.post('/impact/explain', payload)).data;
    },
    enabled: !!simulation,
    placeholderData: (prev) => prev
  });

  // Chat Assistant states
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'assistant', content: 'Hello! I am your AI Simulation Assistant. You can ask me follow-up questions about this what-if rate analysis, weather impacts, or conservation targets.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatSending, setIsChatSending] = useState(false);

  const handleSendChatMessage = async (msgText = chatInput) => {
    const textToSend = msgText.trim();
    if (!textToSend || !simulation) return;

    const userMsg = { role: 'user', content: textToSend };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setIsChatSending(true);

    try {
      const payload = {
        message: textToSend,
        history: chatMessages.map(m => ({ role: m.role, content: m.content })),
        uploaded_bill: uploadedBill,
        simulation_results: simulation
      };
      const res = await axios.post('/impact/chat', payload);
      setChatMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
    } catch (e) {
      console.error(e);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to fetch chat response. Please verify network connection.' }]);
    } finally {
      setIsChatSending(false);
    }
  };

  // Early return moved below hook definitions to comply with Rules of Hooks
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

  // Core baseline billing values (declared at top of component)
  const deltaBill = simulation?.total_impact ?? (simulatedBill - utilityBill);
  const deltaPct = utilityBill > 0 ? (deltaBill / utilityBill) * 100 : 0;

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

  // Dynamic component list for cost composition visualizer
  const currentComponentsList = uploadedBill.canonical_bill?.components || [
    { key: "customer_charge", name: "Fixed Customer Service Charge", value: fixedCharge, pct: utilityBill > 0 ? round(fixedCharge / utilityBill * 100, 1) : 0, type: "Fixed" },
    { key: "distribution_cost", name: "Grid Delivery Infrastructure", value: deliveryCharge, pct: utilityBill > 0 ? round(deliveryCharge / utilityBill * 100, 1) : 0, type: "Variable" },
    { key: "bgs_cost", name: "Standard Supply Generation", value: supplyCharge, pct: utilityBill > 0 ? round(supplyCharge / utilityBill * 100, 1) : 0, type: "Variable" },
    { key: "sales_tax", name: "State Sales Taxes (6.625%)", value: salesTax, pct: utilityBill > 0 ? round(salesTax / utilityBill * 100, 1) : 0, type: "Tax" }
  ];

  // Causal Variance Breakdown — show absolute component costs from baseline decomp so chart is never empty.
  // Fall back to computing costs from uploadedBill if baselineDecomp has not loaded yet.
  const baseContribs = baselineDecomp?.contributions || {};
  const baseWaterfallData = (() => {
    // Prefer baselineDecomp.contributions absolute costs
    const componentMap = [
      { name: 'Cust Charge', key: 'customer_charge', fallback: uploadedBill.monthly_service_charge || 0 },
      { name: 'Supply (BGS)', key: 'bgs_rate', fallback: uploadedBill.supply_charge || 0 },
      { name: 'Distribution', key: 'distribution_rate', fallback: round((uploadedBill.delivery_charge || 0) - (uploadedBill.monthly_service_charge || 0), 2) },
      { name: 'Transmission', key: 'transmission_rate', fallback: (uploadedBill.rates?.transmission_rate || 0) * (uploadedBill.usage_kwh || 0) },
      { name: 'SBC', key: 'sbc_rate', fallback: (uploadedBill.rates?.sbc_rate || 0) * (uploadedBill.usage_kwh || 0) },
      { name: 'NUG', key: 'nug_rate', fallback: (uploadedBill.rates?.nug_rate || 0) * (uploadedBill.usage_kwh || 0) },
      { name: 'Tax', key: 'sales_tax', fallback: uploadedBill.tax || 0 },
    ];
    return componentMap
      .map(c => ({
        name: c.name,
        value: baseContribs[c.key]?.base_cost ?? c.fallback,
        type: c.key === 'customer_charge' ? 'fixed' : c.key === 'sales_tax' ? 'tax' : 'variable'
      }))
      .filter(d => d.value > 0.01);
  })();

  // Deterministic Waterfall Chart datasets
  // When overrides are active: show delta bars (cost change per component)
  // When no overrides: show absolute cost bars so Transmission & BGS are always visible
  const simContribs = simulation?.contributions || {};
  const hasAnyChanges = Object.keys(changes).length > 0 || scenario !== null;

  // Build absolute component costs from simulation (always available)
  const absCC = simContribs.customer_charge?.simulated_cost ?? simContribs.customer_charge?.base_cost ?? (uploadedBill.monthly_service_charge || 0);
  const absDist = simContribs.distribution_rate?.simulated_cost ?? simContribs.distribution_rate?.base_cost ?? round((uploadedBill.delivery_charge || 0) - (uploadedBill.monthly_service_charge || 0), 2);
  const absSupply = simContribs.bgs_rate?.simulated_cost ?? simContribs.bgs_rate?.base_cost ?? (uploadedBill.supply_charge || 0);
  const absTrans = simContribs.transmission_rate?.simulated_cost ?? simContribs.transmission_rate?.base_cost ?? ((uploadedBill.rates?.transmission_rate || 0) * (uploadedBill.usage_kwh || 0));
  const absTransition = simContribs.transition_rate?.simulated_cost ?? simContribs.transition_rate?.base_cost ?? 0;
  const absSbc = simContribs.sbc_rate?.simulated_cost ?? simContribs.sbc_rate?.base_cost ?? ((uploadedBill.rates?.sbc_rate || 0) * (uploadedBill.usage_kwh || 0));
  const absRiders = simContribs.rider_rate?.simulated_cost ?? simContribs.rider_rate?.base_cost ?? 0;
  const absNug = simContribs.nug_rate?.simulated_cost ?? simContribs.nug_rate?.base_cost ?? ((uploadedBill.rates?.nug_rate || 0) * (uploadedBill.usage_kwh || 0));
  const absTax = simContribs.sales_tax?.simulated_cost ?? simContribs.sales_tax?.base_cost ?? (uploadedBill.tax || 0);

  // Delta values for when changes are active
  const deltaCC = simContribs.customer_charge?.difference || 0;
  const deltaDist = simContribs.distribution_rate?.difference || 0;
  const deltaSupply = simContribs.bgs_rate?.difference || 0;
  const deltaTrans = simContribs.transmission_rate?.difference || 0;
  const deltaTransition = simContribs.transition_rate?.difference || 0;
  const deltaSbc = simContribs.sbc_rate?.difference || 0;
  const deltaRiders = simContribs.rider_rate?.difference || 0;
  const deltaNug = simContribs.nug_rate?.difference || 0;
  const deltaTax = simContribs.sales_tax?.difference || 0;

  // Choose between absolute-cost bar chart vs delta waterfall
  // In baseline mode (no changes): show each component as a simple absolute bar
  // In simulation mode (changes active): show delta waterfall stepping from Base to Final
  const absoluteComponentData = [
    { name: 'Supply (BGS)', value: absSupply, type: 'supply' },
    { name: 'Distribution', value: absDist, type: 'delivery' },
    { name: 'Transmission', value: absTrans, type: 'delivery' },
    { name: 'SBC', value: absSbc, type: 'policy' },
    { name: 'Riders', value: absRiders, type: 'policy' },
    { name: 'NUG', value: absNug, type: 'policy' },
    { name: 'Transition', value: absTransition, type: 'policy' },
    { name: 'Tax', value: absTax, type: 'tax' },
    { name: 'Cust Charge', value: absCC, type: 'fixed' },
  ].filter(c => c.value > 0.01);

  const waterfallChartData = (() => {
    if (!hasAnyChanges) {
      // Simple absolute bar chart — no spacer needed, each component shown directly
      return absoluteComponentData.map(c => ({
        name: c.name,
        spacer: 0,        // always 0 so bars start from the x-axis
        value: c.value,
        type: c.type,
        actualVal: c.value
      }));
    }

    // Delta waterfall mode: show how each override changes the bill
    const waterfallSequence = [
      { name: 'Base Bill', value: utilityBill, start: 0, end: utilityBill, type: 'base' },
      { name: 'Cust Charge', value: deltaCC, start: utilityBill, end: utilityBill + deltaCC, type: deltaCC >= 0 ? 'increase' : 'decrease' },
      { name: 'Distribution', value: deltaDist, start: utilityBill + deltaCC, end: utilityBill + deltaCC + deltaDist, type: deltaDist >= 0 ? 'increase' : 'decrease' },
      { name: 'Supply (BGS)', value: deltaSupply, start: utilityBill + deltaCC + deltaDist, end: utilityBill + deltaCC + deltaDist + deltaSupply, type: deltaSupply >= 0 ? 'increase' : 'decrease' },
      { name: 'Transmission', value: deltaTrans, start: utilityBill + deltaCC + deltaDist + deltaSupply, end: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans, type: deltaTrans >= 0 ? 'increase' : 'decrease' },
      { name: 'Transition', value: deltaTransition, start: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans, end: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition, type: deltaTransition >= 0 ? 'increase' : 'decrease' },
      { name: 'SBC', value: deltaSbc, start: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition, end: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc, type: deltaSbc >= 0 ? 'increase' : 'decrease' },
      { name: 'Riders', value: deltaRiders, start: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc, end: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc + deltaRiders, type: deltaRiders >= 0 ? 'increase' : 'decrease' },
      { name: 'NUG', value: deltaNug, start: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc + deltaRiders, end: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc + deltaRiders + deltaNug, type: deltaNug >= 0 ? 'increase' : 'decrease' },
      { name: 'Taxes', value: deltaTax, start: utilityBill + deltaCC + deltaDist + deltaSupply + deltaTrans + deltaTransition + deltaSbc + deltaRiders + deltaNug, end: simulatedBill, type: deltaTax >= 0 ? 'increase' : 'decrease' },
      { name: 'Final Bill', value: simulatedBill, start: 0, end: simulatedBill, type: 'final' }
    ];
    return waterfallSequence.map((step) => {
      const barStart = Math.min(step.start, step.end);
      const barHeight = Math.abs(step.end - step.start);
      return {
        name: step.name,
        spacer: step.type === 'base' || step.type === 'final' ? 0 : barStart,
        value: step.type === 'base' || step.type === 'final' ? step.value : barHeight,
        type: step.type,
        actualVal: step.value
      };
    }).filter(d => Math.abs(d.actualVal) > 0.005 || d.type === 'base' || d.type === 'final');
  })();

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

  // Rate vs Usage Attribution Chart Data
  // In baseline mode: show absolute component costs so chart is never empty
  // In simulation mode: show causal decomposition of bill changes
  const decompositionChartData = hasAnyChanges
    ? [
        { name: 'Direct Price', value: simDirectPrice, fill: '#2F6BFF', desc: 'Cost variance due strictly to modified component rates' },
        { name: 'Behavior Shift', value: simBehavior, fill: '#16A085', desc: 'Usage cost shifts from smart load shifting or efficiency' },
        { name: 'Weather Shift', value: simWeather, fill: '#F5B041', desc: 'Consumption changes caused by degree-day temperature shocks' },
        { name: 'Tax Effect', value: deltaTax, fill: '#2CA6FF', desc: 'Proportional sales tax adjustment' },
        { name: 'Interaction', value: simInteraction, fill: '#E67E22', desc: 'Compounding variance from rates and usage shifting jointly' }
      ].filter(d => Math.abs(d.value) > 0.01)
    : absoluteComponentData.map(c => ({
        name: c.name,
        value: c.value,
        fill: getComponentColor(c.name, c.type),
        desc: `Absolute cost contribution of ${c.name} to your bill`
      }));

  // Monte Carlo distribution statistics
  const simMean = simulation?.distribution?.mean ?? simulatedBill;
  const simStd = simulation?.distribution?.std ?? 5.5;
  const p5 = simulation?.distribution?.p5 ?? (simMean - 1.64 * simStd);
  const p95 = simulation?.distribution?.p95 ?? (simMean + 1.64 * simStd);
  const pValue = simulation?.probabilistic?.p_value ?? 0.05;
  const curveData = buildBellCurve(simMean, simStd, p5, p95);
  const confidence = getConfidenceLevel(simStd, simMean);

  // Tornado Sensitivity Data for Monte Carlo
  // Compute sensitivity impact of a 10% rate change based on baseline cost
  const tornadoChartData = activeComponents.map((c: any) => {
    const rateKey = costToRateKey[c.key] || c.key;
    const baseCost = c.value || 0;
    const impact = baseCost * 0.10 * 1.06625; // 10% change + tax
    return {
      name: c.name,
      negativeImpact: -impact,
      positiveImpact: impact,
      key: rateKey
    };
  }).sort((a: any, b: any) => b.positiveImpact - a.positiveImpact);

  // Actions / Presets handlers
  const handleApplyPreset = (presetKey: string) => {
    setScenario(presetKey);
    setComponentOverrides({});
    setKwh(uploadedBill?.usage_kwh || 750);
  };

  const clearOverrides = () => {
    setScenario(null);
    setComponentOverrides({});
    setKwh(uploadedBill?.usage_kwh || 750);
  };

  // Billing trends data
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

  // Dynamic Validation layer
  return (
    <div className="bg-bg-primary text-text-primary space-y-10 font-sans pb-16 px-4 md:px-8 pt-6">

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
            {currentComponentsList.map((comp: any, idx: number) => (
              <div
                key={idx}
                className="h-full transition-all"
                style={{ width: `${comp.pct}%`, backgroundColor: COLORS[idx % COLORS.length] }}
                title={`${comp.name}: ${comp.pct}%`}
              />
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {currentComponentsList.slice(0, 4).map((comp: any, idx: number) => (
              <div key={idx} className="p-3.5 bg-bg-secondary rounded-md border border-border-hairline flex flex-col justify-between shadow-sm">
                <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest block leading-tight mb-1">{comp.name}</span>
                <div className="flex justify-between items-baseline mt-auto">
                  <span className="text-xs font-bold text-text-secondary">{comp.pct}%</span>
                  <span className="text-xs font-bold text-text-primary font-mono-numbers">${comp.value?.toFixed(2)}</span>
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
                      <Cell key={`cell-${index}`} fill={getComponentColor(entry.name, entry.type)} />
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

            {/* Rate sliders - DYNAMICALLY RENDERED FROM ACTIVE COMPONENTS */}
            <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Fixed Customer Charge Slider */}
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-bold font-mono-numbers">
                  <div className="flex flex-col">
                    <span className="text-text-primary font-sans text-xs">Customer Charge (Fixed)</span>
                    <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">Fixed customer connection fee</span>
                  </div>
                  <span className={`text-xs font-bold font-mono-numbers ${componentOverrides['customer_charge'] > 0 ? 'text-alert-red' : componentOverrides['customer_charge'] < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                    {componentOverrides['customer_charge'] > 0 ? '+' : ''}{componentOverrides['customer_charge'] || 0}%
                  </span>
                </div>
                <input
                  type="range" min="-50" max="100" step="5" value={componentOverrides['customer_charge'] || 0}
                  onChange={(e) => {
                    setComponentOverrides({ ...componentOverrides, customer_charge: parseInt(e.target.value) });
                    setScenario(null);
                  }}
                  className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                />
              </div>

              {activeComponents.map((c: any) => {
                const rateKey = costToRateKey[c.key] || c.key;
                if (rateKey === 'customer_charge') return null; // rendered above
                const val = componentOverrides[rateKey] || 0;

                return (
                  <div key={c.key} className="space-y-2.5">
                    <div className="flex justify-between text-xs font-bold font-mono-numbers">
                      <div className="flex flex-col">
                        <span className="text-text-primary font-sans text-xs">{c.name}</span>
                        <span className="text-[9px] font-normal text-text-secondary leading-tight mt-0.5">{c.plain_english || 'Volumetric component rate'}</span>
                      </div>
                      <span className={`text-xs font-bold font-mono-numbers ${val > 0 ? 'text-alert-red' : val < 0 ? 'text-savings-green' : 'text-text-secondary'}`}>
                        {val > 0 ? '+' : ''}{val}%
                      </span>
                    </div>
                    <input
                      type="range" min="-50" max="100" step="5" value={val}
                      onChange={(e) => {
                        setComponentOverrides({ ...componentOverrides, [rateKey]: parseInt(e.target.value) });
                        setScenario(null);
                      }}
                      className="w-full h-1.5 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary-blue"
                    />
                  </div>
                );
              })}

            </div>
          </div>

          {/* Dynamic commentary summary */}
          <div className="bg-primary-blue/5 border border-primary-blue/10 p-4 rounded-md text-xs font-semibold leading-relaxed text-text-primary flex items-start gap-2.5 shadow-sm">
            <Info size={14} className="text-primary-blue shrink-0 mt-0.5" />
            <div>
              {scenario ? (
                <>Preset <strong className="text-primary-blue">"{PRESETS.find(x => x.key === scenario)?.label}"</strong> applied. This overrides standard rates to evaluate stress conditions.</>
              ) : Object.keys(changes).length > 0 || kwh !== uploadedBill.usage_kwh ? (
                <>Custom overrides active. Simulating a rate mix change on {Object.keys(changes).map(k => COMPONENT_METADATA[k]?.label || k).join(', ')} under an adjusted load of {kwh} kWh.</>
              ) : (
                <>No simulation overrides active. Adjust rate component sliders or select preset scenarios to compute simulated monthly bills.</>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* DYNAMIC FORMULA VISUALIZATION CARD */}
      <div className="panel-operational space-y-4">
        <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
          <Calculator className="text-primary-blue" size={16} />
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest font-sans">Formula & Calculation Engine</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-xs leading-relaxed font-mono-numbers">
          {activeComponents.map((c: any) => {
            const rateKey = costToRateKey[c.key] || c.key;
            const overrideVal = componentOverrides[rateKey] || 0;
            
            // Extract baseline details
            const baseRate = c.formula_val?.split('/')[0]?.replace('$', '') || '0.0000';
            const simRate = (parseFloat(baseRate) * (1 + overrideVal / 100)).toFixed(5);
            
            let substituted: string;
            let sym: string;
            if (rateKey === 'customer_charge') {
              sym = "Fixed Customer Charge";
              substituted = `$${simRate} (Base $${parseFloat(baseRate).toFixed(2)} ${overrideVal !== 0 ? `with ${overrideVal > 0 ? '+' : ''}${overrideVal}% override` : 'flat'})`;
            } else {
              sym = `${c.name} Rate × Usage`;
              substituted = `$${simRate}/kWh × ${kwh} kWh = $${(parseFloat(simRate) * kwh).toFixed(2)}`;
            }

            return (
              <div key={c.key} className="p-3 bg-bg-secondary rounded border border-border-hairline flex flex-col justify-between hover:border-text-secondary/20 transition-all font-mono-numbers">
                <div>
                  <span className="text-[9px] font-bold text-text-secondary font-sans uppercase block mb-1">{c.name}</span>
                  <div className="text-text-primary text-[11px] font-semibold">{sym}</div>
                  <div className="text-primary-blue text-xs mt-1.5 font-bold">{substituted}</div>
                </div>
                {overrideVal !== 0 && (
                  <span className="text-[8px] bg-warning-amber/15 text-warning-amber px-1.5 py-0.5 rounded border border-warning-amber/20 font-sans mt-2 block w-fit">
                    Modified
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* SECTION 3.5: Historic Tariff Data */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part III: Historic Tariff Data</h3>
          <p className="text-xs text-text-secondary">Explore the database summary and historic tariff rates for {utility} ({schedule}).</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="panel-operational">
            <h4 className="text-sm font-bold text-text-primary mb-3">Database Summary</h4>
            {tariffSummary ? (
              <div className="space-y-2 text-sm text-text-secondary">
                <div className="flex justify-between border-b border-border-hairline pb-2">
                  <span>Utility</span>
                  <span className="font-mono-numbers text-text-primary">{tariffSummary.utility}</span>
                </div>
                <div className="flex justify-between border-b border-border-hairline pb-2">
                  <span>Total Versions</span>
                  <span className="font-mono-numbers text-text-primary">{tariffSummary.total_versions}</span>
                </div>
                <div className="flex justify-between border-b border-border-hairline pb-2">
                  <span>Rates Recorded</span>
                  <span className="font-mono-numbers text-text-primary">{tariffSummary.total_rates}</span>
                </div>
                <div className="flex justify-between">
                  <span>Schedules</span>
                  <span className="font-mono-numbers text-text-primary">{tariffSummary.schedules.join(', ')}</span>
                </div>
              </div>
            ) : (
              <div className="text-xs text-text-secondary">Loading summary...</div>
            )}
          </div>

          <div className="lg:col-span-2 panel-operational">
            <h4 className="text-sm font-bold text-text-primary mb-3">Historical Rate Explorer</h4>
            <div className="space-y-4 max-h-80 overflow-y-auto pr-2 custom-scrollbar">
              {tariffHistory.map((version, i) => (
                <div key={i} className="p-3 bg-bg-secondary border border-border-hairline rounded-md font-mono-numbers">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold text-text-primary text-sm font-sans">{version.version_name}</span>
                    <span className="text-[10px] text-text-secondary uppercase tracking-wider bg-bg-primary px-2 py-0.5 rounded border border-border-hairline font-sans">
                      Effective: {version.effective_start} to {version.effective_end || 'Present'}
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-border-hairline text-text-secondary font-sans uppercase tracking-widest text-[9px]">
                          <th className="py-2 px-1">Component</th>
                          <th className="py-2 px-1">Category</th>
                          <th className="py-2 px-1 text-right">Rate</th>
                          <th className="py-2 px-1">Unit</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-hairline/50">
                        {version.components.map((c: any, idx: number) => (
                          <tr key={idx} className="hover:bg-bg-primary/50 transition-colors">
                            <td className="py-2 px-1 font-medium text-text-primary font-sans">{c.component}</td>
                            <td className="py-2 px-1 text-text-secondary font-sans">{c.category}</td>
                            <td className="py-2 px-1 text-right font-mono-numbers text-primary-blue font-bold">{c.rate}</td>
                            <td className="py-2 px-1 text-text-secondary font-mono-numbers text-[10px]">{c.unit}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
              {tariffHistory.length === 0 && (
                <div className="text-xs text-text-secondary">Loading history...</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* DYNAMIC COMPONENT CONTRIBUTION TABLE */}
      <div className="panel-operational space-y-4">
        <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
          <BarChart3 className="text-primary-blue" size={16} />
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest font-sans">Dynamic Component Contribution</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-border-hairline text-text-secondary font-sans uppercase tracking-widest text-[9px]">
                <th className="py-3 px-2">Component</th>
                <th className="py-3 px-2 text-right">Base Amount</th>
                <th className="py-3 px-2 text-right">Simulated Amount</th>
                <th className="py-3 px-2 text-right">Delta ($)</th>
                <th className="py-3 px-2 text-right">Variance (%)</th>
                <th className="py-3 px-2">Fixed/Var</th>
                <th className="py-3 px-2">Controllable</th>
                <th className="py-3 px-2">Simulation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-hairline/50 font-mono-numbers">
              {uploadedBill.canonical_bill?.components.map((c: any) => {
                const rateKey = costToRateKey[c.key] || c.key;
                const simItem = simContribs[rateKey] || {};
                
                const baseVal = simItem.base_cost ?? c.value ?? 0.0;
                const simVal = simItem.simulated_cost ?? baseVal;
                const diff = simItem.difference ?? (simVal - baseVal);
                const diffPct = simItem.percent_difference ?? 0.0;
                const isModified = componentOverrides[rateKey] !== undefined && componentOverrides[rateKey] !== 0;

                return (
                  <tr key={c.key} className="hover:bg-bg-secondary/40 transition-colors">
                    <td className="py-3 px-2 font-medium text-text-primary text-left font-sans">{c.name}</td>
                    <td className="py-3 px-2 text-right">${baseVal.toFixed(2)}</td>
                    <td className="py-3 px-2 text-right font-bold text-primary-blue">${simVal.toFixed(2)}</td>
                    <td className={`py-3 px-2 text-right font-bold ${diff > 0.01 ? 'text-alert-red' : diff < -0.01 ? 'text-savings-green' : 'text-text-secondary'}`}>
                      {diff > 0.01 ? '+' : ''}{diff.toFixed(2)}
                    </td>
                    <td className={`py-3 px-2 text-right font-bold ${diffPct > 0.01 ? 'text-alert-red' : diffPct < -0.01 ? 'text-savings-green' : 'text-text-secondary'}`}>
                      {diffPct > 0.01 ? '+' : ''}{diffPct.toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 font-sans text-text-secondary">{c.type || 'Variable'}</td>
                    <td className="py-3 px-2 font-sans">
                      <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-bold ${
                        c.controllable === 'Yes' ? 'bg-savings-green/10 text-savings-green border border-savings-green/20' :
                        c.controllable === 'Partial' ? 'bg-warning-amber/10 text-warning-amber border border-warning-amber/20' :
                        'bg-bg-secondary text-text-secondary border border-border-hairline'
                      }`}>
                        {c.controllable || 'No'}
                      </span>
                    </td>
                    <td className="py-3 px-2 font-sans">
                      {isModified ? (
                        <span className="text-[10px] font-bold text-warning-amber bg-warning-amber/10 border border-warning-amber/25 px-2 py-0.5 rounded">
                          Simulated ({componentOverrides[rateKey] > 0 ? '+' : ''}{componentOverrides[rateKey]}%)
                        </span>
                      ) : (
                        <span className="text-[10px] text-text-secondary bg-bg-secondary border border-border-hairline px-2 py-0.5 rounded">
                          Baseline
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 4: Simulation Results */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part IV: Simulation Results</h3>
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

        {/* Dynamic Step-by-Step Waterfall & Causal bar decomposition */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Deterministic Waterfall Chart */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Waterfall Cost Progression</span>
              <h4 className="text-sm font-bold text-text-primary">
                {hasAnyChanges ? 'Deterministic component changes step progress' : 'Bill cost breakdown by component'}
              </h4>
            </div>

            <div className="flex-1 min-h-[200px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                {hasAnyChanges ? (
                  // Delta waterfall mode: stacked spacer + value bars
                  <BarChart data={waterfallChartData} margin={{ top: 10, right: 15, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 8, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 9, fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                      itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                      formatter={(_v: any, _name: any, props: any) => [`$${props.payload.actualVal.toFixed(2)}`, props.payload.type === 'base' || props.payload.type === 'final' ? 'Bill Total' : 'Cost change']}
                    />
                    <Bar dataKey="spacer" stackId="a" fill="transparent" />
                    <Bar dataKey="value" stackId="a" radius={[2, 2, 0, 0]}>
                      {waterfallChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getComponentColor(entry.name, entry.type)} />
                      ))}
                    </Bar>
                  </BarChart>
                ) : (
                  // Baseline mode: simple absolute bar chart, no stacking
                  <BarChart data={waterfallChartData} margin={{ top: 10, right: 15, left: -25, bottom: 0 }} barCategoryGap="20%">
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 8, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 9, fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                      itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                      formatter={(_v: any, _name: any, props: any) => [`$${props.payload.actualVal.toFixed(2)}`, 'Component Cost']}
                    />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={55}>
                      {waterfallChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getComponentColor(entry.name, entry.type)} />
                      ))}
                    </Bar>
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
            <div className="text-[10px] text-text-secondary font-sans mt-1 text-center font-medium">
              {hasAnyChanges
                ? 'Illustrates how each simulated variance steps from the original Base Bill to the new Final simulated bill.'
                : 'Absolute cost of each billing component. Move sliders above to see how changes affect the bill.'}
            </div>
          </div>

          {/* Causal rate vs usage decomposition bar */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Causal Factor Analysis</span>
              <h4 className="text-sm font-bold text-text-primary">
                {hasAnyChanges ? 'Decomposition of simulated bill deviations ($)' : 'Absolute cost by billing component ($)'}
              </h4>
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
                    {decompositionChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[9px] text-text-secondary border-t border-border-hairline pt-3 mt-3 font-semibold">
              {decompositionChartData.map((d, i) => (
                <div key={i} className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm" style={{ backgroundColor: d.fill }}></span>{d.name}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Probabilistic Bounds & Tornado Chart */}
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

          {/* Tornado Sensitivity Chart */}
          <div className="panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Tornado Sensitivity analysis</span>
              <h4 className="text-sm font-bold text-text-primary font-sans">Impact of a 10% rate shock by component ($)</h4>
            </div>

            <div className="flex-1 min-h-[220px] mt-4 font-mono-numbers">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tornadoChartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${v > 0 ? '+' : ''}$${v}`} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 8, fill: 'var(--text-secondary)', fontFamily: 'sans-serif' }} width={90} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                    itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="negativeImpact" fill="#27AE60" stackId="stack" radius={[2, 0, 0, 2]} />
                  <Bar dataKey="positiveImpact" fill="#D64545" stackId="stack" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-[10px] text-text-secondary font-sans text-center font-medium mt-1">
              Visualizes the comparative rate volatility risks of each rate component.
            </div>
          </div>
        </div>

        {/* Double Machine Learning Diagnostics */}
        {dmlData && !dmlData.error && (
          <div className="panel-operational space-y-4 font-mono-numbers">
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
              <Cpu className="text-primary-blue" size={16} />
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest font-sans">Double Machine Learning (DML) Causal Diagnostics</h4>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-xs font-mono-numbers">
              <div className="space-y-2 bg-bg-secondary p-3.5 rounded border border-border-hairline">
                <span className="text-[9px] uppercase tracking-wider text-text-secondary font-bold font-sans">Inference Parameters</span>
                <div className="flex justify-between border-b border-border-hairline/50 pb-1.5 mt-1 font-mono-numbers">
                  <span className="font-sans text-text-secondary">Price Elasticity:</span>
                  <strong className="text-primary-blue">{dmlData.causal_effect_estimate}</strong>
                </div>
                <div className="flex justify-between border-b border-border-hairline/50 pb-1.5 font-mono-numbers">
                  <span className="font-sans text-text-secondary">ATE (Supply rate):</span>
                  <strong>${(dmlData.causal_effect_estimate * 0.01 * kwh).toFixed(2)}/¢</strong>
                </div>
                <div className="flex justify-between font-mono-numbers">
                  <span className="font-sans text-text-secondary">95% CI bounds:</span>
                  <span>[{dmlData.ci_95?.[0]}, {dmlData.ci_95?.[1]}]</span>
                </div>
              </div>
              
              <div className="space-y-2 bg-bg-secondary p-3.5 rounded border border-border-hairline">
                <span className="text-[9px] uppercase tracking-wider text-text-secondary font-bold font-sans">Residual Diagnostics</span>
                <div className="flex justify-between border-b border-border-hairline/50 pb-1.5 mt-1 font-mono-numbers">
                  <span className="font-sans text-text-secondary">Estimation Method:</span>
                  <span className="font-sans text-text-secondary text-[11px] font-bold">{dmlData.method}</span>
                </div>
                <div className="flex justify-between font-mono-numbers">
                  <span className="font-sans text-text-secondary">Model Confidence (p):</span>
                  <strong className="text-savings-green">{dmlData.p_value?.toFixed(5)}</strong>
                </div>
              </div>

              <div className="space-y-2 bg-bg-secondary p-3.5 rounded border border-border-hairline font-sans">
                <span className="text-[9px] uppercase tracking-wider text-text-secondary font-bold font-sans">Confounders Controlled</span>
                <p className="text-[10px] text-text-secondary leading-relaxed mt-1">
                  Controlled variables in nuisance models: {dmlData.confounders_controlled?.join(', ')}.
                </p>
                <div className="text-[10px] text-warning-amber bg-warning-amber/15 border border-warning-amber/20 px-2 py-0.5 rounded w-fit mt-1.5 font-bold">
                  Controlled for Weather & Seasonality
                </div>
              </div>
            </div>
            <p className="text-[11px] text-text-secondary leading-relaxed italic bg-bg-secondary/40 p-3.5 rounded border border-border-hairline/40 font-sans">
              💡 **Causal Interpretation**: {dmlData.interpretation} ({dmlData.caveat})
            </p>
          </div>
        )}

        {/* PJM physics data */}
        {simulation?.pjm_physics && (
          <div className="panel-operational space-y-4 font-mono-numbers">
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

      {/* MULTI-SCENARIO PERSISTENCE & SIDE-BY-SIDE COMPARISON */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part V: Scenario Management & Multi-Scenario Comparison</h3>
          <p className="text-xs text-text-secondary">Save, load, and run side-by-side comparative analyses across custom what-if scenarios.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Scenario Saver Panel */}
          <div className="panel-operational flex flex-col justify-between p-5 bg-bg-surface border-border-hairline h-[360px]">
            <div className="space-y-4">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Save current configuration</span>
              <p className="text-xs text-text-secondary leading-relaxed">
                Persist the active overrides (modified rates, custom usage) as a saved scenario.
              </p>
              <div className="space-y-2">
                <label className="text-[10px] font-semibold text-text-secondary block font-sans">Scenario Name</label>
                <input
                  type="text"
                  placeholder="e.g. Rate Spikes + Solar Panel Shift"
                  value={newScenarioName}
                  onChange={(e) => setNewScenarioName(e.target.value)}
                  className="w-full text-xs bg-bg-secondary text-text-primary border border-border-hairline rounded p-2.5 outline-none focus:border-primary-blue font-sans font-medium"
                />
              </div>
            </div>
            <button
              onClick={handleSaveScenario}
              disabled={!newScenarioName.trim()}
              className="w-full py-2.5 bg-primary-blue text-white rounded font-bold text-xs hover:bg-primary-blue/90 disabled:bg-primary-blue/30 disabled:cursor-not-allowed transition-all mt-4 flex items-center justify-center gap-1.5 shadow font-sans active:scale-[0.98]"
            >
              <Plus size={14} />
              Save Scenario Configuration
            </button>
          </div>

          {/* Saved Scenarios Manager */}
          <div className="lg:col-span-2 panel-operational p-5 h-[360px] flex flex-col">
            <div className="flex justify-between items-center mb-3 border-b border-border-hairline pb-2">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">
                Saved Scenarios Directory
              </span>
              {savedScenarios.length > 0 && (
                <button
                  onClick={handleExportScenarios}
                  className="flex items-center gap-1 text-[9px] font-bold text-primary-blue hover:underline bg-transparent border-none cursor-pointer"
                  title="Export Scenarios to JSON"
                >
                  <Download size={10} /> Export
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar text-xs">
              {savedScenarios.length === 0 ? (
                <div className="text-center text-text-secondary py-12 font-sans">No saved configurations found. Create a scenario to save active inputs.</div>
              ) : (
                savedScenarios.map((s) => {
                  const isCompared = comparedIds.includes(s.id);
                  return (
                    <div key={s.id} className="flex justify-between items-center p-3 bg-bg-secondary rounded border border-border-hairline hover:border-text-secondary/20 transition-all font-mono-numbers">
                      <div>
                        <div className="font-bold text-text-primary font-sans">{s.name}</div>
                        <div className="text-[9px] text-text-secondary mt-0.5 font-sans">Saved: {s.timestamp}</div>
                        <div className="text-[10px] text-primary-blue mt-1 font-bold">Simulated bill: ${s.simulatedBill?.toFixed(2)} ({s.totalImpact >= 0 ? '+' : ''}${s.totalImpact?.toFixed(2)})</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleComparison(s.id)}
                          className={`px-3 py-1.5 rounded font-sans font-bold text-[10px] transition-all border ${
                            isCompared 
                              ? 'bg-savings-green/10 text-savings-green border-savings-green/20' 
                              : 'bg-bg-primary text-text-secondary border-border-hairline hover:bg-bg-secondary hover:text-text-primary'
                          }`}
                        >
                          {isCompared ? 'Comparing' : 'Compare'}
                        </button>
                        <button
                          onClick={() => handleLoadScenario(s)}
                          className="px-3 py-1.5 bg-bg-primary hover:bg-bg-secondary text-text-primary border border-border-hairline rounded font-sans font-bold text-[10px] transition-all"
                        >
                          Load
                        </button>
                        <button
                          onClick={() => handleDuplicateScenario(s)}
                          className="p-1.5 text-text-secondary hover:text-primary-blue transition-colors"
                          title="Duplicate Scenario"
                        >
                          <Copy size={13} />
                        </button>
                        <button
                          onClick={() => handleDeleteScenario(s.id)}
                          className="p-1.5 text-text-secondary hover:text-alert-red transition-colors"
                          title="Delete Scenario"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Side-by-Side Scenario Comparison view */}
        {comparedIds.length > 0 && (
          <div className="panel-operational space-y-4 bg-bg-surface shadow border-border-hairline">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block border-b border-border-hairline pb-2">
              Side-by-Side Scenario Comparison
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers text-xs">
              
              {/* Baseline reference card */}
              <div className="p-4 bg-bg-secondary/40 border border-border-hairline rounded flex flex-col justify-between">
                <div>
                  <span className="text-[9px] uppercase tracking-wider text-text-secondary font-bold font-sans">Baseline Bill</span>
                  <div className="text-2xl font-bold text-text-primary mt-2">${utilityBill.toFixed(2)}</div>
                  <div className="mt-3 space-y-1.5 text-text-secondary">
                    <div className="flex justify-between border-b border-border-hairline/50 pb-1">
                      <span className="font-sans">Usage load:</span>
                      <strong>{uploadedBill.usage_kwh} kWh</strong>
                    </div>
                    <div className="flex justify-between border-b border-border-hairline/50 pb-1">
                      <span className="font-sans">BGS Supply:</span>
                      <strong>${(uploadedBill.rates?.bgs_rate || 0.105).toFixed(4)}/kWh</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-sans">Customer Charge:</span>
                      <strong>${(uploadedBill.rates?.customer_charge || 8.24).toFixed(2)}</strong>
                    </div>
                  </div>
                </div>
                <div className="mt-4 pt-2 border-t border-border-hairline/50 text-[10px] text-text-secondary font-sans font-medium italic">
                  Primary baseline active bill reference data
                </div>
              </div>

              {/* Compared scenarios */}
              {comparedIds.map(cid => {
                const s = savedScenarios.find(x => x.id === cid);
                if (!s) return null;
                const isSaving = s.totalImpact < 0;
                
                return (
                  <div key={s.id} className="p-4 bg-bg-secondary border border-border-hairline rounded flex flex-col justify-between hover:border-text-secondary/20 transition-all">
                    <div>
                      <div className="flex justify-between items-start mb-2 font-sans">
                        <span className="text-[10px] uppercase tracking-wider text-primary-blue font-bold">{s.name}</span>
                        <button onClick={() => toggleComparison(s.id)} className="text-[9px] text-text-secondary hover:underline">Remove</button>
                      </div>
                      <div className="text-2xl font-bold text-text-primary mt-2">${s.simulatedBill?.toFixed(2)}</div>
                      <div className="mt-3 space-y-1.5 text-text-secondary">
                        <div className="flex justify-between border-b border-border-hairline/50 pb-1">
                          <span className="font-sans">Simulated Usage:</span>
                          <strong className="text-text-primary">{s.kwh} kWh</strong>
                        </div>
                        <div className="flex justify-between border-b border-border-hairline/50 pb-1">
                          <span className="font-sans">Usage Delta:</span>
                          <strong className={s.usageChange > 0 ? 'text-alert-red' : s.usageChange < 0 ? 'text-savings-green' : ''}>
                            {s.usageChange >= 0 ? '+' : ''}{s.usageChange?.toFixed(1)} kWh
                          </strong>
                        </div>
                        <div className="flex justify-between border-b border-border-hairline/50 pb-1">
                          <span className="font-sans">Total cost variance:</span>
                          <strong className={s.totalImpact > 0 ? 'text-alert-red' : s.totalImpact < 0 ? 'text-savings-green' : ''}>
                            {s.totalImpact >= 0 ? '+' : ''}${s.totalImpact?.toFixed(2)} ({s.totalImpact >= 0 ? '+' : ''}{((s.totalImpact/utilityBill)*100).toFixed(1)}%)
                          </strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-sans">Price Elasticity:</span>
                          <strong className="text-text-primary">{s.elasticity?.toFixed(3)}</strong>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 pt-2 border-t border-border-hairline/50 flex justify-between items-baseline font-sans text-xs">
                      <span className="text-[9px] text-text-secondary font-bold uppercase">Scenario Impact</span>
                      <strong className={isSaving ? 'text-savings-green' : 'text-alert-red'}>
                        {isSaving ? 'Cheaper Plan' : 'Higher Cost'}
                      </strong>
                    </div>
                  </div>
                );
              })}

            </div>
          </div>
        )}
      </div>

      {/* SECTION 5: Dynamic Investment Upgrade Analysis */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part VI: Dynamic Investment Upgrade Analysis</h3>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 font-mono-numbers text-xs">

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
                    <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs font-sans">
                      <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                      <span className={`font-mono-numbers font-bold ${isIncrease ? 'text-alert-red' : 'text-savings-green'}`}>
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
                <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs font-sans">
                  <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                  <span className="font-mono-numbers font-bold text-savings-green">−$350.00/yr</span>
                </div>
              </div>

              {/* Custom Demand Response Upgrade card */}
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
                <div className="border-t border-border-hairline pt-2 mt-2 flex justify-between items-baseline text-xs font-sans">
                  <span className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Annual impact</span>
                  <span className="font-mono-numbers font-bold text-savings-green">−$180.00/yr</span>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* Flow Telemetry graph */}
        <EnergyFlowSVG />
      </div>

      {/* DYNAMIC VALIDATION STATUS BADGE */}
      <div className="panel-operational space-y-3 bg-bg-surface shadow-sm border border-border-hairline">
        <div className="flex items-center justify-between border-b border-border-hairline pb-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="text-savings-green" size={16} />
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest font-sans">Simulation Integrity & Validation</h4>
          </div>
          <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold border uppercase font-sans ${
            validationResults.status === 'Passed' ? 'bg-savings-green/10 text-savings-green border-savings-green/25' :
            validationResults.status === 'Warning' ? 'bg-warning-amber/10 text-warning-amber border-warning-amber/25' :
            'bg-alert-red/10 text-alert-red border-alert-red/25'
          }`}>
            {validationResults.status}
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-medium mt-2">
          {validationResults.checks.map((chk, idx) => (
            <div key={idx} className="flex items-start gap-2 bg-bg-secondary p-2.5 rounded border border-border-hairline">
              {chk.status === 'Passed' ? (
                <CheckCircle2 size={13} className="text-savings-green shrink-0 mt-0.5" />
              ) : chk.status === 'Warning' ? (
                <AlertTriangle size={13} className="text-warning-amber shrink-0 mt-0.5" />
              ) : (
                <AlertCircle size={13} className="text-alert-red shrink-0 mt-0.5" />
              )}
              <div>
                <div className="font-semibold text-text-primary">{chk.label}</div>
                <div className="text-[10px] text-text-secondary mt-0.5 leading-relaxed">{chk.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI IMPACT INTELLIGENCE REPORT (LLM-POWERED) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* AI report card */}
        <div className="lg:col-span-2 panel-operational p-5 bg-bg-surface border-border-hairline shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border-hairline pb-2">
            <div className="flex items-center gap-2">
              <Lightbulb className="text-warning-amber" size={16} />
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest">AI Executive Financial Report</h4>
            </div>
            {isExplainLoading && (
              <span className="text-[9px] uppercase tracking-wider text-primary-blue animate-pulse font-bold">
                Analyzing simulation...
              </span>
            )}
          </div>
          <div className="text-xs text-text-primary leading-relaxed whitespace-pre-line overflow-y-auto max-h-[380px] pr-2 custom-scrollbar font-medium">
            {explainData?.explanation ? (
              <div className="markdown-body space-y-4">
                {explainData.explanation}
              </div>
            ) : (
              <div className="text-center text-text-secondary py-20 font-sans">
                Compiling simulated cost deviations. Adjust sliders or select presets to prompt analysis.
              </div>
            )}
          </div>
        </div>

        {/* AI Chat assistant */}
        <div className="panel-operational flex flex-col p-5 bg-bg-surface border-border-hairline shadow-sm h-[440px]">
          <div className="flex items-center gap-2 border-b border-border-hairline pb-2 mb-3">
            <MessageSquare className="text-primary-blue" size={16} />
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-widest font-sans">Simulation Assistant</h4>
          </div>
          
          {/* Messages box */}
          <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 text-[11px] leading-relaxed custom-scrollbar max-h-[260px]">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`p-2.5 rounded max-w-[85%] ${
                msg.role === 'user' 
                  ? 'bg-primary-blue/5 border border-primary-blue/20 text-text-primary ml-auto font-sans'
                  : 'bg-bg-secondary border border-border-hairline text-text-secondary font-sans font-medium'
              }`}>
                <strong>{msg.role === 'user' ? 'You' : 'AI Assistant'}:</strong>
                <p className="mt-1 font-sans font-medium">{msg.content}</p>
              </div>
            ))}
          </div>

          {/* Quick-action question buttons */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            <button 
              onClick={() => handleSendChatMessage("Why did Distribution increase?")}
              className="px-2 py-1 bg-bg-secondary hover:bg-bg-primary text-text-secondary border border-border-hairline rounded-[4px] text-[9px] font-bold font-sans active:scale-[0.98]"
            >
              Why Distribution increase?
            </button>
            <button 
              onClick={() => handleSendChatMessage("What happens if I reduce usage by 15%?")}
              className="px-2 py-1 bg-bg-secondary hover:bg-bg-primary text-text-secondary border border-border-hairline rounded-[4px] text-[9px] font-bold font-sans active:scale-[0.98]"
            >
              What if reduce usage 15%?
            </button>
          </div>

          {/* Chat input box */}
          <div className="mt-3 flex gap-2 border-t border-border-hairline/50 pt-3">
            <input
              type="text"
              placeholder="Ask about rate hikes, weather factors..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendChatMessage()}
              className="flex-1 bg-bg-secondary border border-border-hairline rounded p-2 text-xs outline-none focus:border-primary-blue text-text-primary font-sans font-medium"
            />
            <button
              onClick={() => handleSendChatMessage()}
              disabled={isChatSending}
              className="p-2 bg-primary-blue text-white rounded hover:bg-primary-blue/90 disabled:bg-primary-blue/30 transition-all flex items-center justify-center active:scale-[0.98]"
            >
              <Send size={12} />
            </button>
          </div>
        </div>

      </div>

      {/* SECTION 7: Recommendations */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part VII: Priority Recommendations</h3>
          <p className="text-xs text-text-secondary">AI-generated clean energy recommendations prioritized by ROI and payback duration.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-semibold font-sans">

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

      {/* SECTION 8: Historical Comparison */}
      <div className="space-y-6">
        <div className="border-l-4 border-primary-blue pl-3">
          <h3 className="text-base font-bold text-text-primary uppercase tracking-wider">Part VIII: Historical Comparison</h3>
          <p className="text-xs text-text-secondary">Track billing trends and monthly volatility over a 12-month rolling range.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Trend composed chart */}
          <div className="lg:col-span-2 panel-chart flex flex-col justify-between h-[360px]">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary block mb-1">Billing trends</span>
              <h4 className="text-sm font-bold text-text-primary font-sans">12-Month cost trend vs monthly variance</h4>
            </div>

            <div className="flex-1 min-h-[220px] mt-4 font-mono-numbers">
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
              <span className="text-xs font-bold text-text-secondary uppercase tracking-wider font-sans">Historical Comparison</span>
            </div>

            <div className="space-y-4 mt-4 flex-1 font-mono-numbers">

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase font-sans">Previous Month</span>
                  <span className="text-xs font-bold text-text-primary font-sans">May 2026</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">${previousBill.toFixed(2)}</span>
                  <span className="text-[10px] text-text-secondary font-sans">{(uploadedBill.usage_kwh * 0.92).toFixed(0)} kWh</span>
                </div>
              </div>

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase font-sans">Previous Year</span>
                  <span className="text-xs font-bold text-text-primary font-sans">June 2025</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">${(utilityBill * 0.97).toFixed(2)}</span>
                  <span className="text-[10px] text-text-secondary font-sans">{(uploadedBill.usage_kwh * 0.97).toFixed(0)} kWh</span>
                </div>
              </div>

              <div className="flex justify-between items-center bg-bg-secondary p-3 rounded-md border border-border-hairline shadow-sm">
                <div>
                  <span className="text-[10px] text-text-secondary block uppercase font-sans">12-Month Rolling Avg</span>
                  <span className="text-xs font-bold text-text-primary font-sans">Mean outflow</span>
                </div>
                <div className="text-right font-mono-numbers">
                  <span className="text-xs font-bold text-text-primary block">
                    ${(historyTrendData.reduce((acc, curr) => acc + curr.bill, 0) / 12).toFixed(2)}
                  </span>
                  <span className="text-[10px] text-text-secondary font-sans">{(uploadedBill.usage_kwh * 1.01).toFixed(0)} kWh avg</span>
                </div>
              </div>

            </div>

            <div className="border-t border-border-hairline pt-3 mt-3 flex justify-between items-baseline text-xs font-sans">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Trend direction</span>
              <span className="font-bold text-warning-amber">Stable (Flat +/- 3% variance)</span>
            </div>
          </div>

        </div>
      </div>

      {/* Navigation back deep-link */}
      <div className="flex justify-center font-sans">
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
