import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Cell
} from 'recharts';
import { ArrowUpRight, ArrowDownRight, Zap, TrendingUp } from 'lucide-react';

const OverviewTab = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/overview');
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500">Loading data...</div>;
  if (error) return <div className="text-red-500">Failed to load overview data.</div>;

  const kpi = data.kpis;
  const isUp = kpi.bill_change_pct > 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      {/* Primary KPI */}
      <div className="md:col-span-2 card flex flex-col justify-between">
        <div>
          <span className="text-sm font-medium text-slate-500">Current Bill</span>
          <div className="flex items-baseline gap-2 mt-1">
            <h2 className="text-4xl font-bold text-slate-900">${kpi.current_bill.toFixed(2)}</h2>
            <div className={`flex items-center text-sm font-medium ${isUp ? 'text-negative' : 'text-positive'}`}>
              {isUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
              {Math.abs(kpi.bill_change_pct).toFixed(1)}%
            </div>
          </div>
        </div>
        <div className="mt-8">
          <p className="text-sm text-slate-500">Reflects your last billing cycle's total expenditure including taxes and surcharges.</p>
        </div>
      </div>

      {/* Secondary KPIs */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><Zap className="w-5 h-5" /></div>
          <span className="text-sm font-medium text-slate-500">Usage</span>
        </div>
        <h3 className="text-2xl font-bold text-slate-900">{kpi.usage_kwh.toFixed(0)} <span className="text-lg font-medium text-slate-400">kWh</span></h3>
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-slate-50 text-slate-600 rounded-lg"><TrendingUp className="w-5 h-5" /></div>
          <span className="text-sm font-medium text-slate-500">Rate</span>
        </div>
        <h3 className="text-2xl font-bold text-slate-900">${kpi.effective_rate.toFixed(4)} <span className="text-lg font-medium text-slate-400">/kWh</span></h3>
      </div>

      {/* Breakdown Chart */}
      <div className="md:col-span-2 card">
        <h3 className="text-lg font-semibold mb-6">Bill Breakdown</h3>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={[data.breakdown]} layout="vertical" margin={{ left: 40, right: 40 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" hide />
              <Tooltip 
                cursor={{fill: 'transparent'}}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-white border border-border p-3 shadow-sm rounded-lg">
                        {payload.map((entry: any, index: number) => (
                          <div key={index} className="flex justify-between gap-4 text-sm">
                            <span className="text-slate-500">{entry.name}:</span>
                            <span className="font-medium">${entry.value}</span>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {data.breakdown.map((entry: any, index: number) => (
                <Bar 
                  key={entry.label} 
                  dataKey={() => entry.value} 
                  name={entry.label} 
                  stackId="a" 
                  fill={['#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'][index % 5]}
                  radius={index === 0 ? [4, 0, 0, 4] : index === data.breakdown.length - 1 ? [0, 4, 4, 0] : [0, 0, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          {data.breakdown.map((item: any, i: number) => (
            <div key={item.label} className="flex justify-between items-center text-xs">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{backgroundColor: ['#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'][i % 5]}}></div>
                <span className="text-slate-600">{item.label}</span>
              </div>
              <span className="font-semibold text-slate-900">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trend Chart */}
      <div className="md:col-span-2 card">
        <h3 className="text-lg font-semibold mb-6">Historical Trends</h3>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.trends.months.map((m: any, i: number) => ({
              month: m,
              bill: data.trends.total_bills[i],
              yoy: data.trends.yoy_changes[i]
            }))}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94A3B8', fontSize: 12}}
                tickFormatter={(val) => val.split('-')[1] === '01' ? val.split('-')[0] : ''}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94A3B8', fontSize: 12}}
                tickFormatter={(val) => `$${val}`}
              />
              <YAxis 
                orientation="right" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94A3B8', fontSize: 12}}
                tickFormatter={(val) => `${val}%`}
              />
              <Tooltip 
                contentStyle={{borderRadius: '8px', border: '1px solid #E5E7EB', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}
              />
              <Bar dataKey="yoy" name="YoY Change %" yAxisId={1} radius={[4, 4, 0, 0]}>
                {data.trends.yoy_changes.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry > 0 ? '#DC2626' : '#16A34A'} opacity={0.2} />
                ))}
              </Bar>
              <Line 
                type="monotone" 
                dataKey="bill" 
                name="Total Bill" 
                stroke="#2563EB" 
                strokeWidth={3} 
                dot={false}
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;
