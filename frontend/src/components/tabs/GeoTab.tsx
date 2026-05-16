import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  TrendingDown, TrendingUp, Play, Pause, Map as MapIcon, Globe
} from 'lucide-react';
import { 
  ResponsiveContainer, AreaChart, Area
} from 'recharts';
import USMap from '../USMap.tsx';

const GeoTab = () => {
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [selectedState, setSelectedState] = useState('NJ');
  const [currentMonthIdx, setCurrentMonthIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const { data: geoData, isLoading, error } = useQuery({
    queryKey: ['geo', viewMode],
    queryFn: async () => {
      const res = await axios.get(`/geo?view_mode=${viewMode}`);
      return res.data;
    }
  });

  const { data: trendData } = useQuery({
    queryKey: ['geo_trend', selectedState, viewMode],
    queryFn: async () => {
      const res = await axios.get(`/geo/trend?state=${selectedState}&view_mode=${viewMode}`);
      return res.data;
    },
    enabled: !!selectedState
  });

  const { data: detailData } = useQuery({
    queryKey: ['geo_detail', selectedState, geoData?.current_month],
    queryFn: async () => {
      const res = await axios.get(`/geo/detail?state=${selectedState}&month=${geoData?.current_month}`);
      return res.data;
    },
    enabled: !!selectedState && !!geoData?.current_month
  });

  useEffect(() => {
    let interval: any;
    if (isPlaying && geoData?.available_months) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, geoData]);

  const mapValues = useMemo(() => {
    if (!geoData?.data) return [];
    return geoData.data.map((s: any) => ({
      state: s.state,
      value: viewMode === 'bill' ? s.avg_bill : s.avg_rate
    }));
  }, [geoData, viewMode]);

  const currentMonth = useMemo(() => {
    if (!geoData?.available_months) return '';
    return geoData.available_months[currentMonthIdx];
  }, [geoData, currentMonthIdx]);

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 mx-auto mt-20" />;
  if (error) return <div className="p-8 text-red-600">Failed to load geographic data.</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <Globe className="text-blue-600" size={24} />
          <h2 className="text-3xl font-black text-slate-900 tracking-tight">Geographic Insights</h2>
        </div>
        <div className="flex items-center gap-4 bg-white p-2 rounded-2xl border border-slate-100 shadow-xl">
          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button onClick={() => setViewMode('bill')} className={`px-4 py-2 rounded-lg text-xs font-black ${viewMode === 'bill' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>BILL ($)</button>
            <button onClick={() => setViewMode('rate')} className={`px-4 py-2 rounded-lg text-xs font-black ${viewMode === 'rate' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>RATE ($/kWh)</button>
          </div>
          <button onClick={() => setIsPlaying(!isPlaying)} className={`p-2 rounded-xl ${isPlaying ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'}`}>
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{currentMonth}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 card p-0 overflow-hidden relative min-h-[600px] bg-[#F8FAFC]">
          <div className="absolute top-8 left-8 z-10 p-4 bg-white/80 rounded-2xl border border-slate-100 shadow-2xl">
              <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)} className="bg-transparent border-none font-black text-lg text-slate-900 outline-none">
                {geoData?.data?.map((s: any) => <option key={s.state} value={s.state}>{s.state}</option>)}
              </select>
          </div>
          <USMap data={mapValues} selectedState={selectedState} onStateClick={setSelectedState} colorRange={viewMode === 'bill' ? ["#EFF6FF", "#1D4ED8"] : ["#F0FDF4", "#166534"]} />
          <div className="absolute bottom-8 right-8 p-6 bg-slate-900 text-white rounded-[32px] shadow-2xl min-w-[280px]">
             <div className="flex justify-between items-start mb-6">
                <h4 className="text-3xl font-black">{selectedState}</h4>
                <MapIcon size={20} className="text-white/40" />
             </div>
             {detailData && (
               <div className="space-y-4">
                  <div className="flex justify-between items-center"><span className="text-xs font-bold text-white/60">Avg. Bill</span><span className="text-xl font-black">${detailData.avg_bill.toFixed(2)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-xs font-bold text-white/60">Rate</span><span className="text-xl font-black">${detailData.avg_rate.toFixed(4)}</span></div>
               </div>
             )}
          </div>
        </div>

        <div className="space-y-6">
           <div className="card p-6 bg-gradient-to-br from-blue-600 to-blue-700 border-none shadow-xl text-white">
              <h4 className="text-[10px] font-black uppercase tracking-widest mb-4 opacity-70">State Trendline</h4>
              <div className="h-[150px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData?.months.map((m: any, i: number) => ({ month: m, val: trendData.values[i] }))}>
                       <Area type="monotone" dataKey="val" stroke="#FFF" strokeWidth={3} fill="#FFF" fillOpacity={0.1} />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>
              <div className="mt-4 flex justify-between items-end">
                 <div>
                    <p className="text-[10px] font-black opacity-60 uppercase">Period Growth</p>
                    <p className="text-2xl font-black">{trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}%</p>
                 </div>
                 {trendData?.total_growth_pct > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default GeoTab;
