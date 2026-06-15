import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Legend, Area, Cell, LineChart
} from 'recharts';
import { 
  ArrowUpRight, ArrowDownRight, Zap, TrendingUp, DollarSign, 
  AlertTriangle, Lightbulb, Activity, Award, Calendar, MapPin, Building2,
  FileText, Sparkles, PieChart
} from 'lucide-react';

const COLORS = {
  generation: '#2563EB',   // Deep Blue
  transmission: '#8B5CF6', // Purple
  distribution: '#0D9488', // Teal
  tax: '#EF4444',          // Red
  sbc: '#F59E0B',          // Amber
  nug: '#38BDF8',          // Sky Blue
  customer: '#64748B',     // Gray-Slate
  transition: '#F43F5E',   // Rose
  others: '#94A3B8'        // Slate-Gray
};

const getComponentColor = (label: string) => {
  const l = label.toLowerCase();
  if (l.includes('bgs') || l.includes('generation') || l.includes('supply')) return COLORS.generation;
  if (l.includes('transmission')) return COLORS.transmission;
  if (l.includes('distribution')) return COLORS.distribution;
  if (l.includes('tax')) return COLORS.tax;
  if (l.includes('societal') || l.includes('sbc')) return COLORS.sbc;
  if (l.includes('nug')) return COLORS.nug;
  if (l.includes('customer') || l.includes('fixed')) return COLORS.customer;
  if (l.includes('transition')) return COLORS.transition;
  return COLORS.others;
};

const TimeRangeSelector = ({ value, onChange, options }: { value: number, onChange: (v: number) => void, options: number[] }) => (
  <div className="flex bg-slate-100 p-1 rounded-xl">
    {options.map((opt) => (
      <button
        key={opt}
        onClick={() => onChange(opt)}
        className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
          value === opt 
            ? 'bg-white text-slate-900 shadow-sm' 
            : 'text-slate-500 hover:text-slate-700'
        }`}
      >
        {opt}m
      </button>
    ))}
  </div>
);

// Custom Premium Tooltip for Bar Chart showing both $ and %
const CustomBarTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const total = payload.reduce((sum: number, entry: any) => sum + (entry.value || 0), 0);
    return (
      <div className="bg-white p-4 rounded-xl shadow-xl border border-slate-100 max-w-sm">
        <p className="text-xs font-bold text-slate-400 mb-2">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry: any) => {
            const val = entry.value || 0;
            const pct = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
            return (
              <div key={entry.name} className="flex justify-between items-center gap-4 text-xs font-semibold">
                <span className="flex items-center gap-1.5 text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                  {entry.name}:
                </span>
                <span className="text-slate-900 font-bold">${val.toFixed(2)} ({pct}%)</span>
              </div>
            );
          })}
          <div className="border-t border-slate-100 pt-2 mt-2 flex justify-between items-center text-xs font-bold text-slate-900">
            <span>Total Bill:</span>
            <span>${total.toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

// Custom Premium Tooltip for Composed Cost Trend Chart
const CustomTrendTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const bill = payload.find((x: any) => x.dataKey === 'bill')?.value;
    const mom = payload.find((x: any) => x.dataKey === 'mom')?.value;
    return (
      <div className="bg-white p-4 rounded-xl shadow-xl border border-slate-100">
        <p className="text-xs font-bold text-slate-400 mb-2">{label}</p>
        <div className="space-y-1">
          {bill !== undefined && (
            <p className="text-sm font-bold text-slate-900">
              Total Bill: <span className="text-blue-600">${bill.toFixed(2)}</span>
            </p>
          )}
          {mom !== undefined && mom !== null && (
            <p className={`text-xs font-semibold flex items-center gap-1 ${mom > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
              {mom > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              Monthly changes: {Math.abs(mom).toFixed(1)}%
            </p>
          )}
        </div>
      </div>
    );
  }
  return null;
};

