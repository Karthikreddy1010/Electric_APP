import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import {
  TrendingDown, TrendingUp, Play, Pause, Map as MapIcon, Globe,
  Sparkles, AlertTriangle, CheckCircle, ArrowUpRight, ArrowDownRight,
  Zap, BarChart2, Info
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts';
import USMap from '../USMap.tsx';
import StateZipMap from '../StateZipMap.tsx';


// ─── NJ PSE&G ZIP codes used to construct synthetic geo-insight payload ──────
const NJ_ZIPS = ['07101', '07201', '07301', '07401', '07501'];
const NATIONAL_AVG_RATE = 0.1284; // EIA 2024 national residential avg

const ANOMALY_STYLES: Record<string, { bg: string; text: string; icon: React.ReactElement }> = {
  spike:  { bg: 'bg-red-50',     text: 'text-red-600',    icon: <AlertTriangle size={12} /> },
  drop:   { bg: 'bg-emerald-50', text: 'text-emerald-600', icon: <ArrowDownRight size={12} /> },
  stable: { bg: 'bg-slate-100',  text: 'text-slate-500',   icon: <CheckCircle size={12} /> },
};

// ─── Build the request payload from PSEG rate history ────────────────────────
function buildInsightsPayload(psegData: any[]) {
  const electricity_data: any[] = [];

  // Group by year+month, average rates across tiers
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
    electricity_data: electricity_data.slice(0, 60), // cap payload
  };
}

