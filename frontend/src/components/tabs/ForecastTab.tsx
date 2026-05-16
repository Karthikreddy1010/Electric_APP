import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { Calendar, Info, ShieldCheck } from 'lucide-react';

const ForecastTab = () => {
  const [model, setModel] = useState("ensemble");
  const [range, setRange] = useState(12);

  const { data, isLoading, error } = useQuery({
    queryKey: ['forecast', model, range],
    queryFn: async () => {
      const res = await axios.get(`/forecast?horizon=${range}&model=${model}`);
      return res.data;
    }
  });

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;
  if (error) return <div className="p-8 text-red-600">Failed to generate forecast.</div>;

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
            {[12, 24].map((r) => (
              <button key={r} onClick={() => setRange(r)} className={`px-4 py-1.5 rounded-lg text-xs font-black ${range === r ? 'bg-white shadow-sm' : 'text-slate-500'}`}>{r}M</button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 card p-8">
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.forecasts}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="month" hide />
                <YAxis hide />
                <Tooltip />
                <Line type="monotone" dataKey="forecast" stroke="#2563EB" strokeWidth={3} dot={{ r: 4, fill: '#2563EB' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-6 bg-slate-900 text-white">
            <ShieldCheck className="text-emerald-400 mb-4" size={20} />
            <h3 className="text-4xl font-black">{(data.metrics.confidence_score * 100).toFixed(1)}%</h3>
            <p className="text-xs text-slate-400">Confidence Score</p>
          </div>
          <div className="card p-6">
            <Calendar className="text-blue-600 mb-4" size={18} />
            <h4 className="text-sm font-bold">Projected Peak</h4>
            <p className="text-2xl font-black">{data.forecasts[0].month}</p>
          </div>
          <div className="card p-6 border-dashed border-2">
            <Info size={16} className="text-slate-400 mb-2" />
            <p className="text-xs text-slate-500 italic">"The {model} model indicates a {data.metrics.trend_direction} trend."</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForecastTab;
