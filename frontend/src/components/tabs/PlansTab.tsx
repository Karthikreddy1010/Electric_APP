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

  if (isLoading) return <div className="text-slate-500 p-8">Comparing retail plans...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Retail Plan Comparison</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 card p-8">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-8">Estimated 12-Month Total</h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.plans} layout="vertical" margin={{ left: 40, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" hide />
                <YAxis dataKey="provider" type="category" axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 11, fontWeight: 600}} />
                <Tooltip />
                <Bar dataKey="simulated_annual_cost" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-6 border-2 border-primary bg-primary/5 shadow-xl shadow-primary/5">
             <div className="flex items-center gap-2 mb-4">
                <ShieldCheck className="text-primary" size={20} />
                <span className="text-[10px] font-black uppercase tracking-widest text-primary">Best Value</span>
             </div>
             <h3 className="text-xl font-bold text-slate-900 mb-1">{data.plans[0].provider}</h3>
             <p className="text-sm text-slate-500 mb-6">{data.plans[0].plan_name}</p>
             <div className="space-y-4">
                <div className="flex justify-between items-center">
                   <span className="text-xs text-slate-500">Avg. Monthly</span>
                   <span className="text-lg font-bold text-slate-900">${(data.plans[0].simulated_annual_cost / 12).toFixed(2)}</span>
                </div>
                <button className="w-full bg-primary text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:brightness-110 transition-all shadow-lg shadow-primary/20">
                   Switch Now <ArrowRight size={16} />
                </button>
             </div>
          </div>

          <div className="card p-6">
             <div className="flex items-center gap-2 mb-4">
                <Zap className="text-amber-500" size={18} />
                <h4 className="text-sm font-bold text-slate-900">Current Provider</h4>
             </div>
             <p className="text-xs text-slate-500 leading-relaxed">
                You are currently on the PSE&G Standard Offer.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlansTab;
