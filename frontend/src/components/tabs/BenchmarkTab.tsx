import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, Legend, LineChart, Line
} from 'recharts';
import { Trophy, TrendingUp, TrendingDown, MapPin, Activity, BarChart3, Info, Calendar, Building2 } from 'lucide-react';

const REGION_COLORS: Record<string, string> = {
  Northeast: '#2F6BFF',   // Primary blue
  South: '#F5B041',       // Warning amber
  Midwest: '#16A085',     // Energy teal
  West: '#D64545',       // Alert red
};

const BenchmarkTab = ({ uploadedBill, setActiveTab }: { uploadedBill: any, setActiveTab?: (tab: string) => void }) => {
  if (setActiveTab) { /* no-op check */ }
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
        {"name": "State average (NJ)", "avg_bill": state_avg_bill, "avg_usage_kwh": state_avg_usage, "diff_bill": round(cust_bill - state_avg_bill, 2)},
        {"name": "Regional average (Mid-Atlantic)", "avg_bill": regional_avg_bill, "avg_usage_kwh": regional_avg_usage, "diff_bill": round(cust_bill - regional_avg_bill, 2)},
        {"name": "National average (US)", "avg_bill": national_avg_bill, "avg_usage_kwh": national_avg_usage, "diff_bill": round(cust_bill - national_avg_bill, 2)}
      ],
      savings_opportunity: round(savings, 2)
    };
  }, [uploadedBill, data]);

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

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading benchmarking datasets">
        <div className="h-20 bg-bg-surface border border-border-hairline rounded-md" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 h-[450px] bg-bg-surface border border-border-hairline rounded-md" />
          <div className="h-[450px] bg-bg-surface border border-border-hairline rounded-md" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-operational flex items-center justify-center p-12 border-alert-red/30">
        <span className="text-alert-red font-semibold">Failed to load benchmark data.</span>
      </div>
    );
  }

  const nj = data.focus_state;
  const njAbove = nj.vs_national_pct > 0;

  return (
    <div className="space-y-6 font-sans">

      {/* Title block */}
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          State & regional metrics
        </span>
        <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Regional benchmarks</h2>
        <p className="text-xs text-text-secondary mt-1">
          Compare customer usage characteristics against EIA regional indicators and OpenEI coverage profiles.
        </p>
      </div>

      {/* ── Personalized Benchmarking Summary ── */}
      {customerBenchmark && (
        <div className="panel-operational relative overflow-hidden bg-bg-surface">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
            <div>
              <span className="bg-primary-blue/10 text-primary-blue text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-[4px] border border-primary-blue/20">
                Personalized benchmarking
              </span>
              <h3 className="text-sm font-bold mt-3 text-text-primary">Your bill performance comparison</h3>
              <p className="text-xs text-text-secondary mt-0.5">Comparing customer consumption against state, regional, and national residential benchmarks</p>
            </div>
            
            <div className="flex items-center gap-6 font-mono-numbers">
              <div>
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Percentile rank</span>
                <span className="text-xl font-bold text-warning-amber">{customerBenchmark.customer.percentile}th</span>
              </div>
              <div className="border-l border-border-hairline pl-6">
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Savings opportunity</span>
                <span className="text-xl font-bold text-savings-green">${customerBenchmark.savings_opportunity?.toFixed(2)}<span className="text-xs font-normal text-text-secondary font-sans">/mo</span></span>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers">
            {customerBenchmark.comparisons.map((c: any, idx: number) => {
              const above = c.diff_bill > 0;
              return (
                <div key={idx} className="p-4 bg-bg-primary rounded-md border border-border-hairline flex flex-col justify-between shadow-sm">
                  <div>
                    <span className="text-xs font-bold text-text-primary block mb-2 font-sans">{c.name}</span>
                    <div className="flex justify-between text-xs text-text-secondary mb-1">
                      <span className="font-sans">Avg bill:</span>
                      <span className="font-bold text-text-primary">${c.avg_bill?.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs text-text-secondary mb-3">
                      <span className="font-sans">Avg usage:</span>
                      <span className="font-bold text-text-primary">{c.avg_usage_kwh} kWh</span>
                    </div>
                  </div>
                  <div className="border-t border-border-hairline pt-2 flex justify-between items-baseline">
                    <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Difference</span>
                    <span className={`text-sm font-bold ${above ? 'text-alert-red' : 'text-savings-green'}`}>
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
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 font-mono-numbers text-text-primary">
        <div className="lg:col-span-2 panel-operational flex flex-col justify-center">
          <h3 className="text-xl font-bold text-text-primary font-sans leading-snug">
            NJ is the <span className="text-primary-blue">#{nj.rank}</span> most expensive state.
          </h3>
          <p className="text-text-secondary text-xs mt-3 leading-relaxed font-sans">
            Your average residential rate of <span className="font-bold text-text-primary">${(nj.avg_rate * 100).toFixed(1)}¢/kWh</span> is{' '}
            <span className={`font-bold ${njAbove ? 'text-alert-red' : 'text-savings-green'}`}>
              {Math.abs(nj.vs_national_pct).toFixed(1)}% {njAbove ? 'higher' : 'lower'}
            </span>{' '}
            than the national average of ${(data.national_avg * 100).toFixed(1)}¢/kWh.
          </p>
        </div>

        <div className="panel-operational flex flex-col justify-between h-[110px] relative overflow-hidden bg-bg-surface">
          <div className="relative z-10">
            <p className="text-[10px] text-text-secondary mb-1 font-sans font-bold uppercase tracking-wider">Avg monthly bill</p>
            <h4 className="text-2xl font-bold text-text-primary">${nj.avg_bill.toFixed(0)}</h4>
            <span className={`text-[10px] font-bold flex items-center mt-1.5 font-sans uppercase tracking-wider ${njAbove ? 'text-alert-red' : 'text-savings-green'}`}>
              {njAbove ? <TrendingUp size={12} className="mr-0.5" /> : <TrendingDown size={12} className="mr-0.5" />}
              {njAbove ? '+' : ''}{nj.vs_national_pct.toFixed(1)}% vs avg
            </span>
          </div>
        </div>

        <div className="panel-operational bg-primary-blue/5 border-primary-blue/20 flex flex-col justify-between h-[110px] relative overflow-hidden">
          <div className="relative z-10 text-primary-blue">
            <p className="text-[10px] text-primary-blue/80 mb-1 font-sans font-bold uppercase tracking-wider">Avg monthly usage</p>
            <h4 className="text-2xl font-bold">{nj.avg_usage_kwh} kWh</h4>
            <p className="text-[10px] text-primary-blue/80 mt-2 font-sans font-semibold">{data.total_states} states tracked</p>
          </div>
        </div>
      </div>

      {/* ── Map + Year Toggle + Insights ────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 panel-operational p-0 relative min-h-[500px] bg-bg-surface overflow-hidden">
          <div className="absolute top-6 left-6 z-10 bg-bg-surface border border-border-hairline p-2 rounded-[6px] shadow-sm">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-transparent border-none text-xs font-bold text-text-primary outline-none cursor-pointer pr-2"
              aria-label="Select benchmark year"
            >
              {(data.available_years || Array.from({length: 22}, (_, i) => 2005 + i)).map((y: number) => (
                <option key={y} value={y}>{y} benchmark</option>
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
              <div className="absolute bottom-4 left-4 bg-bg-surface rounded-md p-4 shadow-md border border-border-hairline text-xs z-10 font-mono-numbers text-text-primary">
                <p className="font-bold text-text-primary font-sans">{s.state_name || s.state}</p>
                <p className="text-text-secondary mt-1">Rate: <span className="font-bold text-text-primary">{(s.avg_rate * 100).toFixed(1)}¢/kWh</span></p>
                <p className="text-text-secondary">Bill: <span className="font-bold text-text-primary">${s.avg_bill.toFixed(0)}/mo</span></p>
                <p className="text-text-secondary">Rank: <span className="font-bold text-primary-blue font-sans">#{s.rank}</span></p>
              </div>
            );
          })()}
        </div>

        <div className="space-y-4">
          {(data.insights || []).slice(0, 4).map((insight: any, i: number) => {
            const IconComp = insightIcons[insight.icon] || Info;
            return (
              <div key={i} className="panel-operational hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-[6px] bg-primary-blue/10 flex items-center justify-center flex-shrink-0">
                    <IconComp size={14} className="text-primary-blue" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-text-primary mb-1">{insight.title}</p>
                    <p className="text-[10px] text-text-secondary leading-relaxed">{insight.text}</p>
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
        <div className="panel-chart h-[380px] flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <TrendingUp size={14} className="text-alert-red" /> Top 10 most expensive
          </h4>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.top_10_expensive} layout="vertical" margin={{ left: -10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="state" tick={{ fontSize: 10, fill: 'var(--text-primary)', fontWeight: 'bold' }} width={30} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                <Bar dataKey="avg_rate" radius={[0, 2, 2, 0]}>
                  {(data.top_10_expensive || []).map((_: any, idx: number) => (
                    <Cell key={idx} fill={idx === 0 ? 'var(--alert-red)' : idx < 3 ? 'var(--warning-amber)' : '#E6EAF0'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 10 Cheapest */}
        <div className="panel-chart h-[380px] flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <TrendingDown size={14} className="text-savings-green" /> 10 cheapest states
          </h4>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.cheapest_10} layout="vertical" margin={{ left: -10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="state" tick={{ fontSize: 10, fill: 'var(--text-primary)', fontWeight: 'bold' }} width={30} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                <Bar dataKey="avg_rate" radius={[0, 2, 2, 0]}>
                  {(data.cheapest_10 || []).map((_: any, idx: number) => (
                    <Cell key={idx} fill={idx === 0 ? 'var(--savings-green)' : idx < 3 ? 'var(--energy-teal)' : '#E6EAF0'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Price vs Bill Scatter */}
        <div className="panel-chart h-[380px] flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <Activity size={14} className="text-primary-blue" /> Price vs bill (efficiency)
          </h4>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ bottom: 10, left: -20, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis type="number" dataKey="avg_rate" name="Rate" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }}
                  tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`}
                  label={{ value: 'Rate (¢/kWh)', position: 'insideBottom', offset: -5, fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                <YAxis type="number" dataKey="avg_bill" name="Bill" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(v: any, name: any) => [
                    name === 'Rate' ? `${(Number(v) * 100).toFixed(1)}¢/kWh` : `$${Number(v).toFixed(0)}`,
                    name
                  ]}
                  labelFormatter={() => ''}
                />
                <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '9px' }} />
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
        <div className="panel-operational">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 border-b border-border-hairline pb-2">Regional average residential rates ({selectedYear})</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono-numbers">
            {Object.entries(data.region_averages).map(([region, rate]) => (
              <div key={region} className="flex items-center gap-3 p-4 rounded-md bg-bg-primary border border-border-hairline shadow-sm">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: REGION_COLORS[region] || 'var(--text-secondary)' }} />
                <div>
                  <p className="text-[10px] text-text-secondary font-sans">{region}</p>
                  <p className="text-base font-bold text-text-primary">{((rate as number) * 100).toFixed(1)}¢</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Sub-State ZCTA & Utility Benchmarking ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Utility Comparison within state */}
        <div className="panel-chart h-[360px] flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <Building2 size={14} className="text-primary-blue" /> Utility rate comparison ({comparisonState || 'NJ'})
          </h4>
          <div className="flex-1 min-h-[260px]">
            {utilityBenchmark && utilityBenchmark.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={utilityBenchmark} margin={{ bottom: 10, left: -25 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="utility_name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} interval={0} 
                    tickFormatter={(name) => name.length > 12 ? name.substring(0, 12) + '...' : name} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(2)}¢/kWh`, 'Rate']} />
                  <Bar dataKey="residential_rate" fill="var(--primary-blue)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-text-secondary">
                No utility data available for this state.
              </div>
            )}
          </div>
        </div>

        {/* ZIP-level distribution metrics within state */}
        <div className="panel-operational space-y-4 h-[360px]">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <Activity size={14} className="text-primary-blue" /> ZIP code rate disparity ({comparisonState || 'NJ'})
          </h4>
          {zipBenchmark && zipBenchmark.zips && zipBenchmark.zips.length > 0 ? (
            <div className="space-y-4 font-mono-numbers">
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="bg-bg-primary rounded-md p-3 border border-border-hairline shadow-sm">
                  <p className="text-[9px] font-bold text-text-secondary uppercase tracking-wider mb-1 font-sans">State average</p>
                  <p className="text-sm font-bold text-text-primary">${(zipBenchmark.avg_rate * 100).toFixed(2)}¢</p>
                </div>
                <div className="bg-savings-green/10 rounded-md p-3 border border-savings-green/20 shadow-sm text-savings-green">
                  <p className="text-[9px] font-bold text-savings-green uppercase tracking-wider mb-1 font-sans">Below Avg ZIPs</p>
                  <p className="text-sm font-bold">{zipBenchmark.below_average_count}</p>
                </div>
                <div className="bg-alert-red/10 rounded-md p-3 border border-alert-red/20 shadow-sm text-alert-red">
                  <p className="text-[9px] font-bold text-alert-red uppercase tracking-wider mb-1 font-sans">Above Avg ZIPs</p>
                  <p className="text-sm font-bold">{zipBenchmark.above_average_count}</p>
                </div>
              </div>
              
              <div className="pt-2">
                <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-2 font-sans border-b border-border-hairline pb-1">Top 5 most expensive ZIPs</p>
                <div className="space-y-1 font-sans max-h-[170px] overflow-y-auto pr-1">
                  {zipBenchmark.zips.slice(0, 5).map((z: any) => (
                    <div key={z.zip_code} className="flex justify-between items-center text-xs text-text-primary p-2 bg-bg-primary rounded-md border border-border-hairline shadow-sm font-mono-numbers">
                      <span className="font-bold font-sans">ZIP {z.zip_code}</span>
                      <div className="flex gap-2 items-center">
                        <span className="font-bold text-text-primary">${(z.rate * 100).toFixed(2)}¢/kWh</span>
                        <span className="text-[9px] text-alert-red font-bold font-sans">+{z.vs_state_avg_pct}% vs avg</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-text-secondary">
              No ZIP code data available for this state.
            </div>
          )}
        </div>
      </div>

      {/* ── Monthly Trends & Utility Listings (EIA-861M & OpenEI) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart: National Monthly Sales Trends (EIA-861M) */}
        <div className="panel-chart h-[380px] flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <Calendar size={14} className="text-primary-blue" /> National monthly energy sales (EIA-861M)
          </h4>
          <div className="flex-1 min-h-[300px]">
            {monthlyTrends ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthlyTrends.periods.map((p: string, idx: number) => ({
                  period: p,
                  sales: monthlyTrends.sales[idx] / 1e6, // MWh to TWh
                  price: monthlyTrends.prices[idx],
                })).slice(-24)} margin={{ left: -25, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="left" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${v.toFixed(0)}T`} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${v.toFixed(0)}¢`} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: '9px' }} />
                  <Line yAxisId="left" type="monotone" dataKey="sales" name="Sales (TWh)" stroke="var(--primary-blue)" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="price" name="Avg Price (¢/kWh)" stroke="var(--warning-amber)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-text-secondary">Loading monthly trends...</div>
            )}
          </div>
        </div>

        {/* Table: NJ Utility Rate Rankings (OpenEI) */}
        <div className="panel-operational h-[380px] flex flex-col justify-between overflow-hidden">
          <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
            <Building2 size={14} className="text-primary-blue" /> NJ utility service areas & rates (OpenEI)
          </h4>
          <div className="flex-1 overflow-x-auto max-h-[300px]">
            <table className="w-full text-left border-collapse text-xs relative">
              <thead>
                <tr className="border-b border-border-hairline text-text-secondary font-bold uppercase text-[9px] sticky top-0 bg-bg-surface z-10">
                  <th className="py-2">Utility Name</th>
                  <th className="py-2">Type</th>
                  <th className="py-2 text-right">ZIP Codes</th>
                  <th className="py-2 text-right">Res. Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-hairline font-mono-numbers text-text-primary">
                {njUtilities ? (
                  njUtilities.slice(0, 10).map((util: any) => (
                    <tr key={util.eia_utility_id} className="hover:bg-bg-primary/50 transition-colors">
                      <td className="py-2.5 truncate max-w-[180px] font-sans font-semibold">{util.utility_name}</td>
                      <td className="py-2.5 text-text-secondary font-sans">{util.ownership_type || 'Other'}</td>
                      <td className="py-2.5 text-right text-text-secondary">{util.zip_count}</td>
                      <td className="py-2.5 text-right text-primary-blue font-bold">
                        {util.residential_rate ? `${(util.residential_rate * 100).toFixed(2)}¢` : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-text-secondary font-sans">Loading utilities...</td>
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
