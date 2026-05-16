import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { ShieldCheck, Zap, ArrowRight } from 'lucide-react';

const PlansTab = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const res = await axios.get('/plans');
      return res.data;
    }
  });

  if (isLoading) return (
    <div className="flex flex-col items-center justify-center p-20 space-y-4">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p className="text-slate-500 font-medium animate-pulse">Running Monte Carlo Simulations...</p>
    </div>
  );

  if (!data || !data.comparison || data.comparison.length === 0) {
    return (
      <div className="p-12 text-center card bg-slate-50 border-dashed border-2 border-slate-200">
        <h3 className="text-lg font-bold text-slate-900 mb-2">Analysis Unavailable</h3>
        <p className="text-sm text-slate-500">We could not retrieve plan comparison data. Please ensure the backend is active.</p>
      </div>
    );
  }

  const bestPlan = data.comparison[0];
  const savings = data.savings_vs_default || 0;
  const currentCost = (bestPlan?.expected_annual_cost || 0) + savings;
  const savingsPct = currentCost > 0 ? (savings / currentCost * 100).toFixed(1) : "0.0";

  return (
    <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-4xl font-black text-slate-900 tracking-tight">Retail Plan Comparison</h2>
          <p className="text-slate-500 text-sm mt-2">Personalized simulation based on 12 months of historical consumption.</p>
        </div>
        <div className="hidden md:block bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
           Live Analysis
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 card p-8 bg-white shadow-2xl shadow-slate-200/50">
          <div className="flex justify-between items-center mb-10">
             <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Annual Cost Projections</h3>
             <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                   <div className="w-2 h-2 rounded-full bg-blue-600"></div>
                   <span className="text-[10px] font-bold text-slate-500 uppercase">Simulated Mean</span>
                </div>
             </div>
          </div>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.comparison} layout="vertical" margin={{ left: 20, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" hide domain={[0, 'auto']} />
                <YAxis 
                  dataKey="provider" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#475569', fontSize: 11, fontWeight: 800}} 
                  width={140}
                />
                <Tooltip 
                  cursor={{fill: '#F1F5F9'}}
                  contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)'}}
                />
                <Bar 
                  dataKey="expected_annual_cost" 
                  fill="#2563EB" 
                  radius={[0, 8, 8, 0]} 
                  barSize={32}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-8 border-none bg-slate-900 text-white shadow-2xl shadow-blue-900/20 relative overflow-hidden group">
             <div className="absolute -right-4 -top-4 w-32 h-32 bg-blue-600/20 rounded-full blur-3xl group-hover:bg-blue-600/30 transition-all duration-700"></div>
             
             <div className="relative z-10">
                <div className="flex items-center gap-2 mb-6">
                   <ShieldCheck className="text-blue-400" size={20} />
                   <span className="text-[10px] font-black uppercase tracking-widest text-blue-400">Best Value Pick</span>
                </div>
                <h3 className="text-3xl font-black tracking-tight mb-1">{bestPlan?.provider}</h3>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-10">{bestPlan?.plan_type}</p>
                
                <div className="space-y-6 pt-8 border-t border-white/10">
                   <div className="flex justify-between items-center">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Est. Monthly</span>
                      <span className="text-3xl font-black">${((bestPlan?.expected_annual_cost || 0) / 12).toFixed(2)}</span>
                   </div>
                   <div className="flex justify-between items-center text-emerald-400">
                      <span className="text-[10px] font-black uppercase tracking-widest">Yearly Savings</span>
                      <span className="text-lg font-black">+${savings.toFixed(2)}</span>
                   </div>
                   <button className="w-full bg-blue-600 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-2 hover:bg-blue-500 transition-all shadow-xl shadow-blue-600/20 mt-4">
                      Enroll Today <ArrowRight size={18} />
                   </button>
                </div>
             </div>
          </div>

          <div className="card p-8 bg-white border border-slate-100 shadow-lg">
             <div className="flex items-center gap-2 mb-4">
                <Zap className="text-amber-500" size={20} />
                <h4 className="text-[10px] font-black text-slate-900 uppercase tracking-widest">Analysis Result</h4>
             </div>
             <p className="text-sm text-slate-600 leading-relaxed font-medium">
                Switching from the standard tariff to <span className="text-slate-900 font-bold">{bestPlan?.provider}</span> is projected to reduce your overall cost burden by <span className="text-emerald-600 font-bold">{savingsPct}%</span>.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlansTab;
