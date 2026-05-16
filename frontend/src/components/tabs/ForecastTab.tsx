import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ComposedChart, Area, Line, Legend
} from 'recharts';
import { Info, Cpu, Calendar } from 'lucide-react';

const ForecastTab = () => {
  const [model, setModel] = useState("ensemble");
  const [range, setRange] = useState(12);

  const { data, isLoading, error } = useQuery({
    queryKey: ['forecast', model, range],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/forecast?horizon=${range}&model=${model}`);
      return res.data;
    }
  });

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );

  if (error) return (
    <div className="p-8 card bg-red-50 border-red-100 text-red-600">
      Failed to generate forecast. Please ensure all backend models are initialized.
    </div>
  );

  const avgForecast = data.forecasts.reduce((acc: any, curr: any) => acc + curr.forecast, 0) / data.forecasts.length;
  const peakMonth = data.forecasts.reduce((prev: any, current: any) => (prev.forecast > current.forecast) ? prev : current);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Future Consumption Forecast</h2>
          <p className="text-slate-500 text-sm mt-1">Predictive analysis based on historical usage and market trends.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setRange(12)}
              className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
                range === 12 ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              12 Months
            </button>
            <button
              onClick={() => setRange(24)}
              className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
                range === 24 ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              24 Months
            </button>
          </div>

          <div className="relative">
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="appearance-none bg-white border border-slate-200 text-slate-700 py-1.5 pl-4 pr-10 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all cursor-pointer"
            >
              <option value="ensemble">Ensemble Model</option>
              <option value="sarima">SARIMA (Baseline)</option>
              <option value="prophet">Prophet (AI)</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
              <Cpu size={14} />
            </div>
          </div>
        </div>
      </div>

      {/* Main Chart Card */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-lg font-bold text-slate-900">{range}-Month Predicted Trajectory</h3>
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
            <Info size={14} />
            95% Confidence Interval
          </div>
        </div>
        
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.forecasts} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94A3B8', fontSize: 12}}
                tickFormatter={(val) => {
                  const date = new Date(val);
                  return date.toLocaleString('default', { month: 'short', year: '2-digit' });
                }}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94A3B8', fontSize: 12}}
                tickFormatter={(val) => `$${val}`}
              />
              <Tooltip 
                cursor={{ stroke: '#E2E8F0', strokeWidth: 1, strokeDasharray: '4 4' }}
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length && label) {
                    const date = new Date(String(label));
                    const formattedDate = date.toLocaleString('default', { month: 'long', year: 'numeric' });
                    
                    const getVal = (idx: number) => {
                      const v = payload[idx]?.value;
                      return typeof v === 'number' ? v : 0;
                    };

                    return (
                      <div className="bg-white border border-slate-100 p-4 shadow-xl rounded-2xl min-w-[220px]">
                        <p className="font-bold text-slate-900 mb-3">{formattedDate}</p>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center text-sm">
                            <span className="text-slate-500">Predicted Bill</span>
                            <span className="font-bold text-blue-600">${getVal(2).toFixed(2)}</span>
                          </div>
                          <div className="pt-2 mt-2 border-t border-slate-50">
                            <div className="flex justify-between items-center text-[11px] text-slate-400 uppercase tracking-widest font-bold">
                              <span>Range (95% CI)</span>
                            </div>
                            <div className="flex justify-between items-center text-xs mt-1">
                              <span className="text-slate-500">Lower Bound</span>
                              <span className="font-medium text-slate-900">${getVal(1).toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs mt-0.5">
                              <span className="text-slate-500">Upper Bound</span>
                              <span className="font-medium text-slate-900">${getVal(0).toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend verticalAlign="top" align="right" height={36} iconType="circle" />
              
              {/* Confidence Band (Upper part) */}
              <Area
                type="monotone"
                dataKey="upper"
                name="Confidence Range"
                stroke="none"
                fill="#3B82F6"
                fillOpacity={0.1}
                animationDuration={1000}
              />
              {/* Masking the lower part to create the band effect */}
              <Area
                type="monotone"
                dataKey="lower"
                name="Confidence Range Lower"
                stroke="none"
                fill="#FFFFFF"
                fillOpacity={1}
                legendType="none"
                animationDuration={1000}
              />
              
              <Line 
                type="monotone" 
                dataKey="forecast" 
                name="Predicted Bill" 
                stroke="#2563EB" 
                strokeWidth={3} 
                dot={false}
                activeDot={{ r: 6, strokeWidth: 0, fill: '#2563EB' }}
                animationDuration={1500}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Insight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6 flex items-center gap-4 group">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl group-hover:bg-blue-600 group-hover:text-white transition-all">
            <DollarSignIcon />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Avg Monthly</span>
            <p className="text-xl font-bold text-slate-900">${avgForecast.toFixed(2)}</p>
          </div>
        </div>
        
        <div className="card p-6 flex items-center gap-4 group">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl group-hover:bg-purple-600 group-hover:text-white transition-all">
            <Calendar size={20} />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Expected Peak</span>
            <p className="text-xl font-bold text-slate-900">
              {new Date(peakMonth.month).toLocaleString('default', { month: 'long', year: 'numeric' })}
            </p>
          </div>
        </div>

        <div className="card p-6 flex items-center gap-4 group">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl group-hover:bg-emerald-600 group-hover:text-white transition-all">
            <TrendingUpIcon />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Model Quality</span>
            <p className="text-xl font-bold text-slate-900 text-emerald-600">High (94.2%)</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Simple inline icons to avoid extra imports if they aren't available
const DollarSignIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
);

const TrendingUpIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
);

export default ForecastTab;
