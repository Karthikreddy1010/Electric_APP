import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Brain, CheckCircle, AlertCircle, Info } from 'lucide-react';

const TREATMENT_OPTIONS = [
  { key: 'bgs_rate', label: 'BGS Supply Rate ($/kWh)', description: 'Wholesale power supply price' },
  { key: 'distribution_rate', label: 'Distribution Rate ($/kWh)', description: 'Local grid maintenance charge' },
  { key: 'transmission_rate', label: 'Transmission Rate ($/kWh)', description: 'High-voltage delivery cost sharing' },
  { key: 'sbc_rate', label: 'Societal Benefits Charge ($/kWh)', description: 'State clean energy policy funding' },
  { key: 'nug_rate', label: 'Non-Utility Gen Rate ($/kWh)', description: 'Independent power producer recovery' }
];

const CausalTab = () => {
  const [treatment, setTreatment] = useState('bgs_rate');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['causal-impact', treatment],
    queryFn: async () => {
      const res = await axios.post('/impact/causal-v2', { treatment });
      return res.data;
    }
  });

  const getPValueColor = (p: number) => {
    if (p < 0.01) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    if (p < 0.05) return 'text-blue-600 bg-blue-50 border-blue-200';
    return 'text-slate-500 bg-slate-50 border-slate-200';
  };

  const getSignificanceLabel = (p: number) => {
    if (p < 0.01) return 'Highly Significant (p < 0.01)';
    if (p < 0.05) return 'Statistically Significant (p < 0.05)';
    return 'Not Statistically Significant (p >= 0.05)';
  };

  return (
    <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            <Brain className="text-indigo-600" size={36} /> Causal AI Insights
          </h2>
          <p className="text-slate-500 text-sm mt-2">
            Double Machine Learning (DML) causal inference to isolate the true, unconfounded impact of rate changes.
          </p>
        </div>
        <div className="hidden md:block bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
          Double ML (DML) Model
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Treatment Selector & Config */}
        <div className="card p-8 bg-white shadow-xl shadow-slate-200/50 space-y-6">
          <h3 className="text-sm font-black text-slate-950 uppercase tracking-wider border-b border-slate-100 pb-3">
            Select Billing Treatment
          </h3>
          
          <div className="space-y-3">
            {TREATMENT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setTreatment(opt.key)}
                className={`w-full text-left p-4 rounded-2xl border transition-all ${
                  treatment === opt.key
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-950 shadow-md shadow-indigo-100'
                    : 'border-slate-100 hover:border-slate-300 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <div className="font-bold text-sm">{opt.label}</div>
                <div className="text-xs text-slate-400 mt-1">{opt.description}</div>
              </button>
            ))}
          </div>
          
          <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 flex gap-3 text-xs text-slate-500">
            <Info className="text-indigo-500 shrink-0" size={16} />
            <p className="leading-relaxed">
              Standard correlations confuse weather trends with tariff rates. Our Causal DML model controls for weather (HDD/CDD), seasonality, and usage history to identify the true causal effect.
            </p>
          </div>
        </div>

        {/* Causal Estimation Results */}
        <div className="lg:col-span-2 space-y-6">
          {isLoading ? (
            <div className="card p-12 bg-white flex flex-col items-center justify-center min-h-[400px] space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              <p className="text-slate-500 font-medium animate-pulse">Fitting Double Machine Learning Estimator...</p>
            </div>
          ) : isError ? (
            <div className="card p-8 bg-rose-50 border border-rose-200 min-h-[400px] flex flex-col items-center justify-center text-center">
              <AlertCircle className="text-rose-600 mb-4" size={48} />
              <h4 className="text-lg font-bold text-slate-900 mb-2">Causal Fit Failed</h4>
              <p className="text-sm text-slate-500 max-w-md">{(error as any)?.response?.data?.detail || "Make sure the causal model is successfully trained at backend startup."}</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Primary Stat Card */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="card p-6 bg-indigo-900 text-white shadow-xl shadow-indigo-950/20">
                  <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest">Causal Impact</span>
                  <div className="text-3xl font-black mt-2">
                    ${data.causal_effect_estimate.toFixed(2)}
                  </div>
                  <span className="text-xs text-indigo-200 block mt-1">
                    per unit increase in rate
                  </span>
                </div>
                
                <div className="card p-6 bg-white border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Statistical Error</span>
                  <div className="text-3xl font-black mt-2 text-slate-900">
                    ±{data.std_error.toFixed(4)}
                  </div>
                  <span className="text-xs text-slate-500 block mt-1">
                    standard error of estimate
                  </span>
                </div>

                <div className={`card p-6 border ${getPValueColor(data.p_value)}`}>
                  <span className="text-[10px] font-bold uppercase tracking-widest block opacity-75">Significance Check</span>
                  <div className="text-lg font-black mt-2 truncate">
                    {getSignificanceLabel(data.p_value)}
                  </div>
                  <span className="text-xs block mt-1 opacity-90">
                    p-value: {data.p_value.toFixed(5)}
                  </span>
                </div>
              </div>

              {/* Confidence Interval Viz */}
              <div className="card p-8 bg-white shadow-xl shadow-slate-100">
                <h3 className="text-sm font-black text-slate-950 uppercase tracking-wider mb-6">
                  95% Confidence Interval Bounds
                </h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        {
                          name: 'Lower Bound (2.5%)',
                          value: data.ci_95[0],
                        },
                        {
                          name: 'DML Estimate',
                          value: data.causal_effect_estimate,
                        },
                        {
                          name: 'Upper Bound (97.5%)',
                          value: data.ci_95[1],
                        }
                      ]}
                      layout="vertical"
                      margin={{ left: 40, right: 40 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                      <XAxis type="number" stroke="#94A3B8" />
                      <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#475569', fontSize: 11, fontWeight: 700 }} />
                      <Tooltip />
                      <ReferenceLine x={0} stroke="#EF4444" strokeDasharray="3 3" />
                      <Bar dataKey="value" fill="#4F46E5" radius={6} barSize={24} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Interpretations */}
              <div className="card p-8 bg-white border border-slate-100 shadow-md space-y-4">
                <div className="flex items-center gap-2 border-b border-slate-50 pb-3">
                  <CheckCircle className="text-emerald-500" size={20} />
                  <h4 className="text-sm font-black text-slate-900 uppercase tracking-wider">Causal Interpretation</h4>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                  {data.interpretation}
                </p>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-xs text-slate-500 leading-relaxed">
                  <strong>Model Detail & Controls:</strong> Adjusted for confounders: <strong>{data.confounders_controlled.join(', ')}</strong>. Method: {data.method}.
                </div>
                <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-100 text-xs text-amber-700 leading-relaxed">
                  ⚠️ <strong>Model Caveat:</strong> {data.caveat}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CausalTab;
