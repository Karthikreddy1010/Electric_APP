import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import {
  TrendingDown, TrendingUp, Play, Pause,
  X, Layers, Building2, Calendar, Target,
  Activity, ZapOff, ArrowRight, BarChart2, Info
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  BarChart, Bar, Cell
} from 'recharts';
import USMap from '../USMap.tsx';
import StateZipMap from '../StateZipMap.tsx';

const NJ_ZIPS = ['07101', '07201', '07301', '07401', '07501'];

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
        <div className="flex justify-between"><span className="text-text-secondary font-sans font-normal">Avg bill:</span> <span className="text-text-primary">${data.avg_bill?.toFixed(2) || 'N/A'}</span></div>
        <div className="flex justify-between"><span className="text-text-secondary font-sans font-normal">Avg rate:</span> <span className="text-text-primary">${data.avg_rate?.toFixed(4) || 'N/A'}/kWh</span></div>
        {data.usage_kwh && <div className="flex justify-between"><span className="text-text-secondary font-sans font-normal">Avg usage:</span> <span className="text-text-primary">{data.usage_kwh?.toLocaleString()} kWh</span></div>}
        {data.primary_utility && <div className="flex justify-between"><span className="text-text-secondary font-sans font-normal">Primary utility:</span> <span className="text-primary-blue truncate max-w-[100px] text-right font-sans">{data.primary_utility}</span></div>}
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

