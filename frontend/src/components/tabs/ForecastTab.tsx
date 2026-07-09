import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, ReferenceLine
} from 'recharts';
import { Calendar, Info, ShieldCheck } from 'lucide-react';

const ForecastTab = () => {
  const [model, setModel] = useState("ensemble");
  const [range, setRange] = useState(30);

  const { data, isLoading, error } = useQuery({
    queryKey: ['forecast', model, range],
    queryFn: async () => {
      const res = await axios.get(`/forecast?horizon=${range}&model=${model}`);
      return res.data;
    }
  });

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;
  if (error) return <div className="p-8 text-red-600">Failed to generate forecast.</div>;

  const isNaNMetrics = !data || !data.metrics || data.metrics.MAE === undefined || data.metrics.MAE === null || Number.isNaN(Number(data.metrics.MAE));

  // Find the forecast start date for the vertical separator
  const forecastStartItem = data.forecast?.find((d: any) => d.predicted_demand !== null);
  const forecastStartDate = forecastStartItem ? forecastStartItem.date : null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Electricity Demand Forecast</h2>
        <div className="flex gap-3">
          <select value={model} onChange={(e) => setModel(e.target.value)} className="bg-white border p-2 rounded-xl text-sm font-bold">
            <option value="ensemble">Ensemble Model</option>
            <option value="sarima">SARIMA</option>
            <option value="prophet">Prophet</option>
          </select>
          <div className="flex bg-slate-100 p-1 rounded-xl">
            {[7, 30].map((r) => (
              <button key={r} onClick={() => setRange(r)} className={`px-4 py-1.5 rounded-lg text-xs font-black ${range === r ? 'bg-white shadow-sm text-primary' : 'text-slate-500'}`}>{r}D</button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 card p-8 relative">
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data.forecast}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="date" tick={{fontSize: 12}} tickMargin={10} minTickGap={30} />
                {/* FIX: 4 - YAxis tickFormatter and layout label */}
                <YAxis
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`} // FIX: 4
                  label={{ 
                    value: "Demand (MW)", 
                    angle: -90, 
                    position: "insideLeft",
                    offset: -10,
                    style: { textAnchor: 'middle', fill: '#475569', fontSize: 12, fontWeight: 'bold' } // FIX: 4
                  }}
                  domain={['auto', 'auto']} // FIX: 4
                  tick={{fontSize: 12}} // FIX: 4
                />
                {/* FIX: 4 - Custom tooltip formatter */}
                <Tooltip
                  formatter={(value, name) => [
                    value ? `${Number(value).toLocaleString()} MW` : "—", // FIX: 4
                    name === "historical_demand" ? "Historical Demand" : name === "predicted_demand" ? "Predicted Demand" : name // FIX: 4
                  ]}
                  labelFormatter={(label) => `Date: ${label}`} // FIX: 4
                />
                <Area type="monotone" dataKey="upper_band" stroke="none" fill="#DBEAFE" fillOpacity={0.4} />
                <Area type="monotone" dataKey="lower_band" stroke="none" fill="#ffffff" fillOpacity={1} />
                
                <Line type="monotone" dataKey="historical_demand" stroke="#94A3B8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="predicted_demand" stroke="#2563EB" strokeWidth={3} dot={{ r: 3, fill: '#2563EB' }} />
                
                {forecastStartDate && (
                   <ReferenceLine x={forecastStartDate} stroke="#EF4444" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Forecast Start', fill: '#EF4444', fontSize: 12 }} />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
 
        <div className="space-y-6">
          <div className="card p-6 bg-slate-900 text-white">
            <ShieldCheck className="text-emerald-400 mb-4" size={20} />
            {isNaNMetrics ? (
               <h3 className="text-xl font-black text-slate-400">Insufficient data</h3>
            ) : (
               <h3 className="text-4xl font-black">{(data.confidence_score).toFixed(1)}%</h3>
            )}
            <p className="text-xs text-slate-400">Confidence Score</p>
          </div>
          <div className="card p-6">
            <Calendar className="text-blue-600 mb-4" size={18} />
            <h4 className="text-sm font-bold">Projected End</h4>
            <p className="text-xl font-black">{data.forecast && data.forecast.length > 0 ? data.forecast[data.forecast.length - 1].date : 'N/A'}</p>
          </div>
          <div className="card p-6 border-dashed border-2">
            <Info size={16} className="text-slate-400 mb-2" />
            {isNaNMetrics ? (
               <p className="text-xs text-slate-500 italic">Metrics unavailable</p>
            ) : (
               <div className="text-sm text-slate-600 space-y-2 font-medium">
                 <p className="flex justify-between"><span>MAE:</span> <span>{data.metrics.MAE.toLocaleString()}</span></p>
                 <p className="flex justify-between"><span>RMSE:</span> <span>{data.metrics.RMSE.toLocaleString()}</span></p>
                 {/* FIX: 3 - Color-code MAPE for quick interpretation */}
                 <p className="flex justify-between">
                   <span>MAPE:</span>
                   <span className={
                     data.metrics.MAPE < 5 ? "text-emerald-600 font-bold" // FIX: 3
                     : data.metrics.MAPE < 10 ? "text-amber-500 font-bold" // FIX: 3
                     : "text-rose-600 font-bold" // FIX: 3
                   }>
                     {data.metrics.MAPE?.toFixed(1)}% {/* FIX: 3 */}
                   </span>
                 </p>
               </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForecastTab;
// Force IDE cache refresh for ForecastTab types
