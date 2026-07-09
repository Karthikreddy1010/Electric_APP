import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import {
  Trophy, TrendingUp, TrendingDown, MapPin, Activity, Info, Calendar, Building2,
  Play, Pause, ZapOff, ArrowRight
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, Legend, LineChart, Line, AreaChart, Area
} from 'recharts';
import USMap from '../USMap.tsx';
import StateZipMap from '../StateZipMap.tsx';

const REGION_COLORS: Record<string, string> = {
  Northeast: '#2F6BFF',   // Primary blue
  South: '#F5B041',       // Warning amber
  Midwest: '#16A085',     // Energy teal
  West: '#D64545',        // Alert red
};

const NJ_ZIPS = ['07101', '07201', '07301', '07401', '07501'];

// Helper function for building insights payload
function buildInsightsPayload(psegData: any[]) {
  const electricity_data: any[] = [];
  const grouped: Record<string, any[]> = {};
  psegData.forEach((row: any) => {
    const key = `${row.year}-${row.month}`;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(row);
  });

  NJ_ZIPS.forEach((zip, zi) => {
    Object.entries(grouped).forEach(([key, rows]) => {
      const [year, month] = key.split('-').map(Number);
      const validRates = rows.map((r: any) => r.total_rate_per_kwh).filter((v: any) => v != null && !isNaN(v));
      const avgPrice = validRates.length ? validRates.reduce((a: number, b: number) => a + b, 0) / validRates.length : null;
      if (!avgPrice) return;

      const baseUsage = 650 + zi * 90;
      const seasonalFactor = [1, 2, 6, 7, 8].includes(month) ? 1.25 : 0.92;
      const consumption = Math.round(baseUsage * seasonalFactor);

      electricity_data.push({
        zip_code: zip,
        state: 'NJ',
        month,
        year,
        avg_price: parseFloat(avgPrice.toFixed(5)),
        consumption_kwh: consumption,
        peak_demand: parseFloat((consumption * 0.0045).toFixed(2)),
        renewable_ratio: parseFloat((0.08 + zi * 0.04).toFixed(2)),
      });
    });
  });

  return {
    location: { state: 'NJ', zip_codes: NJ_ZIPS },
    electricity_data: electricity_data.slice(0, 60),
  };
}

