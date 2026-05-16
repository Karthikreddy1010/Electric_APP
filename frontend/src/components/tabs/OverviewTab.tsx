import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Cell
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
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="month" hide />
                <YAxis yAxisId="left" hide />
                <YAxis yAxisId="right" orientation="right" hide />
                <Tooltip />
                <Bar yAxisId="right" dataKey="yoy" name="YoY %" barSize={12}>
                  {trendData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.yoy > 0 ? '#EF4444' : '#22C55E'} />
                  ))}
                </Bar>
                <Line yAxisId="left" type="monotone" dataKey="bill" name="Total Bill" stroke="#2563EB" strokeWidth={2.5} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;
