import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Sliders, ShieldAlert, Cpu } from 'lucide-react';

const PRESETS = [
  { key: 'hot_summer', label: '🔥 Hot Summer', desc: 'High CDD temperatures and peak pricing (+25% bgs_rate)' },
  { key: 'cold_winter', label: '❄️ Cold Winter', desc: 'High HDD temperatures and peak heating demand (+15% bgs_rate)' },
  { key: 'high_market', label: '⚡ High Wholesale Market', desc: 'Wholesale prices spike (+40% bgs_rate, +20% transmission_rate)' },
  { key: 'conservation', label: '🌳 Green Conservation', desc: 'Usage drops by 20% (-20% usage)' }
];

const WhatIfTab = () => {
  const [kwh, setKwh] = useState<number>(750);
  const [bgsChange, setBgsChange] = useState<number>(0);
  const [distChange, setDistChange] = useState<number>(0);
  const [transChange, setTransChange] = useState<number>(0);
  const [sbcChange, setSbcChange] = useState<number>(0);
  const [nugChange, setNugChange] = useState<number>(0);
  const [scenario, setScenario] = useState<string | null>(null);

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
    // Reset manual overrides when preset is applied to prevent confusion
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
    setKwh(750);
  };

  const getDecompositionData = (decomp: any) => {
    if (!decomp) return [];
    return [
      { name: 'Direct Price Effect', value: decomp.direct_price_effect, fill: '#3B82F6' },
      { name: 'Indirect Behavioral Effect', value: decomp.indirect_behavioral_effect, fill: '#10B981' },
      { name: 'Weather Effect', value: decomp.weather_effect, fill: '#F59E0B' },
      { name: 'Interaction Effect', value: decomp.interaction_effect, fill: '#8B5CF6' }
    ];
  };

  return (
    <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            <Sliders className="text-blue-600" size={36} /> Scenario Simulator
          </h2>
          <p className="text-slate-500 text-sm mt-2">
            Build custom rate hikes or test preset macro scenarios to simulate the impact on your bill.
          </p>
        </div>
        <button 
          onClick={clearOverrides}
          className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold px-4 py-2 rounded-xl text-xs transition-all"
        >
          Reset Simulator
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Control Panel */}
        <div className="card p-8 bg-white shadow-xl shadow-slate-200/50 space-y-6">
          <h3 className="text-sm font-black text-slate-950 uppercase tracking-wider border-b border-slate-100 pb-3">
            Parameter Controls
          </h3>

          {/* Presets */}
          <div className="space-y-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Preset Scenarios</label>
            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => handleApplyPreset(p.key)}
                  className={`p-3 text-left rounded-xl border text-xs font-bold transition-all ${
                    scenario === p.key
                      ? 'border-blue-600 bg-blue-50/50 text-blue-950'
                      : 'border-slate-100 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-100 my-6"></div>

          {/* Usage Override */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-bold">
              <span className="text-slate-500 uppercase tracking-wider text-[10px]">Monthly Consumption</span>
              <span className="text-slate-950">{kwh} kWh</span>
            </div>
            <input
              type="range"
              min="100"
              max="4000"
              step="50"
              value={kwh}
              onChange={(e) => {
                setKwh(parseInt(e.target.value));
                setScenario(null); // Clear preset to indicate manual
              }}
              className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          {/* Rate Sliders */}
          <div className="space-y-4 pt-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Manual Rate Adjustments</label>
            
            {/* BGS */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-600">BGS Supply Charge</span>
                <span className={bgsChange > 0 ? 'text-rose-600' : bgsChange < 0 ? 'text-emerald-600' : 'text-slate-500'}>
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
                className="w-full h-1 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>

            {/* Distribution */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-600">Distribution Charge</span>
                <span className={distChange > 0 ? 'text-rose-600' : distChange < 0 ? 'text-emerald-600' : 'text-slate-500'}>
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
                className="w-full h-1 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>

            {/* Transmission */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-600">Transmission Charge</span>
                <span className={transChange > 0 ? 'text-rose-600' : transChange < 0 ? 'text-emerald-600' : 'text-slate-500'}>
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
                className="w-full h-1 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>

            {/* SBC */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-600">Societal Benefits Charge</span>
                <span className={sbcChange > 0 ? 'text-rose-600' : sbcChange < 0 ? 'text-emerald-600' : 'text-slate-500'}>
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
                className="w-full h-1 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>
          </div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {isLoading ? (
            <div className="card p-12 bg-white flex flex-col items-center justify-center min-h-[450px] space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-slate-500 font-medium animate-pulse">Simulating 2,000 Monte Carlo Trials...</p>
            </div>
          ) : isError ? (
            <div className="card p-8 bg-rose-50 border border-rose-200 min-h-[450px] flex flex-col items-center justify-center text-center">
              <ShieldAlert className="text-rose-600 mb-4" size={48} />
              <h4 className="text-lg font-bold text-slate-900 mb-2">Simulation Run Failed</h4>
              <p className="text-sm text-slate-500 max-w-md">Failed to retrieve simulation output from PJM physics model.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Core Indicators */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="card p-6 bg-white border border-slate-100 shadow-lg">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Base Monthly Bill</span>
                  <div className="text-4xl font-black mt-2 text-slate-900">${data.base_bill.toFixed(2)}</div>
                  <span className="text-xs text-slate-400 block mt-1">Estimated standard NJ tariff</span>
                </div>

                <div className="card p-6 bg-blue-900 text-white shadow-xl shadow-blue-950/20 relative overflow-hidden">
                  <div className="absolute -right-4 -top-4 w-24 h-24 bg-blue-600/30 rounded-full blur-2xl"></div>
                  <span className="text-[10px] font-bold text-blue-300 uppercase tracking-widest">Simulated Bill Mean</span>
                  <div className="text-4xl font-black mt-2">${data.simulated_bill.toFixed(2)}</div>
                  <span className="text-xs text-blue-200 block mt-1">
                    95% Bounds: ${data.confidence_interval[0].toFixed(2)} - ${data.confidence_interval[1].toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Decomposition chart */}
              <div className="card p-8 bg-white shadow-lg border border-slate-100">
                <h3 className="text-sm font-black text-slate-950 uppercase tracking-wider mb-6">
                  Causal Decomposition of Bill Shift ($)
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getDecompositionData(data.decomposition)}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                      <XAxis dataKey="name" stroke="#94A3B8" fontSize={10} tickLine={false} />
                      <YAxis stroke="#94A3B8" fontSize={11} />
                      <Tooltip />
                      <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={40}>
                        {getDecompositionData(data.decomposition).map((entry: any, index) => (
                          <Bar key={`cell-${index}`} dataKey="value" fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* PJM Physics Data */}
              {data.pjm_physics && (
                <div className="card p-6 bg-slate-50 border border-slate-200 shadow-md">
                  <div className="flex items-center gap-2 mb-4">
                    <Cpu className="text-blue-600" size={20} />
                    <h4 className="text-[10px] font-black text-slate-900 uppercase tracking-widest">PJM Grid Physical State</h4>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                    <div>
                      <span className="text-slate-400 block mb-0.5">Marginal Cost</span>
                      <strong className="text-slate-800">${data.pjm_physics.marginal_cost.toFixed(2)}/MWh</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block mb-0.5">PSEG LMP (DA)</span>
                      <strong className="text-slate-800">${data.pjm_physics.lmp.toFixed(2)}/MWh</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block mb-0.5">Loss Factor</span>
                      <strong className="text-slate-800">{(data.pjm_physics.loss_factor * 100).toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block mb-0.5">DA Demand Cost</span>
                      <strong className="text-slate-800">${data.pjm_physics.da_charge.toFixed(2)}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WhatIfTab;
