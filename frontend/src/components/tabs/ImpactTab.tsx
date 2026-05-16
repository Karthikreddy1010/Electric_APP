import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, 
  PieChart, Pie, Cell, Tooltip, CartesianGrid
} from 'recharts';
import { Calculator, ArrowUpRight, Zap, Layers } from 'lucide-react';

const CATEGORY_COLORS = {
  generation: '#3B82F6',
  transmission: '#14B8A6',
  distribution: '#8B5CF6',
  taxes: '#F59E0B'
};

const COMPONENT_METADATA: Record<string, { label: string; elasticity: number }> = {
  bgs: { label: "BGS Supply", elasticity: 0.58 },
  distribution: { label: "Distribution Charge", elasticity: 0.22 },
  transmission: { label: "Transmission Charge", elasticity: 0.13 },
  sbc: { label: "Societal Benefits Charge", elasticity: 0.045 },
  customer: { label: "Customer Charge", elasticity: 0 },
  transition: { label: "Transition Charge", elasticity: 0 }
};

const ImpactTab = () => {
  const [selectedComp, setSelectedComp] = useState("bgs");
  const [change, setChange] = useState(10);
  const [kwh, setKwh] = useState<number>(950);

  const { data: impactData } = useQuery({
    queryKey: ['impact'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/impact');
      return res.data;
    }
  });

  // Reactive Simulation Logic
  const simulation = useMemo(() => {
    const baseBill = impactData?.base_value || 191.12;
    const elasticity = COMPONENT_METADATA[selectedComp].elasticity;
    
    // Simple elasticity-based impact: Bill * Elasticity * %Change
    const impactAbs = baseBill * elasticity * (change / 100);
    const newBill = baseBill + impactAbs;
    const impactPct = (impactAbs / baseBill) * 100;

    return {
      baseBill,
      newBill,
      impactAbs,
      impactPct
    };
  }, [impactData, selectedComp, change]);

  const donutData = impactData ? Object.entries(impactData.category_impacts).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value
  })) : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Drivers Section */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card-premium p-6">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Impact by Component</h3>
              <p className="text-xs text-slate-400 mt-1">Relative contribution to total bill variance</p>
            </div>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <Zap size={18} />
            </div>
          </div>
          
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={impactData?.top_drivers || []} 
                layout="vertical" 
                margin={{ left: 10, right: 60, top: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#3B82F6" />
                    <stop offset="100%" stopColor="#6366F1" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" hide />
                <YAxis 
                  type="category" 
                  dataKey="feature" 
                  axisLine={false}
                  tickLine={false}
                  tick={{fill: '#64748B', fontSize: 11, fontWeight: 600}}
                  width={120}
                />
                <Tooltip 
                  cursor={{fill: '#F8FAFC'}}
                  contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                />
                <Bar 
                  dataKey="shap_value" 
                  fill="url(#barGradient)"
                  radius={[0, 8, 8, 0]} 
                  barSize={24}
                  label={{ position: 'right', fill: '#94A3B8', fontSize: 11, fontWeight: 700 }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card-premium p-6">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Cost Distribution</h3>
              <p className="text-xs text-slate-400 mt-1">Category breakdown by percentage</p>
            </div>
          </div>
          
          <div className="h-[300px] relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={8}
                  dataKey="value"
                  animationBegin={200}
                  animationDuration={1200}
                >
                  {donutData.map((_, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={Object.values(CATEGORY_COLORS)[index % 4]} 
                      stroke="rgba(255,255,255,0.2)"
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-3xl font-black text-slate-900">100%</span>
              <span className="text-[10px] uppercase tracking-widest font-bold text-slate-400">Allocated</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
              <div key={cat} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: color}}></div>
                <span className="text-xs font-semibold text-slate-500 capitalize">{cat}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Real-time Simulator Section */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl shadow-inner">
              <Calculator size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-slate-900">Bill Sensitivity Simulator</h3>
              <p className="text-xs text-slate-400 font-medium">Interactive "What-If" engine with real-time feedback</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 overflow-hidden rounded-[24px] border border-slate-200 shadow-2xl bg-white">
          {/* Left Panel: Reactive Inputs */}
          <div className="lg:col-span-2 p-8 bg-[#F9FAFB] border-r border-slate-100">
            <div className="space-y-8">
              {/* Component Selector */}
              <div>
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3 block">Target Component</label>
                <div className="relative group">
                  <select 
                    value={selectedComp}
                    onChange={(e) => setSelectedComp(e.target.value)}
                    className="w-full bg-white border border-slate-200 p-4 rounded-2xl text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-blue-500/20 transition-all appearance-none cursor-pointer"
                  >
                    {Object.entries(COMPONENT_METADATA).map(([key, meta]) => (
                      <option key={key} value={key}>{meta.label}</option>
                    ))}
                  </select>
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                    <Layers size={18} />
                  </div>
                </div>
              </div>

              {/* Change Slider */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Rate Modification</label>
                  <span className={`px-4 py-1.5 rounded-xl text-sm font-black shadow-sm transition-all duration-300 ${
                    change > 0 ? 'bg-red-50 text-red-600' : change < 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-400'
                  }`}>
                    {change > 0 ? '+' : ''}{change}%
                  </span>
                </div>
                <input 
                  type="range" 
                  min="-50" 
                  max="50" 
                  step="1"
                  value={change}
                  onChange={(e) => setChange(Number(e.target.value))}
                  className={`w-full h-2.5 rounded-lg appearance-none cursor-pointer transition-all ${
                    change > 0 ? 'accent-red-500 bg-red-100' : 'accent-emerald-500 bg-emerald-100'
                  }`}
                />
                <div className="flex justify-between mt-3 text-[10px] font-black text-slate-400 uppercase tracking-tight">
                  <span>-50% Decrease</span>
                  <span>Neutral</span>
                  <span>+50% Increase</span>
                </div>
              </div>

              {/* Usage Toggle */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Usage Context</label>
                  <span className="text-xs font-bold text-blue-600">{kwh} kWh</span>
                </div>
                <input 
                  type="range" 
                  min="100" 
                  max="2500" 
                  step="50"
                  value={kwh}
                  onChange={(e) => setKwh(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-400"
                />
              </div>

              <div className="p-4 bg-blue-50/50 rounded-2xl border border-blue-100/50">
                <p className="text-[11px] font-semibold text-blue-700 leading-relaxed italic">
                  "A {Math.abs(change)}% {change >= 0 ? 'increase' : 'decrease'} in {COMPONENT_METADATA[selectedComp].label} will {simulation.impactAbs >= 0 ? 'increase' : 'decrease'} your total bill by ${Math.abs(simulation.impactAbs).toFixed(2)} on average."
                </p>
              </div>
            </div>
          </div>

          {/* Right Panel: Live Results */}
          <div className="lg:col-span-3 p-8 flex flex-col justify-center bg-white relative">
            <div className="space-y-10 animate-in fade-in duration-500">
              {/* Primary Metric */}
              <div className="text-center">
                <span className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4 block">Projected Total Bill</span>
                <div className="flex items-center justify-center gap-4">
                  <span className="text-2xl font-bold text-slate-300 line-through">${simulation.baseBill.toFixed(2)}</span>
                  <div className="w-8 h-px bg-slate-200"></div>
                  <h2 className="text-6xl font-black text-slate-900 tracking-tighter">${simulation.newBill.toFixed(2)}</h2>
                </div>
              </div>

              {/* Impact Indicators */}
              <div className="grid grid-cols-2 gap-8 max-w-sm mx-auto">
                <div className="text-center p-6 rounded-3xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 block">Abs. Impact</span>
                  <p className={`text-2xl font-black ${simulation.impactAbs > 0 ? 'text-red-600' : simulation.impactAbs < 0 ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {simulation.impactAbs > 0 ? '+' : ''}${simulation.impactAbs.toFixed(2)}
                  </p>
                </div>
                <div className="text-center p-6 rounded-3xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 block">Relative</span>
                  <p className={`text-2xl font-black ${simulation.impactPct > 0 ? 'text-red-600' : simulation.impactPct < 0 ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {simulation.impactPct > 0 ? '+' : ''}{simulation.impactPct.toFixed(2)}%
                  </p>
                </div>
              </div>

              {/* Comparison Visual */}
              <div className="h-16 w-full max-w-md mx-auto relative group">
                <div className="absolute inset-0 bg-slate-100 rounded-full h-3 top-1/2 -translate-y-1/2"></div>
                {/* Base Marker */}
                <div className="absolute left-1/2 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-slate-300"></div>
                {/* Impact Bar */}
                <div 
                  className={`absolute top-1/2 -translate-y-1/2 h-3 rounded-full transition-all duration-300 ${
                    simulation.impactAbs > 0 ? 'bg-red-400' : 'bg-emerald-400'
                  }`}
                  style={{
                    left: simulation.impactAbs >= 0 ? '50%' : `${50 + (simulation.impactPct * 2)}%`,
                    width: `${Math.abs(simulation.impactPct * 2)}%`,
                    minWidth: '4px'
                  }}
                ></div>
                <div className="flex justify-between mt-8 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  <span>-25% Change</span>
                  <span>Current Baseline</span>
                  <span>+25% Change</span>
                </div>
              </div>
            </div>

            {/* Premium Button */}
            <div className="mt-12 flex justify-center">
              <button 
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-black rounded-2xl hover:scale-105 hover:shadow-2xl hover:shadow-blue-200 transition-all active:scale-95 flex items-center gap-3 shadow-xl"
              >
                Save Sensitivity Report
                <ArrowUpRight size={20} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Details Table */}
      <section className="card-premium p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-6">Component Sensitivity Reference</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[11px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">
                <th className="pb-4">Utility Component</th>
                <th className="pb-4">Elasticity (B_coeff)</th>
                <th className="pb-4">Sensitivity</th>
                <th className="pb-4">Impact Direction</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {Object.entries(COMPONENT_METADATA).map(([key, meta]) => (
                <tr key={key} className="group hover:bg-slate-50 transition-colors cursor-default">
                  <td className="py-4 text-sm font-bold text-slate-700">{meta.label}</td>
                  <td className="py-4 font-mono text-sm text-slate-500">{meta.elasticity.toFixed(3)}</td>
                  <td className="py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full max-w-[100px]">
                        <div className="h-full bg-blue-500 rounded-full" style={{width: `${meta.elasticity * 100}%`}}></div>
                      </div>
                      <span className="text-xs font-black text-slate-900">{(meta.elasticity * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="py-4">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-tight bg-blue-50 text-blue-600">
                      <ArrowUpRight size={12} />
                      Positive
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default ImpactTab;