const GeoTab = () => {
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
    queryFn: async () => (await axios.get(`/geo/zip-stats?state=${selectedState}`)).data,
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

  useEffect(() => {
    let interval: any;
    if (isPlaying && geoData?.available_months) {
      interval = setInterval(() => {
        setCurrentMonthIdx((prev) => (prev + 1) % geoData.available_months.length);
      }, 1500);
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

  const handleMapHover = (d: any, level: string) => {
    if (!d) {
      setHoverData(null);
      return;
    }
    const enriched = {
      ...d,
      level,
      avg_bill: d.avg_bill || (level === 'State' && geoData?.data?.find((s:any) => s.state === d.state)?.avg_bill),
      avg_rate: d.avg_rate || (level === 'State' && geoData?.data?.find((s:any) => s.state === d.state)?.avg_rate),
    };
    setHoverData(enriched);
  };

  const handleStateClick = (stateName: string) => {
    setSelectedState(stateName);
    setSelectedRegion(stateName);
    setIsDrilldown(true);
    setFloatingPanelOpen(true);
    if (!insightsMutation.isPending) insightsMutation.mutate();
  };

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
      const match = geoData?.data?.find((s:any) => s.state.toLowerCase().includes(searchInput.toLowerCase()));
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
    <div className="flex flex-col min-h-screen bg-bg-primary relative pb-20 animate-in fade-in duration-500 font-sans">
      
      {/* SECTION 1 — TOP CONTROL PANEL */}
      <div className="sticky top-0 z-40 bg-bg-surface border-b border-border-hairline shadow-sm px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        
        {/* Toggle & Level */}
        <div className="flex flex-col gap-3">
          
          {/* Bill / Price Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">Bill</span>
            <button 
              onClick={() => setViewMode(viewMode === 'bill' ? 'rate' : 'bill')} 
              className="relative inline-flex h-5 w-10 items-center rounded-full border border-border-hairline bg-bg-primary transition-colors focus:outline-none"
              aria-label="Toggle view mode"
            >
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-primary-blue transition-transform ${viewMode === 'rate' ? 'translate-x-5' : 'translate-x-1'}`} />
            </button>
            <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">Price</span>
          </div>

          {/* Control Bar (Heatmap Style) */}
          <div className="flex items-stretch border border-border-hairline bg-bg-surface rounded-md shadow-sm overflow-hidden text-xs font-semibold text-text-primary">
            <button 
              onClick={() => setGeoLevel('state')}
              className={`px-3 py-1.5 border-r border-border-hairline transition-colors ${geoLevel === 'state' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
            >
              State
            </button>
            <button 
              onClick={() => setGeoLevel('utility')}
              className={`px-3 py-1.5 border-r border-border-hairline transition-colors ${geoLevel === 'utility' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
            >
              Utility
            </button>
            <button 
              onClick={() => setGeoLevel('county')}
              className={`px-3 py-1.5 border-r border-border-hairline transition-colors ${geoLevel === 'county' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
            >
              County
            </button>
            <button 
              onClick={() => setGeoLevel('zip')}
              className={`px-3 py-1.5 border-r border-border-hairline transition-colors ${geoLevel === 'zip' ? 'bg-bg-primary text-primary-blue font-bold' : 'hover:bg-bg-primary/50'}`}
            >
              ZIP code
            </button>
            <button 
              onClick={handleReset}
              className="px-3 py-1.5 border-r border-border-hairline hover:bg-bg-primary/50 transition-colors"
            >
              Reset
            </button>
            <form onSubmit={handleSearch} className="flex">
              <input 
                type="text" 
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="07304"
                className="w-24 px-2.5 py-1 text-xs font-bold text-text-primary outline-none border-r border-border-hairline placeholder-text-secondary bg-transparent"
                aria-label="ZIP lookup search"
              />
              <button 
                type="submit"
                className="px-3 py-1.5 hover:bg-bg-primary/50 transition-colors"
              >
                Lookup
              </button>
            </form>
          </div>
        </div>

        {/* Timeline Slider */}
        <div className="flex-1 max-w-xl mx-4 hidden lg:flex items-center gap-4 bg-bg-primary px-4 py-1.5 rounded-md border border-border-hairline">
          <button 
            onClick={() => setIsPlaying(!isPlaying)} 
            className={`p-1.5 rounded-full shadow-sm transition-all ${isPlaying ? 'bg-primary-blue text-white' : 'bg-bg-surface text-text-primary border border-border-hairline hover:bg-bg-primary'}`}
            aria-label={isPlaying ? 'Pause simulation timeline' : 'Play simulation timeline'}
          >
            {isPlaying ? <Pause size={12} fill="currentColor" /> : <Play size={12} fill="currentColor" />}
          </button>
          
          <div className="flex-1 relative flex items-center">
            <input 
              type="range" 
              min={0} 
              max={(geoData?.available_months?.length || 1) - 1} 
              value={currentMonthIdx}
              onChange={(e) => { setCurrentMonthIdx(Number(e.target.value)); setIsPlaying(false); }}
              className="w-full h-1 bg-border-hairline rounded-lg appearance-none cursor-pointer accent-primary-blue"
              aria-label="Month slider control"
            />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-text-secondary w-16 text-right flex items-center justify-end gap-1">
            <Calendar size={12}/> {currentMonth}
          </span>
        </div>

        {/* AI Insights Button */}
        <div className="flex items-center">
          <button
            onClick={() => insightsMutation.mutate()}
            disabled={insightsMutation.isPending || !psegHistory}
            className="flex items-center gap-2 px-3.5 py-2 bg-primary-blue text-white rounded-md text-xs font-semibold hover:bg-primary-blue/90 transition-all disabled:opacity-50"
          >
            <Info size={12} />
            <span>AI insights</span>
          </button>
        </div>
      </div>

      {/* Hover Tooltip (Applies globally) */}
      <HoverTooltip visible={!!hoverData} data={hoverData} tooltipRef={tooltipRef} />

      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[650px] bg-bg-surface border-b border-border-hairline">
        
        {/* SECTION 2 & 3 — FULL INTERACTIVE MAP & FLOATING PANEL */}
        <div className="lg:col-span-8 lg:border-r border-border-hairline relative bg-bg-primary overflow-hidden flex items-center justify-center shadow-inner group">
          
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
                colorRange={viewMode === 'bill' ? ["#F0F4FF", "#2F6BFF"] : ["#E8F7F3", "#16A085"]} 
              />
            ) : isBoundariesLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-surface/50 backdrop-blur-sm">
                <div className="animate-spin h-8 w-8 border-b-2 border-primary-blue" />
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
            <div className="absolute top-6 left-6 z-30 w-72 bg-bg-surface border border-border-hairline rounded-md shadow-md p-5 animate-in fade-in slide-in-from-left-4 duration-300">
              <button 
                onClick={() => setFloatingPanelOpen(false)} 
                className="absolute top-4 right-4 text-text-secondary hover:text-text-primary bg-bg-primary hover:bg-border-hairline/50 p-1 rounded-full transition-colors"
                aria-label="Close panel"
              >
                <X size={12} />
              </button>
              
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 bg-primary-blue/10 text-primary-blue rounded-[4px] text-[8px] font-bold uppercase tracking-wider">
                  {isDrilldown && selectedRegion !== selectedState ? 'ZIP Level' : 'State Level'}
                </span>
                <span className="px-2 py-0.5 bg-savings-green/10 text-savings-green rounded-[4px] text-[8px] font-bold uppercase tracking-wider">
                  Active
                </span>
              </div>
              
              <h2 className="text-xl font-bold text-text-primary tracking-tight mb-4">
                {selectedRegion || selectedState}
              </h2>

              <div className="space-y-4 font-mono-numbers text-xs">
                <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                  <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-1 font-sans">Avg monthly bill</p>
                  <p className="text-lg font-bold text-text-primary">${detailData?.avg_bill?.toFixed(2) || '---'}</p>
                  {detailData?.vs_national_bill_pct !== undefined && (
                    <p className={`text-[9px] font-semibold mt-1 flex items-center gap-1 font-sans ${detailData.vs_national_bill_pct > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                      {detailData.vs_national_bill_pct > 0 ? '+' : ''}{detailData.vs_national_bill_pct}% vs National
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-0.5 font-sans">Avg rate</p>
                    <p className="text-xs font-bold text-primary-blue">${detailData?.avg_rate?.toFixed(4) || '---'}</p>
                  </div>
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-0.5 font-sans">Avg usage</p>
                    <p className="text-xs font-bold text-text-primary">{detailData?.usage_kwh?.toLocaleString() || '---'} <span className="text-[9px] font-sans font-normal">kWh</span></p>
                  </div>
                </div>

                {isDrilldown && utilityTerritories && (
                  <div className="border-t border-border-hairline pt-3">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-2 flex items-center gap-1 font-sans">
                      <Building2 size={12}/> Primary utilities
                    </p>
                    <div className="space-y-1.5 max-h-24 overflow-y-auto pr-1 custom-scrollbar">
                      {utilityTerritories.slice(0, 3).map((u:any) => (
                        <div key={u.eia_utility_id} className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-text-primary truncate max-w-[120px] font-sans">{u.utility_name}</span>
                          <span className="text-[9px] font-bold text-text-secondary bg-bg-primary border border-border-hairline px-1.5 py-0.5 rounded-[4px]">{u.zip_count} ZIPs</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {!isDrilldown && (
                <button 
                  onClick={() => setIsDrilldown(true)}
                  className="w-full mt-6 bg-text-primary hover:bg-text-primary/90 text-white py-2 rounded-md text-xs font-semibold transition-all flex items-center justify-center gap-2 shadow-sm"
                >
                  Drill to ZIP level <ArrowRight size={12} />
                </button>
              )}
            </div>
          )}
        </div>

        {/* SECTION 4 — RIGHT INTELLIGENCE PANEL */}
        <div className="lg:col-span-4 bg-bg-primary overflow-y-auto max-h-[650px] p-6 space-y-6 custom-scrollbar border-l border-border-hairline shadow-inner">
          
          {/* AI Insights Summary Card */}
          <div className="panel-operational relative overflow-hidden group hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 mb-4 border-b border-border-hairline pb-2">
              <div className="bg-primary-blue/10 text-primary-blue p-1 rounded-[4px]"><Info size={14} /></div>
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">AI regional insights</h3>
            </div>
            
            {insightsResult ? (
              <div className="space-y-4 relative z-10 text-xs">
                <p className="text-text-primary leading-relaxed font-semibold">
                  {insightsResult.state_trend?.trend_analysis || "Analysis complete. High volatility detected in regional markets."}
                </p>
                
                {insightsResult.state_trend?.forecast_hint && (
                  <div className="bg-primary-blue/5 border border-primary-blue/10 rounded-md p-3 flex gap-2 items-start">
                    <Target size={14} className="text-primary-blue mt-0.5 shrink-0" />
                    <p className="text-[10px] font-bold text-primary-blue leading-relaxed">
                      {insightsResult.state_trend.forecast_hint}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4 text-xs font-semibold text-text-secondary">
                <p className="mb-3">Click AI insights to generate analysis for this region.</p>
                <button 
                  onClick={() => insightsMutation.mutate()} 
                  className="bg-bg-surface hover:bg-bg-primary text-text-primary text-xs font-semibold px-4 py-2 rounded-md transition-colors border border-border-hairline shadow-sm"
                >
                  Generate now
                </button>
              </div>
            )}
          </div>

          {/* PJM Grid Status Widget */}
          <div className="panel-operational hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-4 border-b border-border-hairline pb-2">
              <div className="flex items-center gap-2">
                <div className="bg-savings-green/10 text-savings-green p-1 rounded-[4px]"><Activity size={14} /></div>
                <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Grid operations</h3>
              </div>
              <span className="flex items-center gap-1 bg-savings-green/10 text-savings-green text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-[4px] border border-savings-green/20">
                <span className="w-1 h-1 bg-savings-green rounded-full animate-ping"></span> Live PJM
              </span>
            </div>

            {gridStatus ? (
              <div className="space-y-4 font-mono-numbers text-xs">
                <div className="flex items-baseline justify-between">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider font-sans">Current load</span>
                  <span className="text-base font-bold text-text-primary">{(gridStatus.current_demand_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal text-text-secondary">GW</span></span>
                </div>
                {gridStatus.current_generation_mwh && (
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider font-sans">Generation</span>
                    <span className="text-base font-bold text-savings-green">{(gridStatus.current_generation_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal">GW</span></span>
                  </div>
                )}
                
                {gridStatus.fuel_mix && (
                  <div className="pt-3 border-t border-border-hairline space-y-2">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-1.5 font-sans">Fuel mix</p>
                    {gridStatus.fuel_mix.slice(0, 3).map((f: any) => (
                      <div key={f.fuel_type} className="flex justify-between items-center">
                        <span className="font-semibold text-text-secondary font-sans">{f.fuel_type_name}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1 bg-bg-primary rounded-full overflow-hidden border border-border-hairline">
                            <div className="h-full bg-primary-blue rounded-full" style={{ width: `${f.percentage}%` }}></div>
                          </div>
                          <span className="font-bold text-text-primary text-[10px] w-6 text-right">{f.percentage.toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary py-4 justify-center">
                <ZapOff size={14}/> Connecting to grid...
              </div>
            )}
          </div>

          {/* Utility Intelligence */}
          {isDrilldown && zipStats && (
            <div className="panel-operational hover:shadow-md transition-shadow space-y-4">
               <div className="flex items-center gap-2 border-b border-border-hairline pb-2">
                  <div className="bg-primary-blue/10 text-primary-blue p-1 rounded-[4px]"><Building2 size={14} /></div>
                  <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Market statistics</h3>
                </div>
                <div className="grid grid-cols-2 gap-3 font-mono-numbers text-xs">
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-1 font-sans">ZIPs served</p>
                    <p className="text-base font-bold text-text-primary">{zipStats.total_zips}</p>
                  </div>
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-1 font-sans">Rate volatility</p>
                    <p className="text-base font-bold text-text-primary">${zipStats.std_dev?.toFixed(4)}</p>
                  </div>
                </div>
                {zipStats.min_rate && (
                  <div className="bg-bg-primary p-3 rounded-md border border-border-hairline shadow-sm space-y-1.5 text-[10px] font-mono-numbers">
                    <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-1 font-sans">Extremes</p>
                    <div className="flex justify-between font-bold">
                      <span className="text-text-secondary font-sans font-normal">Low (ZIP {zipStats.min_rate.zip_code})</span>
                      <span className="text-savings-green">${zipStats.min_rate.rate?.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between font-bold">
                      <span className="text-text-secondary font-sans font-normal">High (ZIP {zipStats.max_rate.zip_code})</span>
                      <span className="text-alert-red">${zipStats.max_rate.rate?.toFixed(4)}</span>
                    </div>
                  </div>
                )}
            </div>
          )}

        </div>
      </div>

      {/* SECTION 5 — ANALYTICS DASHBOARD */}
      <div className="max-w-[1400px] mx-auto px-6 py-12 space-y-8">
        
        <div className="flex items-center gap-2 mb-6 border-b border-border-hairline pb-3">
          <BarChart2 className="text-text-secondary" size={18} />
          <h2 className="text-xl font-bold text-text-primary tracking-tight">Deep analytics & trends</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Trend Chart (reuses trendData) */}
          <div className="panel-chart h-[340px] flex flex-col justify-between">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">{selectedState} historical {viewMode === 'bill' ? 'bill' : 'rate'} trend</h3>
              <div className={`flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-[4px] border font-mono-numbers ${trendData?.total_growth_pct > 0 ? 'bg-alert-red/10 text-alert-red border-alert-red/20' : 'bg-savings-green/10 text-savings-green border-savings-green/20'}`}>
                {trendData?.total_growth_pct > 0 ? <TrendingUp size={10}/> : <TrendingDown size={10}/>} 
                {trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}% YoY
              </div>
            </div>
            
            <div className="flex-1 min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData?.months ? trendData.months.map((m:any,i:number) => ({ label: m, val: trendData.values[i] })) : []} margin={{ left: -25, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontWeight: 600}} dy={10} minTickGap={30} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontFamily: 'IBM Plex Mono'}} tickFormatter={(v) => viewMode === 'bill' ? `$${v}` : `$${v}`} domain={['auto', 'auto']} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }} 
                    itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }}
                    formatter={(v:any) => [viewMode==='bill'? `$${Number(v).toFixed(2)}` : `$${Number(v).toFixed(4)}/kWh`, 'Average']}
                  />
                  <Area type="monotone" dataKey="val" stroke="var(--primary-blue)" strokeWidth={2} fill="var(--primary-blue)" fillOpacity={0.08} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AI Projected Forecast / Distribution */}
          <div className="panel-operational h-[340px] flex flex-col justify-between">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-6 border-b border-border-hairline pb-2">Rate distribution analysis</h3>
            {zipStats ? (
              <div className="flex-1 flex flex-col justify-between font-mono-numbers text-xs">
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="bg-bg-primary border border-border-hairline rounded-md p-3 text-center shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary mb-1 font-sans">Bottom 10%</p>
                    <p className="text-xs font-bold text-savings-green">${zipStats.min_rate?.rate?.toFixed(4)}</p>
                  </div>
                  <div className="bg-bg-primary border border-primary-blue/30 rounded-md p-3 text-center shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary mb-1 font-sans">Median rate</p>
                    <p className="text-sm font-bold text-text-primary">${zipStats.avg_rate?.toFixed(4)}</p>
                  </div>
                  <div className="bg-bg-primary border border-border-hairline rounded-md p-3 text-center shadow-sm">
                    <p className="text-[9px] font-bold text-text-secondary mb-1 font-sans">Top 10%</p>
                    <p className="text-xs font-bold text-alert-red">${zipStats.max_rate?.rate?.toFixed(4)}</p>
                  </div>
                </div>
                <div className="h-[120px] flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { range: 'Low', val: 20 }, { range: 'Mid-Low', val: 45 }, 
                      { range: 'Median', val: 80 }, { range: 'Mid-High', val: 35 }, { range: 'High', val: 15 }
                    ]}>
                      <Bar dataKey="val" radius={[2,2,0,0]}>
                        {
                          [0,1,2,3,4].map((i) => (
                            <Cell key={i} fill={i === 2 ? 'var(--primary-blue)' : 'var(--border-hairline)'} />
                          ))
                        }
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <Layers className="text-text-secondary opacity-40 mb-2" size={28}/>
                <p className="text-xs font-semibold text-text-secondary">Drill down to state/ZIP level to view rate distributions.</p>
              </div>
            )}
          </div>

        </div>
      </div>
      
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
