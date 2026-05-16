import { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, 
  PieChart, Pie, Cell, Tooltip, CartesianGrid
} from 'recharts';
import { Calculator, Download, Sparkles, Filter, LayoutGrid, Info, Activity, TrendingUp, ShieldCheck } from 'lucide-react';

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
  const [viewType, setViewType] = useState<'abs' | 'signed'>('abs');
  const [selectedComp, setSelectedComp] = useState("bgs");
  const [change, setChange] = useState(10);
  const [report, setReport] = useState<string | null>(null);

  // Fetch Full Analysis (including dynamic sensitivity)
  const { data: fullAnalysis, isLoading: isAnalysisLoading } = useQuery({
    queryKey: ['impact-full-analysis'],
    queryFn: async () => {
      const res = await axios.get('/impact/full-analysis');
      return res.data;
    }
  });

  // Fetch Top-N SHAP Data
  const { data: shapData, isLoading: isShapLoading } = useQuery({
    queryKey: ['impact-top-n', topN],
    queryFn: async () => {
      const res = await axios.get(`/impact/top-features?n=${topN}`);
      return res.data;
    }
  });

  // LLM Report Mutation
  const reportMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.post('/report/generate');
      return res.data;
    },
    onSuccess: (data) => setReport(data.report_text)
  });

  // PDF Export
  const pdfMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.post('/report/pdf', {}, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'bill_analysis.pdf');
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
  });

  const chartData = useMemo(() => {
    if (!shapData) return [];
    return shapData.features.map((f: any, i: number) => {
      const rawVal = shapData.shap_values[i];
      return {
        name: f,
        value: viewType === 'abs' ? Math.abs(rawVal) : rawVal,
        percent: shapData.percent_contribution[i]
      };
    });
  }, [shapData, viewType]);

  const simulation = useMemo(() => {
    const baseBill = 191.12; // In real app, pull from API
    const elasticity = COMPONENT_METADATA[selectedComp]?.elasticity || 0;
    const impactAbs = baseBill * elasticity * (change / 100);
    const newBill = baseBill + impactAbs;
    return { baseBill, newBill, impactAbs };
  }, [selectedComp, change]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Dynamic Header with Top-N Selector */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <h2 className="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <LayoutGrid className="text-blue-600" size={28} />
            SHAP Driver Explorer
          </h2>
          <p className="text-slate-500 text-sm mt-1">Interactive ranking of bill components by marginal impact.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-2 rounded-2xl shadow-sm">
            <Filter size={14} className="text-slate-400" />
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Scope:</span>
            <select 
              value={topN} 
              onChange={(e) => setTopN(Number(e.target.value))}
              className="bg-transparent border-none text-sm font-bold text-slate-900 outline-none cursor-pointer"
            >
              <option value="5">Top 5 Features</option>
              <option value="10">Top 10 Features</option>
              <option value="15">Top 15 Features</option>
            </select>
          </div>

          <button onClick={() => reportMutation.mutate()} className="p-2.5 bg-white border border-slate-200 text-blue-600 rounded-2xl font-bold flex items-center gap-2 hover:bg-slate-50 transition-all shadow-sm">
            <Sparkles size={18} />
            <span className="hidden sm:inline">Explain Bill</span>
          </button>
          
          <button onClick={() => pdfMutation.mutate()} className="p-2.5 bg-slate-900 text-white rounded-2xl font-bold flex items-center gap-2 hover:bg-slate-800 transition-all shadow-xl shadow-slate-200">
            <Download size={18} />
            <span className="hidden sm:inline">PDF Report</span>
          </button>
        </div>
      </div>

      {/* Main Analysis Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Feature Impact (SHAP) - Dark Premium Panel */}
        <div className="card bg-slate-900 text-white border-none shadow-2xl p-8 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <Info size={120} />
          </div>
          <div className="relative z-10">
            <div className="flex justify-between items-center mb-8">
              <div>
                <h3 className="text-lg font-black tracking-tight">Feature Impact (SHAP Values)</h3>
                <p className="text-xs text-slate-400">Attribution of cost variance per component ($)</p>
              </div>
              <div className="flex bg-slate-800 p-1 rounded-xl">
                <button 
                  onClick={() => setViewType('abs')}
                  className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter transition-all ${viewType === 'abs' ? 'bg-blue-600 text-white' : 'text-slate-500'}`}
                >
                  Abs
                </button>
                <button 
                  onClick={() => setViewType('signed')}
                  className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter transition-all ${viewType === 'signed' ? 'bg-blue-600 text-white' : 'text-slate-500'}`}
                >
                  Sign
                </button>
              </div>
            </div>

            <div className="h-[400px]">
              {isShapLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1E293B" />
                    <XAxis type="number" hide />
                    <YAxis 
                      type="category" 
                      dataKey="name" 
                      axisLine={false} 
                      tickLine={false}
                      tick={{fill: '#94A3B8', fontSize: 11, fontWeight: 700}}
                      width={100}
                    />
                    <Tooltip 
                      cursor={{fill: '#1E293B'}}
                      contentStyle={{backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '12px', fontSize: '12px'}}
                    />
                    <Bar 
                      dataKey="value" 
                      radius={[0, 4, 4, 0]}
                      barSize={20}
                      animationDuration={1000}
                    >
                      {chartData.map((entry: any, index: number) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={viewType === 'abs' 
                            ? (index < 3 ? '#60A5FA' : '#3B82F6') 
                            : (entry.value >= 0 ? '#EF4444' : '#10B981')
                          } 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Right: Category Breakdown - Donut Panel */}
        <div className="card p-8 shadow-xl bg-white flex flex-col items-center">
           <div className="w-full mb-8">
              <h3 className="text-lg font-black text-slate-900 tracking-tight">Top-{topN} Contribution</h3>
              <p className="text-xs text-slate-400">Relative weight of ranked importance features</p>
           </div>

           <div className="h-[350px] w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={90}
                    outerRadius={120}
                    paddingAngle={3}
                    dataKey="percent"
                    animationDuration={1000}
                  >
                    {chartData.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Aggregate</span>
                <span className="text-2xl font-black text-slate-900 mt-1">
                  {chartData.reduce((sum: number, d: any) => sum + d.percent, 0).toFixed(0)}%
                </span>
                <span className="text-[10px] font-bold text-slate-400">of Variance</span>
              </div>
           </div>

           <div className="grid grid-cols-2 gap-x-8 gap-y-4 mt-8 w-full border-t border-slate-50 pt-8">
              {chartData.slice(0, 4).map((item: any, index: number) => (
                <div key={item.name} className="flex items-center justify-between group">
                   <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: CATEGORY_COLORS[index]}}></div>
                      <span className="text-[11px] font-bold text-slate-600 uppercase tracking-tight truncate max-w-[100px]">{item.name}</span>
                   </div>
                   <span className="text-xs font-black text-slate-900">{item.percent.toFixed(1)}%</span>
                </div>
              ))}
           </div>
        </div>
      </div>

      {/* Simulator Layer */}
      <section className="card p-8 bg-slate-50 border-dashed border-2 border-slate-200 rounded-[32px]">
        <div className="flex items-center gap-3 mb-8">
          <Calculator size={22} className="text-blue-600" />
          <h3 className="text-xl font-bold text-slate-900">What-If Sensitivity Simulator</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
           <div className="space-y-8">
              <div>
                 <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 block">Simulated Component</label>
                 <select 
                    value={selectedComp} 
                    onChange={(e) => setSelectedComp(e.target.value)}
                    className="w-full bg-white border border-slate-200 p-4 rounded-2xl text-sm font-bold text-slate-900 outline-none"
                 >
                    {Object.entries(COMPONENT_METADATA).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                 </select>
              </div>
              <div>
                 <div className="flex justify-between items-center mb-3">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Rate Change (%)</label>
                    <span className="text-sm font-black text-blue-600 bg-blue-50 px-3 py-1 rounded-lg">{change > 0 ? '+' : ''}{change}%</span>
                 </div>
                 <input 
                    type="range" 
                    min="-50" 
                    max="50" 
                    value={change} 
                    onChange={(e) => setChange(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                 />
              </div>
           </div>

           <div className="text-center p-8 bg-white rounded-3xl shadow-xl shadow-slate-100 border border-slate-100">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Projected Bill Impact</p>
              <div className="flex items-center justify-center gap-4">
                 <span className="text-xl font-bold text-slate-300 line-through">${simulation.baseBill.toFixed(2)}</span>
                 <h2 className="text-6xl font-black text-slate-900 tracking-tighter">${simulation.newBill.toFixed(2)}</h2>
              </div>
              <div className={`inline-flex items-center gap-1 mt-6 px-4 py-1.5 rounded-full text-xs font-black uppercase ${simulation.impactAbs > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                 {simulation.impactAbs > 0 ? 'Increase' : 'Decrease'} of ${Math.abs(simulation.impactAbs).toFixed(2)}
              </div>
           </div>
        </div>
      </section>
      {/* Component Sensitivity Reference */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <TrendingUp size={22} className="text-blue-600" />
          <h3 className="text-xl font-bold text-slate-900">Component Sensitivity Reference</h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="card p-8 bg-white border border-slate-100 shadow-xl lg:col-span-1 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center text-blue-600 mb-6">
                <Activity size={24} />
              </div>
              <h4 className="text-lg font-black text-slate-900 mb-3">Engine Logic</h4>
              <p className="text-sm text-slate-500 leading-relaxed mb-6">
                Sensitivity coefficients (elasticity) represent the deterministic relationship between individual component rate changes and the final bill amount. 
                Values &gt; 0.10 are considered high-impact drivers of monthly volatility.
              </p>
            </div>
            
            <div className="pt-6 border-t border-slate-50 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center text-emerald-600">
                  <ShieldCheck size={16} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Reliability Score</p>
                  <p className="text-sm font-bold text-slate-900">99.8% Deterministic</p>
                </div>
              </div>
            </div>
          </div>

          <div className="card p-0 bg-white border border-slate-100 shadow-xl lg:col-span-2 overflow-hidden">
            <div className="overflow-x-auto">
              {isAnalysisLoading ? (
                <div className="flex items-center justify-center p-12">
                   <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/50">
                      <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">Component</th>
                      <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">Primary Driver</th>
                      <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">Elasticity</th>
                      <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">Volatility Risk</th>
                      <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 text-right">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {fullAnalysis?.sensitivity?.map((item: any) => (
                      <tr key={item.component} className="hover:bg-slate-50/50 transition-colors group">
                        <td className="px-8 py-5">
                          <span className="text-sm font-bold text-slate-700 block">{item.component}</span>
                        </td>
                        <td className="px-8 py-5">
                           <span className="text-[10px] font-black px-2 py-1 rounded-md bg-slate-100 text-slate-500 uppercase tracking-tighter">
                              {item.driver}
                           </span>
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-slate-900">{(item.elasticity).toFixed(3)}</span>
                            <div className={`w-1.5 h-1.5 rounded-full ${item.elasticity > 0.4 ? 'bg-red-500 animate-pulse' : item.elasticity > 0.1 ? 'bg-amber-500' : 'bg-slate-300'}`} />
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-tight ${
                            item.impact_type === 'high' ? 'bg-red-50 text-red-600' : 
                            item.impact_type === 'medium' ? 'bg-amber-50 text-amber-600' : 
                            'bg-slate-100 text-slate-500'
                          }`}>
                            {item.impact_type}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-right max-w-[200px]">
                           <p className="text-[10px] font-medium text-slate-400 leading-tight italic truncate hover:whitespace-normal transition-all">
                              {item.reasoning}
                           </p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </section>


      {/* AI Report Fragment */}
      {report && (
        <div className="card p-8 border-l-4 border-l-blue-600 animate-in slide-in-from-left-4 duration-500">
           <h4 className="text-lg font-black text-slate-900 mb-4 flex items-center gap-2">
              <Sparkles size={20} className="text-blue-600" />
              Automated Bill Narrative
           </h4>
           <div className="text-sm text-slate-600 leading-relaxed space-y-4">
              {report.split('\n').filter(l => l.trim()).map((p, i) => <p key={i}>{p}</p>)}
           </div>
        </div>
      )}
    </div>
  );
};

export default ImpactTab;
