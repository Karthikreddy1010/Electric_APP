import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';
import { Info, TrendingUp, TrendingDown, Target, Globe } from 'lucide-react';

const BenchmarkTab = () => {
  const [selectedYear, setSelectedYear] = useState('2025');
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [comparisonState, setComparisonState] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/benchmark?year=${selectedYear}`);
      return res.data;
    }
  });

  const mapData = useMemo(() => {
    if (!data) return [];
    return data.states.map((s: any) => ({
      state: s.state,
      value: s.avg_rate * 100 // cents
    }));
  }, [data]);

  const stats = useMemo(() => {
    if (!data) return null;
    const sorted = [...data.states].sort((a, b) => b.avg_rate - a.avg_rate);
    const njRank = sorted.findIndex(s => s.state === 'NJ') + 1;
    const hoveredData = hoveredState ? data.states.find((s: any) => s.state === hoveredState) : null;
    const compData = comparisonState ? data.states.find((s: any) => s.state === comparisonState) : null;

    return {
      njRank,
      totalStates: data.states.length,
      hoveredData,
      compData,
      nationalAvg: data.national_avg
    };
  }, [data, hoveredState, comparisonState]);

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );

  const nj = data.focus_state;

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Top Intelligence Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-8 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="px-3 py-1 bg-blue-50 text-blue-600 text-[10px] font-black uppercase tracking-widest rounded-lg">Market Ranking</span>
              <span className="text-slate-400 text-xs font-bold">Updated {selectedYear}</span>
            </div>
            <h3 className="text-3xl font-black text-slate-900 tracking-tight">
              NJ is the <span className="text-blue-600">#{stats?.njRank}</span> most expensive state.
            </h3>
            <p className="text-slate-500 mt-4 leading-relaxed max-w-xl">
              Your average rate of <span className="font-bold text-slate-900">${nj.avg_rate.toFixed(4)}/kWh</span> is 
              <span className={`mx-1 font-black ${nj.avg_rate > data.national_avg ? 'text-red-500' : 'text-emerald-500'}`}>
                {Math.abs((nj.avg_rate - data.national_avg) / data.national_avg * 100).toFixed(1)}% {nj.avg_rate > data.national_avg ? 'higher' : 'lower'}
              </span>
              than the national average.
            </p>
          </div>
          <div className="mt-8 flex items-center gap-6">
             <div className="flex -space-x-3">
                {[1,2,3,4].map(i => (
                  <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-slate-200"></div>
                ))}
             </div>
             <span className="text-xs font-bold text-slate-400">Used by 4,200+ NJ households</span>
          </div>
        </div>

        <div className="card p-8 bg-gradient-to-br from-slate-900 to-slate-800 border-none shadow-2xl relative overflow-hidden group">
          <Globe className="absolute -right-8 -bottom-8 text-white/5 group-hover:scale-110 transition-transform duration-1000" size={200} />
          <div className="relative z-10">
            <span className="text-[10px] font-black text-white/40 uppercase tracking-[0.2em] mb-8 block">National Benchmark</span>
            <div className="space-y-6">
              <div>
                <p className="text-xs font-bold text-white/60 mb-1">National Average Bill</p>
                <div className="flex items-end gap-2">
                  <h4 className="text-4xl font-black text-white">$138.20</h4>
                  <span className="text-emerald-400 text-xs font-black mb-1.5 flex items-center"><TrendingDown size={14} /> -2.1%</span>
                </div>
              </div>
              <div className="w-full h-px bg-white/10"></div>
              <div>
                <p className="text-xs font-bold text-white/60 mb-1">NJ Focus Avg Bill</p>
                <h4 className="text-4xl font-black text-white">${nj.avg_bill.toFixed(2)}</h4>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Interactive Map Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 card p-0 overflow-hidden relative min-h-[600px]">
          {/* Map Controls Overlay */}
          <div className="absolute top-6 left-6 z-10 flex flex-col gap-4">
            <div className="bg-white/80 backdrop-blur-md p-2 rounded-2xl border border-slate-100 shadow-xl flex items-center gap-2">
              {['2023', '2024', '2025'].map(year => (
                <button
                  key={year}
                  onClick={() => setSelectedYear(year)}
                  className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
                    selectedYear === year ? 'bg-slate-900 text-white' : 'text-slate-400 hover:text-slate-600'
                  }`}
                >
                  {year}
                </button>
              ))}
            </div>
            
            {/* Heatmap Legend */}
            <div className="bg-white/80 backdrop-blur-md p-4 rounded-2xl border border-slate-100 shadow-xl">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 block text-center">Price Intensity</span>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-[10px] font-bold text-slate-500">Low</span>
                  <div className="h-1.5 flex-1 w-24 bg-gradient-to-r from-blue-50 to-blue-700 rounded-full"></div>
                  <span className="text-[10px] font-bold text-slate-500">High</span>
                </div>
              </div>
            </div>
          </div>

          <div className="w-full h-full p-12 flex items-center justify-center bg-[#F8FAFC]">
            <USMap 
              data={mapData} 
              colorRange={["#EFF6FF", "#1D4ED8"]} 
              selectedState={comparisonState || "NJ"}
              onStateClick={(s) => setComparisonState(s === comparisonState ? null : s)}
              onStateHover={setHoveredState}
            />
          </div>

          {/* Hover Tooltip Overlay */}
          {stats?.hoveredData && (
            <div className="absolute bottom-6 left-6 bg-white border border-slate-200 p-6 rounded-[24px] shadow-2xl animate-in zoom-in-95 duration-200 min-w-[240px]">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="text-2xl font-black text-slate-900">{stats.hoveredData.state}</h4>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Selected Region</p>
                </div>
                <div className="p-2 bg-slate-50 text-slate-400 rounded-lg">
                  <Target size={16} />
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-500">Avg. Rate</span>
                  <span className="text-lg font-black text-slate-900">${stats.hoveredData.avg_rate.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-500">National Diff.</span>
                  <span className={`text-xs font-black ${stats.hoveredData.avg_rate > stats.nationalAvg ? 'text-red-500' : 'text-emerald-500'}`}>
                    {Math.abs((stats.hoveredData.avg_rate - stats.nationalAvg) / stats.nationalAvg * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Comparison Sidebar */}
        <div className="space-y-6">
          <div className="card p-6 bg-blue-600 border-none shadow-xl text-white">
            <h4 className="text-sm font-black uppercase tracking-widest mb-4 opacity-80">Quick Comparison</h4>
            <div className="space-y-4">
              <div className="p-4 bg-white/10 rounded-2xl border border-white/10">
                <div className="flex justify-between text-[10px] font-black opacity-60 uppercase mb-2">
                  <span>Primary</span>
                  <span>New Jersey</span>
                </div>
                <p className="text-xl font-black">${nj.avg_rate.toFixed(4)} <span className="text-xs font-medium opacity-60">/kWh</span></p>
              </div>
              
              <div className="flex justify-center">
                <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white/60">
                  <TrendingUp size={16} />
                </div>
              </div>

              <div className={`p-4 rounded-2xl border transition-all duration-500 ${
                stats?.compData ? 'bg-white/20 border-white/20' : 'bg-transparent border-white/10 border-dashed'
              }`}>
                {stats?.compData ? (
                  <>
                    <div className="flex justify-between text-[10px] font-black opacity-60 uppercase mb-2">
                      <span>Comparison</span>
                      <span>{stats.compData.state}</span>
                    </div>
                    <p className="text-xl font-black">${stats.compData.avg_rate.toFixed(4)} <span className="text-xs font-medium opacity-60">/kWh</span></p>
                  </>
                ) : (
                  <div className="py-4 text-center">
                    <p className="text-xs font-bold opacity-60">Click a state to compare</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Info size={16} className="text-blue-500" />
              <h4 className="text-sm font-bold text-slate-900">Regional Context</h4>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed italic">
              "Price volatility is highest in the Northeast corridor due to higher transmission maintenance costs and density-driven grid pressure."
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BenchmarkTab;
