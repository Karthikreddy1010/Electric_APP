import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, Legend, LineChart, Line
} from 'recharts';
import { Trophy, TrendingUp, TrendingDown, Globe, MapPin, Activity, BarChart3, Info, Zap, Calendar, Building2 } from 'lucide-react';

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

  // Fetch EIA-861M Monthly Trends
  const { data: monthlyTrends } = useQuery({
    queryKey: ['eia861m-trends'],
    queryFn: async () => {
      const res = await axios.get('/eia861m/trends?sector=total');
      return res.data;
    }
  });

  // Fetch OpenEI Utility Coverage for NJ
  const { data: njUtilities } = useQuery({
    queryKey: ['nj-utilities'],
    queryFn: async () => {
      const res = await axios.get('/utility/coverage?state=NJ');
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
          <div className="absolute top-6 left-6 z-10 bg-white/90 backdrop-blur p-2 rounded-xl shadow-sm">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-transparent border-none text-sm font-black text-slate-900 outline-none cursor-pointer pr-2"
            >
              {(data.available_years || Array.from({length: 22}, (_, i) => 2005 + i)).map((y: number) => (
                <option key={y} value={y}>{y} Benchmark</option>
              ))}
            </select>
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

      {/* ── 🔹 NEW SECTION: Monthly Trends & Utility Listings (EIA-861M & OpenEI) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart: National Monthly Sales Trends (EIA-861M) */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <Calendar size={16} className="text-blue-600" /> National Monthly Energy Sales (EIA-861M)
          </h4>
          <div className="h-[320px]">
            {monthlyTrends ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthlyTrends.periods.map((p: string, idx: number) => ({
                  period: p,
                  sales: monthlyTrends.sales[idx] / 1e6, // MWh to TWh
                  price: monthlyTrends.prices[idx],
                })).slice(-36)}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(1)}TWh`} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(1)}¢`} />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="sales" name="Sales (TWh)" stroke="#2563EB" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="price" name="Avg Price (¢/kWh)" stroke="#F59E0B" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">Loading monthly trends...</div>
            )}
          </div>
        </div>

        {/* Table: NJ Utility Rate Rankings (OpenEI) */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <Building2 size={16} className="text-purple-600" /> NJ Utility Service Areas & Rates (OpenEI)
          </h4>
          <div className="overflow-x-auto max-h-[320px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-bold">
                  <th className="py-2">Utility Name</th>
                  <th className="py-2">Type</th>
                  <th className="py-2 text-right">ZIP Codes</th>
                  <th className="py-2 text-right">Res. Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 font-semibold text-slate-700">
                {njUtilities ? (
                  njUtilities.slice(0, 10).map((util: any) => (
                    <tr key={util.eia_utility_id} className="hover:bg-slate-50/55 transition-colors">
                      <td className="py-2.5 truncate max-w-[200px]">{util.utility_name}</td>
                      <td className="py-2.5 text-slate-500">{util.ownership_type || 'Other'}</td>
                      <td className="py-2.5 text-right text-slate-500">{util.zip_count}</td>
                      <td className="py-2.5 text-right text-blue-600 font-bold">
                        {util.residential_rate ? `${(util.residential_rate * 100).toFixed(2)}¢` : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-slate-400">Loading utilities...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BenchmarkTab;
