import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ShieldAlert, Cpu, Activity, RefreshCw } from 'lucide-react';

const PRESETS = [
  { key: 'hot_summer', label: '🔥 Hot Summer', desc: 'High CDD temperatures and peak pricing (+25% bgs_rate)' },
  { key: 'cold_winter', label: '❄️ Cold Winter', desc: 'High HDD temperatures and peak heating demand (+15% bgs_rate)' },
  { key: 'high_market', label: '⚡ High Wholesale Market', desc: 'Wholesale prices spike (+40% bgs_rate, +20% transmission_rate)' },
  { key: 'conservation', label: '🌳 Green Conservation', desc: 'Usage drops by 20% (-20% usage)' }
];

const COLORS = [
  '#2F6BFF', // Primary blue
  '#16A085', // Energy teal
  '#2CA6FF', // Electric cyan
  '#27AE60', // Savings green
  '#F5B041', // Warning amber
  '#D64545', // Alert red
];

// Flat modern SVG showing energy flow from grid to customer
const EnergyFlowSVG = () => (
  <div className="w-full bg-bg-primary rounded-md p-4 border border-border-hairline flex flex-col items-center">
    <span className="text-[9px] uppercase tracking-widest text-text-secondary mb-3 font-semibold">Grid dispatch to customer flow telemetry</span>
    <svg className="w-full max-w-lg h-14 text-text-secondary/30" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 320 40">
      {/* Power Plant / Grid Tower */}
      <g transform="translate(10, 5)" stroke="var(--primary-blue)" opacity="0.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 5l10 30M15 5L5 35M2 35h26M5 15h20M2 25h26" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">GRID</text>
      </g>
      {/* Substation */}
      <g transform="translate(110, 10)" stroke="var(--energy-teal)" opacity="0.8">
        <rect x="5" y="5" width="20" height="20" rx="2" />
        <path d="M15 5v20M5 15h20" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">SUBSTATION</text>
      </g>
      {/* Smart Meter */}
      <g transform="translate(210, 10)" stroke="var(--electric-cyan)" opacity="0.8">
        <circle cx="15" cy="15" r="10" />
        <path d="M10 15h10M15 10v10" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">METER</text>
      </g>
      {/* Consumer Home */}
      <g transform="translate(290, 8)" stroke="var(--text-primary)" opacity="0.8">
        <path d="M5 25V13l10-8 10 8v12H5z" />
        <path d="M12 25v-6h6v6" />
        <text x="15" y="-2" textAnchor="middle" fontSize="6" fill="var(--text-secondary)" stroke="none" fontWeight="bold">HOME</text>
      </g>
      {/* Flowing connector arrows */}
      <g stroke="var(--primary-blue)" strokeWidth="1" strokeDasharray="3 3" opacity="0.5">
        <path d="M40 22h65" />
        <path d="M140 22h65" />
        <path d="M235 22h50" />
      </g>
    </svg>
  </div>
);