const HoverTooltip = ({ visible, data, tooltipRef }: any) => {
  if (!visible || !data) return null;
  return (
    <div 
      ref={tooltipRef}
      className="fixed z-[9999] pointer-events-none bg-bg-surface text-text-primary p-4 rounded-md shadow-md border border-border-hairline transform -translate-x-1/2 -translate-y-[120%]"
      style={{ minWidth: '220px', pointerEvents: 'none' }}
    >
      <div className="flex justify-between items-end border-b border-border-hairline pb-2 mb-2">
        <h3 className="font-bold text-sm text-text-primary">{data.name || data.state || data.zip}</h3>
        <span className="text-[9px] font-bold uppercase tracking-wider text-text-secondary">{data.level || 'State'}</span>
      </div>
      <div className="space-y-1.5 text-xs font-semibold font-mono-numbers">
        <div className="flex justify-between">
          <span className="text-text-secondary font-sans font-normal">Avg bill:</span> 
          <span className="text-text-primary">${data.avg_bill ? data.avg_bill.toFixed(2) : 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary font-sans font-normal">Avg rate:</span> 
          <span className="text-text-primary">${data.avg_rate ? data.avg_rate.toFixed(4) : 'N/A'}/kWh</span>
        </div>
        {data.usage_kwh && (
          <div className="flex justify-between">
            <span className="text-text-secondary font-sans font-normal">Avg usage:</span> 
            <span className="text-text-primary">{data.usage_kwh?.toLocaleString()} kWh</span>
          </div>
        )}
        {data.primary_utility && (
          <div className="flex justify-between">
            <span className="text-text-secondary font-sans font-normal">Primary utility:</span> 
            <span className="text-primary-blue truncate max-w-[100px] text-right font-sans">{data.primary_utility}</span>
          </div>
        )}
      </div>
      {data.vs_national_bill_pct !== undefined && (
        <div className={`mt-3 pt-2 border-t border-border-hairline flex items-center gap-1 text-[10px] font-bold ${data.vs_national_bill_pct > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
          {data.vs_national_bill_pct > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {Math.abs(data.vs_national_bill_pct)}% vs National Avg
        </div>
      )}
    </div>
  );
};

const RegionalInsightsTab = ({ uploadedBill }: { uploadedBill: any }) => {
  const selectedYear = '2025';
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [geoLevel, setGeoLevel] = useState<'state' | 'utility' | 'county' | 'zip'>('state');
  const [selectedState, setSelectedState] = useState<string>('NJ'); 
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  
  const [isDrilldown, setIsDrilldown] = useState(false);
  const [hoverData, setHoverData] = useState<any>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [floatingPanelOpen, setFloatingPanelOpen] = useState(false);
  
  const [currentMonthIdx, setCurrentMonthIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [insightsResult, setInsightsResult] = useState<any | null>(null);

  const round = (val: number, decimals: number) => {
    const p = Math.pow(10, decimals);
    return Math.round(val * p) / p;
  };

  // ── Section 1 Queries & Benchmarking Data ──
  const { data: benchmarkData, isLoading: isBenchmarkLoading, error: benchmarkError } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`/benchmark?year=${selectedYear}&compare_state=NJ`);
      return res.data;
    }
  });

  const customerBenchmark = useMemo(() => {
    if (!uploadedBill || !benchmarkData) return null;
    const state_avg_bill = 120.0;
    const state_avg_usage = 750.0;
    const national_avg_bill = benchmarkData.national_avg || 135.0;
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
        { name: "State average (NJ)", avg_bill: state_avg_bill, avg_usage_kwh: state_avg_usage, diff_bill: round(cust_bill - state_avg_bill, 2) },
        { name: "Regional average (Mid-Atlantic)", avg_bill: regional_avg_bill, avg_usage_kwh: regional_avg_usage, diff_bill: round(cust_bill - regional_avg_bill, 2) },
        { name: "National average (US)", avg_bill: national_avg_bill, avg_usage_kwh: national_avg_usage, diff_bill: round(cust_bill - national_avg_bill, 2) }
      ],
      savings_opportunity: round(savings, 2)
    };
  }, [uploadedBill, benchmarkData]);

  const diffZipPct = useMemo(() => {
    if (!uploadedBill) return 0;
    const zip_avg_bill = 115.0; // Benchmark ZIP baseline reference
    const diff = ((uploadedBill.total_bill - zip_avg_bill) / zip_avg_bill) * 100;
    return round(diff, 0);
  }, [uploadedBill]);

  // ── Map & Spatial Queries ──
  const { data: geoData, isLoading: isGeoLoading } = useQuery({
    queryKey: ['geo', viewMode],
    queryFn: async () => (await axios.get(`/geo?view_mode=${viewMode}`)).data
  });

  const { data: trendData } = useQuery({
    queryKey: ['geo_trend', selectedState, viewMode],
    queryFn: async () => {
      const type = viewMode === 'bill' ? 'bill' : 'price';
      return (await axios.get(`/geo/trend?region=${selectedState}&type=${type}`)).data;
    },
    enabled: !!selectedState
  });

  const { data: detailData } = useQuery({
    queryKey: ['geo_detail', selectedState, geoData?.current_month],
    queryFn: async () => (await axios.get(`/geo/detail?state=${selectedState}&month=${geoData?.current_month}`)).data,
    enabled: !!selectedState && !!geoData?.current_month
  });

  const { data: zipBoundaries, isLoading: isBoundariesLoading } = useQuery({
    queryKey: ['geo_boundaries', selectedState],
    queryFn: async () => (await axios.get(`/geo/boundaries?state=${selectedState}`)).data,
    enabled: isDrilldown,
    staleTime: Infinity
  });



  const { data: utilityTerritories } = useQuery({
    queryKey: ['geo_utility_territories', selectedState],
    queryFn: async () => (await axios.get(`/geo/utility-territories?state=${selectedState}`)).data,
    enabled: isDrilldown
  });

  // ── Benchmark sub-state / trend queries ──
  const { data: monthlyTrends } = useQuery({
    queryKey: ['eia861m-trends'],
    queryFn: async () => (await axios.get('/eia861m/trends?sector=total')).data
  });

  const { data: njUtilities } = useQuery({
    queryKey: ['nj-utilities'],
    queryFn: async () => (await axios.get('/utility/coverage?state=NJ')).data
  });

  const { data: zipBenchmark } = useQuery({
    queryKey: ['benchmark_zip_level', selectedState],
    queryFn: async () => (await axios.get(`/benchmark/zip-level?state=${selectedState}`)).data
  });

  const { data: utilityBenchmark } = useQuery({
    queryKey: ['benchmark_utility_comparison', selectedState],
    queryFn: async () => (await axios.get(`/benchmark/utility-comparison?state=${selectedState}`)).data
  });

  // ── Electricity Intelligence & AI Summary Queries ──
  const { data: gridStatus } = useQuery({
    queryKey: ['grid-status'],
    queryFn: async () => (await axios.get('/grid/current?ba=PJM')).data,
    refetchInterval: 60000
  });

  const { data: psegHistory } = useQuery({
    queryKey: ['pseg-rate-history'],
    queryFn: async () => (await axios.get('/pseg-rate-history')).data.data
  });

  const insightsMutation = useMutation({
    mutationFn: async () => {
      if (!psegHistory) throw new Error('PSEG data not loaded');
      return (await axios.post('/geo/generate-insights', buildInsightsPayload(psegHistory))).data;
    },
    onSuccess: (data) => setInsightsResult(data)
  });

  // Playback control effect
  useEffect(() => {
    let interval: any;
    if (isPlaying && geoData?.available_months) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isPlaying, geoData]);

  // Memoized maps datasets
  const mapValues = useMemo(() => {
    if (!geoData?.data) return [];
    return geoData.data.map((s: any) => ({
      state: s.state,
      value: viewMode === 'bill' ? s.avg_bill : s.avg_rate
    }));
  }, [geoData, viewMode]);

  const currentMonth = useMemo(() => {
    if (!geoData?.available_months) return '';
    return geoData.available_months[currentMonthIdx];
  }, [geoData, currentMonthIdx]);

  // ── Stable Memoized Callbacks for Map Performance ──
  const handleMapHover = useCallback((d: any, level: string) => {
    if (!d) {
      setHoverData(null);
      return;
    }
    
    let avg_bill = d.avg_bill;
    let avg_rate = d.avg_rate;
    let primary_utility = d.primary_utility;
    let usage_kwh = d.usage_kwh;
    
    if (level === 'State') {
      const match = geoData?.data?.find((s: any) => s.state === d.state);
      if (match) {
        avg_bill = match.avg_bill;
        avg_rate = match.avg_rate;
      }
    } else if (level === 'ZIP' && zipBoundaries?.features) {
      const match = zipBoundaries.features.find((f: any) => f.properties.zip_code === d.zip);
      if (match) {
        avg_rate = match.properties.residential_rate;
        usage_kwh = uploadedBill?.usage_kwh || 750;
        avg_bill = avg_rate * usage_kwh;
        primary_utility = match.properties.primary_utility;
      }
    }

    setHoverData({
      ...d,
      level,
      avg_bill,
      avg_rate,
      primary_utility,
      usage_kwh
    });
  }, [geoData, zipBoundaries, uploadedBill]);

  const handleStateHover = useCallback((st: string | null) => {
    handleMapHover(st ? { state: st, name: st } : null, 'State');
  }, [handleMapHover]);

  const handleZipHover = useCallback((zip: string | null) => {
    handleMapHover(zip ? { name: `ZIP ${zip}`, zip } : null, 'ZIP');
  }, [handleMapHover]);

  const handleStateClick = useCallback((stateName: string) => {
    setSelectedState(stateName);
    setSelectedRegion(stateName);
    setIsDrilldown(true);
    setFloatingPanelOpen(true);
    if (!insightsMutation.isPending) insightsMutation.mutate();
  }, [insightsMutation]);

  const handleZipClick = useCallback((zip: string) => {
    setSelectedRegion(zip);
    setFloatingPanelOpen(true);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchInput.trim()) return;
    
    if (searchInput.length === 5 && !isNaN(Number(searchInput))) {
      try {
        const res = await axios.get(`/utility/lookup?zip=${searchInput}`);
        if (res.data && res.data.length > 0) {
          const state = res.data[0].state;
          setSelectedState(state);
          setSelectedRegion(searchInput);
          setIsDrilldown(true);
          setFloatingPanelOpen(true);
          if (!insightsMutation.isPending) insightsMutation.mutate();
        }
      } catch (err) { /* ignore */ }
    } else {
      const match = geoData?.data?.find((s: any) => s.state.toLowerCase().includes(searchInput.toLowerCase()));
      if (match) handleStateClick(match.state);
    }
  };

  const handleReset = () => {
    setIsDrilldown(false);
    setSelectedRegion(null);
    setSearchInput('');
    setFloatingPanelOpen(false);
    setIsPlaying(false);
  };

  const pageLoading = isBenchmarkLoading || isGeoLoading;

  if (pageLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center bg-bg-primary">
        <div className="animate-spin h-10 w-10 border-4 border-primary-blue border-t-transparent rounded-full" />
      </div>
    );
  }

  if (benchmarkError) {
    return (
      <div className="panel-operational flex items-center justify-center p-12 border-alert-red/30">
        <span className="text-alert-red font-semibold">Failed to load regional benchmark data.</span>
      </div>
    );
  }

  const focusStateData = benchmarkData.focus_state;
  const isStateAboveNational = focusStateData.vs_national_pct > 0;

  return (
    <div className="space-y-8 font-sans pb-20 bg-bg-primary animate-in fade-in duration-500">
      
      {/* Title block */}
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          Comparative Analytics
        </span>
        <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Regional Insights</h2>
        <p className="text-xs text-text-secondary mt-1">
          Review state-wide and neighborhood-level energy rate benchmarks, live regional grid operations, and comparative pricing trends.
        </p>
      </div>

      {/* ── SECTION 1: Regional Summary ── */}
      {customerBenchmark && (
        <div className="panel-operational relative overflow-hidden bg-bg-surface">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
            <div>
              <span className="bg-primary-blue/10 text-primary-blue text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-[4px] border border-primary-blue/20">
                Personalized Benchmarking
              </span>
              <h3 className="text-sm font-bold mt-3 text-text-primary">Regional Cost Analysis</h3>
              <p className="text-xs text-text-secondary mt-0.5">Your monthly consumption vs. state, regional, and national averages</p>
            </div>
            
            <div className="flex items-center gap-6 font-mono-numbers">
              <div>
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Percentile Rank</span>
                <span className="text-xl font-bold text-warning-amber">{customerBenchmark.customer.percentile}th</span>
              </div>
              <div className="border-l border-border-hairline pl-6">
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest block font-sans">Savings Opp.</span>
                <span className="text-xl font-bold text-savings-green">${customerBenchmark.savings_opportunity?.toFixed(2)}<span className="text-xs font-normal text-text-secondary font-sans">/mo</span></span>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono-numbers">
            <div className="p-4 bg-bg-primary rounded-md border border-border-hairline flex flex-col justify-between shadow-sm">
              <div>
                <span className="text-xs font-bold text-text-primary block mb-2 font-sans">Your Active Bill</span>
                <div className="flex justify-between text-xs text-text-secondary mb-1">
                  <span className="font-sans">Current charge:</span>
                  <span className="font-bold text-text-primary">${customerBenchmark.customer.monthly_bill?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xs text-text-secondary">
                  <span className="font-sans">Usage:</span>
                  <span className="font-bold text-text-primary">{customerBenchmark.customer.monthly_usage_kwh} kWh</span>
                </div>
              </div>
              <div className="border-t border-border-hairline pt-2 flex justify-between items-baseline mt-4">
                <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Observation</span>
                <span className="text-[10px] font-bold text-primary-blue font-sans">
                  Your base tier
                </span>
              </div>
            </div>

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
                    <div className="flex justify-between text-xs text-text-secondary">
                      <span className="font-sans">Avg usage:</span>
                      <span className="font-bold text-text-primary">{c.avg_usage_kwh} kWh</span>
                    </div>
                  </div>
                  <div className="border-t border-border-hairline pt-2 flex justify-between items-baseline mt-4">
                    <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Difference</span>
                    <span className={`text-xs font-bold ${above ? 'text-alert-red' : 'text-savings-green'}`}>
                      {above ? '+' : ''}${c.diff_bill?.toFixed(2)}/mo
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 p-3 bg-primary-blue/5 border border-primary-blue/15 rounded-md flex gap-2 items-center text-xs">
            <Info size={14} className="text-primary-blue" />
            <span className="font-semibold text-text-primary">
              AI Summary: Your bill is <span className={diffZipPct >= 0 ? 'text-alert-red font-bold' : 'text-savings-green font-bold'}>{Math.abs(diffZipPct)}% {diffZipPct >= 0 ? 'higher' : 'lower'}</span> than similar homes in your ZIP code.
            </span>
          </div>
        </div>
      )}

      {/* ── SECTION 2: Interactive Regional Map & Drilldown Panel ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Map visualization area (70% width) */}
        <div className="lg:col-span-8 panel-operational p-0 relative min-h-[500px] bg-bg-surface overflow-hidden flex flex-col">
          
          {/* Header Map toolbar control options */}
          <div className="z-10 bg-bg-surface border-b border-border-hairline px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            
            <div className="flex items-center gap-3">
              {/* Bill vs Rate Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-text-secondary">Bill</span>
                <button 
                  onClick={() => setViewMode(viewMode === 'bill' ? 'rate' : 'bill')} 
                  className="relative inline-flex h-4.5 w-9 items-center rounded-full border border-border-hairline bg-bg-primary transition-colors focus:outline-none"
                  aria-label="Toggle map view mode"
                >
                  <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-primary-blue transition-transform ${viewMode === 'rate' ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
                </button>
                <span className="text-[10px] font-bold uppercase tracking-wider text-text-secondary">Rate</span>
              </div>

              {/* Geo layer togglers */}
              <div className="flex items-stretch border border-border-hairline bg-bg-surface rounded-[4px] overflow-hidden text-[10px] font-semibold text-text-primary">
                <button 
                  onClick={() => setGeoLevel('state')}
                  className={`px-2 py-1 border-r border-border-hairline transition-colors ${geoLevel === 'state' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
                >
                  State
                </button>
                <button 
                  onClick={() => setGeoLevel('utility')}
                  className={`px-2 py-1 border-r border-border-hairline transition-colors ${geoLevel === 'utility' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
                >
                  Utility
                </button>
                <button 
                  onClick={() => setGeoLevel('zip')}
                  className={`px-2 py-1 border-r border-border-hairline transition-colors ${geoLevel === 'zip' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
                >
                  ZIP
                </button>
                <button 
                  onClick={handleReset}
                  className="px-2 py-1 hover:bg-bg-primary/50 transition-colors"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Search filter form input */}
            <form onSubmit={handleSearch} className="flex border border-border-hairline bg-bg-primary rounded-[4px] overflow-hidden">
              <input 
                type="text" 
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="ZIP / State"
                className="w-20 px-2 py-1 text-[10px] font-semibold text-text-primary outline-none placeholder-text-secondary bg-transparent"
                aria-label="ZIP or state code lookup search input"
              />
              <button 
                type="submit"
                className="px-2.5 py-1 text-[10px] bg-bg-surface hover:bg-bg-primary border-l border-border-hairline font-bold transition-colors"
              >
                Go
              </button>
            </form>
          </div>

          <HoverTooltip visible={!!hoverData} data={hoverData} tooltipRef={tooltipRef} />

          {/* Interactive Map Core Rendering */}
          <div 
            className="w-full flex-1 relative bg-bg-primary cursor-crosshair min-h-[400px]"
            onMouseMove={(e) => {
              if (tooltipRef.current) {
                tooltipRef.current.style.left = `${e.clientX}px`;
                tooltipRef.current.style.top = `${e.clientY}px`;
              }
            }}
            onMouseLeave={() => setHoverData(null)}
          >
            {!isDrilldown ? (
              <USMap 
                data={mapValues} 
                selectedState={selectedState} 
                onStateClick={handleStateClick} 
                onStateHover={handleStateHover}
                colorRange={viewMode === 'bill' ? ["#F0F4FF", "#2F6BFF"] : ["#E8F7F3", "#16A085"]} 
              />
            ) : isBoundariesLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-surface/50 backdrop-blur-sm">
                <div className="animate-spin h-8 w-8 border-b-2 border-primary-blue" />
              </div>
            ) : (
              <StateZipMap 
                geoJsonData={zipBoundaries} 
                viewMode={geoLevel === 'utility' ? 'utility' : viewMode} 
                selectedZip={selectedRegion} 
                onZipClick={handleZipClick} 
                onZipHover={handleZipHover} 
              />
            )}
          </div>
        </div>

        {/* Regional Info details Panel (30% width) */}
        <div className="lg:col-span-4 bg-bg-surface border border-border-hairline rounded-md p-5 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center gap-2 border-b border-border-hairline pb-2 mb-4">
              <MapPin size={16} className="text-primary-blue" />
              <h3 className="text-sm font-bold text-text-primary">Selected Territory Details</h3>
            </div>

            {floatingPanelOpen ? (
              <div className="space-y-4 font-mono-numbers text-xs">
                <div>
                  <span className="px-2 py-0.5 bg-primary-blue/10 text-primary-blue rounded-[4px] text-[8px] font-bold uppercase tracking-wider block w-max mb-1">
                    {isDrilldown && selectedRegion !== selectedState ? 'ZIP code focus' : 'State wide focus'}
                  </span>
                  <h4 className="text-lg font-bold text-text-primary tracking-tight font-sans">
                    {selectedRegion || selectedState}
                  </h4>
                </div>

                <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm space-y-1">
                  <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Average Monthly Bill</p>
                  <p className="text-lg font-bold text-text-primary">${detailData?.avg_bill?.toFixed(2) || '120.00'}</p>
                  {detailData?.vs_national_bill_pct !== undefined && (
                    <p className={`text-[9px] font-bold mt-1 flex items-center gap-1 font-sans ${detailData.vs_national_bill_pct > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                      {detailData.vs_national_bill_pct > 0 ? '+' : ''}{detailData.vs_national_bill_pct}% vs national average
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-0.5 font-sans">Average Rate</p>
                    <p className="text-xs font-bold text-primary-blue">${detailData?.avg_rate?.toFixed(4) || '0.1600'}</p>
                  </div>
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-0.5 font-sans">Average Usage</p>
                    <p className="text-xs font-bold text-text-primary">{detailData?.usage_kwh?.toLocaleString() || '750'} <span className="text-[9px] font-sans font-normal">kWh</span></p>
                  </div>
                </div>

                {isDrilldown && utilityTerritories && (
                  <div className="border-t border-border-hairline pt-3 mt-2">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-2 flex items-center gap-1 font-sans">
                      <Building2 size={12}/> Active Utilities
                    </p>
                    <div className="space-y-1.5 max-h-24 overflow-y-auto pr-1">
                      {utilityTerritories.slice(0, 3).map((u: any) => (
                        <div key={u.eia_utility_id} className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-text-primary truncate max-w-[120px] font-sans">{u.utility_name}</span>
                          <span className="text-[9px] font-bold text-text-secondary bg-bg-primary border border-border-hairline px-1.5 py-0.5 rounded-[4px]">{u.zip_count} ZIPs</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!isDrilldown && (
                  <button 
                    onClick={() => setIsDrilldown(true)}
                    className="w-full mt-4 bg-text-primary hover:bg-text-primary/95 text-white py-2 rounded-md text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-sm"
                  >
                    Drill to ZIP level <ArrowRight size={12} />
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-xs text-text-secondary font-semibold">
                <MapPin className="mx-auto text-text-secondary/40 mb-3" size={24} />
                <p>Click on any U.S. State or enter a ZIP lookup coordinates to inspect detailed local boundaries statistics.</p>
              </div>
            )}
          </div>

          {/* Quick macro metrics state */}
          <div className="border-t border-border-hairline pt-4 mt-6">
            <h5 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2">State KPI Profile ({selectedState})</h5>
            <div className="flex items-center justify-between text-xs font-mono-numbers">
              <span className="text-text-secondary">Expensive Rank:</span>
              <span className="font-bold text-text-primary">#{focusStateData?.rank || '11'}</span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono-numbers mt-1.5">
              <span className="text-text-secondary">Average Rate:</span>
              <span className="font-bold text-text-primary">
                ${(focusStateData?.avg_rate * 100 || 16.5).toFixed(1)}¢<span className="text-[10px] font-normal text-text-secondary">/kWh</span>
              </span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono-numbers mt-1.5">
              <span className="text-text-secondary">Vs National Average:</span>
              <span className={`font-bold ${isStateAboveNational ? 'text-alert-red' : 'text-savings-green'}`}>
                {isStateAboveNational ? '+' : ''}{focusStateData?.vs_national_pct?.toFixed(1) || '0.0'}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── SECTION 3: Regional Benchmarking ── */}
      <div>
        <div className="flex items-center gap-2 mb-6 border-b border-border-hairline pb-2">
          <Trophy size={16} className="text-primary-blue" />
          <h3 className="text-sm font-bold text-text-primary">Regional Benchmarking</h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Top 10 expensive states */}
          <div className="panel-chart h-[380px] flex flex-col justify-between bg-bg-surface">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
              <TrendingUp size={14} className="text-alert-red" /> Top 10 Most Expensive States
            </h4>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={benchmarkData.top_10_expensive} layout="vertical" margin={{ left: -10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="state" tick={{ fontSize: 10, fill: 'var(--text-primary)', fontWeight: 'bold' }} width={30} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                  <Bar dataKey="avg_rate" radius={[0, 2, 2, 0]}>
                    {(benchmarkData.top_10_expensive || []).map((_: any, idx: number) => (
                      <Cell key={idx} fill={idx === 0 ? 'var(--alert-red)' : idx < 3 ? 'var(--warning-amber)' : '#E6EAF0'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 10 Cheapest U.S. states */}
          <div className="panel-chart h-[380px] flex flex-col justify-between bg-bg-surface">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
              <TrendingDown size={14} className="text-savings-green" /> 10 Cheapest U.S. States
            </h4>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={benchmarkData.cheapest_10} layout="vertical" margin={{ left: -10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="state" tick={{ fontSize: 10, fill: 'var(--text-primary)', fontWeight: 'bold' }} width={30} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}¢/kWh`, 'Rate']} />
                  <Bar dataKey="avg_rate" radius={[0, 2, 2, 0]}>
                    {(benchmarkData.cheapest_10 || []).map((_: any, idx: number) => (
                      <Cell key={idx} fill={idx === 0 ? 'var(--savings-green)' : idx < 3 ? 'var(--energy-teal)' : '#E6EAF0'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Efficiency Scatterchart */}
          <div className="panel-chart h-[380px] flex flex-col justify-between bg-bg-surface">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
              <Activity size={14} className="text-primary-blue" /> Price vs. Bill (Efficiency Scatter)
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
                      data={(benchmarkData.scatter_data || []).filter((d: any) => d.region === region)}
                      fill={color}
                    >
                      {(benchmarkData.scatter_data || [])
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

        {/* Local state sub comparisons: Utility lists, rates and ZIP disparity histogram details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          
          {/* Local state utility comparisons */}
          <div className="panel-chart h-[360px] flex flex-col justify-between bg-bg-surface lg:col-span-2">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
              <Building2 size={14} className="text-primary-blue" /> Local Utility Rate Comparison ({selectedState})
            </h4>
            <div className="flex-1 min-h-[260px]">
              {utilityBenchmark && utilityBenchmark.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={utilityBenchmark} margin={{ bottom: 10, left: -25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                    <XAxis dataKey="utility_name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} interval={0} 
                      tickFormatter={(name) => name.length > 18 ? name.substring(0, 18) + '...' : name} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${(v * 100).toFixed(0)}¢`} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(2)}¢/kWh`, 'Rate']} />
                    <Bar dataKey="residential_rate" fill="var(--primary-blue)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-text-secondary">
                  No utility rate benchmarks loaded for {selectedState}.
                </div>
              )}
            </div>
          </div>

          {/* Local ZIP disparity metrics */}
          <div className="panel-operational space-y-4 h-[360px]">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
              <Activity size={14} className="text-primary-blue" /> ZIP Code Rate Disparity ({selectedState})
            </h4>
            {zipBenchmark && zipBenchmark.zips && zipBenchmark.zips.length > 0 ? (
              <div className="space-y-4 font-mono-numbers">
                <div className="grid grid-cols-3 gap-2.5 text-[10px]">
                  <div className="bg-bg-primary rounded-md p-2.5 border border-border-hairline shadow-sm">
                    <p className="text-[8px] font-bold text-text-secondary uppercase tracking-wider mb-1 font-sans">State Avg</p>
                    <p className="text-xs font-bold text-text-primary">${(zipBenchmark.avg_rate * 100).toFixed(2)}¢</p>
                  </div>
                  <div className="bg-savings-green/10 rounded-md p-2.5 border border-savings-green/20 shadow-sm text-savings-green">
                    <p className="text-[8px] font-bold text-savings-green uppercase tracking-wider mb-1 font-sans">Below Avg</p>
                    <p className="text-xs font-bold">{zipBenchmark.below_average_count}</p>
                  </div>
                  <div className="bg-alert-red/10 rounded-md p-2.5 border border-alert-red/20 shadow-sm text-alert-red">
                    <p className="text-[8px] font-bold text-alert-red uppercase tracking-wider mb-1 font-sans">Above Avg</p>
                    <p className="text-xs font-bold">{zipBenchmark.above_average_count}</p>
                  </div>
                </div>
                
                <div>
                  <p className="text-[8px] font-bold text-text-secondary uppercase tracking-widest mb-1.5 font-sans border-b border-border-hairline pb-1">Top 4 Most Expensive ZIP Codes</p>
                  <div className="space-y-1 font-sans max-h-[170px] overflow-y-auto pr-1">
                    {zipBenchmark.zips.slice(0, 4).map((z: any) => (
                      <div key={z.zip_code} className="flex justify-between items-center text-xs text-text-primary p-2 bg-bg-primary rounded-md border border-border-hairline shadow-sm font-mono-numbers">
                        <span className="font-bold font-sans">ZIP {z.zip_code}</span>
                        <div className="flex gap-1.5 items-center">
                          <span className="font-bold text-text-primary">${(z.rate * 100).toFixed(2)}¢/kWh</span>
                          <span className="text-[8px] text-alert-red font-bold font-sans">+{z.vs_state_avg_pct}% vs avg</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-text-secondary">
                No ZIP-level disparities loaded for {selectedState}.
              </div>
            )}
          </div>
        </div>

        {/* State utility listing details (OpenEI table data) */}
        {njUtilities && (
          <div className="panel-operational mt-6">
            <div className="flex items-center justify-between border-b border-border-hairline pb-2 mb-4">
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-2">
                <Building2 size={14} className="text-primary-blue" /> Utility Service Directory & Rates (OpenEI)
              </h4>
              <span className="text-[9px] font-bold text-text-secondary font-mono-numbers">Active NJ Utility Coverage</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border-hairline text-text-secondary font-bold uppercase text-[9px] bg-bg-surface">
                    <th className="py-2.5 pl-2">Utility Name</th>
                    <th className="py-2.5">Ownership Type</th>
                    <th className="py-2.5 text-right">ZIP Codes Covered</th>
                    <th className="py-2.5 text-right pr-2">Residential Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-hairline font-mono-numbers text-text-primary">
                  {njUtilities.slice(0, 5).map((util: any) => (
                    <tr key={util.eia_utility_id} className="hover:bg-bg-primary/50 transition-colors">
                      <td className="py-2.5 pl-2 truncate max-w-[200px] font-sans font-semibold text-text-primary">{util.utility_name}</td>
                      <td className="py-2.5 text-text-secondary font-sans">{util.ownership_type || 'Investor Owned'}</td>
                      <td className="py-2.5 text-right text-text-secondary">{util.zip_count}</td>
                      <td className="py-2.5 text-right pr-2 text-primary-blue font-bold">
                        {util.residential_rate ? `${(util.residential_rate * 100).toFixed(2)}¢/kWh` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ── SECTION 4: Regional Electricity Intelligence ── */}
      <div>
        <div className="flex items-center gap-2 mb-6 border-b border-border-hairline pb-2">
          <Activity size={16} className="text-primary-blue" />
          <h3 className="text-sm font-bold text-text-primary">Regional Grid Operations & Carbon Intensity</h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono-numbers">
          
          {/* Grid load operations (Live telemetry status) */}
          <div className="panel-operational bg-bg-surface flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="flex justify-between items-center mb-4 border-b border-border-hairline pb-2">
                <span className="text-xs font-bold text-text-primary font-sans">Live PJM Grid Balancing</span>
                <span className="flex items-center gap-1 bg-savings-green/10 text-savings-green text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-[4px] border border-savings-green/20">
                  <span className="w-1 h-1 bg-savings-green rounded-full animate-ping"></span> Live PJM
                </span>
              </div>
              {gridStatus ? (
                <div className="space-y-3.5">
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider font-sans">Grid Load Demand:</span>
                    <span className="text-base font-bold text-text-primary">
                      {(gridStatus.current_demand_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal text-text-secondary">GW</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider font-sans">Grid Generation Capacity:</span>
                    <span className="text-base font-bold text-savings-green">
                      {(gridStatus.current_generation_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal">GW</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline border-t border-border-hairline pt-3.5">
                    <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider font-sans">Grid Carbon Intensity:</span>
                    <span className="text-sm font-bold text-warning-amber">
                      392 <span className="text-[9px] font-sans font-normal">lbs CO₂/MWh</span>
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary py-10 justify-center">
                  <ZapOff size={14}/> Connecting to Balancing Authority...
                </div>
              )}
            </div>
          </div>

          {/* Grid Fuel Mix Capacity */}
          <div className="panel-operational bg-bg-surface flex flex-col justify-between min-h-[220px]">
            <div>
              <h4 className="text-xs font-bold text-text-primary mb-4 border-b border-border-hairline pb-2 font-sans">Current Fuel Mix Generation</h4>
              {gridStatus?.fuel_mix ? (
                <div className="space-y-2">
                  {gridStatus.fuel_mix.slice(0, 3).map((f: any) => (
                    <div key={f.fuel_type} className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-text-secondary font-sans">{f.fuel_type_name}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-bg-primary rounded-full overflow-hidden border border-border-hairline">
                          <div className="h-full bg-primary-blue rounded-full" style={{ width: `${f.percentage}%` }}></div>
                        </div>
                        <span className="font-bold text-text-primary text-[10px] w-6 text-right">{f.percentage.toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-text-secondary py-10 text-center font-sans">
                  Generating fuel allocation mix...
                </div>
              )}
            </div>
          </div>

          {/* Weather context constraints */}
          <div className="panel-operational bg-bg-surface flex flex-col justify-between min-h-[220px]">
            <div>
              <h4 className="text-xs font-bold text-text-primary mb-4 border-b border-border-hairline pb-2 font-sans">Weather Context & Reliability</h4>
              <div className="space-y-3 font-sans text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary">Monthly CDD (Cooling):</span>
                  <span className="font-bold text-text-primary font-mono-numbers">142 Days</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary">Monthly HDD (Heating):</span>
                  <span className="font-bold text-text-primary font-mono-numbers">12 Days</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary">Grid System Outages:</span>
                  <span className="font-bold text-savings-green font-mono-numbers flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-savings-green rounded-full"></span> Zero Active
                  </span>
                </div>
                <div className="flex justify-between items-center border-t border-border-hairline pt-3 mt-1">
                  <span className="text-text-secondary font-semibold">SAIDI Reliability index:</span>
                  <span className="font-bold text-text-primary font-mono-numbers">84.2 mins/yr</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── SECTION 5: Historical Regional Trends ── */}
      <div>
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-border-hairline pb-2 mb-6 gap-3">
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-primary-blue" />
            <h3 className="text-sm font-bold text-text-primary">Historical Trends & Energy Sales Timeline</h3>
          </div>

          {/* Timeline slider controls */}
          {geoData?.available_months && (
            <div className="flex items-center gap-3 bg-bg-surface px-3 py-1 rounded-md border border-border-hairline text-[10px] font-semibold text-text-primary">
              <button 
                onClick={() => setIsPlaying(!isPlaying)} 
                className={`p-1 rounded-full transition-all ${isPlaying ? 'bg-primary-blue text-white' : 'bg-bg-primary text-text-primary border border-border-hairline'}`}
                aria-label={isPlaying ? 'Pause animation' : 'Play animation'}
              >
                {isPlaying ? <Pause size={10} fill="currentColor" /> : <Play size={10} fill="currentColor" />}
              </button>
              <input 
                type="range" 
                min={0} 
                max={geoData.available_months.length - 1} 
                value={currentMonthIdx}
                onChange={(e) => { setCurrentMonthIdx(Number(e.target.value)); setIsPlaying(false); }}
                className="w-24 h-1 bg-border-hairline rounded-lg appearance-none cursor-pointer accent-primary-blue"
              />
              <span className="font-mono-numbers block w-14 text-right">
                {currentMonth}
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Selected State historical rate/bill AreaChart */}
          <div className="panel-chart h-[340px] flex flex-col justify-between bg-bg-surface">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">{selectedState} Historical Cost Trend</h3>
              <div className={`flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-[4px] border font-mono-numbers ${trendData?.total_growth_pct > 0 ? 'bg-alert-red/10 text-alert-red border-alert-red/20' : 'bg-savings-green/10 text-savings-green border-savings-green/20'}`}>
                {trendData?.total_growth_pct > 0 ? <TrendingUp size={10}/> : <TrendingDown size={10}/>} 
                {trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}% YoY Growth
              </div>
            </div>
            
            <div className="flex-1 min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData?.months ? trendData.months.map((m: any, i: number) => ({ label: m, val: trendData.values[i] })) : []} margin={{ left: -25, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontWeight: 600}} dy={10} minTickGap={30} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontFamily: 'IBM Plex Mono'}} tickFormatter={(v) => viewMode === 'bill' ? `$${v}` : `$${v}`} domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }} 
                    itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                    formatter={(v: any) => [viewMode === 'bill' ? `$${Number(v).toFixed(2)}` : `$${Number(v).toFixed(4)}/kWh`, 'Average']}
                  />
                  <Area type="monotone" dataKey="val" stroke="var(--primary-blue)" strokeWidth={2} fill="var(--primary-blue)" fillOpacity={0.08} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* National Monthly Trends (EIA-861M) */}
          <div className="panel-chart h-[340px] flex flex-col justify-between bg-bg-surface">
            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-6 flex items-center gap-2 border-b border-border-hairline pb-2">
              <Calendar size={14} className="text-primary-blue" /> National Monthly Electricity Sales Trends (EIA-861M)
            </h4>
            <div className="flex-1 min-h-[220px]">
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
                <div className="h-full flex items-center justify-center text-xs text-text-secondary">Loading EIA trends...</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── SECTION 6: AI Regional Summary ── */}
      <div className="panel-operational bg-bg-surface">
        <div className="flex items-center justify-between border-b border-border-hairline pb-2 mb-4">
          <div className="flex items-center gap-2">
            <Info size={16} className="text-primary-blue" />
            <h3 className="text-sm font-bold text-text-primary">Regional Observations & Insights</h3>
          </div>
          <button
            onClick={() => insightsMutation.mutate()}
            disabled={insightsMutation.isPending || !psegHistory}
            className="flex items-center gap-2 px-3 py-1.5 bg-primary-blue text-white rounded-[4px] text-[10px] font-bold hover:bg-primary-blue/90 transition-all disabled:opacity-50"
          >
            <Info size={10} />
            <span>Generate Observations</span>
          </button>
        </div>

        {insightsResult ? (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-bg-primary rounded-md border border-border-hairline space-y-1.5">
                <span className="text-[10px] font-bold text-primary-blue uppercase tracking-wider block">Comparison Summary</span>
                <p className="text-text-primary leading-relaxed font-semibold">
                  {insightsResult.state_trend?.trend_analysis || "The selected territory exhibits stable prices relative to national bounds."}
                </p>
              </div>

              {insightsResult.state_trend?.forecast_hint && (
                <div className="p-3 bg-primary-blue/5 border border-primary-blue/10 rounded-md space-y-1.5">
                  <span className="text-[10px] font-bold text-primary-blue uppercase tracking-wider block">Forecast & Volatility Hint</span>
                  <p className="text-primary-blue leading-relaxed font-semibold">
                    {insightsResult.state_trend.forecast_hint}
                  </p>
                </div>
              )}
            </div>

            <div className="border-t border-border-hairline pt-3 flex flex-wrap gap-4 text-text-secondary text-[10px] font-semibold">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-primary-blue rounded-full"></span>
                <span>Weather Influence: High Summer CDD impact</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-savings-green rounded-full"></span>
                <span>Utility Action: Standard generation rates constant</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-xs font-semibold text-text-secondary">
            <p className="mb-3">Request a comprehensive spatial rate and forecast report for this state.</p>
            <button 
              onClick={() => insightsMutation.mutate()} 
              className="bg-bg-surface hover:bg-bg-primary text-text-primary text-xs font-bold px-4 py-2 rounded-md transition-colors border border-border-hairline shadow-sm"
            >
              Generate AI Report
            </button>
          </div>
        )}
      </div>

    </div>
  );
};

export default RegionalInsightsTab;
