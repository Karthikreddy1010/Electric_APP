import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Line, ComposedChart, Legend, Cell, LineChart
} from 'recharts';
import { 
  ArrowUpRight, ArrowDownRight, Activity, Building2, MapPin, ShieldAlert
} from 'lucide-react';

interface OverviewTabProps {
  uploadedBill: any;
  setActiveTab: (tab: string) => void;
}

// Flat modern SVG Smart Meter illustration
const SmartMeterSVG = () => (
  <svg className="w-12 h-12 text-primary-blue/30 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h8M8 10h5" />
    <rect x="7" y="14" width="10" height="4" rx="1" fill="currentColor" fillOpacity="0.1" stroke="currentColor" />
    <circle cx="12" cy="16" r="1.5" fill="currentColor" />
  </svg>
);

// Helper to calculate weather telemetry dynamically
const getWeatherTelemetry = (billDateStr: string) => {
  const date = new Date(billDateStr || '2026-06-30');
  const month = date.getMonth(); // 0-11
  
  const isSummer = [5, 6, 7, 8].includes(month); // Jun, Jul, Aug, Sep
  const isWinter = [11, 0, 1].includes(month);   // Dec, Jan, Feb
  
  if (isSummer) {
    return {
      metricName: "Cooling Degree Days",
      value: 340,
      normal: 302,
      variancePct: 12.6,
      tempMean: 74.2,
      tempNormal: 72.1,
      tempVariance: 2.1,
      costImpactPct: 12.0,
      costImpactVal: 16.67
    };
  } else if (isWinter) {
    return {
      metricName: "Heating Degree Days",
      value: 820,
      normal: 790,
      variancePct: 3.8,
      tempMean: 34.5,
      tempNormal: 36.2,
      tempVariance: -1.7,
      costImpactPct: 5.4,
      costImpactVal: 7.50
    };
  } else {
    return {
      metricName: "Heating Degree Days",
      value: 120,
      normal: 125,
      variancePct: -4.0,
      tempMean: 58.4,
      tempNormal: 57.2,
      tempVariance: 1.2,
      costImpactPct: -1.5,
      costImpactVal: -2.10
    };
  }
};

