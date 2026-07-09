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
const BenchmarkTab = ({ uploadedBill, setActiveTab }: { uploadedBill: any, setActiveTab?: (tab: string) => void }) => {
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

  const round = (val: number, decimals: number) => {
    const p = Math.pow(10, decimals);
    return Math.round(val * p) / p;
  };

  const customerBenchmark = useMemo(() => {
    if (!uploadedBill || !data) return null;
    const state_avg_bill = 120.0;
    const state_avg_usage = 750.0;
    
    const national_avg_bill = data.national_avg || 135.0;
    const national_avg_usage = 890.0;
    
    const regional_avg_bill = 128.0;
    const regional_avg_usage = 800.0;
    
    const cust_usage = uploadedBill.usage_kwh;
    const cust_bill = uploadedBill.total_bill;
    
    const erf = (x: number) => {
      const a1 =  0.254829592;
      const a2 = -0.284496736;
      const a3 =  1.421413741;
      const a4 = -1.453152027;
      const a5 =  1.061405429;
      const p  =  0.3275911;

      const sign = (x < 0) ? -1 : 1;
      const t = Math.abs(x);

      const a = t / (1.0 + p * t);
      const y = 1.0 - (((((a5 * a + a4) * a) + a3) * a + a2) * a + a1) * a * Math.exp(-t * t);

      return sign * y;
    };
    
    const std_dev = state_avg_usage * 0.35;
    const z = (cust_usage - state_avg_usage) / (std_dev * Math.sqrt(2));
    const percentile = round((0.5 * (1 + erf(z))) * 100, 1);
    
    const savings_opp = Math.max(0, cust_bill - state_avg_bill);
    const savings = savings_opp === 0 ? cust_bill * 0.10 : savings_opp;
    
    return {
      customer: {
        monthly_bill: cust_bill,
        monthly_usage_kwh: cust_usage,
        percentile: percentile
      },
      comparisons: [
        {"name": "State Average (NJ)", "avg_bill": state_avg_bill, "avg_usage_kwh": state_avg_usage, "diff_bill": round(cust_bill - state_avg_bill, 2)},
        {"name": "Regional Average (Mid-Atlantic)", "avg_bill": regional_avg_bill, "avg_usage_kwh": regional_avg_usage, "diff_bill": round(cust_bill - regional_avg_bill, 2)},
        {"name": "National Average (US)", "avg_bill": national_avg_bill, "avg_usage_kwh": national_avg_usage, "diff_bill": round(cust_bill - national_avg_bill, 2)}
      ],
      savings_opportunity: round(savings, 2)
    };
  }, [uploadedBill, data]);

  if (!uploadedBill) {
    return (
      <div className="flex flex-col items-center justify-center p-16 card bg-slate-50 border-dashed border-2 border-slate-200 text-center max-w-xl mx-auto space-y-4 my-12">
        <Zap size={48} className="text-slate-400 animate-bounce" />
        <h3 className="text-xl font-bold text-slate-800">Benchmark Locked</h3>
        <p className="text-sm text-slate-500 max-w-sm">
          Please upload and analyze an electricity bill on the Bill Analysis page to run benchmark comparison algorithms.
        </p>
        <button 
          onClick={() => setActiveTab?.("Bill Analysis")}
          className="bg-primary text-white hover:bg-primary-hover font-bold px-6 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 mt-4"
        >
          Go to Bill Analysis
        </button>
      </div>
    );
  }

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

  // Fetch ZIP-level benchmarking for selected comparison state
  const { data: zipBenchmark } = useQuery({
    queryKey: ['benchmark_zip_level', comparisonState || 'NJ'],
    queryFn: async () => {
      const res = await axios.get(`/benchmark/zip-level?state=${comparisonState || 'NJ'}`);
      return res.data;
    }
  });

  // Fetch utility rates comparison for selected comparison state
  const { data: utilityBenchmark } = useQuery({
    queryKey: ['benchmark_utility_comparison', comparisonState || 'NJ'],
    queryFn: async () => {
      const res = await axios.get(`/benchmark/utility-comparison?state=${comparisonState || 'NJ'}`);
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
      {/* ── Personalized Benchmarking Summary ── */}
      {customerBenchmark && (
        <div className="card p-6 bg-slate-900 text-white relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-32 h-32 bg-blue-600/10 rounded-full blur-3xl"></div>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10 mb-6">
            <div>
              <span className="bg-blue-600 text-white text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full">
                Personalized Benchmarking
              </span>
              <h3 className="text-xl font-bold mt-2">Your Bill Performance Comparison</h3>
              <p className="text-xs text-slate-400 mt-0.5">Comparing customer consumption against state, regional, and national residential benchmarks</p>
            </div>
            
            <div className="flex items-center gap-6">
              <div>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Percentile Rank</span>
                <span className="text-2xl font-black text-amber-400">{customerBenchmark.customer.percentile}th</span>
              </div>
              <div className="border-l border-slate-800 pl-6">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Savings Opportunity</span>
                <span className="text-2xl font-black text-emerald-400">${customerBenchmark.savings_opportunity?.toFixed(2)}<span className="text-xs font-normal text-slate-400">/mo</span></span>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
            {customerBenchmark.comparisons.map((c: any, idx: number) => {
              const above = c.diff_bill > 0;
              return (
                <div key={idx} className="p-4 bg-slate-800/50 rounded-xl border border-slate-755/30 flex flex-col justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-300 block mb-2">{c.name}</span>
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>Avg Bill:</span>
                      <span className="font-bold text-white">${c.avg_bill?.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs text-slate-400 mb-3">
                      <span>Avg Usage:</span>
                      <span className="font-bold text-white">{c.avg_usage_kwh} kWh</span>
                    </div>
                  </div>
                  <div className="border-t border-slate-700/50 pt-2 flex justify-between items-baseline">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Difference</span>
                    <span className={`text-sm font-bold ${above ? 'text-red-400' : 'text-emerald-400'}`}>
                      {above ? '+' : ''}${c.diff_bill?.toFixed(2)}/mo
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
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

      {/* ── Sub-State ZCTA & Utility Benchmarking ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Utility Comparison within state */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <Building2 size={16} className="text-blue-600" /> Utility Rate Comparison ({comparisonState || 'NJ'})
          </h4>
          <div className="h-[280px]">
            {utilityBenchmark && utilityBenchmark.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={utilityBenchmark} margin={{ bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="utility_name" tick={{ fontSize: 9 }} interval={0} 
                    tickFormatter={(name) => name.length > 15 ? name.substring(0, 15) + '...' : name} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}¢`} />
                  <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(2)}¢/kWh`, 'Rate']} />
                  <Bar dataKey="residential_rate" fill="#3B82F6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No utility data available for this state.
              </div>
            )}
          </div>
        </div>

        {/* ZIP-level distribution metrics within state */}
        <div className="card p-6">
          <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
            <Zap size={16} className="text-amber-500" /> ZIP Code Rate Disparity ({comparisonState || 'NJ'})
          </h4>
          {zipBenchmark && zipBenchmark.zips && zipBenchmark.zips.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100/50">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">State average</p>
                  <p className="text-base font-black text-slate-900">${(zipBenchmark.avg_rate * 100).toFixed(2)}¢</p>
                </div>
                <div className="bg-emerald-50/50 rounded-xl p-3.5 border border-emerald-100/20">
                  <p className="text-[9px] font-black text-emerald-600 uppercase tracking-wider mb-1">Below Avg ZIPs</p>
                  <p className="text-base font-black text-emerald-700">{zipBenchmark.below_average_count}</p>
                </div>
                <div className="bg-red-50/50 rounded-xl p-3.5 border border-red-100/20">
                  <p className="text-[9px] font-black text-red-600 uppercase tracking-wider mb-1">Above Avg ZIPs</p>
                  <p className="text-base font-black text-red-700">{zipBenchmark.above_average_count}</p>
                </div>
              </div>
              
              <div className="pt-2">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2.5">Top 5 Most Expensive ZIPs</p>
                <div className="space-y-1.5 font-sans">
                  {zipBenchmark.zips.slice(0, 5).map((z: any) => (
                    <div key={z.zip_code} className="flex justify-between items-center text-xs text-slate-700 p-2 bg-slate-50 rounded-lg">
                      <span className="font-bold">ZIP {z.zip_code}</span>
                      <div className="flex gap-2 items-center">
                        <span className="font-black text-slate-900">${(z.rate * 100).toFixed(2)}¢/kWh</span>
                        <span className="text-[10px] text-red-500 font-bold">+{z.vs_state_avg_pct}% vs avg</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No ZIP code data available for this state.
            </div>
          )}
        </div>
      </div>


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
