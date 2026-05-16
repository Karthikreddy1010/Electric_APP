import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, 
  PieChart, Pie, Cell, Tooltip, CartesianGrid
} from 'recharts';
import { Calculator, ArrowUpRight, Layers, Filter } from 'lucide-react';

const CATEGORY_COLORS = ['#3B82F6', '#8B5CF6', '#14B8A6', '#F59E0B', '#6366F1', '#EC4899', '#10B981', '#F97316'];

const COMPONENT_METADATA: Record<string, { label: string; elasticity: number }> = {
  bgs: { label: "BGS Supply", elasticity: 0.58 },
  distribution: { label: "Distribution Charge", elasticity: 0.22 },
  transmission: { label: "Transmission Charge", elasticity: 0.13 },
  sbc: { label: "Societal Benefits Charge", elasticity: 0.045 },
  customer: { label: "Customer Charge", elasticity: 0 },
  transition: { label: "Transition Charge", elasticity: 0 }
};

const ImpactTab = () => {
  const [topN, setTopN] = useState(10);
  const [selectedComp, setSelectedComp] = useState("bgs");
  const [change, setChange] = useState(10);

  // General Impact Data
  const { data: impactData } = useQuery({
    queryKey: ['impact'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/impact');
      return res.data;
    }
  });

  // Top-N Features Data
  const { data: topFeatures, isLoading: isTopLoading } = useQuery({
    queryKey: ['top-features', topN],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/impact/top-features?n=${topN}`);
      return res.data;
    }
  });

  // Reactive Simulation Logic
  const simulation = useMemo(() => {
    const baseBill = impactData?.base_value || 191.12;
    const elasticity = COMPONENT_METADATA[selectedComp]?.elasticity || 0;
    
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

  const barData = useMemo(() => {
    if (!topFeatures) return [];
    return topFeatures.features.map((f: string, i: number) => ({
      name: f,
      value: topFeatures.shap_values[i],
      percent: topFeatures.percent_contribution[i]
    }));
  }, [topFeatures]);

  const donutData = useMemo(() => {
    if (!topFeatures) return [];
    return topFeatures.features.map((f: string, i: number) => ({
      name: f,
      value: topFeatures.percent_contribution[i]
    }));
  }, [topFeatures]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* SHAP Impact Section */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card-premium p-6">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Feature Impact (SHAP Values)</h3>
              <p className="text-xs text-slate-400 mt-1">Dollar contribution to total bill variance</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Top-N</span>
              <select 
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="bg-slate-100 border-none rounded-lg px-2 py-1 text-xs font-bold text-slate-600 outline-none cursor-pointer"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
              </select>
            </div>
          </div>
          
          <div className="h-[350px]">
            {isTopLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  data={barData} 
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
                    dataKey="name" 
                    axisLine={false}
                    tickLine={false}
                    tick={{fill: '#64748B', fontSize: 11, fontWeight: 600}}
                    width={120}
                  />
                  <Tooltip 
                    cursor={{fill: '#F8FAFC'}}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white border border-slate-100 p-3 shadow-xl rounded-xl">
                            <p className="text-xs font-black text-slate-900 mb-1">{payload[0].payload.name}</p>
                            <p className="text-sm font-bold text-blue-600">${Number(payload[0].value).toFixed(2)}</p>
                            <p className="text-[10px] text-slate-400 font-bold uppercase mt-1">Impact Magnitude</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="url(#barGradient)"
                    radius={[0, 8, 8, 0]} 
                    barSize={20}
                    label={{ 
                      position: 'right', 
                      fill: '#94A3B8', 
                      fontSize: 11, 
                      fontWeight: 700,
                      formatter: (val: any) => `$${Number(val).toFixed(0)}`
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="card-premium p-6">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Relative Contribution</h3>
              <p className="text-xs text-slate-400 mt-1">% importance among Top-{topN} features</p>
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
                  paddingAngle={4}
                  dataKey="value"
                  animationDuration={1000}
                >
                  {donutData.map((_: any, index: number) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} 
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
              <span className="text-[10px] uppercase tracking-widest font-black text-slate-400">Total Top-{topN}</span>
              <span className="text-2xl font-black text-slate-900 mt-1">Drivers</span>
            </div>
          </div>
        </div>
      </section>

      {/* Real-time Simulator Section */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl shadow-inner">
            <Calculator size={20} />
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-900">Bill Sensitivity Simulator</h3>
            <p className="text-xs text-slate-400 font-medium">Interactive "What-If" engine with real-time feedback</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 overflow-hidden rounded-[24px] border border-slate-200 shadow-2xl bg-white">
          <div className="lg:col-span-2 p-8 bg-[#F9FAFB] border-r border-slate-100">
            <div className="space-y-8">
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
              </div>

              <div className="p-4 bg-blue-50/50 rounded-2xl border border-blue-100/50">
                <p className="text-[11px] font-semibold text-blue-700 leading-relaxed italic">
                  "A {Math.abs(change)}% {change >= 0 ? 'increase' : 'decrease'} in {COMPONENT_METADATA[selectedComp]?.label || selectedComp} will {simulation.impactAbs >= 0 ? 'increase' : 'decrease'} your total bill by ${Math.abs(simulation.impactAbs).toFixed(2)} on average."
                </p>
              </div>
            </div>
          </div>

          <div className="lg:col-span-3 p-8 flex flex-col justify-center bg-white relative">
            <div className="space-y-10 animate-in fade-in duration-500">
              <div className="text-center">
                <span className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4 block">Projected Total Bill</span>
                <div className="flex items-center justify-center gap-4">
                  <span className="text-2xl font-bold text-slate-300 line-through">${simulation.baseBill.toFixed(2)}</span>
                  <div className="w-8 h-px bg-slate-200"></div>
                  <h2 className="text-6xl font-black text-slate-900 tracking-tighter">${simulation.newBill.toFixed(2)}</h2>
                </div>
              </div>

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
            </div>
          </div>
        </div>
      </section>

      {/* Reference Table */}
      <section className="card-premium p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-slate-900">Component Sensitivity Reference</h3>
          <div className="p-2 bg-slate-50 text-slate-400 rounded-lg">
            <Filter size={16} />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[11px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">
                <th className="pb-4">Utility Component</th>
                <th className="pb-4">Elasticity</th>
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
