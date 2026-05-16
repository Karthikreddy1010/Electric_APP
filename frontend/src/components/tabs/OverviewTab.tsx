import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Legend, Area, Cell
} from 'recharts';
import { ArrowUpRight, ArrowDownRight, Zap, TrendingUp, DollarSign } from 'lucide-react';

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
  if (l.includes('bgs') || l.includes('generation')) return COLORS.generation;
  if (l.includes('transmission')) return COLORS.transmission;
  if (l.includes('distribution')) return COLORS.distribution;
  if (l.includes('tax')) return COLORS.tax;
  if (l.includes('societal') || l.includes('sbc')) return COLORS.sbc;
  if (l.includes('nug')) return COLORS.nug;
  if (l.includes('customer')) return COLORS.customer;
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

const OverviewTab = () => {
  const [breakdownRange, setBreakdownRange] = useState(12);
  const [trendRange, setTrendRange] = useState(36);

  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const res = await axios.get('/overview');
      return res.data;
    }
  });

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mt-20" />;
  if (error) return <div className="text-red-500 p-8">Failed to load dashboard data.</div>;

  const filteredBreakdown = data.historical_breakdown.slice(-breakdownRange);
  const trendData = data.trends.months.map((m: any, i: number) => ({
    month: m,
    bill: data.trends.total_bills[i],
    yoy: data.trends.yoy_changes[i]
  })).slice(-trendRange);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex justify-between items-start mb-4">
            <DollarSign size={20} className="text-blue-600" />
            <div className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg ${data.kpis.bill_change_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
              {data.kpis.bill_change_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {Math.abs(data.kpis.bill_change_pct).toFixed(1)}%
            </div>
          </div>
          <p className="text-sm font-medium text-slate-500">Current Bill</p>
          <h2 className="text-3xl font-bold">${data.kpis.current_bill.toFixed(2)}</h2>
        </div>
        <div className="card p-6">
          <Zap size={20} className="text-purple-600 mb-4" />
          <p className="text-sm font-medium text-slate-500">Usage</p>
          <h2 className="text-3xl font-bold">{data.kpis.usage_kwh.toLocaleString()} kWh</h2>
        </div>
        <div className="card p-6">
          <TrendingUp size={20} className="text-emerald-600 mb-4" />
          <p className="text-sm font-medium text-slate-500">Effective Rate</p>
          <h2 className="text-3xl font-bold">${data.kpis.effective_rate.toFixed(4)} /kWh</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-lg font-bold">Bill Component Breakdown</h3>
            <TimeRangeSelector value={breakdownRange} onChange={setBreakdownRange} options={[6, 12, 24]} />
          </div>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={filteredBreakdown}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="month" hide />
                <YAxis hide />
                <Tooltip />
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
        <div className="card p-6">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-lg font-bold">Cost Trend</h3>
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
                <Tooltip 
                  cursor={{stroke: '#E2E8F0', strokeWidth: 1}}
                  contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                />
                <Area yAxisId="left" type="monotone" dataKey="bill" stroke="none" fill="url(#colorBill)" />
                <Bar yAxisId="right" dataKey="yoy" name="YoY Change %" fill="#EF4444" barSize={8} radius={[2, 2, 0, 0]} opacity={0.6}>
                  {trendData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.yoy > 0 ? '#22C55E' : '#EF4444'} />
                  ))}
                </Bar>
                <Line yAxisId="left" type="monotone" dataKey="bill" name="Total Bill" stroke="#2563EB" strokeWidth={3} dot={false} />
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
    </div>
  );
};

export default OverviewTab;
