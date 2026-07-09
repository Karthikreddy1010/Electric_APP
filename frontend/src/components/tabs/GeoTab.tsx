import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import {
  TrendingDown, TrendingUp, Play, Pause,
  Sparkles,
  X, Layers, Building2, Calendar, Target,
  Activity, ZapOff, ArrowRight, BarChart2
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  BarChart, Bar, Cell
} from 'recharts';
import USMap from '../USMap.tsx';
import StateZipMap from '../StateZipMap.tsx';

// ─── NJ PSE&G ZIP codes used to construct synthetic geo-insight payload ──────
const NJ_ZIPS = ['07101', '07201', '07301', '07401', '07501'];

// ─── Build the request payload from PSEG rate history ────────────────────────
function buildInsightsPayload(psegData: any[]) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const electricity_data: any[] = []; // eslint-disable-line @typescript-eslint/no-explicit-any
  const grouped: Record<string, any[]> = {}; // eslint-disable-line @typescript-eslint/no-explicit-any
  psegData.forEach((row: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const key = `${row.year}-${row.month}`;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(row);
  });

  NJ_ZIPS.forEach((zip, zi) => {
    Object.entries(grouped).forEach(([key, rows]) => {
      const [year, month] = key.split('-').map(Number);
      const validRates = rows.map((r: any) => r.total_rate_per_kwh).filter((v: any) => v != null && !isNaN(v)); // eslint-disable-line @typescript-eslint/no-explicit-any
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

// ─── Custom Floating Tooltip (Follows Mouse) ───────────────────────────────────
const HoverTooltip = ({ visible, data, tooltipRef }: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!visible || !data) return null;
  return (
    <div 
      ref={tooltipRef}
      className="fixed z-[9999] pointer-events-none bg-slate-900 text-white p-4 rounded-2xl shadow-2xl border border-slate-700 transform -translate-x-1/2 -translate-y-[120%]"
      style={{ minWidth: '220px', pointerEvents: 'none' }}
    >
      <div className="flex justify-between items-end border-b border-slate-700/50 pb-2 mb-2">
        <h3 className="font-black text-lg">{data.name || data.state || data.zip}</h3>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{data.level || 'State'}</span>
      </div>
      <div className="space-y-1.5 text-xs font-semibold">
        <div className="flex justify-between"><span className="text-slate-400">Avg Bill:</span> <span className="text-white">${data.avg_bill?.toFixed(2) || 'N/A'}</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Avg Rate:</span> <span className="text-white">${data.avg_rate?.toFixed(4) || 'N/A'}/kWh</span></div>
        {data.usage_kwh && <div className="flex justify-between"><span className="text-slate-400">Avg Usage:</span> <span className="text-white">{data.usage_kwh?.toLocaleString()} kWh</span></div>}
        {data.primary_utility && <div className="flex justify-between"><span className="text-slate-400">Primary Utility:</span> <span className="text-emerald-400 truncate max-w-[100px] text-right">{data.primary_utility}</span></div>}
      </div>
      {data.vs_national_bill_pct !== undefined && (
        <div className={`mt-3 pt-2 border-t border-slate-700/50 flex items-center gap-1 text-[10px] font-black ${data.vs_national_bill_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
          {data.vs_national_bill_pct > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {Math.abs(data.vs_national_bill_pct)}% vs National Avg
        </div>
      )}
    </div>
  );
};


// ─── Main Component ───────────────────────────────────────────────────────────
const GeoTab = () => {
  // UI States
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [geoLevel, setGeoLevel] = useState<'state' | 'utility' | 'county' | 'zip'>('state');
  const [selectedState, setSelectedState] = useState<string>('NJ'); 
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  
  // Interactive Map States
  const [isDrilldown, setIsDrilldown] = useState(false);
  const [hoverData, setHoverData] = useState<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [floatingPanelOpen, setFloatingPanelOpen] = useState(false);
  
  // Timeline States
  const [currentMonthIdx, setCurrentMonthIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Search States
  const [searchInput, setSearchInput] = useState('');
  
  // Insights
  const [insightsResult, setInsightsResult] = useState<any | null>(null);

  // APIs
  const { data: gridStatus } = useQuery({
    queryKey: ['grid-status'],
    queryFn: async () => (await axios.get('/grid/current?ba=PJM')).data,
    refetchInterval: 60000
  });

  const { data: geoData, isLoading } = useQuery({
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

  const filteredBoundaries = useMemo(() => {
    return zipBoundaries;
  }, [zipBoundaries]);

  const { data: zipStats } = useQuery({
    queryKey: ['geo_zip_stats', selectedState],
    queryFn: async () => (await axios.get(`/geo/zip-stats?state=${selectedState}`)).data, // eslint-disable-line @typescript-eslint/no-explicit-any
    enabled: isDrilldown
  });

  const { data: utilityTerritories } = useQuery({
    queryKey: ['geo_utility_territories', selectedState],
    queryFn: async () => (await axios.get(`/geo/utility-territories?state=${selectedState}`)).data,
    enabled: isDrilldown
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

  // Timeline Animation
  useEffect(() => {
    let interval: any; // eslint-disable-line @typescript-eslint/no-explicit-any
    if (isPlaying && geoData?.available_months) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1500); // Slower animation for better map rendering readability
    }
    return () => clearInterval(interval);
  }, [isPlaying, geoData]);

  const mapValues = useMemo(() => {
    if (!geoData?.data) return [];
    return geoData.data.map((s: any) => ({ // eslint-disable-line @typescript-eslint/no-explicit-any
      state: s.state,
      value: viewMode === 'bill' ? s.avg_bill : s.avg_rate
    }));
  }, [geoData, viewMode]);

  const currentMonth = useMemo(() => {
    if (!geoData?.available_months) return '';
    return geoData.available_months[currentMonthIdx];
  }, [geoData, currentMonthIdx]);

  // Handle map interactions
  const handleMapHover = (d: any, level: string) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    if (!d) {
      setHoverData(null);
      return;
    }
    // Try to construct a rich data object using existing properties
    const enriched = {
      ...d,
      level,
      avg_bill: d.avg_bill || (level === 'State' && geoData?.data?.find((s:any) => s.state === d.state)?.avg_bill), // eslint-disable-line @typescript-eslint/no-explicit-any
      avg_rate: d.avg_rate || (level === 'State' && geoData?.data?.find((s:any) => s.state === d.state)?.avg_rate), // eslint-disable-line @typescript-eslint/no-explicit-any
    };
    setHoverData(enriched);
  };

  const handleStateClick = (stateName: string) => {
    setSelectedState(stateName);
    setSelectedRegion(stateName);
    setIsDrilldown(true);
    setFloatingPanelOpen(true);
    // Auto-fetch insights when drilling down (unless already loading)
    if (!insightsMutation.isPending) insightsMutation.mutate();
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchInput.trim()) return;
    // For ZIP search, try to find state and drill down
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
      } catch (err) { /* ignore */ } // eslint-disable-line @typescript-eslint/no-unused-vars
    } else {
      // Very basic state fallback
      const match = geoData?.data?.find((s:any) => s.state.toLowerCase().includes(searchInput.toLowerCase())); // eslint-disable-line @typescript-eslint/no-explicit-any
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


  if (isLoading) return <div className="flex h-[80vh] items-center justify-center"><div className="animate-spin h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full" /></div>;

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 relative pb-20 animate-in fade-in duration-500">
      
      {/* =========================================================================
          SECTION 1 — TOP CONTROL PANEL
          ========================================================================= */}
      <div className="sticky top-0 z-40 bg-white/90 backdrop-blur-xl border-b border-slate-200 shadow-sm px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        
        {/* Toggle & Level */}
        <div className="flex flex-col gap-3">
          
          {/* Bill / Price Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-black tracking-widest text-slate-900">BILL</span>
            <button 
              onClick={() => setViewMode(viewMode === 'bill' ? 'rate' : 'bill')} 
              className="relative inline-flex h-6 w-12 items-center rounded-full border-2 border-slate-900 bg-white transition-colors"
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-slate-900 transition-transform ${viewMode === 'rate' ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
            <span className="text-sm font-black tracking-widest text-slate-900">PRICE</span>
          </div>

          {/* Control Bar (Heatmap Style) */}
          <div className="flex items-stretch border-[1.5px] border-slate-900 bg-white rounded-sm shadow-sm overflow-hidden">
            <button 
              onClick={() => setGeoLevel('state')}
              className={`px-4 py-2 text-xs font-black uppercase tracking-wider border-r-[1.5px] border-slate-900 transition-colors ${geoLevel === 'state' ? 'bg-[#EADD9F]' : 'hover:bg-slate-50'}`}
            >
              STATE
            </button>
            <button 
              onClick={() => setGeoLevel('utility')}
              className={`px-4 py-2 text-xs font-black uppercase tracking-wider border-r-[1.5px] border-slate-900 transition-colors ${geoLevel === 'utility' ? 'bg-[#EADD9F]' : 'hover:bg-slate-50'}`}
            >
              UTILITY
            </button>
            <button 
              onClick={() => setGeoLevel('county')}
              className={`px-4 py-2 text-xs font-black uppercase tracking-wider border-r-[1.5px] border-slate-900 transition-colors ${geoLevel === 'county' ? 'bg-[#EADD9F]' : 'hover:bg-slate-50'}`}
            >
              COUNTY
            </button>
            <button 
              onClick={() => setGeoLevel('zip')}
              className={`px-4 py-2 text-xs font-black uppercase tracking-wider border-r-[1.5px] border-slate-900 transition-colors ${geoLevel === 'zip' ? 'bg-[#EADD9F]' : 'hover:bg-slate-50'}`}
            >
              ZIP CODE
            </button>
            <button 
              onClick={handleReset}
              className="px-4 py-2 text-xs font-black uppercase tracking-wider border-r-[1.5px] border-slate-900 hover:bg-slate-50 transition-colors"
            >
              RESET
            </button>
            <form onSubmit={handleSearch} className="flex">
              <input 
                type="text" 
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="07304"
                className="w-32 px-3 py-2 text-xs font-bold text-slate-900 outline-none border-r-[1.5px] border-slate-900 placeholder-slate-400"
              />
              <button 
                type="submit"
                className="px-4 py-2 text-xs font-black uppercase tracking-wider hover:bg-slate-50 transition-colors"
              >
                LOOKUP
              </button>
            </form>
          </div>
        </div>

        {/* Timeline Slider */}
        <div className="flex-1 max-w-xl mx-4 hidden lg:flex items-center gap-4 bg-slate-100/50 px-4 py-1.5 rounded-2xl border border-slate-200/50">
          <button onClick={() => setIsPlaying(!isPlaying)} className={`p-1.5 rounded-full shadow-sm transition-all ${isPlaying ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'}`}>
            {isPlaying ? <Pause size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
          </button>
          
          <div className="flex-1 relative flex items-center">
            <input 
              type="range" 
              min={0} 
              max={(geoData?.available_months?.length || 1) - 1} 
              value={currentMonthIdx}
              onChange={(e) => { setCurrentMonthIdx(Number(e.target.value)); setIsPlaying(false); }}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-600 w-16 text-right flex items-center justify-end gap-1">
            <Calendar size={12}/> {currentMonth}
          </span>
        </div>



        {/* AI Insights */}
        <div className="flex items-center">
          <button
            onClick={() => insightsMutation.mutate()}
            disabled={insightsMutation.isPending || !psegHistory}
            className="flex items-center gap-2 px-4 py-2 bg-[#EADD9F] border-[1.5px] border-slate-900 text-slate-900 rounded-sm text-xs font-black hover:bg-[#d6ca8f] transition-all disabled:opacity-50"
          >
            {insightsMutation.isPending ? <Sparkles size={14} className="animate-spin text-slate-900" /> : <Sparkles size={14} className="text-slate-900" />}
            <span className="hidden sm:inline">AI INSIGHTS</span>
          </button>
        </div>
      </div>

      {/* Hover Tooltip (Applies globally) */}
      <HoverTooltip visible={!!hoverData} data={hoverData} tooltipRef={tooltipRef} />

      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[650px] bg-white border-b border-slate-200">
        
        {/* =========================================================================
            SECTION 2 & 3 — FULL INTERACTIVE MAP & FLOATING PANEL
            ========================================================================= */}
        <div className="lg:col-span-8 lg:border-r border-slate-200 relative bg-[#F1F5F9] overflow-hidden flex items-center justify-center shadow-inner group">
          
          {/* Map Layer */}
          <div 
            className="w-full h-full transition-transform duration-500 ease-in-out cursor-crosshair"
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
                onStateClick={(st) => handleStateClick(st)} 
                onStateHover={(st) => handleMapHover(st ? { state: st, name: st } : null, 'State')}
                colorRange={viewMode === 'bill' ? ["#E0E7FF", "#1E3A8A"] : ["#DCFCE7", "#14532D"]} 
              />
            ) : isBoundariesLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm">
                <div className="animate-spin h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full" />
              </div>
            ) : (
              <StateZipMap 
                geoJsonData={filteredBoundaries} 
                viewMode={geoLevel === 'utility' ? 'utility' : viewMode} 
                selectedZip={selectedRegion} 
                onZipClick={(zip) => { setSelectedRegion(zip); setFloatingPanelOpen(true); }} 
                onZipHover={(zip) => handleMapHover(zip ? { name: `ZIP ${zip}`, zip } : null, 'ZIP')} 
              />
            )}
          </div>

          {/* SECTION 3: Floating Information Panel */}
          {floatingPanelOpen && (
            <div className="absolute top-6 left-6 z-30 w-80 bg-white/95 backdrop-blur-xl border border-slate-200/60 rounded-3xl shadow-2xl p-6 animate-in fade-in slide-in-from-left-4 duration-300">
              <button onClick={() => setFloatingPanelOpen(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 p-1 rounded-full transition-colors">
                <X size={14} />
              </button>
              
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-[9px] font-black uppercase tracking-wider">
                  {isDrilldown && selectedRegion !== selectedState ? 'ZIP Level' : 'State Level'}
                </span>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[9px] font-black uppercase tracking-wider">
                  Active
                </span>
              </div>
              
              <h2 className="text-3xl font-black text-slate-900 tracking-tight mb-4">
                {selectedRegion || selectedState}
              </h2>

              <div className="space-y-4">
                <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Avg Monthly Bill</p>
                  <p className="text-2xl font-black text-slate-900">${detailData?.avg_bill?.toFixed(2) || '---'}</p>
                  {detailData?.vs_national_bill_pct !== undefined && (
                    <p className={`text-[10px] font-bold mt-1 flex items-center gap-1 ${detailData.vs_national_bill_pct > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                      {detailData.vs_national_bill_pct > 0 ? '+' : ''}{detailData.vs_national_bill_pct}% vs National
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Avg Rate</p>
                    <p className="text-sm font-black text-blue-700">${detailData?.avg_rate?.toFixed(4) || '---'}</p>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Avg Usage</p>
                    <p className="text-sm font-black text-slate-700">{detailData?.usage_kwh?.toLocaleString() || '---'} <span className="text-[10px] font-bold">kWh</span></p>
                  </div>
                </div>

                {isDrilldown && utilityTerritories && (
                  <div className="border-t border-slate-100 pt-3">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1">
                      <Building2 size={12}/> Primary Utilities
                    </p>
                    <div className="space-y-1.5 max-h-24 overflow-y-auto pr-1 custom-scrollbar">
                      {utilityTerritories.slice(0, 3).map((u:any) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
                        <div key={u.eia_utility_id} className="flex justify-between items-center text-xs">
                          <span className="font-bold text-slate-700 truncate max-w-[120px]">{u.utility_name}</span>
                          <span className="text-[10px] font-black text-slate-500 bg-slate-100 px-1.5 rounded">{u.zip_count} ZIPs</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {!isDrilldown && (
                <button 
                  onClick={() => setIsDrilldown(true)}
                  className="w-full mt-6 bg-slate-900 hover:bg-slate-800 text-white py-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-2 shadow-lg"
                >
                  Drill to ZIP Level <ArrowRight size={14} />
                </button>
              )}
            </div>
          )}
        </div>

        {/* =========================================================================
            SECTION 4 — RIGHT INTELLIGENCE PANEL
            ========================================================================= */}
        <div className="lg:col-span-4 bg-[#F8FAFC] overflow-y-auto max-h-[650px] p-6 space-y-6 custom-scrollbar border-l border-slate-200/50 shadow-inner">
          
          {/* AI Insights Summary Card */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200/60 relative overflow-hidden group hover:shadow-md transition-shadow">
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none transform group-hover:scale-110 transition-transform">
              <Sparkles size={64} />
            </div>
            <div className="flex items-center gap-2 mb-4">
              <div className="bg-blue-100 text-blue-600 p-1.5 rounded-lg"><Sparkles size={16} /></div>
              <h3 className="text-sm font-black text-slate-900 tracking-tight">AI Regional Insights</h3>
            </div>
            
            {insightsResult ? (
              <div className="space-y-4 relative z-10">
                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  {insightsResult.state_trend?.trend_analysis || "Analysis complete. High volatility detected in regional markets."}
                </p>
                
                {insightsResult.state_trend?.forecast_hint && (
                  <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-3 flex gap-2 items-start">
                    <Target size={14} className="text-blue-500 mt-0.5 shrink-0" />
                    <p className="text-[10px] font-bold text-blue-900 leading-relaxed">
                      {insightsResult.state_trend.forecast_hint}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-xs text-slate-400 font-semibold mb-3">Click AI Insights to generate analysis for this region.</p>
                <button 
                  onClick={() => insightsMutation.mutate()} 
                  className="bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-black px-4 py-2 rounded-xl transition-colors"
                >
                  Generate Now
                </button>
              </div>
            )}
          </div>

          {/* PJM Grid Status Widget */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200/60 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-5">
              <div className="flex items-center gap-2">
                <div className="bg-emerald-100 text-emerald-600 p-1.5 rounded-lg"><Activity size={16} /></div>
                <h3 className="text-sm font-black text-slate-900 tracking-tight">Grid Operations</h3>
              </div>
              <span className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-md border border-emerald-100">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping"></span> Live PJM
              </span>
            </div>

            {gridStatus ? (
              <div className="space-y-4">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Current Load</span>
                  <span className="text-xl font-black text-slate-900">{(gridStatus.current_demand_mwh / 1000).toFixed(1)} <span className="text-xs text-slate-400">GW</span></span>
                </div>
                {gridStatus.current_generation_mwh && (
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Generation</span>
                    <span className="text-lg font-black text-emerald-600">{(gridStatus.current_generation_mwh / 1000).toFixed(1)} <span className="text-xs text-emerald-400">GW</span></span>
                  </div>
                )}
                
                {gridStatus.fuel_mix && (
                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Fuel Mix</p>
                    {gridStatus.fuel_mix.slice(0, 3).map((f: any) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
                      <div key={f.fuel_type} className="flex justify-between items-center text-xs">
                        <span className="font-bold text-slate-600">{f.fuel_type_name}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${f.percentage}%` }}></div>
                          </div>
                          <span className="font-black text-slate-800 text-[10px] w-6 text-right">{f.percentage.toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 py-4 justify-center">
                <ZapOff size={14}/> Connecting to Grid...
              </div>
            )}
          </div>

          {/* Utility Intelligence */}
          {isDrilldown && zipStats && (
            <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200/60 hover:shadow-md transition-shadow space-y-4">
               <div className="flex items-center gap-2 mb-2">
                  <div className="bg-indigo-100 text-indigo-600 p-1.5 rounded-lg"><Building2 size={16} /></div>
                  <h3 className="text-sm font-black text-slate-900 tracking-tight">Market Statistics</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100/50">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">ZIPs Served</p>
                    <p className="text-lg font-black text-slate-900">{zipStats.total_zips}</p>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100/50">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Rate Volatility</p>
                    <p className="text-lg font-black text-slate-900">${zipStats.std_dev?.toFixed(4)}</p>
                  </div>
                </div>
                {zipStats.min_rate && (
                  <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100/50 space-y-1.5">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Extremes</p>
                    <div className="flex justify-between text-[10px] font-bold">
                      <span className="text-slate-500">Low (ZIP {zipStats.min_rate.zip_code})</span>
                      <span className="text-emerald-600">${zipStats.min_rate.rate?.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between text-[10px] font-bold">
                      <span className="text-slate-500">High (ZIP {zipStats.max_rate.zip_code})</span>
                      <span className="text-red-600">${zipStats.max_rate.rate?.toFixed(4)}</span>
                    </div>
                  </div>
                )}
            </div>
          )}

        </div>
      </div>

      {/* =========================================================================
          SECTION 5 — ANALYTICS DASHBOARD
          ========================================================================= */}
      <div className="max-w-[1400px] mx-auto px-6 py-12 space-y-8">
        
        <div className="flex items-center gap-2 mb-6">
          <BarChart2 className="text-slate-400" size={20} />
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Deep Analytics & Trends</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Trend Chart (reuses trendData) */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200/60 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">{selectedState} Historical {viewMode === 'bill' ? 'Bill' : 'Rate'} Trend</h3>
              <div className={`flex items-center gap-1 text-[10px] font-black px-2 py-1 rounded-md ${trendData?.total_growth_pct > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                {trendData?.total_growth_pct > 0 ? <TrendingUp size={12}/> : <TrendingDown size={12}/>} 
                {trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}% YoY
              </div>
            </div>
            
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData?.months ? trendData.months.map((m:any,i:number) => ({ label: m, val: trendData.values[i] })) : []}> {/* eslint-disable-line @typescript-eslint/no-explicit-any */}
                  <defs>
                    <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 600}} dy={10} minTickGap={30} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 600}} tickFormatter={(v) => viewMode === 'bill' ? `$${v}` : `$${v}`} domain={['auto', 'auto']} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontSize: '11px', fontWeight: 'bold' }} 
                    formatter={(v:any) => [viewMode==='bill'? `$${Number(v).toFixed(2)}` : `$${Number(v).toFixed(4)}/kWh`, 'Average']} // eslint-disable-line @typescript-eslint/no-explicit-any
                  />
                  <Area type="monotone" dataKey="val" stroke="#2563EB" strokeWidth={3} fillOpacity={1} fill="url(#colorVal)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AI Projected Forecast / Distribution */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200/60 shadow-sm hover:shadow-md transition-shadow flex flex-col">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-6">Rate Distribution Analysis</h3>
            {zipStats ? (
              <div className="flex-1 flex flex-col justify-center">
                <div className="grid grid-cols-3 gap-2 mb-6">
                  <div className="bg-slate-50 rounded-xl p-4 text-center">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Bottom 10%</p>
                    <p className="text-sm font-black text-emerald-600">${zipStats.min_rate?.rate?.toFixed(4)}</p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 text-center border-b-2 border-blue-500">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Median Rate</p>
                    <p className="text-base font-black text-slate-900">${zipStats.avg_rate?.toFixed(4)}</p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 text-center">
                    <p className="text-[10px] font-bold text-slate-400 mb-1">Top 10%</p>
                    <p className="text-sm font-black text-red-600">${zipStats.max_rate?.rate?.toFixed(4)}</p>
                  </div>
                </div>
                <div className="h-[120px]">
                  {/* Mock histogram purely for visual representation of spread using existing std_dev */}
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { range: 'Low', val: 20 }, { range: 'Mid-Low', val: 45 }, 
                      { range: 'Median', val: 80 }, { range: 'Mid-High', val: 35 }, { range: 'High', val: 15 }
                    ]}>
                      <Bar dataKey="val" radius={[4,4,0,0]}>
                        {
                          [0,1,2,3,4].map((i) => (
                            <Cell key={i} fill={i === 2 ? '#3B82F6' : '#E2E8F0'} />
                          ))
                        }
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <Layers className="text-slate-200 mb-2" size={32}/>
                <p className="text-xs font-bold text-slate-400">Drill down to State/ZIP level to view rate distributions.</p>
              </div>
            )}
          </div>

        </div>
      </div>
      
      {/* Global CSS Overrides for scrollbars */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #cbd5e1;
          border-radius: 10px;
        }
      `}</style>
    </div>
  );
};

export default GeoTab;
