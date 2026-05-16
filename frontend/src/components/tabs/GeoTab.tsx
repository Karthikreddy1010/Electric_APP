import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  TrendingDown, TrendingUp, Play, Pause, RotateCcw
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import USMap from '../USMap.tsx';

const GeoTab = () => {
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [selectedState, setSelectedState] = useState('NJ');
  const [currentMonthIdx, setCurrentMonthIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const { data: geoData, isLoading } = useQuery({
    queryKey: ['geo', viewMode],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/geo?view_mode=${viewMode}`);
      return res.data;
    }
  });

  const { data: trendData } = useQuery({
    queryKey: ['geo_trend', selectedState, viewMode],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/geo/trend?state=${selectedState}&view_mode=${viewMode}`);
      return res.data;
    },
    enabled: !!selectedState
  });

  const { data: detailData } = useQuery({
    queryKey: ['geo_detail', selectedState, geoData?.current_month],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/geo/detail?state=${selectedState}&month=${geoData?.current_month}`);
      return res.data;
    },
    enabled: !!selectedState && !!geoData?.current_month
  });

  useEffect(() => {
    let interval: any;
    if (isPlaying && geoData) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, geoData]);

  if (isLoading) return <div className="text-slate-500 p-8">Initializing geographic data...</div>;

  const mapValues = geoData.data.map((s: any) => ({
    state: s.state,
    value: viewMode === 'bill' ? s.avg_bill : s.avg_rate
  }));

  const currentMonth = geoData.available_months[currentMonthIdx];

  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col md:flex-row items-center gap-6 bg-white p-4 rounded-xl border border-border shadow-sm">
        <div className="flex bg-slate-100 p-1 rounded-lg">
          <button 
            onClick={() => setViewMode('bill')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'bill' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Avg Bill ($)
          </button>
          <button 
            onClick={() => setViewMode('rate')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'rate' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Avg Price ($/kWh)
          </button>
        </div>

        <div className="flex-1 flex items-center gap-4 w-full">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap">Timeline: {currentMonth}</span>
          <div className="flex-1 h-1.5 bg-slate-100 rounded-full relative group">
            <input 
              type="range"
              min="0"
              max={geoData.available_months.length - 1}
              value={currentMonthIdx}
              onChange={(e) => {
                setCurrentMonthIdx(parseInt(e.target.value));
                setIsPlaying(false);
              }}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            />
            <div 
              className="absolute top-0 left-0 h-full bg-primary rounded-full"
              style={{ width: `${(currentMonthIdx / (geoData.available_months.length - 1)) * 100}%` }}
            ></div>
            <div 
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-primary rounded-full shadow-md"
              style={{ left: `${(currentMonthIdx / (geoData.available_months.length - 1)) * 100}%`, transform: `translate(-50%, -50%)` }}
            ></div>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-2 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors"
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
            </button>
            <button 
              onClick={() => {setCurrentMonthIdx(0); setIsPlaying(false);}}
              className="p-2 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Map Side */}
        <div className="lg:col-span-2 card p-0 overflow-hidden min-h-[500px] flex items-center justify-center bg-slate-50/30">
          <USMap 
            data={mapValues} 
            selectedState={selectedState}
            onStateClick={setSelectedState}
            colorRange={viewMode === 'bill' ? ["#BFDBFE", "#1E40AF"] : ["#BBF7D0", "#166534"]}
          />
        </div>

        {/* Info Side */}
        <div className="space-y-6">
          {/* Regional Trend */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-tight">Regional Trend</h4>
              <span className="text-[10px] bg-slate-100 px-2 py-1 rounded text-slate-500 font-bold">{selectedState}</span>
            </div>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData?.months.map((m: any, i: number) => ({ month: m, val: trendData.values[i] }))}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="month" hide />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                    labelStyle={{fontSize: '10px', color: '#94A3B8'}}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="val" 
                    stroke="#2563EB" 
                    strokeWidth={3} 
                    dot={false}
                    animationDuration={500}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-slate-400">Period Growth</span>
              <span className={`text-sm font-bold ${trendData?.total_growth_pct > 0 ? 'text-negative' : 'text-positive'}`}>
                {trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}%
              </span>
            </div>
          </div>

          {/* Region Detail */}
          <div className="card bg-slate-900 text-white border-none">
            <h4 className="text-sm font-bold text-slate-400 mb-6 uppercase tracking-widest">Region Detail: <span className="text-white">{selectedState}</span></h4>
            {detailData ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Monthly Bill</span>
                    <span className="text-xl font-bold">${detailData.avg_bill.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Price per kWh</span>
                    <span className="text-xl font-bold">${detailData.avg_rate.toFixed(4)}</span>
                  </div>
                </div>
                <div className="pt-4 border-t border-slate-800">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Component Breakdown</span>
                  </div>
                  <div className="space-y-3">
                    {Object.entries(detailData.components || {}).map(([name, val]: [string, any]) => (
                      <div key={name} className="flex justify-between items-center text-xs">
                        <span className="text-slate-400 capitalize">{name}</span>
                        <span className="font-mono text-slate-300">${val.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-slate-500 text-sm italic">Select a state on the map for details</div>
            )}
          </div>
        </div>
      </div>

      {/* Extreme Rankings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="card border-l-4 border-l-negative">
          <div className="flex items-center gap-2 mb-4 text-negative">
            <TrendingUp className="w-5 h-5" />
            <h4 className="font-bold uppercase text-xs tracking-widest">Most Expensive ({currentMonth})</h4>
          </div>
          <div className="space-y-4">
            {geoData.top_5_expensive.map((state: any, i: number) => (
              <div key={state.state} className="flex justify-between items-center">
                <span className="text-sm font-medium text-slate-600">{i + 1}. {state.state}</span>
                <span className="font-bold text-slate-900">${state.avg_bill.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card border-l-4 border-l-positive">
          <div className="flex items-center gap-2 mb-4 text-positive">
            <TrendingDown className="w-5 h-5" />
            <h4 className="font-bold uppercase text-xs tracking-widest">Most Affordable ({currentMonth})</h4>
          </div>
          <div className="space-y-4">
            {geoData.top_5_cheapest.map((state: any, i: number) => (
              <div key={state.state} className="flex justify-between items-center">
                <span className="text-sm font-medium text-slate-600">{i + 1}. {state.state}</span>
                <span className="font-bold text-slate-900">${state.avg_bill.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeoTab;
