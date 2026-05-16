import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer
} from 'recharts';
import { Info, Calculator, AlertCircle } from 'lucide-react';

const ImpactTab = () => {
  const [modifications, setModifications] = useState<Record<string, number>>({ bgs_rate: 10 });
  const [kwh, setKwh] = useState<number>(750);

  const { data: impactData } = useQuery({
    queryKey: ['impact'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/impact');
      return res.data;
    }
  });

  const mutation = useMutation({
    mutationFn: async (vars: { modifications: any, kwh: number }) => {
      const res = await axios.post('http://localhost:8000/simulate', vars);
      return res.data;
    }
  });

  const handleSimulate = () => {
    mutation.mutate({ modifications, kwh });
  };

  return (
    <div className="space-y-8">
      {/* Drivers Section */}
      <section>
        <h3 className="text-xl font-bold text-slate-900 mb-2">What’s Driving Your Bill</h3>
        <p className="text-slate-500 mb-6 text-sm">Key components contributing to your monthly costs based on historical analysis.</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="card">
            <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">Impact by Component</h4>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  data={impactData?.top_drivers || []} 
                  layout="vertical" 
                  margin={{ left: 100, right: 40 }}
                >
                  <XAxis type="number" hide />
                  <YAxis 
                    type="category" 
                    dataKey="feature" 
                    axisLine={false}
                    tickLine={false}
                    tick={{fill: '#475569', fontSize: 12}}
                  />
                  <Bar dataKey="shap_value" radius={[0, 4, 4, 0]} barSize={20} fill="#2563EB" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">Impact by Category</h4>
            <div className="space-y-6">
              {Object.entries(impactData?.category_impacts || {}).map(([cat, val]: [string, any]) => (
                <div key={cat}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-slate-700 capitalize">{cat}</span>
                    <span className="text-sm font-bold text-slate-900">{val}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${val}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Impact Simulator Section */}
      <section>
        <div className="flex items-center gap-2 mb-6">
          <Calculator className="w-6 h-6 text-primary" />
          <h3 className="text-xl font-bold text-slate-900">Impact Simulator</h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Inputs */}
          <div className="card space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Usage (kWh)</label>
              <input 
                type="number" 
                value={kwh}
                onChange={(e) => setKwh(Number(e.target.value))}
                className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">BGS Rate Change (%)</label>
              <div className="flex items-center gap-4">
                <input 
                  type="range" 
                  min="-50" 
                  max="50" 
                  value={modifications.bgs_rate}
                  onChange={(e) => setModifications({ ...modifications, bgs_rate: Number(e.target.value) })}
                  className="flex-1 accent-primary"
                />
                <span className={`w-12 text-right font-mono font-bold ${modifications.bgs_rate > 0 ? 'text-negative' : 'text-positive'}`}>
                  {modifications.bgs_rate > 0 ? '+' : ''}{modifications.bgs_rate}%
                </span>
              </div>
            </div>
            <button 
              onClick={handleSimulate}
              disabled={mutation.isPending}
              className="w-full bg-primary text-white font-semibold py-3 rounded-xl hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {mutation.isPending ? 'Simulating...' : 'Run Simulation'}
            </button>
          </div>

          {/* Results */}
          <div className="lg:col-span-2 space-y-6">
            {mutation.data ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="card text-center">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Before</span>
                    <p className="text-2xl font-bold text-slate-400 mt-1">${mutation.data.old_bill.toFixed(2)}</p>
                  </div>
                  <div className="card text-center border-primary bg-blue-50/30">
                    <span className="text-xs font-medium text-primary uppercase tracking-wider">After</span>
                    <p className="text-2xl font-bold text-slate-900 mt-1">${mutation.data.new_bill.toFixed(2)}</p>
                  </div>
                  <div className="card text-center">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Delta</span>
                    <p className={`text-2xl font-bold mt-1 ${mutation.data.delta_abs > 0 ? 'text-negative' : 'text-positive'}`}>
                      {mutation.data.delta_abs > 0 ? '+' : ''}${Math.abs(mutation.data.delta_abs).toFixed(2)} 
                      <span className="text-sm ml-1">({mutation.data.delta_pct}%)</span>
                    </p>
                  </div>
                </div>

                <div className="card bg-slate-50 border-none">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-2">Calculation Logic</p>
                      <code className="text-xs bg-white border border-border px-2 py-1 rounded text-slate-600 block mb-3">
                        {mutation.data.formula}
                      </code>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {mutation.data.explanation}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="card h-full flex flex-col items-center justify-center text-slate-400 border-dashed border-2 bg-transparent">
                <AlertCircle className="w-12 h-12 mb-4 opacity-20" />
                <p>Modify inputs and run simulation to see results</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

export default ImpactTab;
