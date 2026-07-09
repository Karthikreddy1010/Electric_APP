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

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading forecast data">
        <div className="h-10 bg-bg-surface border border-border-hairline rounded-md" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 h-96 bg-bg-surface border border-border-hairline rounded-md" />
          <div className="space-y-4">
            <div className="h-28 bg-bg-surface border border-border-hairline rounded-md" />
            <div className="h-28 bg-bg-surface border border-border-hairline rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-operational flex flex-col items-center justify-center p-12 border-alert-red/30">
        <span className="text-alert-red text-sm font-semibold">Failed to generate forecast metrics.</span>
      </div>
    );
  }

  const isNaNMetrics = !data || !data.metrics || data.metrics.MAE === undefined || data.metrics.MAE === null || Number.isNaN(Number(data.metrics.MAE));

  const forecastStartItem = data.forecast?.find((d: any) => d.predicted_demand !== null);
  const forecastStartDate = forecastStartItem ? forecastStartItem.date : null;

  return (
    <div className="space-y-6 font-sans">
      
      {/* Title block */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
            Grid demand modeling
          </span>
          <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Electricity demand forecast</h2>
          <p className="text-xs text-text-secondary mt-1">Multi-model ensemble forecasting with 95% confidence intervals.</p>
        </div>
        
        {/* Controls */}
        <div className="flex gap-3">
          <select 
            value={model} 
            onChange={(e) => setModel(e.target.value)} 
            className="bg-bg-surface border border-border-hairline px-3 py-1.5 rounded-[6px] text-xs font-semibold text-text-primary outline-none focus:border-primary-blue"
            aria-label="Select model type"
          >
            <option value="ensemble">Ensemble model</option>
            <option value="sarima">SARIMA</option>
            <option value="prophet">Prophet</option>
          </select>
          <div className="panel-control" role="group" aria-label="Select forecast range">
            {[7, 30].map((r) => (
              <button 
                key={r} 
                onClick={() => setRange(r)} 
                className={`px-3 py-1 rounded-[4px] text-[10px] font-mono-numbers focus:outline-none focus:ring-1 focus:ring-primary-blue ${
                  range === r 
                    ? 'bg-bg-surface text-primary-blue border border-border-hairline shadow-sm' 
                    : 'text-text-secondary border border-transparent hover:text-text-primary'
                }`}
                aria-label={`Forecast ${r} days`}
              >
                {r}D
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Primary forecast line chart */}
        <div className="lg:col-span-3 panel-chart h-[440px] flex flex-col justify-between">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Ensemble timeline</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5 mb-4">Historical load vs forecast range</h3>
          </div>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data.forecast} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickMargin={10} minTickGap={30} axisLine={false} tickLine={false} />
                <YAxis
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`}
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 10, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const hist = payload.find((x: any) => x.dataKey === 'historical_demand')?.value;
                      const pred = payload.find((x: any) => x.dataKey === 'predicted_demand')?.value;
                      return (
                        <div className="bg-bg-surface border border-border-hairline p-3 rounded-md text-[11px] space-y-1 shadow-md">
                          <p className="font-mono-numbers text-text-secondary">{label}</p>
                          {hist !== undefined && hist !== null && (
                            <p className="font-semibold text-text-primary">
                              Actual: <span className="font-mono-numbers text-text-secondary">{Number(hist).toLocaleString()} MW</span>
                            </p>
                          )}
                          {pred !== undefined && pred !== null && (
                            <p className="font-semibold text-text-primary">
                              Forecast: <span className="font-mono-numbers text-primary-blue">{Number(pred).toLocaleString()} MW</span>
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                  cursor={{ stroke: 'var(--border-hairline)', strokeWidth: 1 }}
                />
                <Area type="monotone" dataKey="upper_band" stroke="none" fill="var(--primary-blue)" fillOpacity={0.08} />
                <Area type="monotone" dataKey="lower_band" stroke="none" fill="var(--bg-surface)" fillOpacity={1} />
                
                <Line type="monotone" dataKey="historical_demand" stroke="var(--text-secondary)" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="predicted_demand" stroke="var(--primary-blue)" strokeWidth={2.5} dot={{ r: 2, fill: 'var(--primary-blue)', strokeWidth: 0 }} />
                
                {forecastStartDate && (
                   <ReferenceLine x={forecastStartDate} stroke="var(--alert-red)" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Forecast start', fill: 'var(--alert-red)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 text-[10px] text-text-secondary mt-2">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-text-secondary inline-block" /> Historical demand</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-primary-blue inline-block" /> Forecasted demand</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-1.5 bg-primary-blue opacity-10 inline-block" /> Confidence interval (95%)</span>
          </div>
        </div>
 
        {/* Metric widgets */}
        <div className="space-y-6">
          <div className="panel-operational flex flex-col justify-between h-[120px] relative overflow-hidden bg-bg-surface">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Confidence score</span>
                {isNaNMetrics ? (
                   <h3 className="text-xl font-bold text-text-secondary mt-2">Insufficient data</h3>
                ) : (
                   <h3 className="text-3xl font-bold font-mono-numbers text-text-primary mt-2">{(data.confidence_score).toFixed(1)}%</h3>
                )}
              </div>
              <ShieldCheck className="text-savings-green" size={20} />
            </div>
            <span className="text-[9px] text-text-secondary">Expected forecast accuracy rating</span>
          </div>

          <div className="panel-operational flex flex-col justify-between h-[120px] bg-bg-surface">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Projected end</span>
                <p className="text-lg font-bold font-mono-numbers text-text-primary mt-2">{data.forecast && data.forecast.length > 0 ? data.forecast[data.forecast.length - 1].date : 'N/A'}</p>
              </div>
              <Calendar className="text-primary-blue" size={18} />
            </div>
            <span className="text-[9px] text-text-secondary">Forecast horizon target cycle</span>
          </div>

          <div className="panel-operational flex flex-col justify-between min-h-[140px] bg-bg-surface">
            <div className="flex items-center justify-between border-b border-border-hairline pb-2 mb-2">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Evaluation metrics</span>
              <Info size={12} className="text-text-secondary" />
            </div>
            {isNaNMetrics ? (
               <p className="text-xs text-text-secondary italic">Metrics unavailable</p>
            ) : (
               <div className="text-xs text-text-primary space-y-1.5 font-semibold font-mono-numbers">
                 <p className="flex justify-between">
                   <span className="text-text-secondary font-sans font-normal">MAE:</span> 
                   <span>{data.metrics.MAE.toLocaleString()} MW</span>
                 </p>
                 <p className="flex justify-between">
                   <span className="text-text-secondary font-sans font-normal">RMSE:</span> 
                   <span>{data.metrics.RMSE.toLocaleString()} MW</span>
                 </p>
                 <p className="flex justify-between">
                   <span className="text-text-secondary font-sans font-normal">MAPE:</span>
                   <span className={
                     data.metrics.MAPE < 5 ? "text-savings-green font-bold" 
                     : data.metrics.MAPE < 10 ? "text-warning-amber font-bold" 
                     : "text-alert-red font-bold" 
                   }>
                     {data.metrics.MAPE?.toFixed(1)}%
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
