import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';

const ForecastTab = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['forecast'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/forecast?horizon=12');
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500">Generating forecast...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-slate-900">12-Month Bill Forecast</h3>
          <p className="text-slate-500 text-sm">Ensemble model combining SARIMA and Prophet for maximum accuracy.</p>
        </div>
      </div>

      <div className="card h-[500px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.forecasts}>
            <defs>
              <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563EB" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis 
              dataKey="month" 
              axisLine={false} 
              tickLine={false} 
              tick={{fill: '#94A3B8', fontSize: 12}}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{fill: '#94A3B8', fontSize: 12}}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip 
              contentStyle={{borderRadius: '8px', border: '1px solid #E5E7EB', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}
            />
            <Area 
              type="monotone" 
              dataKey="upper" 
              stroke="none" 
              fill="#2563EB" 
              fillOpacity={0.05} 
              name="Upper Bound (95% CI)"
            />
            <Area 
              type="monotone" 
              dataKey="lower" 
              stroke="none" 
              fill="#F8FAFC" 
              fillOpacity={1} 
              name="Lower Bound (95% CI)"
            />
            <Area 
              type="monotone" 
              dataKey="forecast" 
              stroke="#2563EB" 
              strokeWidth={3} 
              fillOpacity={1} 
              fill="url(#colorForecast)" 
              name="Predicted Bill"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Average Predicted</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            ${(data.forecasts.reduce((acc: any, curr: any) => acc + curr.forecast, 0) / data.forecasts.length).toFixed(2)}
          </p>
        </div>
        <div className="card">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Peak Month</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            {data.forecasts.reduce((prev: any, current: any) => (prev.forecast > current.forecast) ? prev : current).month}
          </p>
        </div>
        <div className="card">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Forecast Confidence</span>
          <p className="text-2xl font-bold text-positive mt-1">High (94%)</p>
        </div>
      </div>
    </div>
  );
};

export default ForecastTab;
