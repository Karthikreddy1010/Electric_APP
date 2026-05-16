import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';
import { Info, TrendingDown, Globe } from 'lucide-react';

const BenchmarkTab = () => {
  const [selectedYear, setSelectedYear] = useState('2025');
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [comparisonState, setComparisonState] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`/benchmark?year=${selectedYear}`);
      return res.data;
    }
  });

  const mapData = useMemo(() => {
    if (!data) return [];
    return data.states.map((s: any) => ({
      state: s.state,
      value: s.avg_rate * 100
    }));
  }, [data]);

  const stats = useMemo(() => {
    if (!data) return null;
    const sorted = [...data.states].sort((a, b) => b.avg_rate - a.avg_rate);
    const njRank = sorted.findIndex(s => s.state === 'NJ') + 1;
    const hoveredData = hoveredState ? data.states.find((s: any) => s.state === hoveredState) : null;
    return { njRank, hoveredData, nationalAvg: data.national_avg };
  }, [data, hoveredState]);

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;

  const nj = data.focus_state;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-8">
          <h3 className="text-3xl font-black text-slate-900">NJ is the <span className="text-blue-600">#{stats?.njRank}</span> most expensive state.</h3>
          <p className="text-slate-500 mt-4 leading-relaxed">Your average rate of <span className="font-bold text-slate-900">${nj.avg_rate.toFixed(4)}/kWh</span> is {Math.abs((nj.avg_rate - data.national_avg) / data.national_avg * 100).toFixed(1)}% {nj.avg_rate > data.national_avg ? 'higher' : 'lower'} than national avg.</p>
        </div>
        <div className="card p-8 bg-slate-900 text-white relative overflow-hidden">
          <Globe className="absolute -right-8 -bottom-8 text-white/5" size={200} />
          <div className="relative z-10">
            <h4 className="text-4xl font-black">$138.20</h4>
            <span className="text-emerald-400 text-xs font-black flex items-center mt-2"><TrendingDown size={14} /> -2.1%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 card p-0 relative min-h-[500px]">
          <div className="absolute top-6 left-6 z-10 flex gap-2 bg-white/80 p-2 rounded-xl">
            {['2023', '2024', '2025'].map(y => <button key={y} onClick={() => setSelectedYear(y)} className={`px-4 py-2 rounded-lg text-xs font-black ${selectedYear === y ? 'bg-slate-900 text-white' : 'text-slate-400'}`}>{y}</button>)}
          </div>
          <USMap data={mapData} selectedState={comparisonState || "NJ"} onStateClick={setComparisonState} onStateHover={setHoveredState} />
        </div>
        <div className="space-y-6">
          <div className="card p-6">
            <Info size={16} className="text-blue-500 mb-4" />
            <p className="text-xs text-slate-500 italic">"Price volatility is highest in the Northeast corridor."</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BenchmarkTab;
