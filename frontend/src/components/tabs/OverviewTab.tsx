import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Cell, Legend
} from 'recharts';
import { ArrowUpRight, ArrowDownRight, Zap, TrendingUp, DollarSign } from 'lucide-react';

const COLORS = {
  generation: '#3B82F6',
  transmission: '#8B5CF6',
  distribution: '#14B8A6',
  tax: '#EF4444',
  others: '#F59E0B'
};

const getComponentColor = (label: string) => {
  const l = label.toLowerCase();
  if (l.includes('bgs') || l.includes('generation')) return COLORS.generation;
  if (l.includes('transmission')) return COLORS.transmission;
  if (l.includes('distribution')) return COLORS.distribution;
  if (l.includes('tax')) return COLORS.tax;
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

const OverviewTab = () => {
  const [breakdownRange, setBreakdownRange] = useState(12);
  const [trendRange, setTrendRange] = useState(36);

  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/overview');
      return res.data;
    }
  });

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );
  if (error) return <div className="text-red-500 p-8 card bg-red-50 border-red-100">Failed to load dashboard data.</div>;

  // Filter historical data based on selected range
  const filteredBreakdown = data.historical_breakdown.slice(-breakdownRange);
  const trendData = data.trends.months.map((m: any, i: number) => ({
    month: m,
    bill: data.trends.total_bills[i],
    yoy: data.trends.yoy_changes[i]
  })).slice(-trendRange);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* KPI Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6 flex flex-col justify-between group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
              <DollarSign size={20} />
            </div>
            <div className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg ${
              data.kpis.bill_change_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'
            }`}>
              {data.kpis.bill_change_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {Math.abs(data.kpis.bill_change_pct).toFixed(1)}%
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 mb-1">Current Bill</p>
            <h2 className="text-3xl font-bold text-slate-900">${data.kpis.current_bill.toFixed(2)}</h2>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Total expenditure for the last billing cycle.
            </p>
          </div>
        </div>

        <div className="card p-6 flex flex-col justify-between group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2.5 bg-purple-50 text-purple-600 rounded-xl group-hover:bg-purple-600 group-hover:text-white transition-colors">
              <Zap size={20} />
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 mb-1">Usage</p>
            <h2 className="text-3xl font-bold text-slate-900">{data.kpis.usage_kwh.toLocaleString()} <span className="text-lg font-medium text-slate-400">kWh</span></h2>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Energy consumption across all active meters.
            </p>
          </div>
        </div>

        <div className="card p-6 flex flex-col justify-between group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl group-hover:bg-emerald-600 group-hover:text-white transition-colors">
              <TrendingUp size={20} />
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 mb-1">Effective Rate</p>
            <h2 className="text-3xl font-bold text-slate-900">${data.kpis.effective_rate.toFixed(4)} <span className="text-lg font-medium text-slate-400">/kWh</span></h2>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Blended cost including fixed charges and taxes.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Breakdown Chart */}
        <div className="card p-6">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Bill Component Breakdown</h3>
              <p className="text-xs text-slate-400 mt-0.5">Cost distribution by utility component</p>
            </div>
            <TimeRangeSelector 
              value={breakdownRange} 
              onChange={setBreakdownRange} 
              options={[6, 12, 24]} 
            />
          </div>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={filteredBreakdown} 
                margin={{ left: -20, right: 0, top: 10 }}
                barGap={8}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis 
                  dataKey="month" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 11}}
                  tickFormatter={(val) => {
                    const [y, m] = String(val).split('-');
                    const date = new Date(parseInt(y), parseInt(m) - 1);
                    return date.toLocaleString('default', { month: 'short' });
                  }}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 11}}
                  tickFormatter={(val) => `$${val}`}
                />
                <Tooltip 
                  cursor={{fill: '#F8FAFC'}}
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length && label) {
                      const total = payload.reduce((sum, entry) => sum + Number(entry.value), 0);
                      const [y, m] = String(label).split('-');
                      const dateLabel = new Date(parseInt(y), parseInt(m) - 1).toLocaleString('default', { month: 'long', year: 'numeric' });
                      return (
                        <div className="bg-white border border-slate-100 p-4 shadow-xl rounded-2xl min-w-[200px]">
                          <div className="flex justify-between items-center mb-3 border-b border-slate-50 pb-2">
                            <p className="font-bold text-slate-900">{dateLabel}</p>
                            <p className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">${total.toFixed(2)}</p>
                          </div>
                          <div className="space-y-2">
                            {payload.map((entry: any, index: number) => (
                              <div key={index} className="flex justify-between items-center text-xs">
                                <div className="flex items-center gap-2">
                                  <div className="w-2 h-2 rounded-full" style={{backgroundColor: entry.color}}></div>
                                  <span className="text-slate-500">{entry.name}</span>
                                </div>
                                <span className="font-semibold text-slate-900">${Number(entry.value).toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {data.breakdown.map((entry: any, index: number) => (
                  <Bar 
                    key={entry.label} 
                    dataKey={entry.label} 
                    stackId="a" 
                    fill={getComponentColor(entry.label)}
                    opacity={0.85}
                    radius={index === data.breakdown.length - 1 ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                    barSize={breakdownRange > 12 ? 15 : 25}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-2 mt-8 justify-center border-t border-slate-50 pt-6">
            {data.breakdown.map((item: any) => (
              <div key={item.label} className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold">
                <div className="w-2.5 h-2.5 rounded-sm" style={{backgroundColor: getComponentColor(item.label)}}></div>
                <span className="text-slate-400">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Trend Chart */}
        <div className="card p-6">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Cost Trend & YoY Change</h3>
              <p className="text-xs text-slate-400 mt-0.5">Historical bill vs regional growth percentage</p>
            </div>
            <TimeRangeSelector 
              value={trendRange} 
              onChange={setTrendRange} 
              options={[12, 24, 36]} 
            />
          </div>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trendData} margin={{ left: -15, right: 10, top: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis 
                  dataKey="month" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 11}}
                  tickFormatter={(val) => {
                    const [y, m] = val.split('-');
                    return m === '01' ? y : (m === '07' ? val.split('-')[1] : '');
                  }}
                />
                <YAxis 
                  yAxisId="left"
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 11}}
                  tickFormatter={(val) => `$${val}`}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94A3B8', fontSize: 11}}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip 
                  cursor={{ fill: '#F8FAFC' }}
                  contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', padding: '12px' }}
                  labelFormatter={(label) => {
                    const [y, m] = label.split('-');
                    return new Date(parseInt(y), parseInt(m) - 1).toLocaleString('default', { month: 'long', year: 'numeric' });
                  }}
                />
                <Legend verticalAlign="top" align="right" height={36} iconType="circle" />
                <Bar 
                  yAxisId="right"
                  dataKey="yoy" 
                  name="YoY %" 
                  radius={[4, 4, 4, 4]}
                  barSize={12}
                >
                  {trendData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.yoy > 0 ? '#EF4444' : '#22C55E'} opacity={0.6} />
                  ))}
                </Bar>
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="bill" 
                  name="Total Bill" 
                  stroke="#2563EB" 
                  strokeWidth={2.5} 
                  dot={false}
                  activeDot={{ r: 5, strokeWidth: 0, fill: '#2563EB' }}
                  animationDuration={1000}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;