const OverviewTab = () => {
  const [breakdownRange, setBreakdownRange] = useState(12);
  const [trendRange, setTrendRange] = useState(36);
  const [selectedMuni, setSelectedMuni] = useState('Newark City');
  const [billText, setBillText] = useState('');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const handleAnalyzeBill = async () => {
    if (!billText.trim()) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await axios.post('/analyze-ocr', { bill_text: billText });
      setAnalysisResult(res.data);
    } catch (err) {
      console.error(err);
      setAnalysisError('Failed to analyze the bill text. Please check the format and try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const res = await axios.get('/overview');
      return res.data;
    }
  });

  const { data: muniList } = useQuery({
    queryKey: ['municipal-list'],
    queryFn: async () => {
      const res = await axios.get('/municipal/list');
      return res.data;
    }
  });

  const { data: muniBenchmark } = useQuery({
    queryKey: ['municipal-benchmark', selectedMuni],
    queryFn: async () => {
      const res = await axios.get(`/municipal/benchmark?name=${encodeURIComponent(selectedMuni)}`);
      return res.data;
    },
    enabled: !!selectedMuni
  });

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;
  if (error) return <div className="text-red-500 p-8">Failed to load dashboard data.</div>;

  const filteredBreakdown = data.historical_breakdown.slice(-breakdownRange);
  
  // Transform trends to map to line (bill) and bar (mom % change)
  const trendData = data.trends.months.map((m: any, i: number) => ({
    month: m,
    bill: data.trends.total_bills[i],
    yoy: data.trends.yoy_changes[i],
    mom: data.trends.mom_changes ? data.trends.mom_changes[i] : null
  })).slice(-trendRange);

  return (
    <div className="space-y-6">
      {/* 🔹 1. KPI CARDS (TOP ROW) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Current Bill */}
        <div className="card p-6 relative overflow-hidden transition-all duration-300 hover:shadow-lg border border-slate-100">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <DollarSign size={20} />
            </div>
            <div className={`flex items-center gap-0.5 text-xs font-bold px-2.5 py-1 rounded-lg ${data.kpis.bill_change_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
              {data.kpis.bill_change_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {Math.abs(data.kpis.bill_change_pct).toFixed(1)}% vs last month
            </div>
          </div>
          <p className="text-sm font-medium text-slate-500">Current Computed Bill</p>
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">${data.kpis.current_bill.toFixed(2)}</h2>
          <p className="text-xs text-slate-400 mt-3 flex items-center gap-1">
            <Calendar size={12} className="text-slate-400" />
            Billing cycle: {data.trends.months[data.trends.months.length - 1]}
          </p>
        </div>

        {/* Card 2: Usage */}
        <div className="card p-6 relative overflow-hidden transition-all duration-300 hover:shadow-lg border border-slate-100">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Zap size={20} />
            </div>
            {data.kpis.usage_change_pct !== undefined && data.kpis.usage_change_pct !== null && (
              <div className={`flex items-center gap-0.5 text-xs font-bold px-2.5 py-1 rounded-lg ${data.kpis.usage_change_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                {data.kpis.usage_change_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {Math.abs(data.kpis.usage_change_pct).toFixed(1)}% Monthly changes
              </div>
            )}
          </div>
          <p className="text-sm font-medium text-slate-500">Electricity Consumption</p>
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">{data.kpis.usage_kwh.toLocaleString()} kWh</h2>
          <p className="text-xs text-slate-400 mt-3">Reflects active user monthly usage inputs</p>
        </div>

        {/* Card 3: Effective Rate */}
        <div className="card p-6 relative overflow-hidden transition-all duration-300 hover:shadow-lg border border-slate-100">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-teal-50 text-teal-600 rounded-xl">
              <TrendingUp size={20} />
            </div>
            {data.kpis.rate_change_pct !== undefined && data.kpis.rate_change_pct !== null && (
              <div className={`flex items-center gap-0.5 text-xs font-bold px-2.5 py-1 rounded-lg ${data.kpis.rate_change_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                {data.kpis.rate_change_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {Math.abs(data.kpis.rate_change_pct).toFixed(1)}% Monthly changes
              </div>
            )}
          </div>
          <p className="text-sm font-medium text-slate-500">Effective Unit Rate</p>
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">${data.kpis.effective_rate.toFixed(4)} <span className="text-sm font-normal text-slate-400">/kWh</span></h2>
          <p className="text-xs text-slate-400 mt-3">Computed as Total Bill / Usage</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 🔹 2. BILL COMPONENT BREAKDOWN */}
        <div className="card p-6 border border-slate-100 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-950">Bill Component Breakdown</h3>
              <p className="text-xs text-slate-400 mt-0.5">Real-time tariff allocation values (excluding synthetic fallbacks)</p>
            </div>
            <TimeRangeSelector value={breakdownRange} onChange={setBreakdownRange} options={[6, 12, 24]} />
          </div>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={filteredBreakdown}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis 
                  dataKey="month" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}}
                  tickFormatter={(val) => `$${val}`}
                />
                <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'rgba(226, 232, 240, 0.2)' }} />
                {data.breakdown.map((entry: any) => (
                  <Bar key={entry.label} dataKey={entry.label} stackId="a" fill={getComponentColor(entry.label)} />
                ))}
                <Legend 
                  iconType="circle" 
                  verticalAlign="bottom" 
                  align="center" 
                  wrapperStyle={{ paddingTop: '20px', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 🔹 3. COST TREND CHART */}
        <div className="card p-6 border border-slate-100 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-950">Cost Trend</h3>
              <p className="text-xs text-slate-400 mt-0.5">Total monthly bill vs Monthly changes</p>
            </div>
            <TimeRangeSelector value={trendRange} onChange={setTrendRange} options={[12, 24, 36]} />
          </div>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trendData}>
                <defs>
                  <linearGradient id="colorBill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis 
                  dataKey="month" 
                  axisLine={false}
                  tickLine={false}
                  tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}}
                  dy={10}
                  interval={Math.floor(trendData.length / 6)}
                />
                <YAxis 
                  yAxisId="left" 
                  axisLine={false}
                  tickLine={false}
                  tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}}
                  tickFormatter={(val) => `$${val}`}
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  axisLine={false}
                  tickLine={false}
                  tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip content={<CustomTrendTooltip />} cursor={{stroke: '#E2E8F0', strokeWidth: 1}} />
                <Area yAxisId="left" type="monotone" dataKey="bill" stroke="none" fill="url(#colorBill)" />
                
                {/* Monthly changes % Bars */}
                <Bar yAxisId="right" dataKey="mom" name="Monthly changes" barSize={8} radius={[2, 2, 0, 0]} opacity={0.7}>
                  {trendData.map((entry: any, index: number) => {
                    const isPositive = (entry.mom || 0) > 0;
                    return (
                      <Cell key={`cell-${index}`} fill={isPositive ? '#EF4444' : '#22C55E'} />
                    );
                  })}
                </Bar>
                
                <Line yAxisId="left" type="monotone" dataKey="bill" name="Total Bill ($)" stroke="#2563EB" strokeWidth={3} dot={false} />
                <Legend 
                  verticalAlign="bottom" 
                  align="center" 
                  wrapperStyle={{ paddingTop: '30px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em' }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 🔹 4, 5, 6. NEW DYNAMIC BENCHMARKS, INSIGHTS AND ALERTS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 4: Benchmark Comparison Insight */}
        <div className="card p-6 lg:col-span-1 border border-slate-100 flex flex-col justify-between hover:shadow-md transition-shadow">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-900 text-sm tracking-wide uppercase">Benchmark Insight</h3>
              <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                <Award size={18} />
              </div>
            </div>
            
            <p className="text-sm font-semibold text-slate-800 leading-relaxed mb-6">
              {data.vs_national_label}
            </p>
            
            {/* Visual rate gauge indicator */}
            <div className="bg-slate-50 p-4 rounded-xl space-y-4 mb-4 border border-slate-100">
              <div className="flex justify-between items-center text-xs text-slate-500 font-bold">
                <span>Your Rate</span>
                <span>National Avg</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-extrabold text-blue-600">${data.kpis.effective_rate.toFixed(4)}</span>
                <span className="text-sm font-bold text-slate-600">${(data.kpis.effective_rate / (1 + (data.vs_national_pct / 100))).toFixed(4)}</span>
              </div>
              
              <div className="relative pt-1">
                <div className="overflow-hidden h-2.5 text-xs flex rounded bg-slate-200">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, 50 + (data.vs_national_pct || 0)))}%` }} 
                    className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${data.vs_national_pct > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                  />
                </div>
              </div>
              <div className="flex justify-between items-center text-[10px] text-slate-400 font-semibold pt-1">
                <span>Cheaper</span>
                <span>Expensive</span>
              </div>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-4 flex justify-between items-center">
            <span className="text-xs text-slate-500 font-medium">NJ State Ranking:</span>
            <span className="text-xs font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded">
              #{data.state_rank || 10} / 51 states
            </span>
          </div>
        </div>

        {/* Card 5: Smart Analytics Cost Drivers */}
        <div className="card p-6 lg:col-span-1 border border-slate-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900 text-sm tracking-wide uppercase">Dynamic Cost Drivers</h3>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <Lightbulb size={18} />
            </div>
          </div>
          
          <div className="space-y-4">
            {data.insights && data.insights.map((insight: string, idx: number) => (
              <div key={idx} className="flex items-start gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100/50">
                <div className="mt-0.5 text-blue-600">
                  <Activity size={15} />
                </div>
                <p className="text-xs text-slate-600 leading-normal font-medium">{insight}</p>
              </div>
            ))}
            {(!data.insights || data.insights.length === 0) && (
              <p className="text-xs text-slate-400 italic">No cost insights generated for this period.</p>
            )}
          </div>
        </div>

        {/* Card 6: Dynamic Active Warnings & Alerts */}
        <div className="card p-6 lg:col-span-1 border border-slate-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900 text-sm tracking-wide uppercase">Active Alerts & Anomalies</h3>
            <div className="p-2 bg-red-50 text-red-600 rounded-lg">
              <AlertTriangle size={18} />
            </div>
          </div>

          <div className="space-y-4">
            {data.alerts && data.alerts.map((alert: string, idx: number) => {
              const isWarning = alert.toLowerCase().includes('increase') || alert.toLowerCase().includes('higher');
              return (
                <div 
                  key={idx} 
                  className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                    isWarning 
                      ? 'bg-red-50/50 border-red-100 text-red-700' 
                      : 'bg-emerald-50/50 border-emerald-100 text-emerald-700'
                  }`}
                >
                  <div className="mt-0.5">
                    {isWarning ? <AlertTriangle size={15} /> : <Zap size={15} />}
                  </div>
                  <p className="text-xs leading-normal font-semibold">{alert}</p>
                </div>
              );
            })}
            {(!data.alerts || data.alerts.length === 0) && (
              <div className="flex items-center gap-2 bg-emerald-50/30 border border-emerald-100/30 p-3 rounded-xl text-emerald-600">
                <Zap size={15} />
                <p className="text-xs font-semibold">All bill signals normal. No active anomalies.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 🔹 7. NJ MUNICIPAL BENCHMARKING (NEW) */}
      <div className="card p-6 border border-slate-100 hover:shadow-md transition-shadow">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950 flex items-center gap-2">
              <Building2 className="text-blue-600" size={20} /> NJ Municipal Benchmarking
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Compare your usage against community-scale averages</p>
          </div>
          {muniList?.municipalities && (
            <div className="relative">
              <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <select
                value={selectedMuni}
                onChange={(e) => setSelectedMuni(e.target.value)}
                className="pl-8 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold text-slate-700 outline-none focus:border-blue-500 appearance-none min-w-[200px]"
              >
                {muniList.municipalities.map((m: string) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {muniBenchmark ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={muniBenchmark.history}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="year" tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}} axisLine={false} tickLine={false} />
                  <YAxis tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 500}} axisLine={false} tickLine={false} tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}} />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px', fontWeight: 600 }} />
                  <Line type="monotone" dataKey="residential_electricity_kwh" name="Residential (kWh)" stroke="#2563EB" strokeWidth={3} dot={{r: 4}} />
                  <Line type="monotone" dataKey="commercial_electricity_kwh" name="Commercial (kWh)" stroke="#8B5CF6" strokeWidth={3} dot={{r: 4}} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div className="space-y-4">
              <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Total Residential Usage</p>
                <h4 className="text-2xl font-black text-slate-900 mb-1">
                  {muniBenchmark.history[muniBenchmark.history.length - 1]?.residential_electricity_kwh?.toLocaleString() || 0} <span className="text-sm font-medium text-slate-400">kWh</span>
                </h4>
                <p className="text-xs text-slate-500">In {muniBenchmark.history[muniBenchmark.history.length - 1]?.year}</p>
              </div>

              <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Your Monthly Usage vs Muni Avg</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <h4 className="text-xl font-black text-blue-600">{data.kpis.usage_kwh.toLocaleString()}</h4>
                  <span className="text-sm font-bold text-slate-400">vs</span>
                  <h4 className="text-lg font-black text-slate-700">
                    {Math.round((muniBenchmark.history[muniBenchmark.history.length - 1]?.residential_electricity_kwh || 0) / 12 / 5000).toLocaleString()} <span className="text-xs font-medium">kWh/hh</span>
                  </h4>
                </div>
                <p className="text-[10px] text-slate-400 mt-2 italic">*Muni avg assumes ~5000 households</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-[200px] flex items-center justify-center bg-slate-50 rounded-xl border border-slate-100 border-dashed">
            <p className="text-sm font-bold text-slate-400">Loading benchmark data...</p>
          </div>
        )}
      </div>

      {/* 🔹 8. BILL OCR STATEMENT ANALYZER */}
      <div className="card p-6 border border-slate-100 hover:shadow-md transition-shadow">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="text-blue-600" size={20} />
          <h3 className="text-lg font-bold text-slate-950">Bill Statement Extraction & Analysis</h3>
        </div>
        <p className="text-xs text-slate-400 mb-6">Paste raw OCR text from your electricity bill statement to parse components and identify cost drivers.</p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Area */}
          <div className="lg:col-span-1 space-y-4">
            <textarea
              placeholder="Paste raw bill text here... (e.g. Total Due: $145.20, Electricity Used: 780 kWh, Supply: $55.00, Customer charge: $12.00...)"
              value={billText}
              onChange={(e) => setBillText(e.target.value)}
              rows={10}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs font-medium text-slate-700 outline-none focus:border-blue-500 resize-none"
            />
            {analysisError && (
              <p className="text-xs font-bold text-red-500">{analysisError}</p>
            )}
            <button
              onClick={handleAnalyzeBill}
              disabled={isAnalyzing || !billText.trim()}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all shadow-md shadow-blue-500/20 flex items-center justify-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <div className="animate-spin h-4 w-4 border-b-2 border-slate-500" />
                  Analyzing Statement...
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  Analyze Bill Statement
                </>
              )}
            </button>
          </div>

          {/* Result Dashboard */}
          <div className="lg:col-span-2 flex flex-col justify-center">
            {analysisResult ? (
              <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 space-y-6">
                {/* Header info */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200/60 pb-4">
                  <div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
                      Utility Match
                    </span>
                    <h4 className="text-lg font-black text-slate-900 mt-2">
                      {analysisResult.utility_name || "Unknown Utility"}
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Period: {analysisResult.billing_period || "Unknown Billing Period"}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`inline-block px-3 py-1.5 rounded-full text-xs font-black uppercase tracking-wider border ${
                      analysisResult.driver === 'usage' 
                        ? 'bg-amber-50 text-amber-600 border-amber-200' 
                        : analysisResult.driver === 'rate'
                        ? 'bg-red-50 text-red-600 border-red-200'
                        : 'bg-indigo-50 text-indigo-600 border-indigo-200'
                    }`}>
                      Driver: {analysisResult.driver}
                    </span>
                    <div className="text-2xl font-black text-slate-900 mt-1.5">
                      ${analysisResult.total_amount?.toFixed(2) || "0.00"}
                    </div>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest font-black">
                      {analysisResult.kwh_used?.toLocaleString() || "0"} kWh used
                    </p>
                  </div>
                </div>

                {/* Grid breakdown */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-xl p-4 border border-slate-100/80 shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Supply Cost</p>
                    <h5 className="text-sm font-black text-slate-900">${analysisResult.charges.supply?.toFixed(2)}</h5>
                    <p className="text-[10px] text-slate-500 font-bold mt-0.5">{analysisResult.percentages.supply_pct?.toFixed(1)}%</p>
                  </div>
                  <div className="bg-white rounded-xl p-4 border border-slate-100/80 shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Delivery Cost</p>
                    <h5 className="text-sm font-black text-slate-900">${analysisResult.charges.delivery?.toFixed(2)}</h5>
                    <p className="text-[10px] text-slate-500 font-bold mt-0.5">{analysisResult.percentages.delivery_pct?.toFixed(1)}%</p>
                  </div>
                  <div className="bg-white rounded-xl p-4 border border-slate-100/80 shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Fixed Cost</p>
                    <h5 className="text-sm font-black text-slate-900">${analysisResult.charges.fixed?.toFixed(2)}</h5>
                    <p className="text-[10px] text-slate-500 font-bold mt-0.5">{analysisResult.percentages.fixed_pct?.toFixed(1)}%</p>
                  </div>
                  <div className="bg-white rounded-xl p-4 border border-slate-100/80 shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Taxes</p>
                    <h5 className="text-sm font-black text-slate-900">${analysisResult.charges.tax?.toFixed(2)}</h5>
                    <p className="text-[10px] text-slate-500 font-bold mt-0.5">{analysisResult.percentages.tax_pct?.toFixed(1)}%</p>
                  </div>
                </div>

                {/* Insight Text */}
                <div className="bg-blue-50/50 border border-blue-100/50 rounded-xl p-4 flex gap-3 text-xs leading-relaxed text-slate-700">
                  <Lightbulb size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
                  <p className="font-medium">{analysisResult.insight}</p>
                </div>
              </div>
            ) : (
              <div className="h-[260px] flex flex-col items-center justify-center bg-slate-50 rounded-2xl border border-slate-200 border-dashed text-slate-400 gap-2">
                <PieChart size={36} className="text-slate-300" />
                <p className="text-xs font-bold">Analysis results will appear here once parsed</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;