// ─── ZipInsightCard ───────────────────────────────────────────────────────────
const ZipInsightCard = ({ insight }: { insight: any }) => {
  const anomaly = insight.anomaly_detection?.toLowerCase() as string;
  const anomalyKey = anomaly?.includes('spike') ? 'spike' : anomaly?.includes('drop') ? 'drop' : 'stable';
  const style = ANOMALY_STYLES[anomalyKey];

  return (
    <div className="card p-6 bg-white border border-slate-100 shadow-lg hover:shadow-xl transition-shadow duration-200 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-black text-slate-400 uppercase tracking-widest">ZIP {insight.zip_code}</span>
        <span className={`flex items-center gap-1 text-[10px] font-black px-2 py-1 rounded-full uppercase ${style.bg} ${style.text}`}>
          {style.icon} {anomalyKey}
        </span>
      </div>

      <p className="text-sm text-slate-600 leading-relaxed">{insight.summary}</p>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Rate</p>
          <p className="text-lg font-black text-slate-900">${insight.metrics?.avg_price?.toFixed(4)}<span className="text-xs font-medium text-slate-400">/kWh</span></p>
        </div>
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Consumption</p>
          <p className="text-lg font-black text-slate-900">{insight.metrics?.consumption_kwh?.toLocaleString()}<span className="text-xs font-medium text-slate-400"> kWh</span></p>
        </div>
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Peak Demand</p>
          <p className="text-lg font-black text-slate-900">{insight.metrics?.peak_demand?.toFixed(2)}<span className="text-xs font-medium text-slate-400"> kW</span></p>
        </div>
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Renewable</p>
          <p className="text-lg font-black text-emerald-600">{((insight.metrics?.renewable_ratio ?? 0) * 100).toFixed(0)}%</p>
        </div>
      </div>

      {/* Comparisons */}
      {insight.comparisons && (
        <div className="flex gap-2">
          {insight.comparisons.vs_state_avg && (
            <span className={`text-[10px] font-black px-2 py-1 rounded-lg ${insight.comparisons.vs_state_avg.startsWith('+') ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
              {insight.comparisons.vs_state_avg} vs State
            </span>
          )}
          {insight.comparisons.vs_national_avg && (
            <span className={`text-[10px] font-black px-2 py-1 rounded-lg ${insight.comparisons.vs_national_avg.startsWith('+') ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'}`}>
              {insight.comparisons.vs_national_avg} vs National
            </span>
          )}
        </div>
      )}

      {/* Recommendation */}
      <div className="border-t border-slate-100 pt-3">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Recommendation</p>
        <p className="text-xs text-slate-600 leading-relaxed">{insight.recommendation}</p>
      </div>
    </div>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────
const GeoTab = () => {
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [selectedState, setSelectedState] = useState('NJ');
  const [currentMonthIdx, setCurrentMonthIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [insightsResult, setInsightsResult] = useState<any | null>(null);
  const [activeZip, setActiveZip] = useState<string | null>(null);

  // New datasets UI states
  const [zipInput, setZipInput] = useState('');
  const [zipUtility, setZipUtility] = useState<any[]>([]);
  const [zipSearchLoading, setZipSearchLoading] = useState(false);
  const [zipSearchError, setZipSearchError] = useState<string | null>(null);

  // Drilldown states
  const [isDrilldown, setIsDrilldown] = useState(false);
  const [mapViewMode, setMapViewMode] = useState<'bill' | 'rate' | 'utility'>('rate');
  const [hoveredZip, setHoveredZip] = useState<string | null>(null);


  // Fetch EIA-930 hourly grid status
  const { data: gridStatus } = useQuery({
    queryKey: ['grid-status'],
    queryFn: async () => {
      const res = await axios.get('/grid/current?ba=PJM');
      return res.data;
    },
    refetchInterval: 60000 // every 1 min
  });

  const handleZipSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!zipInput.trim() || zipInput.length < 5) return;
    setZipSearchLoading(true);
    setZipSearchError(null);
    setZipUtility([]);
    try {
      const res = await axios.get(`/utility/lookup?zip=${zipInput}`);
      setZipUtility(res.data);
    } catch (err: any) {
      setZipSearchError(err.response?.data?.detail || 'ZIP code not found');
    } finally {
      setZipSearchLoading(false);
    }
  };

  const handleZipClick = async (zip: string) => {
    setZipInput(zip);
    setZipSearchLoading(true);
    setZipSearchError(null);
    setZipUtility([]);
    try {
      const res = await axios.get(`/utility/lookup?zip=${zip}`);
      setZipUtility(res.data);
    } catch (err: any) {
      setZipSearchError(err.response?.data?.detail || 'ZIP code not found');
    } finally {
      setZipSearchLoading(false);
    }
  };

  // Map data
  const { data: geoData, isLoading, error } = useQuery({
    queryKey: ['geo', viewMode],
    queryFn: async () => {
      const res = await axios.get(`/geo?view_mode=${viewMode}`);
      return res.data;
    }
  });

  // State trendline — uses geo_insights router params: region + type
  const { data: trendData } = useQuery({
    queryKey: ['geo_trend', selectedState, viewMode],
    queryFn: async () => {
      const type = viewMode === 'bill' ? 'bill' : 'price';
      const res = await axios.get(`/geo/trend?region=${selectedState}&type=${type}`);
      return res.data;
    },
    enabled: !!selectedState
  });

  // State detail card — uses geo_insights router
  const { data: detailData } = useQuery({
    queryKey: ['geo_detail', selectedState, geoData?.current_month],
    queryFn: async () => {
      const res = await axios.get(`/geo/detail?state=${selectedState}&month=${geoData?.current_month}`);
      return res.data;
    },
    enabled: !!selectedState && !!geoData?.current_month
  });

  // Fetch ZCTA boundaries for selected state when in drill-down mode
  const { data: zipBoundaries, isLoading: isBoundariesLoading } = useQuery({
    queryKey: ['geo_boundaries', selectedState],
    queryFn: async () => {
      const res = await axios.get(`/geo/boundaries?state=${selectedState}`);
      return res.data;
    },
    enabled: isDrilldown
  });

  // Fetch ZIP statistics for the selected state
  const { data: zipStats } = useQuery({
    queryKey: ['geo_zip_stats', selectedState],
    queryFn: async () => {
      const res = await axios.get(`/geo/zip-stats?state=${selectedState}`);
      return res.data;
    },
    enabled: isDrilldown
  });

  // Fetch utility territories counts
  const { data: utilityTerritories } = useQuery({
    queryKey: ['geo_utility_territories', selectedState],
    queryFn: async () => {
      const res = await axios.get(`/geo/utility-territories?state=${selectedState}`);
      return res.data;
    },
    enabled: isDrilldown
  });


  // PSEG rate history
  const { data: psegHistory } = useQuery({
    queryKey: ['pseg-rate-history'],
    queryFn: async () => {
      const res = await axios.get('/pseg-rate-history');
      return res.data.data;
    }
  });

  // AI Geo Insights mutation
  const insightsMutation = useMutation({
    mutationFn: async () => {
      if (!psegHistory) throw new Error('PSEG data not loaded');
      const payload = buildInsightsPayload(psegHistory);
      const res = await axios.post('/geo/generate-insights', payload);
      return res.data;
    },
    onSuccess: (data) => {
      setInsightsResult(data);
      setActiveZip(data.zip_insights?.[0]?.zip_code ?? null);
    }
  });

  // Timeline animation
  useEffect(() => {
    let interval: any;
    if (isPlaying && geoData?.available_months) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, geoData]);

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

  // State trend chart data from AI insights
  const stateTrendChartData = useMemo(() => {
    if (!insightsResult?.state_trend?.time_series) return [];
    return insightsResult.state_trend.time_series.map((pt: any) => ({
      label: `${pt.month} ${pt.year}`,
      avg_price: pt.avg_price,
      consumption_kwh: pt.consumption_kwh,
    }));
  }, [insightsResult]);

  // Fallback trendline from /geo/trend API
  const fallbackTrendData = useMemo(() => {
    if (!trendData?.months) return [];
    return trendData.months.map((m: string, i: number) => ({
      label: m,
      val: trendData.values[i]
    }));
  }, [trendData]);

  const activeInsight = insightsResult?.zip_insights?.find((z: any) => z.zip_code === activeZip);

  if (isLoading) return <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 mx-auto mt-20" />;
  if (error) return <div className="p-8 text-red-600">Failed to load geographic data.</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">

      {/* ── Header ── */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <Globe className="text-blue-600" size={24} />
          <h2 className="text-3xl font-black text-slate-900 tracking-tight">Geographic Insights</h2>
        </div>
        <div className="flex items-center gap-4 bg-white p-2 rounded-2xl border border-slate-100 shadow-xl">
          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button onClick={() => setViewMode('bill')} className={`px-4 py-2 rounded-lg text-xs font-black ${viewMode === 'bill' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>BILL ($)</button>
            <button onClick={() => setViewMode('rate')} className={`px-4 py-2 rounded-lg text-xs font-black ${viewMode === 'rate' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>RATE ($/kWh)</button>
          </div>
          <button onClick={() => setIsPlaying(!isPlaying)} className={`p-2 rounded-xl ${isPlaying ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'}`}>
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{currentMonth}</span>
          <button
            onClick={() => insightsMutation.mutate()}
            disabled={insightsMutation.isPending || !psegHistory}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-black hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {insightsMutation.isPending
              ? <><Sparkles size={14} className="animate-pulse" /> Analyzing...</>
              : <><Sparkles size={14} /> AI Insights</>
            }
          </button>
        </div>
      </div>

      {/* ── Map + Detail Panel ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 card p-0 overflow-hidden relative min-h-[600px] bg-[#F8FAFC]">
          <div className="absolute top-8 left-8 z-10 flex gap-2">
            <div className="p-4 bg-white/80 rounded-2xl border border-slate-100 shadow-2xl">
              <select 
                value={selectedState} 
                onChange={(e) => { setSelectedState(e.target.value); setIsDrilldown(false); }} 
                className="bg-transparent border-none font-black text-lg text-slate-900 outline-none"
              >
                {geoData?.data?.map((s: any) => <option key={s.state} value={s.state}>{s.state}</option>)}
              </select>
            </div>
            {isDrilldown && (
              <button 
                onClick={() => setIsDrilldown(false)}
                className="bg-white/80 border border-slate-100 rounded-2xl px-4 text-xs font-black shadow-2xl text-slate-700 hover:bg-slate-50 transition-colors"
              >
                ← Back to US
              </button>
            )}
          </div>
          
          {isDrilldown && (
            <div className="absolute top-8 right-8 z-10 bg-white/80 rounded-2xl p-2 border border-slate-100 shadow-2xl flex bg-slate-100 p-1">
              <button 
                onClick={() => setMapViewMode('rate')} 
                className={`px-3 py-1.5 rounded-xl text-[10px] font-black ${mapViewMode === 'rate' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}
              >
                Color by Rate
              </button>
              <button 
                onClick={() => setMapViewMode('utility')} 
                className={`px-3 py-1.5 rounded-xl text-[10px] font-black ${mapViewMode === 'utility' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}
              >
                Color by Utility
              </button>
            </div>
          )}

          {!isDrilldown ? (
            <USMap data={mapValues} selectedState={selectedState} onStateClick={setSelectedState} colorRange={viewMode === 'bill' ? ["#EFF6FF", "#1D4ED8"] : ["#F0FDF4", "#166534"]} />
          ) : isBoundariesLoading ? (
            <div className="w-full h-full min-h-[500px] flex items-center justify-center">
              <div className="animate-spin h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : (
            <StateZipMap 
              geoJsonData={zipBoundaries} 
              viewMode={mapViewMode} 
              selectedZip={zipInput} 
              onZipClick={handleZipClick} 
              onZipHover={setHoveredZip} 
            />
          )}

          {isDrilldown && hoveredZip && zipBoundaries?.features && (() => {
            const f = zipBoundaries.features.find((feat: any) => feat.properties.zip_code === hoveredZip);
            if (!f) return null;
            return (
              <div className="absolute bottom-8 left-8 bg-white/95 backdrop-blur rounded-2xl p-4 shadow-2xl border text-xs z-10 space-y-1">
                <p className="font-black text-slate-900">ZIP {f.properties.zip_code}</p>
                <p className="text-slate-500 font-semibold">Utility: <span className="font-black text-slate-900">{f.properties.primary_utility}</span></p>
                <p className="text-slate-500 font-semibold">Rate: <span className="font-black text-blue-600">${f.properties.residential_rate?.toFixed(4)}/kWh</span></p>
              </div>
            );
          })()}

          <div className="absolute bottom-8 right-8 p-6 bg-slate-900 text-white rounded-[32px] shadow-2xl min-w-[280px]">
            <div className="flex justify-between items-start mb-6">
              <h4 className="text-3xl font-black">{selectedState}</h4>
              <MapIcon size={20} className="text-white/40" />
            </div>
            {detailData && (
              <div className="space-y-3">
                <div className="flex justify-between items-center"><span className="text-xs font-bold text-white/60">Avg. Bill</span><span className="text-xl font-black">${detailData.avg_bill.toFixed(2)}</span></div>
                <div className="flex justify-between items-center"><span className="text-xs font-bold text-white/60">Rate</span><span className="text-xl font-black">${detailData.avg_rate.toFixed(4)}</span></div>
                <div className="flex justify-between items-center"><span className="text-xs font-bold text-white/60">Usage</span><span className="text-base font-black">{detailData.usage_kwh?.toLocaleString()} kWh</span></div>
                {detailData.vs_national_bill_pct !== undefined && (
                  <div className={`flex items-center gap-1 text-xs font-black mt-2 ${detailData.vs_national_bill_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {detailData.vs_national_bill_pct > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                    {Math.abs(detailData.vs_national_bill_pct)}% vs National Avg
                  </div>
                )}
                {!isDrilldown && (
                  <button
                    onClick={() => setIsDrilldown(true)}
                    className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-2 text-xs font-black transition-all flex items-center justify-center gap-1"
                  >
                    <MapIcon size={12} /> Drill Down to ZIP level
                  </button>
                )}
              </div>
            )}
          </div>
        </div>


      {/* ── Side Panel ── */}
      <div className="space-y-6">
        {/* State ZIP statistics when drilled down */}
        {isDrilldown && zipStats && (
          <div className="card p-5 bg-white border border-slate-100 shadow-lg space-y-4">
            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1">
              <BarChart2 size={12} /> {selectedState} ZIP Statistics
            </h4>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-baseline">
                <span className="text-slate-500 font-semibold">Total ZIPs</span>
                <span className="font-black text-slate-900">{zipStats.total_zips}</span>
              </div>
              <div className="flex justify-between items-baseline">
                <span className="text-slate-500 font-semibold">Avg. Rate</span>
                <span className="font-black text-slate-900">${zipStats.avg_rate?.toFixed(4)}/kWh</span>
              </div>
              <div className="flex justify-between items-baseline">
                <span className="text-slate-500 font-semibold">Rate Spread (σ)</span>
                <span className="font-black text-slate-600">${zipStats.std_dev?.toFixed(4)}</span>
              </div>
              {zipStats.min_rate && (
                <div className="pt-2 border-t border-slate-50 text-[10px] text-slate-500 space-y-1">
                  <div className="flex justify-between">
                    <span>Cheapest ZIP: {zipStats.min_rate.zip_code}</span>
                    <span className="font-bold text-emerald-600">${zipStats.min_rate.rate?.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Primiest ZIP: {zipStats.max_rate.zip_code}</span>
                    <span className="font-bold text-red-600">${zipStats.max_rate.rate?.toFixed(4)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* State Utility Coverage when drilled down */}
        {isDrilldown && utilityTerritories && (
          <div className="card p-5 bg-white border border-slate-100 shadow-lg space-y-4">
            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1">
              <Zap size={12} /> Utility Coverage
            </h4>
            <div className="space-y-2.5 max-h-[220px] overflow-y-auto pt-1">
              {utilityTerritories.map((util: any) => (
                <div key={util.eia_utility_id} className="flex justify-between items-center text-xs">
                  <div className="truncate max-w-[140px]">
                    <p className="font-bold text-slate-900 truncate">{util.utility_name}</p>
                    <p className="text-[9px] text-slate-400 font-semibold">{util.zip_count} ZIPs served</p>
                  </div>
                  <span className="font-black text-blue-600">
                    {util.avg_residential_rate ? `$${util.avg_residential_rate.toFixed(4)}` : 'N/A'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ZIP Code to Utility Lookup (OpenEI) */}
        <div className="card p-5 bg-white border border-slate-100 shadow-lg space-y-4">
          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1">
            <MapIcon size={12} /> Utility ZIP Finder
          </h4>

            <form onSubmit={handleZipSearch} className="flex gap-2">
              <input
                type="text"
                maxLength={5}
                value={zipInput}
                onChange={(e) => setZipInput(e.target.value.replace(/\D/g, ''))}
                placeholder="Enter ZIP code (e.g. 07101)"
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 outline-none focus:border-blue-500 transition-colors"
              />
              <button
                type="submit"
                disabled={zipSearchLoading || zipInput.length < 5}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-4 py-2 text-xs font-black transition-all disabled:opacity-50"
              >
                Find
              </button>
            </form>

            {zipSearchError && (
              <p className="text-[10px] font-bold text-red-500">{zipSearchError}</p>
            )}

            {zipUtility.length > 0 && (
              <div className="space-y-2 max-h-[160px] overflow-y-auto pt-1">
                {zipUtility.map((util: any) => (
                  <div key={util.eia_utility_id} className="p-2.5 bg-slate-50 rounded-xl border border-slate-100/50">
                    <p className="text-[10px] font-bold text-slate-900 truncate">{util.utility_name}</p>
                    <p className="text-[9px] text-slate-400 font-medium">{util.ownership_type} | {util.service_type}</p>
                    {util.residential_rate && (
                      <p className="text-xs font-black text-blue-600 mt-1">{(util.residential_rate * 100).toFixed(2)}¢/kWh</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 🔹 NEW: PJM Real-time Grid Monitor (EIA-930) */}
          <div className="card p-5 bg-white border border-slate-100 shadow-lg space-y-4">
            <div className="flex justify-between items-center">
              <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <Globe size={12} /> PJM Real-time Grid
              </h4>
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-ping" />
            </div>

            {gridStatus ? (
              <div className="space-y-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-slate-500 font-semibold">Demand Load</span>
                  <span className="text-sm font-black text-slate-900">{(gridStatus.current_demand_mwh / 1000).toFixed(1)} GW</span>
                </div>
                {gridStatus.current_generation_mwh && (
                  <>
                    <div className="flex justify-between items-baseline">
                      <span className="text-xs text-slate-500 font-semibold">Net Generation</span>
                      <span className="text-sm font-black text-emerald-600">{(gridStatus.current_generation_mwh / 1000).toFixed(1)} GW</span>
                    </div>
                    {/* Fuel Mix Snapshot */}
                    <div className="pt-2 border-t border-slate-50">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Top Generation Fuels</p>
                      <div className="space-y-1">
                        {gridStatus.fuel_mix?.slice(0, 3).map((f: any) => (
                          <div key={f.fuel_type} className="flex justify-between text-[10px] font-bold text-slate-600">
                            <span>{f.fuel_type_name}</span>
                            <span>{f.percentage.toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
                <p className="text-[8px] text-slate-400 font-medium pt-1">Source: EIA-930 hourly grid database sync</p>
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-2">Loading grid operations...</p>
            )}
          </div>

          <div className="card p-6 bg-gradient-to-br from-blue-600 to-blue-700 border-none shadow-xl text-white">
            <h4 className="text-[10px] font-black uppercase tracking-widest mb-4 opacity-70">State Trendline</h4>
            <div className="h-[150px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={fallbackTrendData}>
                  <Area type="monotone" dataKey="val" stroke="#FFF" strokeWidth={3} fill="#FFF" fillOpacity={0.1} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex justify-between items-end">
              <div>
                <p className="text-[10px] font-black opacity-60 uppercase">Period Growth</p>
                <p className="text-2xl font-black">{trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}%</p>
              </div>
              {trendData?.total_growth_pct > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            </div>
          </div>

          {/* Growth Metrics from AI */}
          {insightsResult?.state_trend && (
            <div className="card p-5 bg-white border border-slate-100 shadow-lg space-y-3">
              <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1"><BarChart2 size={12} /> AI Growth Metrics</h4>
              <div className="flex justify-between"><span className="text-xs text-slate-500 font-medium">MoM</span><span className="text-sm font-black text-slate-900">{insightsResult.state_trend.growth_metrics?.mom}</span></div>
              <div className="flex justify-between"><span className="text-xs text-slate-500 font-medium">YoY</span><span className="text-sm font-black text-slate-900">{insightsResult.state_trend.growth_metrics?.yoy}</span></div>
              <div className="border-t border-slate-50 pt-3">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Forecast (3-Month)</p>
                <p className="text-xs text-slate-600 leading-relaxed">{insightsResult.state_trend.forecast_hint}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── AI Geo Insights Section ── */}
      {insightsResult && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

          {/* State Trend Analysis */}
          <div className="card p-8 bg-slate-900 text-white border-none shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <Sparkles size={20} className="text-blue-400" />
              <h3 className="text-lg font-black tracking-tight">AI State Trend Analysis — NJ</h3>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <p className="text-sm text-slate-300 leading-relaxed mb-4">{insightsResult.state_trend.trend_analysis}</p>
              </div>
              {stateTrendChartData.length > 0 && (
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={stateTrendChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: '#64748B', fontSize: 9, fontWeight: 600 }}
                        interval={Math.floor(stateTrendChartData.length / 5)}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: '#64748B', fontSize: 9 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(v) => `$${v.toFixed(3)}`}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '12px', fontSize: '11px' }}
                        formatter={(v: any) => [`$${Number(v).toFixed(5)}/kWh`, 'Avg Price']}
                      />
                      <Line type="monotone" dataKey="avg_price" stroke="#60A5FA" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* ZIP Code Insights */}
          <div>
            <div className="flex items-center gap-3 mb-5">
              <Zap size={20} className="text-blue-600" />
              <h3 className="text-xl font-bold text-slate-900">ZIP Code Intelligence</h3>
              <div className="flex gap-2 ml-auto">
                {insightsResult.zip_insights?.map((z: any) => (
                  <button
                    key={z.zip_code}
                    onClick={() => setActiveZip(z.zip_code)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${activeZip === z.zip_code ? 'bg-blue-600 text-white shadow-lg' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
                  >
                    {z.zip_code}
                  </button>
                ))}
              </div>
            </div>

            {activeInsight ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ZipInsightCard insight={activeInsight} />
                <div className="card p-8 bg-white border border-slate-100 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <Info size={16} className="text-blue-600" />
                      <h4 className="text-sm font-black text-slate-900 uppercase tracking-wider">Comparison vs Benchmarks</h4>
                    </div>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                        <span className="text-xs font-bold text-slate-500">State Avg (NJ)</span>
                        <span className="text-sm font-black text-slate-900">{activeInsight.comparisons?.vs_state_avg ?? 'N/A'}</span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                        <span className="text-xs font-bold text-slate-500">National Avg</span>
                        <span className="text-sm font-black text-slate-900">{activeInsight.comparisons?.vs_national_avg ?? 'N/A'}</span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                        <span className="text-xs font-bold text-slate-500">National Ref Rate</span>
                        <span className="text-sm font-black text-slate-900">${NATIONAL_AVG_RATE}/kWh</span>
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-slate-100 pt-5 mt-5">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">AI Anomaly Signal</p>
                    <p className="text-xs text-slate-600 leading-relaxed italic">{activeInsight.anomaly_detection}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {insightsResult.zip_insights?.map((insight: any) => (
                  <ZipInsightCard key={insight.zip_code} insight={insight} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GeoTab;
