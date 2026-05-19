import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, Legend
} from 'recharts';
import { Trophy, TrendingUp, TrendingDown, Globe, MapPin, Activity, BarChart3, Info, Zap } from 'lucide-react';

const REGION_COLORS: Record<string, string> = {
  Northeast: '#6366F1',
  South: '#F59E0B',
  Midwest: '#10B981',
  West: '#EF4444',
};

const BenchmarkTab = () => {
  const [selectedYear, setSelectedYear] = useState('2025');
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [comparisonState, setComparisonState] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`/benchmark?year=${selectedYear}&compare_state=NJ`);
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

  const insightIcons: Record<string, any> = {
    trophy: Trophy,
    trending: TrendingUp,
    map: MapPin,
    activity: Activity,
    'bar-chart': BarChart3,
  };

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;
  if (error) return <div className="p-8 text-red-600">Failed to load benchmark data.</div>;

  const nj = data.focus_state;
  const njAbove = nj.vs_national_pct > 0;

  return (
    <div className="space-y-6">
      {/* ── KPI Banner ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-2 card p-8">
          <h3 className="text-3xl font-black text-slate-900">
            NJ is the <span className="text-blue-600">#{nj.rank}</span> most expensive state.
          </h3>
          <p className="text-slate-500 mt-4 leading-relaxed">
            Your average residential rate of <span className="font-bold text-slate-900">${(nj.avg_rate * 100).toFixed(1)}¢/kWh</span> is{' '}
            <span className={`font-black ${njAbove ? 'text-red-500' : 'text-emerald-500'}`}>
              {Math.abs(nj.vs_national_pct).toFixed(1)}% {njAbove ? 'higher' : 'lower'}
            </span>{' '}
            than the national average of ${(data.national_avg * 100).toFixed(1)}¢/kWh.
          </p>
        </div>

        <div className="card p-6 bg-gradient-to-br from-slate-900 to-slate-800 text-white relative overflow-hidden">
          <Globe className="absolute -right-6 -bottom-6 text-white/5" size={140} />
          <div className="relative z-10">
            <p className="text-xs text-slate-400 mb-1">Avg Monthly Bill</p>
            <h4 className="text-4xl font-black">${nj.avg_bill.toFixed(0)}</h4>
            <span className={`text-xs font-bold flex items-center mt-2 ${njAbove ? 'text-red-400' : 'text-emerald-400'}`}>
              {njAbove ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              <span className="ml-1">{njAbove ? '+' : ''}{nj.vs_national_pct.toFixed(1)}% vs avg</span>
            </span>
          </div>
        </div>

        <div className="card p-6 bg-gradient-to-br from-blue-600 to-indigo-700 text-white relative overflow-hidden">
          <Zap className="absolute -right-4 -bottom-4 text-white/10" size={100} />
          <div className="relative z-10">
            <p className="text-xs text-blue-200 mb-1">Avg Monthly Usage</p>
            <h4 className="text-3xl font-black">{nj.avg_usage_kwh} kWh</h4>
            <p className="text-xs text-blue-200 mt-2">{data.total_states} states tracked</p>
          </div>
        </div>
      </div>

      {/* ── Map + Year Toggle + Insights ────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 card p-0 relative min-h-[500px]">
          <div className="absolute top-6 left-6 z-10 flex gap-2 bg-white/90 backdrop-blur p-2 rounded-xl shadow-sm">
            {(data.available_years || [2023, 2024, 2025]).map((y: number) => (
              <button key={y} onClick={() => setSelectedYear(String(y))}
                className={`px-4 py-2 rounded-lg text-xs font-black transition-all ${selectedYear === String(y) ? 'bg-slate-900 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-100'}`}
              >{y}</button>
            ))}
          </div>
          <USMap
            data={mapData}
            selectedState={comparisonState || "NJ"}
            onStateClick={setComparisonState}
            onStateHover={setHoveredState}
          />
          {hoveredState && data.states && (() => {
            const s = data.states.find((st: any) => st.state === hoveredState);
            if (!s) return null;
            return (
              <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur rounded-xl p-4 shadow-xl border text-sm z-10">
                <p className="font-black text-slate-900">{s.state_name || s.state}</p>
                <p className="text-slate-500">Rate: <span className="font-bold text-slate-900">{(s.avg_rate * 100).toFixed(1)}¢/kWh</span></p>
                <p className="text-slate-500">Bill: <span className="font-bold text-slate-900">${s.avg_bill.toFixed(0)}/mo</span></p>
                <p className="text-slate-500">Rank: <span className="font-bold text-blue-600">#{s.rank}</span></p>
              </div>
            );
          })()}
        </div>

        <div className="space-y-4">
          {(data.insights || []).slice(0, 4).map((insight: any, i: number) => {
            const IconComp = insightIcons[insight.icon] || Info;
            return (
              <div key={i} className="card p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <IconComp size={16} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-900 mb-1">{insight.title}</p>
                    <p className="text-xs text-slate-500 leading-relaxed">{insight.text}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Charts Row: Top 10 + Cheapest 10 + Scatter ──────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top 10 Most Expensive */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-red-500" /> Top 10 Most Expensive
          </h4>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.top_10_expensive} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} />
                <YAxis type="category" dataKey="state" tick={{ fontSize: 11, fontWeight: 700 }} width={35} />
                <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                <Bar dataKey="avg_rate" radius={[0, 6, 6, 0]}>
                  {(data.top_10_expensive || []).map((_: any, idx: number) => (
                    <Cell key={idx} fill={idx === 0 ? '#EF4444' : idx < 3 ? '#F97316' : '#F59E0B'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 10 Cheapest */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <TrendingDown size={16} className="text-emerald-500" /> 10 Cheapest States
          </h4>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.cheapest_10} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} />
                <YAxis type="category" dataKey="state" tick={{ fontSize: 11, fontWeight: 700 }} width={35} />
                <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                <Bar dataKey="avg_rate" radius={[0, 6, 6, 0]}>
                  {(data.cheapest_10 || []).map((_: any, idx: number) => (
                    <Cell key={idx} fill={idx === 0 ? '#10B981' : idx < 3 ? '#34D399' : '#6EE7B7'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Price vs Bill Scatter */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <Activity size={16} className="text-indigo-500" /> Price vs Bill (Efficiency)
          </h4>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ bottom: 10, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis type="number" dataKey="avg_rate" name="Rate" tick={{ fontSize: 10 }}
                  tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`}
                  label={{ value: 'Rate (¢/kWh)', position: 'insideBottom', offset: -5, fontSize: 10 }} />
                <YAxis type="number" dataKey="avg_bill" name="Bill" tick={{ fontSize: 10 }}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                <Tooltip
                  formatter={(v: any, name: any) => [
                    name === 'Rate' ? `${(Number(v) * 100).toFixed(1)}¢/kWh` : `$${Number(v).toFixed(0)}`,
                    name
                  ]}
                  labelFormatter={() => ''}
                />
                <Legend verticalAlign="top" height={30} />
                {Object.entries(REGION_COLORS).map(([region, color]) => (
                  <Scatter
                    key={region}
                    name={region}
                    data={(data.scatter_data || []).filter((d: any) => d.region === region)}
                    fill={color}
                  >
                    {(data.scatter_data || [])
                      .filter((d: any) => d.region === region)
                      .map((_: any, idx: number) => (
                        <Cell key={idx} fill={color} opacity={0.7} />
                      ))}
                  </Scatter>
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Regional Averages Bar ────────────────────────────────────────── */}
      {data.region_averages && (
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4">Regional Average Residential Rates ({selectedYear})</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data.region_averages).map(([region, rate]) => (
              <div key={region} className="flex items-center gap-3 p-4 rounded-xl bg-slate-50">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: REGION_COLORS[region] || '#94A3B8' }} />
                <div>
                  <p className="text-xs text-slate-500">{region}</p>
                  <p className="text-lg font-black text-slate-900">{((rate as number) * 100).toFixed(1)}¢</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BenchmarkTab;
