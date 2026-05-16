import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CheckCircle2, AlertTriangle, ShieldCheck, Zap } from 'lucide-react';

const PlansTab = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/plans');
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500">Loading plan analysis...</div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-slate-900">Retail Plan Comparison</h3>
          <p className="text-slate-500 text-sm">Monte Carlo simulation of annual costs based on 10,000 scenarios.</p>
        </div>
        <div className="bg-positive/10 text-positive px-4 py-2 rounded-xl border border-positive/20 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5" />
          <span className="font-bold text-sm">Recommendation: {data.recommended}</span>
        </div>
      </div>

      <div className="card overflow-hidden border-none shadow-md">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-border">
            <tr>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Plan / Provider</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Avg. Annual Cost</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Risk (Std Dev)</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.comparison.map((plan: any) => {
              const isBest = plan.provider === data.recommended;
              const isHighRisk = plan.risk_score > 15;

              return (
                <tr key={plan.provider} className={`transition-colors ${isBest ? 'bg-blue-50/30' : 'hover:bg-slate-50'}`}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${isBest ? 'bg-primary text-white' : 'bg-slate-100 text-slate-500'}`}>
                        <Zap className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-bold text-slate-900">{plan.provider}</p>
                        <p className="text-xs text-slate-500">{(plan.rate * 100).toFixed(2)}¢ per kWh</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                      {plan.plan_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <p className="font-bold text-slate-900">${plan.expected_annual_cost.toFixed(2)}</p>
                    <p className="text-[10px] text-slate-400">P5: ${plan.p5_annual_cost.toFixed(0)} | P95: ${plan.p95_annual_cost.toFixed(0)}</p>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex flex-col items-end">
                      <span className={`text-sm font-bold ${isHighRisk ? 'text-negative' : 'text-slate-600'}`}>
                        {plan.risk_score.toFixed(1)}%
                      </span>
                      <div className="w-20 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                        <div 
                          className={`h-full ${isHighRisk ? 'bg-negative' : 'bg-primary'}`} 
                          style={{ width: `${Math.min(plan.risk_score * 2, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center">
                      {isBest && (
                        <div className="flex items-center gap-1.5 text-positive bg-positive/10 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
                          <CheckCircle2 className="w-3 h-3" />
                          Best Plan
                        </div>
                      )}
                      {isHighRisk && !isBest && (
                        <div className="flex items-center gap-1.5 text-negative bg-negative/10 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
                          <AlertTriangle className="w-3 h-3" />
                          High Risk
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="card">
          <h4 className="font-bold text-slate-900 mb-4">Why this matters?</h4>
          <p className="text-sm text-slate-600 leading-relaxed">
            Switching to the recommended plan could save you approximately <b>${data.savings_vs_default.toFixed(2)}</b> per year. 
            Fixed plans offer price stability but may be higher than average market rates. Variable plans can be cheaper but carry the risk of price spikes during extreme weather or market volatility.
          </p>
        </div>
        <div className="card bg-slate-900 text-white border-none shadow-lg">
          <h4 className="font-bold mb-4">Savings Estimate</h4>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-primary">${data.savings_vs_default.toFixed(2)}</span>
            <span className="text-slate-400">/ Year</span>
          </div>
          <div className="mt-6 pt-6 border-t border-slate-800">
            <p className="text-xs text-slate-400 italic">Based on your current usage profile and 12-month market forward curves.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlansTab;
