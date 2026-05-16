import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine
} from 'recharts';

const BenchmarkTab = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['benchmark'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/benchmark');
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500">Loading benchmark data...</div>;

  const sortedStates = [...data.states].sort((a, b) => b.avg_rate - a.avg_rate);
  const nj = data.focus_state;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div>
          <h3 className="text-2xl font-bold text-slate-900 mb-2">National Rate Comparison</h3>
          <p className="text-slate-500 leading-relaxed">
            NJ ranks among the higher cost states for electricity. 
            Your current rate of <b>${nj.avg_rate.toFixed(4)}/kWh</b> is 
            <span className={nj.avg_rate > data.national_avg ? 'text-negative font-bold' : 'text-positive font-bold'}>
              {' '}{Math.abs((nj.avg_rate - data.national_avg) / data.national_avg * 100).toFixed(1)}% {nj.avg_rate > data.national_avg ? 'above' : 'below'}
            </span> the national average of ${data.national_avg.toFixed(4)}/kWh.
          </p>
        </div>
        <div className="card bg-slate-50 border-none flex justify-around py-8 text-center">
          <div>
            <span className="text-xs font-medium text-slate-500 uppercase">NJ Average Bill</span>
            <p className="text-3xl font-bold text-slate-900 mt-1">${nj.avg_bill.toFixed(2)}</p>
          </div>
          <div className="w-px bg-slate-200"></div>
          <div>
            <span className="text-xs font-medium text-slate-500 uppercase">National Avg Bill</span>
            <p className="text-3xl font-bold text-slate-400 mt-1">$138.20</p>
          </div>
        </div>
      </div>

      <div className="card h-[400px]">
        <h4 className="text-sm font-semibold text-slate-500 mb-6 uppercase tracking-wider">Electricity Rates by State ($/kWh)</h4>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sortedStates}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis 
              dataKey="state" 
              axisLine={false} 
              tickLine={false} 
              tick={{fill: '#94A3B8', fontSize: 10}}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{fill: '#94A3B8', fontSize: 12}}
            />
            <Tooltip 
              cursor={{fill: '#F8FAFC'}}
              contentStyle={{borderRadius: '8px', border: '1px solid #E5E7EB'}}
            />
            <ReferenceLine y={data.national_avg} stroke="#94A3B8" strokeDasharray="3 3" label={{ value: 'National Avg', position: 'right', fill: '#94A3B8', fontSize: 10 }} />
            <Bar dataKey="avg_rate" name="Rate ($/kWh)" radius={[2, 2, 0, 0]}>
              {sortedStates.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.state === 'NJ' ? '#2563EB' : '#E2E8F0'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default BenchmarkTab;