const WhatIfTab = ({ uploadedBill, setActiveTab }: { uploadedBill: any, setActiveTab?: (tab: string) => void }) => {
  const [kwh, setKwh] = useState<number>(750);
  const [bgsChange, setBgsChange] = useState<number>(0);
  const [distChange, setDistChange] = useState<number>(0);
  const [transChange, setTransChange] = useState<number>(0);
  const [sbcChange, setSbcChange] = useState<number>(0);
  const [nugChange, setNugChange] = useState<number>(0);
  const [scenario, setScenario] = useState<string | null>(null);

  // Sync kwh with uploaded bill
  useEffect(() => {
    if (uploadedBill?.usage_kwh) {
      setKwh(uploadedBill.usage_kwh);
    }
  }, [uploadedBill]);

  const { data: customerSimulations } = useQuery({
    queryKey: ['customer-simulations', uploadedBill],
    queryFn: async () => {
      const res = await axios.post('/bill/simulation', uploadedBill);
      return res.data.scenarios;
    },
    enabled: !!uploadedBill
  });

  if (!uploadedBill) {
    return (
      <div className="panel-operational flex flex-col items-center justify-center p-16 text-center max-w-xl mx-auto space-y-4 my-12 border-dashed border border-border-hairline">
        <Activity size={36} className="text-text-secondary opacity-60 animate-pulse" />
        <h3 className="text-sm font-bold text-text-primary">Simulator locked</h3>
        <p className="text-xs text-text-secondary max-w-sm">
          Please upload and analyze an electricity bill on the Bill Analysis page to use the What-If Engine.
        </p>
        <button 
          onClick={() => setActiveTab?.("Bill Analysis")}
          className="px-4 py-2.5 bg-bg-surface border border-border-hairline rounded-md text-xs font-semibold hover:bg-bg-primary transition-all shadow-sm"
        >
          Go to Bill Analysis
        </button>
      </div>
    );
  }

  const customerId = "UPLOADED";

  // Assemble modifications payload
  const changes: Record<string, number> = {};
  if (bgsChange !== 0) changes['bgs_rate'] = bgsChange;
  if (distChange !== 0) changes['distribution_rate'] = distChange;
  if (transChange !== 0) changes['transmission_rate'] = transChange;
  if (sbcChange !== 0) changes['sbc_rate'] = sbcChange;
  if (nugChange !== 0) changes['nug_rate'] = nugChange;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['what-if-v2', changes, kwh, scenario],
    queryFn: async () => {
      const payload = {
        changes,
        kwh,
        scenario: scenario || undefined,
        n_simulations: 2000
      };
      const res = await axios.post('/impact/what-if-v2', payload);
      return res.data;
    }
  });

  const handleApplyPreset = (presetKey: string) => {
    setScenario(presetKey);
    setBgsChange(0);
    setDistChange(0);
    setTransChange(0);
    setSbcChange(0);
    setNugChange(0);
  };

  const clearOverrides = () => {
    setScenario(null);
    setBgsChange(0);
    setDistChange(0);
    setTransChange(0);
    setSbcChange(0);
    setNugChange(0);
    setKwh(uploadedBill?.usage_kwh || 750);
  };

  const getDecompositionData = (decomp: any) => {
    if (!decomp) return [];
    return [
      { name: 'Direct Price', value: decomp.direct_price_effect, fill: '#2F6BFF' },
      { name: 'Indirect Behavior', value: decomp.indirect_behavioral_effect, fill: '#16A085' },
      { name: 'Weather Effect', value: decomp.weather_effect, fill: '#F5B041' },
      { name: 'Interaction', value: decomp.interaction_effect, fill: '#2CA6FF' }
    ];
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* ── Personalized What-If Scenarios ── */}
      {customerSimulations && (
        <div className="panel-operational relative overflow-hidden bg-bg-surface">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
            <div>
              <span className="bg-primary-blue/10 text-primary-blue text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-[4px] border border-primary-blue/20">
                Personalized what-if scenarios
              </span>
              <h3 className="text-sm font-bold mt-3 text-text-primary">Customer {customerId} what-if simulator</h3>
              <p className="text-xs text-text-secondary mt-0.5">Simulated annual bill outcomes using customer history and weather variables</p>
            </div>
            
            <div className="font-mono-numbers">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Actual annual cost (est)</span>
              <span className="text-xl font-bold text-text-primary">${customerSimulations[0]?.actual_annual_cost_estimate?.toFixed(2)}</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers">
            {customerSimulations.map((s: any, idx: number) => {
              const diff = s.difference_vs_actual;
              const isIncrease = diff > 0;
              return (
                <div key={idx} className="p-4 bg-bg-primary rounded-md border border-border-hairline flex flex-col justify-between shadow-sm">
                  <div>
                    <span className="text-xs font-bold text-primary-blue uppercase tracking-wider block mb-2 font-sans">{s.scenario_name}</span>
                    <div className="flex justify-between text-xs text-text-secondary mb-1">
                      <span className="font-sans">Simulated usage:</span>
                      <span className="font-bold text-text-primary">{s.simulated_annual_usage_kwh?.toLocaleString()} kWh</span>
                    </div>
                    <div className="flex justify-between text-xs text-text-secondary mb-3">
                      <span className="font-sans">Simulated cost:</span>
                      <span className="font-bold text-text-primary">${s.simulated_annual_cost?.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="border-t border-border-hairline pt-2 flex justify-between items-baseline">
                    <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Impact</span>
                    <span className={`text-sm font-bold ${isIncrease ? 'text-alert-red' : 'text-savings-green'}`}>
                      {isIncrease ? '+' : ''}${diff?.toFixed(2)}/yr
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Title block */}
      <div className="flex justify-between items-end gap-4">
        <div>
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
            What-if simulator
          </span>
          <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2 flex items-center gap-2">
            Scenario simulator
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Build custom rate hikes or test preset macro scenarios to simulate the impact on your bill.
          </p>
        </div>
        <button 
          onClick={clearOverrides}
          className="bg-bg-surface hover:bg-bg-primary text-text-primary font-semibold px-4 py-2 rounded-md text-xs transition-all border border-border-hairline shadow-sm"
        >
          Reset simulator
        </button>
      </div>

      {/* Energy Flow Visualization */}
      <EnergyFlowSVG />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Control Panel */}
        <div className="panel-operational space-y-6">
          <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider border-b border-border-hairline pb-3">
            Parameter controls
          </h3>

          {/* Presets */}
          <div className="space-y-2">
            <label className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block">Preset scenarios</label>
            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => handleApplyPreset(p.key)}
                  className={`p-3 text-left rounded-md border text-xs font-bold transition-all ${
                    scenario === p.key
                      ? 'border-primary-blue bg-primary-blue/5 text-primary-blue'
                      : 'border-border-hairline hover:bg-bg-primary text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-border-hairline my-6"></div>

          {/* Usage Override */}
          <div className="space-y-2 font-mono-numbers">
            <div className="flex justify-between text-xs font-bold">
              <span className="text-text-secondary uppercase tracking-wider text-[10px] font-sans">Monthly consumption</span>
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
              className="w-full h-1.5 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue border border-border-hairline"
            />
          </div>

          {/* Rate Sliders */}
          <div className="space-y-4 pt-2">
            <label className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block border-b border-border-hairline pb-1.5">Manual rate adjustments</label>
            
            {/* BGS */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold font-mono-numbers">
                <span className="text-text-primary font-sans">BGS supply charge</span>
                <span className={bgsChange > 0 ? 'text-alert-red' : bgsChange < 0 ? 'text-savings-green' : 'text-text-secondary'}>
                  {bgsChange > 0 ? '+' : ''}{bgsChange}%
                </span>
              </div>
              <input
                type="range"
                min="-50"
                max="100"
                value={bgsChange}
                onChange={(e) => {
                  setBgsChange(parseInt(e.target.value));
                  setScenario(null);
                }}
                className="w-full h-1 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue"
              />
            </div>

            {/* Distribution */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold font-mono-numbers">
                <span className="text-text-primary font-sans">Distribution charge</span>
                <span className={distChange > 0 ? 'text-alert-red' : distChange < 0 ? 'text-savings-green' : 'text-text-secondary'}>
                  {distChange > 0 ? '+' : ''}{distChange}%
                </span>
              </div>
              <input
                type="range"
                min="-50"
                max="100"
                value={distChange}
                onChange={(e) => {
                  setDistChange(parseInt(e.target.value));
                  setScenario(null);
                }}
                className="w-full h-1 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue"
              />
            </div>

            {/* Transmission */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold font-mono-numbers">
                <span className="text-text-primary font-sans">Transmission charge</span>
                <span className={transChange > 0 ? 'text-alert-red' : transChange < 0 ? 'text-savings-green' : 'text-text-secondary'}>
                  {transChange > 0 ? '+' : ''}{transChange}%
                </span>
              </div>
              <input
                type="range"
                min="-50"
                max="100"
                value={transChange}
                onChange={(e) => {
                  setTransChange(parseInt(e.target.value));
                  setScenario(null);
                }}
                className="w-full h-1 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue"
              />
            </div>

            {/* SBC */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold font-mono-numbers">
                <span className="text-text-primary font-sans">Societal benefits charge</span>
                <span className={sbcChange > 0 ? 'text-alert-red' : sbcChange < 0 ? 'text-savings-green' : 'text-text-secondary'}>
                  {sbcChange > 0 ? '+' : ''}{sbcChange}%
                </span>
              </div>
              <input
                type="range"
                min="-50"
                max="100"
                value={sbcChange}
                onChange={(e) => {
                  setSbcChange(parseInt(e.target.value));
                  setScenario(null);
                }}
                className="w-full h-1 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-blue"
              />
            </div>
          </div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {isLoading ? (
            <div className="panel-operational flex flex-col items-center justify-center min-h-[450px] space-y-4">
              <RefreshCw size={24} className="animate-spin text-primary-blue" />
              <p className="text-text-secondary font-semibold animate-pulse text-xs">Simulating 2,000 Monte Carlo trials...</p>
            </div>
          ) : isError ? (
            <div className="panel-operational min-h-[450px] flex flex-col items-center justify-center text-center border-alert-red/30">
              <ShieldAlert className="text-alert-red mb-4" size={40} />
              <h4 className="text-sm font-bold text-text-primary mb-2">Simulation run failed</h4>
              <p className="text-xs text-text-secondary max-w-sm">Failed to retrieve simulation output from PJM physics model.</p>
            </div>
          ) : data ? (
            <div className="space-y-6">
              {/* Core Indicators */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono-numbers">
                <div className="panel-operational">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Base monthly bill</span>
                  <div className="text-3xl font-bold mt-2 text-text-primary">${data.base_bill.toFixed(2)}</div>
                  <span className="text-[10px] text-text-secondary block mt-1 font-sans">Estimated standard NJ tariff</span>
                </div>

                <div className="panel-operational bg-primary-blue/5 border-primary-blue/20">
                  <span className="text-[10px] font-bold text-primary-blue uppercase tracking-widest font-sans">Simulated bill mean</span>
                  <div className="text-3xl font-bold mt-2 text-primary-blue">${data.simulated_bill.toFixed(2)}</div>
                  <span className="text-[10px] text-primary-blue block mt-1 font-sans font-semibold">
                    95% Bounds: ${data.confidence_interval[0].toFixed(2)} - ${data.confidence_interval[1].toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Decomposition chart */}
              <div className="panel-chart h-[320px] flex flex-col justify-between">
                <div>
                  <span className="text-xs uppercase tracking-wider text-text-secondary">Causal factors</span>
                  <h3 className="text-sm font-bold text-text-primary mt-0.5 mb-4">Causal decomposition of bill shift ($)</h3>
                </div>
                <div className="flex-1 min-h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getDecompositionData(data.decomposition)} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                      <XAxis dataKey="name" stroke="var(--text-secondary)" fontSize={10} tickLine={false} tick={{ fill: 'var(--text-secondary)' }} />
                      <YAxis stroke="var(--text-secondary)" fontSize={10} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} />
                      <Tooltip />
                      <Bar dataKey="value" radius={[2, 2, 0, 0]} barSize={40}>
                        {getDecompositionData(data.decomposition).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* PJM Physics Data */}
              {data.pjm_physics && (
                <div className="panel-operational space-y-4">
                  <div className="flex items-center gap-2 border-b border-border-hairline pb-2 mb-2">
                    <Cpu className="text-primary-blue" size={16} />
                    <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">PJM grid physical state</h4>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono-numbers">
                    <div>
                      <span className="text-text-secondary block mb-0.5 font-sans">Marginal cost</span>
                      <strong className="text-text-primary">${data.pjm_physics.marginal_cost.toFixed(2)}/MWh</strong>
                    </div>
                    <div>
                      <span className="text-text-secondary block mb-0.5 font-sans">PSEG LMP (DA)</span>
                      <strong className="text-text-primary">${data.pjm_physics.lmp.toFixed(2)}/MWh</strong>
                    </div>
                    <div>
                      <span className="text-text-secondary block mb-0.5 font-sans">Loss factor</span>
                      <strong className="text-text-primary">{(data.pjm_physics.loss_factor * 100).toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span className="text-text-secondary block mb-0.5 font-sans">DA demand cost</span>
                      <strong className="text-text-primary">${data.pjm_physics.da_charge.toFixed(2)}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default WhatIfTab;