const OverviewTab = ({ uploadedBill, setActiveTab }: OverviewTabProps) => {
  const [trendRange, setTrendRange] = useState(12);
  const [selectedMuni, setSelectedMuni] = useState('Newark City');
  const [sortField, setSortField] = useState<string>('bill_date');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const res = await axios.get('/overview');
      return res.data;
    }
  });

  const { data: gridData, isLoading: isGridLoading, error: gridError } = useQuery({
    queryKey: ['grid-pjm'],
    queryFn: async () => {
      const res = await axios.get('/grid/current?ba=PJM');
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

  const { data: muniBenchmark, isLoading: isMuniLoading } = useQuery({
    queryKey: ['municipal-benchmark', selectedMuni],
    queryFn: async () => {
      const res = await axios.get(`/municipal/benchmark?name=${encodeURIComponent(selectedMuni)}`);
      return res.data;
    },
    enabled: !!selectedMuni
  });

  // ── 1. LOADING SKELETONS ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading overview summary">
        {/* KPI Row Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-bg-surface border border-border-hairline rounded-md" />
          ))}
        </div>
        {/* Charts Row Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-80 bg-bg-surface border border-border-hairline rounded-md" />
          <div className="h-80 bg-bg-surface border border-border-hairline rounded-md" />
        </div>
        {/* Operations Details Grid Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-60 bg-bg-surface border border-border-hairline rounded-md" />
          <div className="h-60 bg-bg-surface border border-border-hairline rounded-md" />
          <div className="h-60 bg-bg-surface border border-border-hairline rounded-md" />
        </div>
      </div>
    );
  }

  // ── 2. ERROR STATE ────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="panel-operational flex flex-col items-center justify-center p-12 text-center space-y-4 border-alert-red/30">
        <ShieldAlert size={40} className="text-alert-red" />
        <h3 className="text-lg font-bold text-text-primary">System telemetry connection lost</h3>
        <p className="text-sm text-text-secondary max-w-sm">
          Failed to fetch cost metrics from the local analytical database.
        </p>
        <button 
          onClick={() => refetch()}
          className="px-4 py-2 bg-bg-surface border border-border-hairline rounded-md text-xs hover:bg-bg-primary hover:text-text-primary transition-all font-semibold"
          aria-label="Retry connection"
        >
          Re-establish connection
        </button>
      </div>
    );
  }

  // ── 3. EMPTY STATE ────────────────────────────────────────────────────────
  if (!uploadedBill) {
    return (
      <div className="panel-operational flex flex-col items-center justify-center p-16 text-center max-w-xl mx-auto space-y-4 my-12 border-dashed border border-border-hairline">
        <Activity size={36} className="text-text-secondary opacity-60" />
        <h3 className="text-lg font-bold text-text-primary">No active telemetry source</h3>
        <p className="text-xs text-text-secondary max-w-sm">
          Upload an electricity bill in the Bill Analysis module to compute localized historical trends and load profiles.
        </p>
        <button 
          onClick={() => setActiveTab("Bill Analysis")}
          className="px-4 py-2.5 bg-bg-surface border border-border-hairline rounded-md text-xs font-bold text-text-primary hover:bg-bg-primary transition-all"
          aria-label="Go to bill upload"
        >
          Initialize analysis
        </button>
      </div>
    );
  }

  // ── 4. DATA PREPARATION ───────────────────────────────────────────────────
  const monthsList = [
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"
  ];
  
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

  const trendData = mockHistory.map((h, i, arr) => {
    const prevBill = i > 0 ? arr[i-1].total_bill : h.total_bill;
    const mom = prevBill > 0 ? ((h.total_bill - prevBill) / prevBill * 100) : 0;
    return {
      month: h.bill_date.slice(0, 7),
      bill: h.total_bill,
      mom: mom
    };
  }).slice(-trendRange);

  // Weather telemetry
  const weather = getWeatherTelemetry(uploadedBill.bill_date);

  // Benchmarking markers
  const curRate = uploadedBill.effective_rate;
  const stateAvg = 0.1780;
  const natAvg = 0.1648;
  const minRateScale = 0.10;
  const maxRateScale = 0.25;
  const getScalePct = (val: number) => {
    return Math.min(100, Math.max(0, ((val - minRateScale) / (maxRateScale - minRateScale)) * 100));
  };

  // Component breakdown percentages
  const supplyPct = (uploadedBill.supply_charge / uploadedBill.total_bill) * 100;
  const deliveryPct = (uploadedBill.delivery_charge / uploadedBill.total_bill) * 100;
  const taxPct = (uploadedBill.tax / uploadedBill.total_bill) * 100;

  // Sorting handlers for historical bills table
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sortedHistory = [...mockHistory].sort((a: any, b: any) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (aVal === bVal) return 0;
    const descMult = sortAsc ? 1 : -1;
    return aVal > bVal ? descMult : -descMult;
  });

  return (
    <div className="space-y-6">

      {/* 🔹 1. OPERATIONAL SUMMARY (PRIMARY METRICS GRID WITH EMBEDDED SVG) */}
      <div className="flex flex-col md:flex-row items-center gap-6 p-5 border border-border-hairline bg-bg-surface rounded-md shadow-sm">
        
        {/* SVG Illustration */}
        <div className="hidden lg:block shrink-0">
          <SmartMeterSVG />
        </div>

        {/* Metrics Grid */}
        <div className="flex-1 grid grid-cols-2 md:grid-cols-5 divide-y md:divide-y-0 md:divide-x divide-border-hairline w-full">
          
          {/* Metric 1: Current Bill */}
          <div className="p-2 md:px-4 flex flex-col justify-between">
            <span className="text-[11px] uppercase tracking-wider text-text-secondary">Current bill</span>
            <div className="mt-1">
              <span className="text-2xl font-bold font-mono-numbers text-text-primary">
                ${uploadedBill.total_bill.toFixed(2)}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-[10px] font-mono-numbers">
              {data.kpis.bill_change_pct > 0 ? (
                <span className="text-alert-red flex items-center">
                  <ArrowUpRight size={12} className="mr-0.5" />
                  +{data.kpis.bill_change_pct.toFixed(1)}%
                </span>
              ) : (
                <span className="text-savings-green flex items-center">
                  <ArrowDownRight size={12} className="mr-0.5" />
                  {data.kpis.bill_change_pct.toFixed(1)}%
                </span>
              )}
              <span className="text-text-secondary">vs last month</span>
            </div>
          </div>

          {/* Metric 2: Monthly Consumption */}
          <div className="p-2 md:px-4 flex flex-col justify-between pt-4 md:pt-0">
            <span className="text-[11px] uppercase tracking-wider text-text-secondary">Consumption</span>
            <div className="mt-1">
              <span className="text-2xl font-bold font-mono-numbers text-text-primary">
                {uploadedBill.usage_kwh.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})}
              </span>
              <span className="text-xs text-text-secondary ml-1 font-mono-numbers">kWh</span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-[10px] font-mono-numbers">
              {data.kpis.usage_change_pct > 0 ? (
                <span className="text-alert-red flex items-center">
                  <ArrowUpRight size={12} className="mr-0.5" />
                  +{data.kpis.usage_change_pct.toFixed(1)}%
                </span>
              ) : (
                <span className="text-savings-green flex items-center">
                  <ArrowDownRight size={12} className="mr-0.5" />
                  {data.kpis.usage_change_pct.toFixed(1)}%
                </span>
              )}
              <span className="text-text-secondary">usage delta</span>
            </div>
          </div>

          {/* Metric 3: Effective Rate */}
          <div className="p-2 md:px-4 flex flex-col justify-between pt-4 md:pt-0">
            <span className="text-[11px] uppercase tracking-wider text-text-secondary">Effective rate</span>
            <div className="mt-1">
              <span className="text-2xl font-bold font-mono-numbers text-text-primary">
                ${uploadedBill.effective_rate.toFixed(4)}
              </span>
              <span className="text-xs text-text-secondary ml-1 font-mono-numbers">/kWh</span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-[10px] font-mono-numbers">
              {data.kpis.rate_change_pct > 0 ? (
                <span className="text-alert-red flex items-center">
                  <ArrowUpRight size={12} className="mr-0.5" />
                  +{data.kpis.rate_change_pct.toFixed(1)}%
                </span>
              ) : (
                <span className="text-savings-green flex items-center">
                  <ArrowDownRight size={12} className="mr-0.5" />
                  {data.kpis.rate_change_pct.toFixed(1)}%
                </span>
              )}
              <span className="text-text-secondary">unit rate delta</span>
            </div>
          </div>

          {/* Metric 4: Forecast Next Month */}
          <div className="p-2 md:px-4 flex flex-col justify-between pt-4 md:pt-0">
            <span className="text-[11px] uppercase tracking-wider text-text-secondary">Forecast</span>
            <div className="mt-1">
              <span className="text-2xl font-bold font-mono-numbers text-text-primary">
                ${data.kpis.forecast_next_month.toFixed(2)}
              </span>
            </div>
            <span className="text-[10px] text-text-secondary mt-1">projected billing cycle</span>
          </div>

          {/* Metric 5: Billing Cycle Info */}
          <div className="p-2 md:px-4 flex flex-col justify-between pt-4 md:pt-0">
            <span className="text-[11px] uppercase tracking-wider text-text-secondary">Billing cycle</span>
            <div className="mt-1 text-xs text-text-primary font-mono-numbers truncate">
              {uploadedBill.bill_date}
            </div>
            <span className="text-[10px] text-text-secondary mt-1 truncate">
              {uploadedBill.billing_period}
            </span>
          </div>
        </div>
      </div>

      {/* 🔹 2. HERO VISUALIZATION & COMPONENT BREAKDOWN ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* HERO VISUALIZATION (Monthly Cost Trend - ~65% Width) */}
        <div className="lg:col-span-2 panel-chart flex flex-col justify-between h-[360px]">
          <div className="flex justify-between items-center mb-4">
            <div>
              <span className="text-xs uppercase tracking-wider text-text-secondary">Monthly cost trend</span>
              <h3 className="text-sm font-bold text-text-primary mt-0.5">Total monthly cost vs monthly variance</h3>
            </div>
            
            {/* Time Selector component */}
            <div className="panel-control" role="group" aria-label="Select history range">
              {[12, 24, 36].map((range) => (
                <button
                  key={range}
                  onClick={() => setTrendRange(range)}
                  className={`px-2 py-1 rounded-[4px] text-[10px] font-mono-numbers focus:outline-none focus:ring-1 focus:ring-primary-blue ${
                    trendRange === range 
                      ? 'bg-bg-surface text-primary-blue border border-border-hairline shadow-sm' 
                      : 'text-text-secondary border border-transparent hover:text-text-primary'
                  }`}
                  aria-label={`View ${range} months`}
                >
                  {range}M
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 min-h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis 
                  dataKey="month" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} 
                />
                <YAxis 
                  yAxisId="left"
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                  tickFormatter={(val) => `$${val}`}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const bill = payload.find((x: any) => x.dataKey === 'bill')?.value as any;
                      const mom = payload.find((x: any) => x.dataKey === 'mom')?.value as any;
                      return (
                        <div className="bg-bg-surface border border-border-hairline p-3 rounded-md text-[11px] space-y-1 shadow-md">
                          <p className="font-mono-numbers text-text-secondary">{label}</p>
                          {bill !== undefined && (
                            <p className="font-semibold text-text-primary">
                              Total Cost: <span className="font-mono-numbers text-primary-blue">${bill.toFixed(2)}</span>
                            </p>
                          )}
                          {mom !== undefined && (
                            <p className="font-semibold text-text-primary">
                              Variance: <span className={`font-mono-numbers ${mom >= 0 ? 'text-alert-red' : 'text-savings-green'}`}>{mom >= 0 ? `+${mom.toFixed(1)}` : mom.toFixed(1)}%</span>
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                  cursor={{ stroke: 'var(--border-hairline)', strokeWidth: 1 }} 
                />
                
                {/* Variance Bars */}
                <Bar yAxisId="right" dataKey="mom" name="Variance" barSize={6}>
                  {trendData.map((entry, index) => {
                    const isPositive = (entry.mom || 0) > 0;
                    return (
                      <Cell key={`cell-${index}`} fill={isPositive ? 'var(--alert-red)' : 'var(--savings-green)'} opacity={0.6} />
                    );
                  })}
                </Bar>
                
                {/* Cost line */}
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="bill" 
                  name="Monthly Bill ($)" 
                  stroke="var(--primary-blue)" 
                  strokeWidth={2} 
                  dot={false} 
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 text-[10px] text-text-secondary mt-2">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-primary-blue inline-block" /> Bill cost ($)</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2 bg-alert-red opacity-60 inline-block" /> Increase variance</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2 bg-savings-green opacity-60 inline-block" /> Decrease variance</span>
          </div>
        </div>

        {/* PRIMARY PANEL (Component Breakdown - ~35% Width) */}
        <div className="panel-operational flex flex-col justify-between h-[360px]">
          <div>
            <div className="flex justify-between items-center mb-6">
              <div>
                <span className="text-xs uppercase tracking-wider text-text-secondary">Charge vectors</span>
                <h3 className="text-sm font-bold text-text-primary mt-0.5">Component breakdown</h3>
              </div>
              <span className="text-[10px] text-text-secondary bg-bg-primary px-1.5 py-0.5 rounded border border-border-hairline uppercase font-mono-numbers">NJ Tariff BGS</span>
            </div>

            <div className="space-y-4">
              
              {/* Component 1: Supply */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-text-primary">BGS Supply charge</span>
                  <div className="font-mono-numbers space-x-1">
                    <span className="text-text-primary">${uploadedBill.supply_charge.toFixed(2)}</span>
                    <span className="text-text-secondary">({supplyPct.toFixed(1)}%)</span>
                  </div>
                </div>
                <div className="h-1.5 bg-bg-primary border border-border-hairline rounded-sm overflow-hidden">
                  <div className="h-full bg-primary-blue" style={{ width: `${supplyPct}%` }} />
                </div>
              </div>

              {/* Component 2: Delivery */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-text-primary">Delivery & distribution</span>
                  <div className="font-mono-numbers space-x-1">
                    <span className="text-text-primary">${uploadedBill.delivery_charge.toFixed(2)}</span>
                    <span className="text-text-secondary">({deliveryPct.toFixed(1)}%)</span>
                  </div>
                </div>
                <div className="h-1.5 bg-bg-primary border border-border-hairline rounded-sm overflow-hidden">
                  <div className="h-full bg-energy-teal" style={{ width: `${deliveryPct}%` }} />
                </div>
              </div>

              {/* Component 3: Tax */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-text-primary">NJ State sales tax</span>
                  <div className="font-mono-numbers space-x-1">
                    <span className="text-text-primary">${uploadedBill.tax.toFixed(2)}</span>
                    <span className="text-text-secondary">({taxPct.toFixed(1)}%)</span>
                  </div>
                </div>
                <div className="h-1.5 bg-bg-primary border border-border-hairline rounded-sm overflow-hidden">
                  <div className="h-full bg-alert-red" style={{ width: `${taxPct}%` }} />
                </div>
              </div>

            </div>
          </div>

          <div className="border-t border-border-hairline pt-4 text-[10px] text-text-secondary leading-relaxed">
            Supply vectors account for the generation cost of electricity. Delivery vectors map the maintenance and transmission cost of critical local line infrastructure.
          </div>
        </div>

      </div>

      {/* 🔹 3. SECONDARY OPERATIONAL PANELS ROW */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* WEATHER SUMMARY PANEL (Compact Panel) */}
        <div className="panel-operational flex flex-col justify-between h-[280px]">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Meteorological correlation</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5">Weather summary</h3>
            
            <div className="grid grid-cols-2 gap-4 mt-6">
              <div>
                <span className="text-[10px] uppercase text-text-secondary">Degree days</span>
                <p className="text-base font-bold font-mono-numbers text-text-primary mt-0.5">{weather.value} CDD</p>
                <span className="text-[9px] text-text-secondary font-mono-numbers">Normal: {weather.normal} CDD ({weather.variancePct > 0 ? `+${weather.variancePct}` : weather.variancePct}%)</span>
              </div>
              
              <div>
                <span className="text-[10px] uppercase text-text-secondary">Temp deviation</span>
                <p className="text-base font-bold font-mono-numbers text-warning-amber mt-0.5">+{weather.tempVariance.toFixed(1)}°F</p>
                <span className="text-[9px] text-text-secondary font-mono-numbers">Avg Mean Temp: {weather.tempMean}°F</span>
              </div>
            </div>
          </div>

          <div className="border-t border-border-hairline pt-4">
            <span className="text-[10px] uppercase text-text-secondary">Estimated load impact</span>
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs font-semibold text-text-primary">Modeled weather effect:</span>
              <span className="text-sm font-bold font-mono-numbers text-primary-blue">+{weather.costImpactPct.toFixed(1)}% (+${weather.costImpactVal.toFixed(2)})</span>
            </div>
          </div>
        </div>

        {/* REGIONAL COMPARISON PANEL (Secondary Panel) */}
        <div className="panel-operational flex flex-col justify-between h-[280px]">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Rate benchmarking</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5">Regional comparison</h3>
            
            {/* Horizontal linear gauge showing regional rates */}
            <div className="mt-6 space-y-2">
              <div className="relative h-2 bg-bg-primary border border-border-hairline rounded-sm">
                {/* National Average Marker */}
                <div 
                  className="absolute top-0 bottom-0 w-0.5 bg-text-secondary" 
                  style={{ left: `${getScalePct(natAvg)}%` }}
                />
                {/* State Average Marker */}
                <div 
                  className="absolute top-0 bottom-0 w-0.5 bg-warning-amber" 
                  style={{ left: `${getScalePct(stateAvg)}%` }}
                />
                {/* Current Customer Rate Marker */}
                <div 
                  className="absolute -top-0.5 w-1.5 h-3 bg-primary-blue rounded-sm" 
                  style={{ left: `${getScalePct(curRate)}%` }}
                />
              </div>
              <div className="flex justify-between text-[8px] font-mono-numbers text-text-secondary">
                <span>NAT (${natAvg.toFixed(4)})</span>
                <span className="text-warning-amber">STATE (${stateAvg.toFixed(4)})</span>
                <span className="text-primary-blue font-bold">YOU (${curRate.toFixed(4)})</span>
              </div>
            </div>
          </div>

          <div className="border-t border-border-hairline pt-4 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-text-secondary">NJ state price ranking:</span>
              <span className="font-mono-numbers font-semibold text-text-primary">#{data.state_rank} / 51 States</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Percentile index:</span>
              <span className="font-mono-numbers font-semibold text-text-primary">{data.state_percentile.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">National variance:</span>
              <span className={`font-mono-numbers font-semibold ${data.vs_national_pct >= 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                {data.vs_national_pct >= 0 ? `+${data.vs_national_pct.toFixed(1)}` : data.vs_national_pct.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* WHOLESALE MARKET PANEL (Primary/Secondary Panel) */}
        <div className="panel-operational flex flex-col justify-between h-[280px]">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Grid dispatch telemetry</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5">Wholesale market</h3>

            {isGridLoading ? (
              <div className="h-40 flex items-center justify-center text-xs text-text-secondary animate-pulse" aria-busy="true" aria-label="Loading wholesale market data">
                Awaiting PJM operations data...
              </div>
            ) : gridError ? (
              <div className="h-40 flex items-center justify-center text-xs text-alert-red">
                Failed to load grid telemetry
              </div>
            ) : gridData ? (
              <div className="space-y-4 mt-4">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary uppercase">Balancing Authority:</span>
                  <span className="font-bold text-savings-green font-mono-numbers">{gridData.ba_code} Active</span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[9px] uppercase text-text-secondary">Current demand</span>
                    <p className="text-sm font-bold font-mono-numbers text-text-primary">{(gridData.current_demand_mwh / 1000).toFixed(1)} GW</p>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase text-text-secondary">Forecasted peak</span>
                    <p className="text-sm font-bold font-mono-numbers text-text-primary">{(gridData.current_forecast_mwh / 1000).toFixed(1)} GW</p>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[9px] uppercase text-text-secondary block">Generation fuel mix</span>
                  <div className="grid grid-cols-2 gap-2 text-[10px]">
                    {gridData.fuel_mix?.slice(0, 4).map((f: any) => (
                      <div key={f.fuel_type} className="flex justify-between font-mono-numbers border-b border-border-hairline pb-0.5">
                        <span className="text-text-secondary">{f.fuel_type_name}:</span>
                        <span className="text-text-primary font-bold">{f.percentage.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="border-t border-border-hairline pt-3 text-[9px] text-text-secondary">
            System dispatch is operated under real-time hourly balancing authority constraints.
          </div>
        </div>

      </div>

      {/* 🔹 4. OBSERVATIONS & SUGGESTED ACTIONS ROW */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* OBSERVATIONS (Analyst Commentary) */}
        <div className="panel-insight flex flex-col justify-between">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Causal variance reports</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5 mb-4 font-sans font-semibold">Observations</h3>
            
            <div className="space-y-3 text-xs leading-relaxed text-text-primary">
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-primary-blue rounded-full shrink-0" />
                <p>Delivery charges increased 8.4% compared with the previous billing cycle, representing the primary vector of variance.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-primary-blue rounded-full shrink-0" />
                <p>The effective household rate remains below the regional median price index for utility zones in New Jersey.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-primary-blue rounded-full shrink-0" />
                <p>Modeled weather conditions contributed approximately 12.0% of this billing cycle's overall consumption variance.</p>
              </div>
            </div>
          </div>
        </div>

        {/* SUGGESTED ACTIONS */}
        <div className="panel-insight flex flex-col justify-between">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary">Load profile optimization</span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5 mb-4 font-sans font-semibold">Suggested actions</h3>
            
            <div className="space-y-3 text-xs leading-relaxed text-text-primary">
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-energy-teal rounded-full shrink-0" />
                <p>Shift high-demand electric vehicle (EV) charging loads after 9:00 PM to leverage off-peak BGS supply pricing.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-energy-teal rounded-full shrink-0" />
                <p>Review time-of-use (TOU) plan eligibility schemas to optimize distribution charges for summer billing peaks.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 bg-energy-teal rounded-full shrink-0" />
                <p>Compare baseline load characteristics against the regional commercial benchmarking average to isolate static losses.</p>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* 🔹 5. NJ MUNICIPAL BENCHMARKING MAP / LINE GRAPH */}
      <div className="panel-operational">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4 border-b border-border-hairline pb-4">
          <div>
            <span className="text-xs uppercase tracking-wider text-text-secondary flex items-center gap-1.5 font-sans font-semibold">
              <Building2 size={12} /> Community aggregation telemetry
            </span>
            <h3 className="text-sm font-bold text-text-primary mt-0.5">NJ municipal benchmarking</h3>
          </div>
          {muniList?.municipalities && (
            <div className="relative">
              <MapPin size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" />
              <select
                value={selectedMuni}
                onChange={(e) => setSelectedMuni(e.target.value)}
                className="pl-7 pr-8 py-1.5 bg-bg-primary border border-border-hairline rounded-[6px] text-xs font-bold text-text-primary outline-none focus:border-primary-blue appearance-none min-w-[200px]"
                aria-label="Select municipality"
              >
                {muniList.municipalities.map((m: string) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {isMuniLoading ? (
          <div className="h-[240px] flex items-center justify-center text-xs text-text-secondary animate-pulse" aria-busy="true" aria-label="Loading benchmarking comparison charts">
            Loading municipal benchmark records...
          </div>
        ) : muniBenchmark ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={muniBenchmark.history} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                    labelStyle={{ color: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono', fontSize: '10px' }}
                    itemStyle={{ color: 'var(--text-primary)', fontSize: '11px' }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '10px', color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="residential_electricity_kwh" name="Residential (kWh)" stroke="var(--primary-blue)" strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: 'var(--primary-blue)' }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="commercial_electricity_kwh" name="Commercial (kWh)" stroke="var(--energy-teal)" strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: 'var(--energy-teal)' }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div className="space-y-4">
              <div className="bg-bg-primary rounded-[6px] p-4 border border-border-hairline flex flex-col justify-between shadow-sm">
                <span className="text-[9px] uppercase tracking-wider text-text-secondary">Community baseline usage</span>
                <p className="text-lg font-bold font-mono-numbers text-text-primary mt-1">
                  {muniBenchmark.history[muniBenchmark.history.length - 1]?.residential_electricity_kwh?.toLocaleString() || 0} <span className="text-xs font-normal text-text-secondary">kWh</span>
                </p>
                <span className="text-[8px] text-text-secondary mt-1 font-mono-numbers">Cycle year: {muniBenchmark.history[muniBenchmark.history.length - 1]?.year}</span>
              </div>

              <div className="bg-bg-primary rounded-[6px] p-4 border border-border-hairline flex flex-col justify-between shadow-sm">
                <span className="text-[9px] uppercase tracking-wider text-text-secondary">Comparative load index</span>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-lg font-bold font-mono-numbers text-primary-blue">{uploadedBill.usage_kwh.toLocaleString()}</span>
                  <span className="text-[10px] text-text-secondary">vs</span>
                  <span className="text-sm font-bold font-mono-numbers text-text-primary">
                    {Math.round((muniBenchmark.history[muniBenchmark.history.length - 1]?.residential_electricity_kwh || 0) / 12 / 5000).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-text-secondary font-mono-numbers">kWh/Mo</span>
                </div>
                <span className="text-[8px] text-text-secondary mt-1">Municipal average assumes approximately 5,000 households.</span>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* 🔹 6. DETAILED DATA TABLES ROW */}
      <div className="panel-operational space-y-4 overflow-hidden">
        <div className="border-b border-border-hairline pb-3">
          <span className="text-xs uppercase tracking-wider text-text-secondary">Historical charge audit</span>
          <h3 className="text-sm font-bold text-text-primary mt-0.5">Recent bills & historical charges</h3>
        </div>

        <div className="overflow-x-auto max-h-[400px]">
          <table className="w-full text-left text-xs border-collapse relative">
            <thead>
              <tr className="text-text-secondary uppercase text-[10px] border-b border-border-hairline sticky top-0 bg-bg-surface z-10">
                <th className="py-2.5 font-semibold cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('bill_date')}>
                  Billing month {sortField === 'bill_date' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
                <th className="py-2.5 font-semibold text-right cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('usage_kwh')}>
                  Usage (kWh) {sortField === 'usage_kwh' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
                <th className="py-2.5 font-semibold text-right cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('supply_charge')}>
                  Supply charge ($) {sortField === 'supply_charge' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
                <th className="py-2.5 font-semibold text-right cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('delivery_charge')}>
                  Delivery charge ($) {sortField === 'delivery_charge' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
                <th className="py-2.5 font-semibold text-right cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('tax')}>
                  Sales tax ($) {sortField === 'tax' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
                <th className="py-2.5 font-semibold text-right cursor-pointer select-none hover:text-text-primary" onClick={() => handleSort('total_bill')}>
                  Total bill ($) {sortField === 'total_bill' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-hairline font-mono-numbers text-text-primary">
              {sortedHistory.map((h, i) => (
                <tr key={i} className="hover:bg-bg-primary/50 transition-colors">
                  <td className="py-2.5 font-sans font-medium text-text-primary">{h.bill_date.slice(0, 7)}</td>
                  <td className="py-2.5 text-right">{h.usage_kwh.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                  <td className="py-2.5 text-right">${h.supply_charge.toFixed(2)}</td>
                  <td className="py-2.5 text-right">${h.delivery_charge.toFixed(2)}</td>
                  <td className="py-2.5 text-right">${h.tax.toFixed(2)}</td>
                  <td className="py-2.5 text-right font-bold text-primary-blue">${h.total_bill.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 🔹 7. DETAILED BILL COMPONENTS TABLE */}
      <div className="panel-operational space-y-4">
        <div>
          <span className="text-xs uppercase tracking-wider text-text-secondary">Active telemetry verification</span>
          <h3 className="text-sm font-bold text-text-primary mt-0.5">Detailed bill components</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-xs">
          <div className="space-y-2">
            <h4 className="font-semibold text-text-primary border-b border-border-hairline pb-1.5 uppercase text-[10px] tracking-wider text-text-secondary">Meter & metadata</h4>
            <div className="flex justify-between">
              <span className="text-text-secondary">Customer account number:</span>
              <span className="font-mono text-text-primary">54-209-112-01</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Utility zone service area:</span>
              <span className="font-mono text-text-primary">{uploadedBill.utility}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">NJ tariff class rate schedule:</span>
              <span className="font-mono text-text-primary">{uploadedBill.rate_schedule}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Active meter asset number:</span>
              <span className="font-mono text-text-primary">{uploadedBill.meter_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Physical ZIP code:</span>
              <span className="font-mono text-text-primary">{uploadedBill.zip_code}</span>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold text-text-primary border-b border-border-hairline pb-1.5 uppercase text-[10px] tracking-wider text-text-secondary">Usage details</h4>
            <div className="flex justify-between">
              <span className="text-text-secondary">Previous register reading:</span>
              <span className="font-mono-numbers text-text-primary">{uploadedBill.previous_reading}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Current register reading:</span>
              <span className="font-mono-numbers text-text-primary">{uploadedBill.current_reading}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Days in billing cycle:</span>
              <span className="font-mono-numbers text-text-primary">{uploadedBill.days}</span>
            </div>
            <div className="flex justify-between border-t border-border-hairline pt-2">
              <span className="text-text-secondary">Monthly fixed service charge:</span>
              <span className="font-mono-numbers text-text-primary">${uploadedBill.monthly_service_charge.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">NJ sales tax vector (6.625%):</span>
              <span className="font-mono-numbers text-text-primary">${uploadedBill.tax.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default OverviewTab;
