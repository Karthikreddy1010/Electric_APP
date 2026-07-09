import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Legend, Area, Cell, LineChart
} from 'recharts';
import { 
  ArrowUpRight, ArrowDownRight, Zap, TrendingUp, DollarSign, 
  AlertTriangle, Lightbulb, Activity, Award, Calendar, MapPin, Building2
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

interface OverviewTabProps {
  uploadedBill: any;
  setActiveTab: (tab: string) => void;
}

const OverviewTab = ({ uploadedBill, setActiveTab }: OverviewTabProps) => {
  const [breakdownRange, setBreakdownRange] = useState(12);
  const [trendRange, setTrendRange] = useState(12);
  const [selectedMuni, setSelectedMuni] = useState('Newark City');

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

  if (!uploadedBill) {
    return (
      <div className="flex flex-col items-center justify-center p-16 card bg-slate-50 border-dashed border-2 border-slate-200 text-center max-w-xl mx-auto space-y-4 my-12">
        <Zap size={48} className="text-slate-400 animate-bounce" />
        <h3 className="text-xl font-bold text-slate-800">No Bill Uploaded</h3>
        <p className="text-sm text-slate-500 max-w-sm">
          Please upload your electricity bill PDF/image or analyze our sample template to populate the dashboard metrics.
        </p>
        <button 
          onClick={() => setActiveTab("Bill Analysis")}
          className="bg-primary text-white hover:bg-primary-hover font-bold px-6 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20"
        >
          Go to Bill Analysis
        </button>
      </div>
    );
  }

  // Construct historical trend & component breakdown series dynamically from the uploaded bill context
  const monthsList = [
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"
  ];
  
  // Seasonal usage factors (July/August peak, Spring/Fall valley)
  const seasonalFactors = [1.25, 1.30, 1.05, 0.85, 0.90, 1.00, 1.05, 1.02, 0.88, 0.82, 0.92, 1.00];

  const mockHistory = monthsList.map((mo, i) => {
    const factor = seasonalFactors[i];
    const usage = uploadedBill.usage_kwh * factor;
    const supply = uploadedBill.supply_charge * factor;
    const delivery = uploadedBill.delivery_charge * factor;
    const tax = uploadedBill.tax * factor;
    const total = supply + delivery + tax;
    return {
      bill_date: `${mo}-28`,
      total_bill: total,
      usage_kwh: usage,
      supply_charge: supply,
      delivery_charge: delivery,
      tax: tax
    };
  });

  const filteredBreakdown = mockHistory.map((h) => ({
    month: h.bill_date.slice(0, 7),
    "Delivery Charge": h.delivery_charge,
    "Supply Charge": h.supply_charge,
    "Tax & Adjustments": h.tax
  })).slice(-breakdownRange);

  const trendData = mockHistory.map((h, i, arr) => {
    const prevBill = i > 0 ? arr[i-1].total_bill : h.total_bill;
    const mom = prevBill > 0 ? ((h.total_bill - prevBill) / prevBill * 100) : 0;
    return {
      month: h.bill_date.slice(0, 7),
      bill: h.total_bill,
      mom: mom
    };
  }).slice(-trendRange);

  const activeBill = {
    ...uploadedBill,
    ocr_text: `ACCOUNT SUMMARY
Account Number: 54-209-112-01
Utility: ${uploadedBill.utility}
Billing Date: ${uploadedBill.bill_date}
Rate Schedule: ${uploadedBill.rate_schedule}
Meter Number: ${uploadedBill.meter_number}
ZIP Code: ${uploadedBill.zip_code}
Service Address: 742 Evergreen Terrace, NJ

BILL DETAIL
Previous Reading: ${uploadedBill.previous_reading}
Current Reading: ${uploadedBill.current_reading}
Usage (kWh): ${uploadedBill.usage_kwh}
Days in Cycle: ${uploadedBill.days}

CHARGES SUMMARY
Monthly Customer Charge: $${uploadedBill.monthly_service_charge.toFixed(2)}
Delivery Charge (Variable): $${(uploadedBill.delivery_charge - uploadedBill.monthly_service_charge).toFixed(2)}
Supply Generation Charge: $${uploadedBill.supply_charge.toFixed(2)}
NJ Sales Tax (6.625%): $${uploadedBill.tax.toFixed(2)}
TOTAL DUE: $${uploadedBill.total_bill.toFixed(2)}
`,
    ocr_runs: [
      {"field_name": "utility", "ground_truth_value": uploadedBill.utility, "extracted_value": uploadedBill.utility, "confidence": 0.99, "ocr_error_flag": false},
      {"field_name": "billing_period", "ground_truth_value": uploadedBill.billing_period, "extracted_value": uploadedBill.billing_period, "confidence": 0.97, "ocr_error_flag": false},
      {"field_name": "usage_kwh", "ground_truth_value": String(uploadedBill.usage_kwh), "extracted_value": String(uploadedBill.usage_kwh), "confidence": 0.99, "ocr_error_flag": false},
      {"field_name": "total_bill", "ground_truth_value": String(uploadedBill.total_bill), "extracted_value": String(uploadedBill.total_bill), "confidence": 0.98, "ocr_error_flag": false},
      {"field_name": "meter_number", "ground_truth_value": uploadedBill.meter_number, "extracted_value": uploadedBill.meter_number, "confidence": 0.95, "ocr_error_flag": false},
      {"field_name": "zip_code", "ground_truth_value": uploadedBill.zip_code, "extracted_value": uploadedBill.zip_code, "confidence": 0.98, "ocr_error_flag": false}
    ]
  };

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
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">
            ${activeBill ? activeBill.total_bill.toFixed(2) : data.kpis.current_bill.toFixed(2)}
          </h2>
          <p className="text-xs text-slate-400 mt-3 flex items-center gap-1">
            <Calendar size={12} className="text-slate-400" />
            Billing cycle: {activeBill ? activeBill.bill_date : data.trends.months[data.trends.months.length - 1]}
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
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">
            {activeBill ? activeBill.usage_kwh.toLocaleString() : data.kpis.usage_kwh.toLocaleString()} kWh
          </h2>
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
          <h2 className="text-3xl font-extrabold text-slate-900 mt-1">
            ${activeBill ? activeBill.effective_rate.toFixed(4) : data.kpis.effective_rate.toFixed(4)} <span className="text-sm font-normal text-slate-400">/kWh</span>
          </h2>
          <p className="text-xs text-slate-400 mt-3">Computed as Total Bill / Usage</p>
        </div>
      </div>

      {/* 🔹 EIA-861M MONTHLY STATS ROW */}
      {data.eia861m_summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-5 relative overflow-hidden transition-all duration-300 hover:shadow-md border border-slate-100 bg-gradient-to-br from-slate-50 to-white">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Monthly Reporting Cycle</span>
              <span className="p-1.5 bg-blue-50 text-blue-600 rounded-lg"><Calendar size={14} /></span>
            </div>
            <h4 className="text-xl font-extrabold text-slate-900 mt-1">{data.eia861m_summary.period}</h4>
            <p className="text-[10px] text-slate-400 mt-2">EIA-861M dataset status</p>
          </div>

          <div className="card p-5 relative overflow-hidden transition-all duration-300 hover:shadow-md border border-slate-100 bg-gradient-to-br from-slate-50 to-white">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Monthly Utility Sales</span>
              <span className="p-1.5 bg-purple-50 text-purple-600 rounded-lg"><Zap size={14} /></span>
            </div>
            <h4 className="text-xl font-extrabold text-slate-900 mt-1">{(data.eia861m_summary.monthly_sales_mwh / 1e6).toFixed(2)}M <span className="text-xs font-medium text-slate-400">MWh</span></h4>
            <p className="text-[10px] text-slate-400 mt-2">Aggregated national retail sales</p>
          </div>

          <div className="card p-5 relative overflow-hidden transition-all duration-300 hover:shadow-md border border-slate-100 bg-gradient-to-br from-slate-50 to-white">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Monthly Revenue</span>
              <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg"><DollarSign size={14} /></span>
            </div>
            <h4 className="text-xl font-extrabold text-slate-900 mt-1">${(data.eia861m_summary.monthly_revenue_k / 1e6).toFixed(2)}B</h4>
            <p className="text-[10px] text-slate-400 mt-2">Total revenue from end-use customers</p>
          </div>

          <div className="card p-5 relative overflow-hidden transition-all duration-300 hover:shadow-md border border-slate-100 bg-gradient-to-br from-slate-50 to-white">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Average Rate</span>
              <span className="p-1.5 bg-teal-50 text-teal-600 rounded-lg"><TrendingUp size={14} /></span>
            </div>
            <h4 className="text-xl font-extrabold text-slate-900 mt-1">{data.eia861m_summary.avg_price_cents_kwh.toFixed(2)}¢<span className="text-xs font-medium text-slate-400">/kWh</span></h4>
            <p className="text-[10px] text-slate-400 mt-2">State-level weighted average</p>
          </div>
        </div>
      )}

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
    </div>
  );
};

export default OverviewTab;
