/**
 * Regional Insights Page
 *
 * Architecture responsibility: compares rates, bills, grid loads, and clean energy mixes across territories.
 *
 * Organized into sub-tab workspaces:
 *   - Summary: Customer benchmarking comparison stats
 *   - Map: Geo spatial drilldown map with ZIP/State lookups
 *   - Comparison: Rankings of top expensive & cheapest state averages and efficiency scatter plots
 *   - Utility: Local utilities comparison, ZIP disparities, and EIA service listings
 *   - Grid: Real-time PJM balancing telemetry demand, generation, and fuel mix gauges
 *   - Trends: Volatility timelines, YoY sales, and EIA regional trends
 *   - AI Summary: Automated observations and spatial forecasting hints
 */
import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { useBill } from '../context/BillContext.tsx';
import { useNavigation } from '../context/NavigationContext.tsx';
import EmptyBillState from '../components/shared/EmptyBillState.tsx';
import SectionWrapper from './regional/SectionWrapper.tsx';
import USMap from '../components/USMap.tsx';
import StateZipMap from '../components/StateZipMap.tsx';
import {
  TrendingUp, TrendingDown, MapPin, Activity, Building2,
  Play, Pause, ZapOff, ArrowRight, Search, RefreshCw,
  FileText, Sparkles, Layers, Building, Users, Globe, Award
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, Legend, LineChart, Line, AreaChart, Area
} from 'recharts';

const REGION_COLORS: Record<string, string> = {
  Northeast: '#2F6BFF',   // Primary blue
  South: '#F5B041',       // Warning amber
  Midwest: '#16A085',     // Energy teal
  West: '#D64545',        // Alert red
};

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
      style={{ minWidth: '220px' }}
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

const GridReliabilitySection = ({ state }: { state: string }) => {
  const { data: relRes } = useQuery({
    queryKey: ['reliability-section', state],
    queryFn: async () => {
      const res = await axios.get(`/api/municipal/reliability?state=${state}`);
      return res.data;
    }
  });

  const { data: kpis } = useQuery({
    queryKey: ['reliability-kpis', state],
    queryFn: async () => {
      const res = await axios.get(`/api/municipal/reliability/kpis?state=${state}`);
      return res.data;
    }
  });

  const records = relRes?.data || [];

  return (
    <div className="panel-operational space-y-4 bg-bg-surface border border-border-hairline p-5 rounded-xl font-sans">
      <div className="flex items-center justify-between border-b border-border-hairline pb-3">
        <div>
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
            <Activity size={16} className="text-primary-blue" /> EIA-861 Distribution Grid Reliability Indices (SAIDI / SAIFI)
          </h3>
          <p className="text-[11px] text-text-secondary">
            System Average Interruption Duration (SAIDI) and Frequency (SAIFI) benchmarks for {state} Electric Distribution Companies (EDCs).
          </p>
        </div>
        <span className="text-[10px] bg-primary-blue/10 text-primary-blue border border-primary-blue/20 px-2.5 py-1 rounded font-bold">
          IEEE Standard 1366
        </span>
      </div>

      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
            <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block">State Avg SAIDI</span>
            <span className="text-lg font-bold text-text-primary font-mono-numbers">{kpis.avg_saidi_minutes}</span>
            <span className="text-[9px] text-text-secondary block">minutes outage / cust / yr</span>
          </div>

          <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
            <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block">State Avg SAIFI</span>
            <span className="text-lg font-bold text-primary-blue font-mono-numbers">{kpis.avg_saifi}</span>
            <span className="text-[9px] text-text-secondary block">outages / cust / yr</span>
          </div>

          <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
            <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block">State Avg CAIDI</span>
            <span className="text-lg font-bold text-energy-teal font-mono-numbers">{kpis.avg_caidi_minutes}</span>
            <span className="text-[9px] text-text-secondary block">min / outage restoration</span>
          </div>

          <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
            <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block">Total Customers Served</span>
            <span className="text-lg font-bold text-text-primary font-mono-numbers">{(kpis.total_customers / 1e6).toFixed(2)}M</span>
            <span className="text-[9px] text-text-secondary block">metered customers</span>
          </div>
        </div>
      )}

      {records.length > 0 && (
        <div className="overflow-x-auto pt-2">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-border-hairline text-text-secondary uppercase tracking-widest text-[9px]">
                <th className="py-2.5">Utility Name</th>
                <th className="py-2.5 text-right">SAIDI (min/yr)</th>
                <th className="py-2.5 text-right">SAIFI (events/yr)</th>
                <th className="py-2.5 text-right">CAIDI (min/restoration)</th>
                <th className="py-2.5 text-right">Outage Hours/Yr</th>
                <th className="py-2.5 text-right">Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-hairline font-mono-numbers">
              {records.slice(0, 8).map((r: any, idx: number) => {
                const ratingBadge = r.reliability_rating === 'excellent' 
                  ? 'bg-savings-green/10 text-savings-green border-savings-green/20' 
                  : r.reliability_rating === 'good'
                  ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-500 border-amber-500/20';

                return (
                  <tr key={idx} className="hover:bg-bg-secondary/40 transition-colors font-sans">
                    <td className="py-2.5 font-bold text-text-primary">{r.utility_name}</td>
                    <td className="py-2.5 text-right font-mono-numbers text-text-primary font-bold">{r.saidi_minutes}</td>
                    <td className="py-2.5 text-right font-mono-numbers text-primary-blue">{r.saifi}</td>
                    <td className="py-2.5 text-right font-mono-numbers text-text-secondary">{r.caidi_minutes}</td>
                    <td className="py-2.5 text-right font-mono-numbers text-text-secondary">{r.outage_hours_per_year} hrs</td>
                    <td className="py-2.5 text-right">
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${ratingBadge}`}>
                        {r.reliability_rating}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const CensusEnergyBurdenSection = ({ state }: { state: string }) => {
  const { data: countyRes } = useQuery({
    queryKey: ['county-demographics', state],
    queryFn: async () => (await axios.get(`/api/geo/county-demographics?state=${state}`)).data
  });

  const counties = countyRes?.data || [];

  return (
    <div className="panel-operational space-y-4 bg-bg-surface border border-border-hairline p-5 rounded-xl font-sans">
      <div className="flex items-center justify-between border-b border-border-hairline pb-3">
        <div>
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
            <Users size={16} className="text-primary-blue" /> Census ACS Demographics & Social Vulnerability Index (SVI)
          </h3>
          <p className="text-[11px] text-text-secondary">
            County-level household income, poverty rates, homeownership tenure, and regional energy burden benchmarks.
          </p>
        </div>
        <span className="text-[10px] bg-amber-500/10 text-amber-500 border border-amber-500/20 px-2.5 py-1 rounded font-bold">
          US Census ACS 5-Yr
        </span>
      </div>

      <div className="overflow-x-auto pt-2">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-border-hairline text-text-secondary uppercase tracking-widest text-[9px]">
              <th className="py-2.5">County</th>
              <th className="py-2.5 text-right">Population</th>
              <th className="py-2.5 text-right">Median Income</th>
              <th className="py-2.5 text-right">Poverty Rate</th>
              <th className="py-2.5 text-right">Homeownership</th>
              <th className="py-2.5 text-right">Energy Burden</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-hairline font-mono-numbers">
            {counties.map((c: any, idx: number) => {
              const estBurden = ((1920.0 / c.median_household_income) * 100).toFixed(2);
              return (
                <tr key={idx} className="hover:bg-bg-secondary/40 transition-colors font-sans">
                  <td className="py-2.5 font-bold text-text-primary">{c.county} County</td>
                  <td className="py-2.5 text-right font-mono-numbers text-text-secondary">{c.total_population.toLocaleString()}</td>
                  <td className="py-2.5 text-right font-mono-numbers text-text-primary font-bold">${c.median_household_income.toLocaleString()}</td>
                  <td className="py-2.5 text-right font-mono-numbers text-amber-500">{c.poverty_rate_pct}%</td>
                  <td className="py-2.5 text-right font-mono-numbers text-text-secondary">{c.homeownership_pct}%</td>
                  <td className="py-2.5 text-right font-mono-numbers text-primary-blue font-bold">{estBurden}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const GridInterchangeSection = ({ ba }: { ba: string }) => {
  const { data: interchange } = useQuery({
    queryKey: ['grid-interchange', ba],
    queryFn: async () => (await axios.get(`/api/eia930/grid/interchange?ba=${ba}`)).data
  });

  if (!interchange) return null;

  return (
    <div className="panel-operational space-y-4 bg-bg-surface border border-border-hairline p-5 rounded-xl font-sans">
      <div className="flex items-center justify-between border-b border-border-hairline pb-3">
        <div>
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
            <Globe size={16} className="text-energy-teal" /> EIA-930 Regional Grid Interchange & Flow Balance
          </h3>
          <p className="text-[11px] text-text-secondary">
            Net power imports vs exports across neighboring Balancing Authorities for {ba}.
          </p>
        </div>
        <span className="text-[10px] bg-energy-teal/10 text-energy-teal border border-energy-teal/20 px-2.5 py-1 rounded font-bold">
          Self-Sufficiency: {interchange.self_sufficiency_score}%
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono-numbers">
        <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
          <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block font-sans">Net Interchange</span>
          <span className="text-lg font-bold text-text-primary">{interchange.net_interchange_mw} MW</span>
          <span className="text-[9px] text-text-secondary block font-sans">positive = exporting</span>
        </div>
        <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
          <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block font-sans">Total Imports</span>
          <span className="text-lg font-bold text-amber-500">{interchange.total_imports_mwh} MWh</span>
          <span className="text-[9px] text-text-secondary block font-sans">power drawn in</span>
        </div>
        <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
          <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block font-sans">Total Exports</span>
          <span className="text-lg font-bold text-savings-green">{interchange.total_exports_mwh} MWh</span>
          <span className="text-[9px] text-text-secondary block font-sans">power supplied out</span>
        </div>
        <div className="bg-bg-secondary/50 p-3 rounded-lg border border-border-hairline">
          <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block font-sans">Dependency Ratio</span>
          <span className="text-lg font-bold text-primary-blue">{interchange.dependency_ratio_pct}%</span>
          <span className="text-[9px] text-text-secondary block font-sans">import dependence</span>
        </div>
      </div>
    </div>
  );
};

const SUB_TABS = [
  { id: 'summary',    label: 'Summary',    desc: 'Territory benchmarking parameters' },
  { id: 'map',        label: 'Map',        desc: 'Spatial drilldown network' },
  { id: 'comparison', label: 'Comparison', desc: 'Cheapest vs expensive states' },
  { id: 'utility',    label: 'Utility',    desc: 'Local utility listings' },
  { id: 'community',  label: 'Municipality', desc: 'NJ municipal comparisons' },
  { id: 'grid',       label: 'Grid',       desc: 'Real-time grid dispatch' },
  { id: 'trends',     label: 'Trends',     desc: 'EIA timeline volatility' },
  { id: 'ai',         label: 'AI Summary',  desc: 'Spatial observations report' }
];

const RegionalPage = () => {
  const { uploadedBill } = useBill();
  const navigate = useNavigation();
  const [subTab, setSubTab] = useState<string>('summary');

  // ─── PJM Nodal Congestion Map States ───────────────────────────────────────
  const [nodes, setNodes] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeHistory, setNodeHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [mapHour, setMapHour] = useState(12);
  const [isPlayingLmp, setIsPlayingLmp] = useState(false);

  const fetchNodes = async () => {
    try {
      const res = await axios.get('/grid/nodes');
      setNodes(res.data || []);
      if (res.data && res.data.length > 0 && !selectedNode) {
        setSelectedNode(res.data[0]);
      }
    } catch (err) {
      console.warn("Failed to fetch PJM LMP nodes:", err);
    }
  };

  const fetchNodeHistory = async (nodeId: string) => {
    try {
      setLoadingHistory(true);
      const res = await axios.get(`/grid/nodes/${nodeId}/history`);
      setNodeHistory(res.data || []);
    } catch (err) {
      console.warn(`Failed to fetch history for node ${nodeId}:`, err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (subTab === 'grid') {
      fetchNodes();
    }
  }, [subTab]);

  useEffect(() => {
    if (selectedNode) {
      fetchNodeHistory(selectedNode.node_id);
    }
  }, [selectedNode?.node_id]);

  useEffect(() => {
    let timer: any;
    if (isPlayingLmp) {
      timer = setInterval(() => {
        setMapHour((prev) => (prev + 1) % 24);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isPlayingLmp]);

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

  // Merged Utility Intelligence States
  const [granularity, setGranularity] = useState<'annual' | 'monthly'>('annual');
  const [utilitySearchTerm, setUtilitySearchTerm] = useState<string>('');
  const [selectedUtilityId, setSelectedUtilityId] = useState<number | null>(null);

  const round = (val: number, decimals: number) => {
    const p = Math.pow(10, decimals);
    return Math.round(val * p) / p;
  };

  // Queries
  const { data: benchmarkData } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => (await axios.get(`/benchmark?year=${selectedYear}&compare_state=NJ`)).data
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
      const a1 =  0.254829592; const a2 = -0.284496736; const a3 =  1.421413741;
      const a4 = -1.453152027; const a5 =  1.061405429; const p  =  0.3275911;
      const sign = (x < 0) ? -1 : 1;
      const t = Math.abs(x);
      const a = t / (1.0 + p * t);
      return sign * (1.0 - (((((a5 * a + a4) * a) + a3) * a + a2) * a + a1) * a * Math.exp(-t * t));
    };

    const std_dev = state_avg_usage * 0.35;
    const z = (cust_usage - state_avg_usage) / (std_dev * Math.sqrt(2));
    const percentile = round((0.5 * (1 + erf(z))) * 100, 1);
    const savings_opp = Math.max(0, cust_bill - state_avg_bill);
    const savings = savings_opp === 0 ? cust_bill * 0.10 : savings_opp;

    return {
      customer: { monthly_bill: cust_bill, monthly_usage_kwh: cust_usage, percentile },
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
    const zip_avg_bill = 115.0;
    return round(((uploadedBill.total_bill - zip_avg_bill) / zip_avg_bill) * 100, 0);
  }, [uploadedBill]);

  const { data: geoData } = useQuery({
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

  const { data: monthlyTrends } = useQuery({
    queryKey: ['eia861m-trends'],
    queryFn: async () => (await axios.get('/eia861m/trends?sector=total')).data
  });


  const { data: gridStatus } = useQuery({
    queryKey: ['grid-status'],
    queryFn: async () => (await axios.get('/grid/current?ba=PJM')).data,
    refetchInterval: 60000
  });

  const { data: psegHistory } = useQuery({
    queryKey: ['pseg-rate-history'],
    queryFn: async () => (await axios.get('/pseg-rate-history')).data.data
  });

  const { data: stateMonthlyData, isLoading: isMonthlyLoading } = useQuery({
    queryKey: ['eia861m_state_monthly', selectedState],
    queryFn: async () => (await axios.get(`/eia861m/state/${selectedState}`)).data,
    enabled: granularity === 'monthly'
  });

  const { data: utilitiesData, isLoading: isUtilsLoading } = useQuery({
    queryKey: ['eia861_utilities', selectedState],
    queryFn: async () => (await axios.get(`/eia861/utilities?state=${selectedState}`)).data.utilities as any[]
  });

  const { data: utilityDetail, isLoading: isDetailLoading } = useQuery({
    queryKey: ['eia861_utility', selectedUtilityId, selectedState],
    queryFn: async () => {
      if (!selectedUtilityId) return null;
      return (await axios.get(`/eia861/utility/${selectedUtilityId}?state=${selectedState}`)).data;
    },
    enabled: !!selectedUtilityId
  });

  const { data: utilityMetrics } = useQuery({
    queryKey: ['utilityMetrics', selectedUtilityId, selectedState],
    queryFn: async () => {
      if (!selectedUtilityId) return null;
      return (await axios.get(`/eia861/utility/${selectedUtilityId}/metrics?state=${selectedState}`)).data;
    },
    enabled: !!selectedUtilityId
  });

  const [selectedCounty, setSelectedCounty] = useState<string>('');
  const [selectedMuni, setSelectedMuni] = useState<string>('Newark');

  const { data: municipalRankings, isLoading: isMuniRankingsLoading } = useQuery({
    queryKey: ['municipalRankings', selectedCounty],
    queryFn: async () => {
      const url = selectedCounty ? `/municipal/rankings?county=${selectedCounty}` : '/municipal/rankings';
      return (await axios.get(url)).data;
    }
  });

  const { data: municipalHistory, isLoading: isMuniHistoryLoading } = useQuery({
    queryKey: ['municipalHistory', selectedMuni],
    queryFn: async () => {
      return (await axios.get(`/municipal/benchmark?name=${selectedMuni}`)).data;
    }
  });

  const { data: utilityComparisons } = useQuery({
    queryKey: ['utilityComparisons', selectedState],
    queryFn: async () => (await axios.get(`/benchmark/utility-comparison?state=${selectedState}`)).data
  });


  const filteredUtilities = useMemo(() => {
    if (!utilitiesData) return [];
    return utilitiesData.filter(u =>
      u.utility_name.toLowerCase().includes(utilitySearchTerm.toLowerCase())
    );
  }, [utilitiesData, utilitySearchTerm]);

  const [prevFilteredUtilities, setPrevFilteredUtilities] = useState<any[]>([]);
  if (filteredUtilities !== prevFilteredUtilities) {
    setPrevFilteredUtilities(filteredUtilities);
    if (filteredUtilities.length > 0) {
      const njDefault = filteredUtilities.find(u => u.utility_name.includes('Public Service') || u.utility_name.includes('PSE&G'));
      setSelectedUtilityId(njDefault ? njDefault.utility_id : filteredUtilities[0].utility_id);
    } else {
      setSelectedUtilityId(null);
    }
  }

  const latestUtilityData = useMemo(() => {
    if (!utilityDetail || !utilityDetail.history || utilityDetail.history.length === 0) return null;
    const latest = utilityDetail.history[utilityDetail.history.length - 1];
    return {
      ...latest,
      ...utilityMetrics
    };
  }, [utilityDetail, utilityMetrics]);

  const utilityHistoryData = useMemo(() => {
    if (!utilityDetail || !utilityDetail.history) return [];
    return utilityDetail.history.map((h: any) => ({
      ...h,
      avg_price_cents: h.avg_price ? h.avg_price / 10 : 0
    }));
  }, [utilityDetail]);

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
      } catch { /* ignore */ }
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

  if (!uploadedBill) {
    return (
      <EmptyBillState
        title="Regional insights locked"
        description="Ingest an electricity bill inside the Bill Analysis module to evaluate spatial rate disparities."
        ctaLabel="Go to Bill Analysis"
        ctaTab="Bill Analysis"
      />
    );
  }

  const focusStateData = geoData?.data?.find((s: any) => s.state === selectedState);

  return (
    <div className="space-y-6 font-sans pb-16">

      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border-hairline pb-6">
        <div>
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
            GIS Intelligence Workspace
          </span>
          <h2 className="text-3xl font-bold text-text-primary tracking-tight mt-3">Regional Insights</h2>
          <p className="text-xs text-text-secondary mt-1">
            Compare local retail tariffs, balancing authority dispatch mixes, and national EIA benchmarks.
          </p>
        </div>
      </div>

      {/* Navigation Sub-Tabs bar */}
      <div className="flex overflow-x-auto border-b border-border-hairline pb-px bg-bg-surface p-2 rounded-md shadow-sm gap-1">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-4 py-2 text-xs font-bold rounded-md transition-all whitespace-nowrap active:scale-[0.98] ${
              subTab === tab.id
                ? 'bg-bg-secondary text-primary-blue shadow-sm border border-border-hairline'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-primary/50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-Tab Workspaces */}
      <div className="bg-bg-surface border border-border-hairline rounded-md p-6 shadow-sm min-h-[460px]">

        {/* SUMMARY SUB-TAB */}
        {subTab === 'summary' && (
          <SectionWrapper title="Territory Benchmarking" description="See how your consumption rates stack up against state and national metrics.">
            {customerBenchmark && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers">
                  <div className="bg-bg-secondary p-4 rounded-md border border-border-hairline shadow-sm">
                    <span className="text-[10px] text-text-secondary font-bold font-sans uppercase tracking-wider">Usage Percentile</span>
                    <h4 className="text-2xl font-bold text-text-primary mt-1">{customerBenchmark.customer.percentile}th</h4>
                    <p className="text-[9px] text-text-secondary font-sans font-medium mt-1">Percent of similar households you exceed</p>
                  </div>
                  <div className="bg-bg-secondary p-4 rounded-md border border-border-hairline shadow-sm">
                    <span className="text-[10px] text-text-secondary font-bold font-sans uppercase tracking-wider">Savings Potential</span>
                    <h4 className="text-2xl font-bold text-savings-green mt-1">${customerBenchmark.savings_opportunity.toFixed(2)}</h4>
                    <p className="text-[9px] text-savings-green font-sans font-semibold mt-1">Opportunity compared to state normals</p>
                  </div>
                  <div className="bg-bg-secondary p-4 rounded-md border border-border-hairline shadow-sm">
                    <span className="text-[10px] text-text-secondary font-bold font-sans uppercase tracking-wider">Disparity Margin</span>
                    <h4 className="text-2xl font-bold text-warning-amber mt-1">{diffZipPct > 0 ? '+' : ''}{diffZipPct}%</h4>
                    <p className="text-[9px] text-text-secondary font-sans font-medium mt-1">Vs benchmark local ZIP baseline</p>
                  </div>
                </div>

                <div className="panel-operational space-y-4">
                  <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Comparative Baselines</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono-numbers">
                      <thead>
                        <tr className="border-b border-border-hairline text-text-secondary uppercase text-[9px]">
                          <th className="py-2">Baseline</th>
                          <th className="py-2 text-right">Avg Bill</th>
                          <th className="py-2 text-right">Avg Usage (kWh)</th>
                          <th className="py-2 text-right">Disparity</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-hairline text-text-primary">
                        {customerBenchmark.comparisons.map((c) => (
                          <tr key={c.name} className="hover:bg-bg-secondary/40 transition-colors">
                            <td className="py-3 font-sans font-semibold">{c.name}</td>
                            <td className="py-3 text-right font-bold">${c.avg_bill.toFixed(2)}</td>
                            <td className="py-3 text-right text-text-secondary">{c.avg_usage_kwh.toFixed(0)}</td>
                            <td className={`py-3 text-right font-bold ${c.diff_bill > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                              {c.diff_bill > 0 ? '+' : ''}${c.diff_bill.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Utility Benchmarking Dashboard */}
                <div className="border-t border-border-hairline pt-6 mt-6 space-y-6">
                  <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider font-sans">
                    Utility Operations & Benchmark Comparison
                  </h4>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Horizontal Bar Chart for average annual consumption */}
                    <div className="panel-chart h-[280px] flex flex-col justify-between">
                      <h5 className="text-[10px] font-bold uppercase text-text-secondary border-b border-border-hairline pb-2 mb-4 font-sans">
                        Average Annual Consumption per Customer (kWh)
                      </h5>
                      <div className="flex-1 min-h-[180px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={utilityComparisons?.slice(0, 5) || []}
                            layout="vertical"
                            margin={{ left: 5, right: 10, top: 0, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis type="number" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis
                              type="category"
                              dataKey="utility_name"
                              tick={{ fontSize: 8, fill: 'var(--text-secondary)' }}
                              axisLine={false}
                              tickLine={false}
                              width={100}
                            />
                            <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} kWh`, 'Avg Consumption']} />
                            <Bar dataKey="avg_annual_consumption_kwh" fill="var(--primary-blue)" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Grid Efficiency comparison */}
                    <div className="panel-chart h-[280px] flex flex-col justify-between">
                      <h5 className="text-[10px] font-bold uppercase text-text-secondary border-b border-border-hairline pb-2 mb-4 font-sans">
                        Grid Transmission Losses (%)
                      </h5>
                      <div className="flex-1 min-h-[180px] overflow-y-auto space-y-3 custom-scrollbar">
                        {(utilityComparisons?.slice(0, 5) || []).map((u: any) => (
                          <div key={u.utility_name} className="space-y-1 text-xs">
                            <div className="flex justify-between font-semibold">
                              <span className="text-text-primary truncate max-w-[180px]">{u.utility_name}</span>
                              <span className="text-text-secondary font-mono">{u.transmission_losses_pct}%</span>
                            </div>
                            <div className="w-full bg-bg-secondary h-2 rounded-full overflow-hidden border border-border-hairline">
                              <div
                                className={`h-full rounded-full ${
                                  u.transmission_losses_pct > 6.0 ? 'bg-alert-red' : 'bg-savings-green'
                                }`}
                                style={{ width: `${Math.min(u.transmission_losses_pct * 8, 100)}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </SectionWrapper>
        )}

        {/* MAP SUB-TAB */}
        {subTab === 'map' && (
          <SectionWrapper title="Geographic Spatial Map" description="Drill down into U.S. states and municipal boundaries to inspect tariff variances.">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-8 flex flex-col space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4 bg-bg-secondary p-4 border border-border-hairline rounded-md">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-text-secondary uppercase font-sans">View metrics:</span>
                    <div className="flex bg-bg-surface p-0.5 rounded border border-border-hairline text-[10px] font-bold">
                      <button
                        onClick={() => setViewMode('bill')}
                        className={`px-2.5 py-1 rounded-sm transition-all ${viewMode === 'bill' ? 'bg-bg-secondary text-primary-blue shadow-sm' : 'text-text-secondary'}`}
                      >
                        Bill
                      </button>
                      <button
                        onClick={() => setViewMode('rate')}
                        className={`px-2.5 py-1 rounded-sm transition-all ${viewMode === 'rate' ? 'bg-bg-secondary text-primary-blue shadow-sm' : 'text-text-secondary'}`}
                      >
                        Rate
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-text-secondary uppercase font-sans">Granularity:</span>
                    <div className="flex bg-bg-surface p-0.5 rounded border border-border-hairline text-[10px] font-bold">
                      {['state', 'utility', 'zip'].map((level) => (
                        <button
                          key={level}
                          onClick={() => setGeoLevel(level as any)}
                          className={`px-2.5 py-1 rounded-sm transition-all capitalize ${geoLevel === level ? 'bg-bg-secondary text-primary-blue shadow-sm' : 'text-text-secondary'}`}
                        >
                          {level === 'zip' ? 'ZIP' : level}
                        </button>
                      ))}
                      <button onClick={handleReset} className="px-2.5 py-1 text-text-secondary hover:text-text-primary">
                        Reset
                      </button>
                    </div>
                  </div>

                  <form onSubmit={handleSearch} className="flex border border-border-hairline bg-bg-surface rounded overflow-hidden shadow-sm">
                    <input
                      type="text"
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      placeholder="ZIP / State"
                      className="w-20 px-2 py-1 text-[10px] font-semibold text-text-primary outline-none placeholder-text-secondary bg-transparent"
                      aria-label="ZIP lookup"
                    />
                    <button type="submit" className="px-3 py-1 text-[10px] bg-bg-secondary border-l border-border-hairline font-bold">
                      Go
                    </button>
                  </form>
                </div>

                <HoverTooltip visible={!!hoverData} data={hoverData} tooltipRef={tooltipRef} />

                <div
                  className="w-full relative bg-bg-secondary cursor-crosshair min-h-[400px] border border-border-hairline rounded-md overflow-hidden shadow-inner"
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

              {/* Sidebar Info Details Panel */}
              <div className="lg:col-span-4 bg-bg-secondary border border-border-hairline rounded-md p-5 flex flex-col justify-between shadow-sm">
                <div>
                  <div className="flex items-center gap-2 border-b border-border-hairline pb-2 mb-4">
                    <MapPin size={16} className="text-primary-blue" />
                    <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">Territory Parameters</h4>
                  </div>

                  {floatingPanelOpen ? (
                    <div className="space-y-4 font-mono-numbers text-xs">
                      <div>
                        <span className="px-2 py-0.5 bg-primary-blue/10 text-primary-blue rounded-[4px] text-[8px] font-bold uppercase tracking-wider block w-max mb-1">
                          {isDrilldown && selectedRegion !== selectedState ? 'ZIP code focus' : 'State wide focus'}
                        </span>
                        <h5 className="text-lg font-bold text-text-primary tracking-tight font-sans">
                          {selectedRegion || selectedState}
                        </h5>
                      </div>

                      <div className="bg-bg-surface p-3 rounded-md border border-border-hairline shadow-sm space-y-1">
                        <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest font-sans">Average Monthly Bill</p>
                        <p className="text-lg font-bold text-text-primary">${detailData?.avg_bill?.toFixed(2) || '120.00'}</p>
                        {detailData?.vs_national_bill_pct !== undefined && (
                          <p className={`text-[9px] font-bold mt-1 flex items-center gap-1 font-sans ${detailData.vs_national_bill_pct > 0 ? 'text-alert-red' : 'text-savings-green'}`}>
                            {detailData.vs_national_bill_pct > 0 ? '+' : ''}{detailData.vs_national_bill_pct}% vs national average
                          </p>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-bg-surface p-3 rounded-md border border-border-hairline shadow-sm">
                          <p className="text-[9px] font-bold text-text-secondary uppercase tracking-widest mb-0.5 font-sans">Average Rate</p>
                          <p className="text-xs font-bold text-primary-blue">${detailData?.avg_rate?.toFixed(4) || '0.1600'}</p>
                        </div>
                        <div className="bg-bg-surface p-3 rounded-md border border-border-hairline shadow-sm">
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
                                <span className="text-[9px] font-bold text-text-secondary bg-bg-surface border border-border-hairline px-1.5 py-0.5 rounded-[4px]">{u.zip_count} ZIPs</span>
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

                <div className="border-t border-border-hairline pt-4 mt-6">
                  <h5 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2 font-sans">State KPI Profile ({selectedState})</h5>
                  <div className="flex items-center justify-between text-xs font-mono-numbers">
                    <span className="text-text-secondary">Expensive Rank:</span>
                    <span className="font-bold text-text-primary">#{focusStateData?.rank || '11'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono-numbers mt-1.5">
                    <span className="text-text-secondary">Average Rate:</span>
                    <span className="font-bold text-text-primary">
                      ${(focusStateData?.avg_rate * 100 || 16.5).toFixed(1)}¢<span className="text-[10px] font-sans font-normal text-text-secondary">/kWh</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </SectionWrapper>
        )}

        {/* COMPARISON SUB-TAB */}
        {subTab === 'comparison' && (
          <SectionWrapper title="Regional Rankings" description="National comparison showing the highest and lowest average energy prices.">
            {benchmarkData && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="panel-chart h-[380px] flex flex-col justify-between">
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

                <div className="panel-chart h-[380px] flex flex-col justify-between">
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

                <div className="panel-chart h-[380px] flex flex-col justify-between">
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
                        <Tooltip formatter={(v: any, name: any) => [name === 'Rate' ? `${(Number(v) * 100).toFixed(1)}¢/kWh` : `$${Number(v).toFixed(0)}`, name]} labelFormatter={() => ''} />
                        <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '9px' }} />
                        {Object.entries(REGION_COLORS).map(([region, color]) => (
                          <Scatter key={region} name={region} data={(benchmarkData.scatter_data || []).filter((d: any) => d.region === region)} fill={color}>
                            {(benchmarkData.scatter_data || []).filter((d: any) => d.region === region).map((_: any, idx: number) => (
                              <Cell key={idx} fill={color} opacity={0.7} />
                            ))}
                          </Scatter>
                        ))}
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                {/* Census ACS Demographics & Energy Burden Section */}
                <CensusEnergyBurdenSection state={selectedState} />
              </div>
            )}
          </SectionWrapper>
        )}

        {/* UTILITY SUB-TAB */}
        {subTab === 'utility' && (
          <SectionWrapper title="Local Utilities & DISPARITIES" description="Look up individual load serving entities, rate schedules, and municipal listings.">
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-bg-secondary rounded-md p-4 border border-border-hairline">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5 font-sans">Selected State</label>
                  <div className="w-full bg-bg-surface border border-border-hairline rounded-md px-3 py-2 text-xs font-bold text-text-primary">
                    {selectedState}
                  </div>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5 font-sans">Search Local Utility</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 text-text-secondary" size={14} />
                    <input
                      type="text"
                      placeholder={`Search utilities in ${selectedState}...`}
                      value={utilitySearchTerm}
                      onChange={(e) => setUtilitySearchTerm(e.target.value)}
                      className="w-full bg-bg-surface border border-border-hairline rounded-md pl-9 pr-4 py-2 text-xs font-semibold text-text-primary outline-none focus:border-primary-blue"
                      aria-label="Search utility"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <div className="lg:col-span-1 bg-bg-secondary rounded-md border border-border-hairline p-4 flex flex-col max-h-[460px]">
                  <h4 className="text-[10px] font-bold uppercase text-text-secondary px-1 mb-3 font-sans">Utilities List ({filteredUtilities.length})</h4>
                  <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar text-xs font-semibold">
                    {isUtilsLoading ? (
                      <div className="text-text-secondary p-4 animate-pulse">Loading utilities...</div>
                    ) : filteredUtilities.length === 0 ? (
                      <div className="text-text-secondary p-4 italic">No utilities found.</div>
                    ) : (
                      filteredUtilities.map(u => (
                        <button
                          key={u.utility_id}
                          onClick={() => setSelectedUtilityId(u.utility_id)}
                          className={`w-full text-left px-3 py-2 rounded-md transition-all block truncate active:scale-[0.98] ${
                            selectedUtilityId === u.utility_id
                              ? 'bg-primary-blue text-white shadow-sm font-bold'
                              : 'text-text-primary hover:bg-bg-surface border border-transparent'
                          }`}
                        >
                          {u.utility_name}
                        </button>
                      ))
                    )}
                  </div>
                </div>

                <div className="lg:col-span-3 space-y-6">
                  {isDetailLoading || !latestUtilityData ? (
                    <div className="bg-bg-secondary rounded-md border border-border-hairline p-12 text-center text-text-secondary flex flex-col items-center justify-center">
                      <RefreshCw size={24} className="animate-spin text-primary-blue mb-4" />
                      <span>Loading utility performance analytics...</span>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="bg-bg-secondary rounded-md border border-border-hairline p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-[9px] font-bold uppercase bg-primary-blue/10 text-primary-blue px-2 py-0.5 rounded-[4px] border border-primary-blue/20">
                              {selectedState} network profile
                            </span>
                            <div className="flex bg-bg-surface p-0.5 rounded border border-border-hairline text-[8px] font-bold uppercase">
                              <button
                                onClick={() => setGranularity('annual')}
                                className={`px-2 py-0.5 rounded-sm transition-all ${granularity === 'annual' ? 'bg-bg-secondary text-primary-blue shadow-sm border border-border-hairline' : 'text-text-secondary'}`}
                              >
                                Annual
                              </button>
                              <button
                                onClick={() => setGranularity('monthly')}
                                className={`px-2 py-0.5 rounded-sm transition-all ${granularity === 'monthly' ? 'bg-bg-secondary text-primary-blue shadow-sm border border-border-hairline' : 'text-text-secondary'}`}
                              >
                                Monthly
                              </button>
                            </div>
                          </div>
                          <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-primary-blue mb-1">
                            <MapPin size={12} /> {utilityDetail.utility_name}
                          </div>
                          <p className="text-[10px] text-text-secondary mt-1 font-mono-numbers">Utility ID: {utilityDetail.utility_id}</p>
                        </div>
                      </div>

                      {granularity === 'monthly' ? (
                        isMonthlyLoading || !stateMonthlyData ? (
                          <div className="bg-bg-secondary rounded-md border border-border-hairline p-12 text-center text-text-secondary flex flex-col items-center justify-center">
                            <RefreshCw size={24} className="animate-spin text-primary-blue mb-4" />
                            <span>Loading monthly trends...</span>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="panel-chart h-[280px] flex flex-col justify-between">
                              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                                Monthly Sales (MWh)
                              </h4>
                              <div className="flex-1 min-h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                  <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({ period: p, sales: stateMonthlyData.sales[idx] })).slice(-12)} margin={{ left: -25, right: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                                    <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} MWh`, 'Sales']} />
                                    <Line type="monotone" dataKey="sales" stroke="var(--primary-blue)" strokeWidth={2} dot={false} />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            </div>

                            <div className="panel-chart h-[280px] flex flex-col justify-between">
                              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                                Retail Price (¢/kWh)
                              </h4>
                              <div className="flex-1 min-h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                  <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({ period: p, price: stateMonthlyData.prices[idx] })).slice(-12)} margin={{ left: -25, right: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                                    <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}¢/kWh`, 'Price']} />
                                    <Line type="monotone" dataKey="price" stroke="var(--energy-teal)" strokeWidth={2} dot={false} />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          </div>
                        )
                      ) : (
                        <div className="space-y-6">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono-numbers text-text-primary text-xs">
                            <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md">
                              <p className="text-[9px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Residential Rate</p>
                              <h4 className="text-lg font-bold">
                                {latestUtilityData.avg_price ? `${(latestUtilityData.avg_price / 10).toFixed(2)}¢` : 'N/A'}
                              </h4>
                            </div>
                            <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md">
                              <p className="text-[9px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Customers Served</p>
                              <h4 className="text-lg font-bold">
                                {latestUtilityData.total_customers ? latestUtilityData.total_customers.toLocaleString() : 'N/A'}
                              </h4>
                            </div>
                            <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md">
                              <p className="text-[9px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Summer Peak</p>
                              <h4 className="text-lg font-bold">
                                {latestUtilityData.peak_demand ? `${latestUtilityData.peak_demand.toLocaleString()} MW` : 'N/A'}
                              </h4>
                            </div>
                            <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md bg-primary-blue/5 border-primary-blue/20">
                              <p className="text-[9px] text-primary-blue font-bold font-sans mb-1 uppercase tracking-wider">Solar Net Metering</p>
                              <h4 className="text-lg font-bold text-primary-blue">
                                {latestUtilityData.nm_customers ? latestUtilityData.nm_customers.toLocaleString() : '0'}
                              </h4>
                            </div>
                          </div>

                          <div className="bg-bg-secondary border border-border-hairline rounded-md p-4 space-y-3">
                            <h5 className="text-[10px] font-bold uppercase tracking-wider text-text-secondary border-b border-border-hairline pb-1.5 font-sans">
                              Infrastructure & Utility Profile Metadata
                            </h5>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-semibold">
                              <div>
                                <span className="text-[9px] text-text-secondary block mb-0.5 font-sans uppercase">Ownership Type</span>
                                <span className="text-text-primary font-mono">{latestUtilityData.ownership_type || 'Investor Owned'}</span>
                              </div>
                              <div>
                                <span className="text-[9px] text-text-secondary block mb-0.5 font-sans uppercase">NERC Region</span>
                                <span className="text-text-primary font-mono">{latestUtilityData.nerc_region || 'RFC'}</span>
                              </div>
                              <div>
                                <span className="text-[9px] text-text-secondary block mb-0.5 font-sans uppercase">RTO / ISO Market</span>
                                <span className="text-text-primary font-mono">{latestUtilityData.rto_iso || 'PJM Interconnection'}</span>
                              </div>
                              <div>
                                <span className="text-[9px] text-text-secondary block mb-0.5 font-sans uppercase">Service Territory</span>
                                <span className="text-text-primary font-mono">{latestUtilityData.service_territory || 'NJ Service Area'}</span>
                              </div>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="panel-chart h-[280px] flex flex-col justify-between">
                              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                                Historical price trend (cents/kWh)
                              </h4>
                              <div className="flex-1 min-h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                  <LineChart data={utilityHistoryData} margin={{ left: -25, right: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                                    <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}¢/kWh`, 'Price']} />
                                    <Line type="monotone" dataKey="avg_price_cents" stroke="var(--primary-blue)" strokeWidth={2} dot={{ r: 3, fill: 'var(--primary-blue)', strokeWidth: 0 }} />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            </div>

                            <div className="panel-chart h-[280px] flex flex-col justify-between">
                              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                                Solar Net Metering (MWh)
                              </h4>
                              <div className="flex-1 min-h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                  <LineChart data={utilityHistoryData} margin={{ left: -25, right: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                                    <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                                    <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} MWh`, 'Energy Sold Back']} />
                                    <Line type="monotone" dataKey="nm_energy_mwh" name="Energy Sold Back (MWh)" stroke="var(--savings-green)" strokeWidth={2} activeDot={{ r: 6 }} dot={false} />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </SectionWrapper>
        )}

        {/* MUNICIPALITY SUB-TAB */}
        {subTab === 'community' && (
          <SectionWrapper title="New Jersey Municipality Dashboard" description="Compare energy intensity, natural gas-to-electricity ratios, and historical community energy baselines.">
            <div className="space-y-6">
              {/* Controls Bar */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-bg-secondary rounded-md p-4 border border-border-hairline">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5 font-sans">Filter by County</label>
                  <select
                    value={selectedCounty}
                    onChange={(e) => setSelectedCounty(e.target.value)}
                    className="w-full bg-bg-surface border border-border-hairline rounded-md px-3 py-2 text-xs font-bold text-text-primary outline-none focus:border-primary-blue"
                    aria-label="Filter county"
                  >
                    <option value="">All NJ Counties</option>
                    <option value="Essex">Essex County</option>
                    <option value="Bergen">Bergen County</option>
                    <option value="Middlesex">Middlesex County</option>
                    <option value="Monmouth">Monmouth County</option>
                    <option value="Hudson">Hudson County</option>
                    <option value="Union">Union County</option>
                    <option value="Morris">Morris County</option>
                    <option value="Ocean">Ocean County</option>
                    <option value="Passaic">Passaic County</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5 font-sans">Selected Municipality</label>
                  <div className="w-full bg-bg-surface border border-border-hairline rounded-md px-3 py-2 text-xs font-bold text-text-primary">
                    {selectedMuni}
                  </div>
                </div>
                <div className="flex items-end">
                  <span className="text-[10px] text-text-secondary font-sans font-semibold mb-2">
                    Click any municipality in the ranking table to view detail charts.
                  </span>
                </div>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono-numbers text-text-primary text-xs">
                <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md">
                  <p className="text-[9px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">County Total Usage</p>
                  <h4 className="text-lg font-bold">
                    {municipalRankings?.county_summary?.[0]?.total_elec_kwh
                      ? `${(municipalRankings.county_summary.reduce((a: number, b: any) => a + (b.total_elec_kwh || 0), 0) / 1000000).toFixed(1)} GWh`
                      : 'N/A'}
                  </h4>
                </div>
                <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md">
                  <p className="text-[9px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Municipalities Surveyed</p>
                  <h4 className="text-lg font-bold">
                    {municipalRankings?.rankings?.length || 0}
                  </h4>
                </div>
                <div className="bg-bg-secondary border border-border-hairline p-3 rounded-md bg-primary-blue/5 border-primary-blue/20">
                  <p className="text-[9px] text-primary-blue font-bold font-sans mb-1 uppercase tracking-wider">Active Focus Rank</p>
                  <h4 className="text-lg font-bold text-primary-blue">
                    #{municipalRankings?.rankings?.find((r: any) => r.municipality === selectedMuni)?.rank || 'N/A'}
                  </h4>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Ranking Table */}
                <div className="lg:col-span-7 bg-bg-secondary rounded-md border border-border-hairline p-4 flex flex-col max-h-[500px]">
                  <h4 className="text-[10px] font-bold uppercase text-text-secondary px-1 mb-3 font-sans">Municipality Rankings</h4>
                  <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar text-xs font-semibold">
                    {isMuniRankingsLoading ? (
                      <div className="text-text-secondary p-4 animate-pulse">Loading rankings...</div>
                    ) : !municipalRankings?.rankings ? (
                      <div className="text-text-secondary p-4 italic">No rankings loaded.</div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="border-b border-border-hairline text-text-secondary text-[10px] uppercase font-sans">
                              <th className="py-2 px-1 text-center w-10">Rank</th>
                              <th className="py-2 px-2">Municipality</th>
                              <th className="py-2 px-2">County</th>
                              <th className="py-2 px-2 text-right">Electricity (MWh)</th>
                              <th className="py-2 px-2 text-right">Gas-to-Elec Ratio</th>
                            </tr>
                          </thead>
                          <tbody>
                            {municipalRankings.rankings.map((r: any) => (
                              <tr
                                key={r.municipality}
                                onClick={() => setSelectedMuni(r.municipality)}
                                className={`border-b border-border-hairline cursor-pointer hover:bg-bg-surface transition-all ${
                                  selectedMuni === r.municipality ? 'bg-primary-blue/5 text-primary-blue font-bold' : ''
                                }`}
                              >
                                <td className="py-2 px-1 text-center font-mono">{r.rank}</td>
                                <td className="py-2 px-2 font-sans truncate max-w-[120px]">{r.municipality}</td>
                                <td className="py-2 px-2 font-sans truncate max-w-[100px]">{r.county}</td>
                                <td className="py-2 px-2 text-right font-mono">{(r.total_electricity_kwh / 1000).toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                <td className="py-2 px-2 text-right font-mono">{r.gas_to_electric_ratio}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>

                {/* Detail Charts */}
                <div className="lg:col-span-5 space-y-6">
                  {isMuniHistoryLoading || !municipalHistory ? (
                    <div className="bg-bg-secondary rounded-md border border-border-hairline p-12 text-center text-text-secondary flex flex-col items-center justify-center h-full">
                      <RefreshCw size={24} className="animate-spin text-primary-blue mb-4" />
                      <span>Loading municipality energy history...</span>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Fuel Mix Chart */}
                      <div className="panel-chart h-[230px] flex flex-col justify-between">
                        <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                          {selectedMuni} Fuel split Share
                        </h4>
                        <div className="flex-1 min-h-[160px]">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                              data={[
                                {
                                  name: 'Electricity',
                                  kwh: municipalHistory.history[municipalHistory.history.length - 1]?.total_electricity_kwh || 0
                                },
                                {
                                  name: 'Natural Gas',
                                  kwh: (municipalHistory.history[municipalHistory.history.length - 1]?.total_natural_gas_therms || 0) * 29.3
                                }
                              ]}
                              margin={{ left: -10, right: 10 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                              <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                              <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(Number(v) / 1000000).toFixed(1)}M`} />
                              <Tooltip formatter={(v) => [`${(Number(v) / 29.3).toLocaleString(undefined, { maximumFractionDigits: 0 })} Units (kWh Equiv)`, 'Usage']} />
                              <Bar dataKey="kwh" fill="var(--primary-blue)" radius={[4, 4, 0, 0]}>
                                <Cell fill="var(--primary-blue)" />
                                <Cell fill="var(--energy-teal)" />
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Historical Consumption Line Chart */}
                      <div className="panel-chart h-[230px] flex flex-col justify-between">
                        <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                          Historical consumption Trend
                        </h4>
                        <div className="flex-1 min-h-[160px]">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={municipalHistory.history} margin={{ left: -15, right: 10 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                              <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                              <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(Number(v) / 1000).toFixed(0)}k`} />
                              <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} kWh`, 'Electricity']} />
                              <Line type="monotone" dataKey="total_electricity_kwh" stroke="var(--primary-blue)" strokeWidth={2} dot={{ r: 3 }} />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </SectionWrapper>
        )}

        {/* GRID SUB-TAB */}
        {subTab === 'grid' && (
          <SectionWrapper title="Live PJM Balancing Dispatch" description="Real-time physical dispatch statistics, marginal costs, and aggregate fuel mix.">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers text-text-primary">
              <div className="panel-operational bg-bg-secondary flex flex-col justify-between min-h-[200px]">
                <div>
                  <div className="flex justify-between items-center mb-4 border-b border-border-hairline pb-2">
                    <span className="text-xs font-bold text-text-primary font-sans">Grid Load Demand</span>
                    <span className="flex items-center gap-1 bg-savings-green/10 text-savings-green text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-[4px] border border-savings-green/20">
                      Live PJM
                    </span>
                  </div>
                  {gridStatus ? (
                    <div className="space-y-3.5">
                      <div className="flex justify-between items-baseline">
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider font-sans">Current Demand:</span>
                        <span className="text-base font-bold">
                          {(gridStatus.current_demand_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal text-text-secondary">GW</span>
                        </span>
                      </div>
                      <div className="flex justify-between items-baseline border-t border-border-hairline pt-3">
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider font-sans">Generation Capacity:</span>
                        <span className="text-base font-bold text-savings-green">
                          {(gridStatus.current_generation_mwh / 1000).toFixed(1)} <span className="text-[10px] font-sans font-normal">GW</span>
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary py-10 justify-center">
                      <ZapOff size={14}/> Connecting to Grid Authority...
                    </div>
                  )}
                </div>
              </div>

              <div className="panel-operational bg-bg-secondary flex flex-col justify-between min-h-[200px]">
                <div>
                  <h4 className="text-xs font-bold text-text-primary mb-4 border-b border-border-hairline pb-2 font-sans">Current Fuel Mix Generation</h4>
                  {gridStatus?.fuel_mix ? (
                    <div className="space-y-2">
                      {gridStatus.fuel_mix.slice(0, 4).map((f: any) => (
                        <div key={f.fuel_type} className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-text-secondary font-sans">{f.fuel_type_name}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-bg-surface rounded-full overflow-hidden border border-border-hairline">
                              <div className="h-full bg-primary-blue rounded-full" style={{ width: `${f.percentage}%` }}></div>
                            </div>
                            <span className="font-bold text-[10px] w-6 text-right">{f.percentage.toFixed(0)}%</span>
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

              <div className="panel-operational bg-bg-secondary flex flex-col justify-between min-h-[200px]">
                <div>
                  <h4 className="text-xs font-bold text-text-primary mb-4 border-b border-border-hairline pb-2 font-sans">Weather Context & Reliability</h4>
                  <div className="space-y-3 font-sans text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-text-secondary">Monthly CDD:</span>
                      <span className="font-bold text-text-primary font-mono-numbers">142 Days</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-text-secondary">Grid System Outages:</span>
                      <span className="font-bold text-savings-green font-mono-numbers flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-savings-green rounded-full"></span> Zero Active
                      </span>
                    </div>
                    <div className="flex justify-between items-center border-t border-border-hairline pt-3">
                      <span className="text-text-secondary font-semibold">SAIDI Reliability:</span>
                      <span className="font-bold text-text-primary font-mono-numbers">84.2 mins/yr</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* PJM LMP Nodal Congestion Analytics Map Section */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-8 font-sans">
              
              {/* Map Panel (7 cols) */}
              <div className="lg:col-span-7 panel-operational bg-bg-secondary space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-border-hairline pb-3 gap-2">
                  <div>
                    <h4 className="text-xs font-bold text-text-primary uppercase tracking-widest flex items-center gap-1.5 font-sans">
                      <Globe size={14} className="text-primary-blue animate-pulse" /> Wholesale PJM LMP Nodal Pricing Map
                    </h4>
                    <p className="text-[10px] text-text-secondary leading-normal mt-0.5">Geographical visualization of LMP nodes in NJ territory. Circle color indicates congestion magnitude.</p>
                  </div>
                  
                  {/* Timeline animation control */}
                  <div className="flex items-center gap-2 bg-bg-surface px-2.5 py-1 rounded border border-border-hairline text-[10px] font-mono-numbers text-text-primary">
                    <button
                      onClick={() => setIsPlayingLmp(!isPlayingLmp)}
                      className={`p-1 rounded-full transition-all cursor-pointer ${isPlayingLmp ? 'bg-primary-blue text-white' : 'bg-bg-primary text-text-primary border border-border-hairline'}`}
                    >
                      {isPlayingLmp ? <Pause size={10} fill="currentColor" /> : <Play size={10} fill="currentColor" />}
                    </button>
                    <span className="font-semibold">Hour: {mapHour}:00</span>
                  </div>
                </div>

                {/* SVG Node Scatter Map */}
                <div className="relative w-full h-[320px] bg-slate-950 rounded-lg overflow-hidden border border-slate-900 flex items-center justify-center">
                  <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:16px_16px]"></div>
                  
                  {nodes.length > 0 ? (
                    <svg className="w-full h-full p-4" viewBox="0 0 500 300">
                      {/* Plot each node dynamically */}
                      {(() => {
                        const minLon = -75.6;
                        const maxLon = -73.8;
                        const minLat = 38.9;
                        const maxLat = 41.5;
                        
                        return nodes.map((node) => {
                          const x = ((node.longitude - minLon) / (maxLon - minLon)) * 440 + 30;
                          const y = 300 - (((node.latitude - minLat) / (maxLat - minLat)) * 240 + 30);
                          
                          // Simulate hourly pricing fluctuation based on clock
                          const hourOffset = Math.sin((mapHour + parseFloat(node.node_id)) * 0.25) * 5.0;
                          const currentLmp = Math.max(10.0, node.total_lmp + hourOffset);
                          const currentCongestion = Math.max(0.0, node.congestion_comp + hourOffset * 0.15);
                          
                          const fill = currentCongestion > 4.5 ? "#EF4444" : currentCongestion > 1.5 ? "#F59E0B" : "#10B981";
                          const isSelected = selectedNode?.node_id === node.node_id;
                          
                          return (
                            <g
                              key={node.node_id}
                              className="cursor-pointer transition-all"
                              onClick={() => setSelectedNode(node)}
                            >
                              {isSelected && (
                                <circle cx={x} cy={y} r={10} fill={fill} fillOpacity={0.2} className="animate-ping" />
                              )}
                              <circle
                                cx={x}
                                cy={y}
                                r={isSelected ? 7 : 5}
                                fill={fill}
                                stroke="#ffffff"
                                strokeWidth={isSelected ? 1.5 : 0.75}
                                className="transition-all hover:scale-150"
                              />
                              {isSelected && (
                                <g transform={`translate(${x > 250 ? x - 80 : x + 12}, ${y - 12})`}>
                                  <rect width="66" height="20" rx="3" fill="#0f172a" stroke="#334155" strokeWidth="1" />
                                  <text x="5" y="13" fill="#ffffff" fontSize="8" fontWeight="bold" fontFamily="monospace">
                                    ${currentLmp.toFixed(1)}/MWh
                                  </text>
                                </g>
                              )}
                            </g>
                          );
                        });
                      })()}
                    </svg>
                  ) : (
                    <div className="text-xs text-slate-500 font-sans flex items-center gap-1.5 animate-pulse">
                      <RefreshCw size={14} className="animate-spin" /> Loading wholesale node distribution...
                    </div>
                  )}

                  {/* Map Legend */}
                  <div className="absolute bottom-3 right-3 bg-slate-900/90 border border-slate-800 rounded p-2 text-[8px] font-sans space-y-1 text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      <span>Low Congestion (&lt;$1.5/MWh)</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                      <span>Medium Congestion ($1.5 - $4.5/MWh)</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                      <span>High Congestion (&gt;$4.5/MWh)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Node Details & Historical Trend Chart (5 cols) */}
              <div className="lg:col-span-5 panel-operational bg-bg-secondary flex flex-col justify-between min-h-[320px] space-y-4">
                {selectedNode ? (
                  <div className="flex-1 flex flex-col justify-between h-full space-y-4">
                    <div className="border-b border-border-hairline pb-2">
                      <span className="text-[9px] text-text-secondary uppercase font-bold tracking-widest font-sans">Node Inspector</span>
                      <h4 className="text-xs font-bold text-text-primary mt-0.5">{selectedNode.name}</h4>
                      <p className="text-[10px] text-text-secondary font-mono-numbers mt-0.5">
                        Zone: {selectedNode.zone} | ID: {selectedNode.node_id} | Coord: {selectedNode.latitude.toFixed(3)}°, {selectedNode.longitude.toFixed(3)}°
                      </p>
                    </div>

                    {/* LMP Component Splits */}
                    <div className="grid grid-cols-3 gap-2 font-mono-numbers text-center">
                      <div className="bg-bg-surface border border-border-hairline rounded p-2">
                        <span className="text-[8px] text-text-secondary uppercase font-semibold font-sans block mb-0.5">Energy</span>
                        <span className="text-xs font-bold text-primary-blue">${selectedNode.energy_comp.toFixed(2)}</span>
                      </div>
                      <div className="bg-bg-surface border border-border-hairline rounded p-2">
                        <span className="text-[8px] text-text-secondary uppercase font-semibold font-sans block mb-0.5">Congestion</span>
                        <span className={`text-xs font-bold ${selectedNode.congestion_comp > 3.0 ? "text-red-500" : "text-amber-500"}`}>
                          ${selectedNode.congestion_comp.toFixed(2)}
                        </span>
                      </div>
                      <div className="bg-bg-surface border border-border-hairline rounded p-2">
                        <span className="text-[8px] text-text-secondary uppercase font-semibold font-sans block mb-0.5">Loss</span>
                        <span className="text-xs font-bold text-text-primary">${selectedNode.loss_comp.toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Historical Area Chart */}
                    <div className="flex-1 min-h-[160px] relative">
                      {loadingHistory ? (
                        <div className="absolute inset-0 flex items-center justify-center text-xs text-text-secondary font-sans animate-pulse">
                          <RefreshCw size={12} className="animate-spin" /> Querying historical dispatch rates...
                        </div>
                      ) : nodeHistory.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={nodeHistory.slice(-24)} margin={{ left: -25, right: 5, top: 10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.3} />
                            <XAxis
                              dataKey="timestamp"
                              tickFormatter={(ts) => {
                                try {
                                  return new Date(ts).getHours() + ":00";
                                } catch (e) {
                                  return ts;
                                }
                              }}
                              tick={{ fontSize: 8, fill: 'var(--text-secondary)' }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fontSize: 8, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }}
                              tickFormatter={(val) => `$${val.toFixed(0)}`}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Tooltip
                              contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }}
                              itemStyle={{ fontSize: '10px', color: 'var(--text-primary)' }}
                              labelFormatter={(lbl) => "Timestamp: " + new Date(lbl).toLocaleString()}
                            />
                            <Area type="monotone" dataKey="total_lmp" name="Total LMP" stroke="var(--primary-blue)" fill="var(--primary-blue)" fillOpacity={0.06} strokeWidth={1.5} />
                            <Area type="monotone" dataKey="congestion_comp" name="Congestion" stroke="var(--warning-amber)" fill="var(--warning-amber)" fillOpacity={0.04} strokeWidth={1} />
                          </AreaChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center text-[10px] text-text-secondary italic">
                          No historical data seeded for this node.
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center text-xs text-text-secondary italic py-16 h-full font-sans">
                    Select a node on the pricing map to analyze historical hourly trends.
                  </div>
                )}
              </div>
            </div>

            {/* Distribution Grid Reliability Indices (SAIDI / SAIFI) */}
            <GridReliabilitySection state={selectedState} />

            {/* EIA-930 Regional Grid Interchange & Flow Balance */}
            <GridInterchangeSection ba="PJM" />
          </SectionWrapper>
        )}

        {/* TRENDS SUB-TAB */}
        {subTab === 'trends' && (
          <SectionWrapper title="Historical Timeline" description="EIA timeline database volatility records and YoY state-wide comparisons.">
            <div className="space-y-6">
              <div className="flex items-center justify-between bg-bg-secondary p-3 border border-border-hairline rounded-md">
                <span className="text-xs font-bold text-text-primary">EIA-861/861M Timelines</span>
                {geoData?.available_months && (
                  <div className="flex items-center gap-3 bg-bg-surface px-3 py-1.5 rounded-md border border-border-hairline text-[10px] font-semibold text-text-primary">
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className={`p-1 rounded-full transition-all ${isPlaying ? 'bg-primary-blue text-white' : 'bg-bg-primary text-text-primary border border-border-hairline'}`}
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
                <div className="panel-chart h-[340px] flex flex-col justify-between">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">{selectedState} Historical Cost Trend</h3>
                    <div className={`flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-[4px] border font-mono-numbers ${trendData?.total_growth_pct > 0 ? 'bg-alert-red/10 text-alert-red border-alert-red/20' : 'bg-savings-green/10 text-savings-green border-savings-green/20'}`}>
                      {trendData?.total_growth_pct > 0 ? '+' : ''}{trendData?.total_growth_pct}% YoY Growth
                    </div>
                  </div>

                  <div className="flex-1 min-h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trendData?.months ? trendData.months.map((m: any, i: number) => ({ label: m, val: trendData.values[i] })) : []} margin={{ left: -25, right: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                        <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontWeight: 600}} dy={10} minTickGap={30} />
                        <YAxis axisLine={false} tickLine={false} tick={{fill: 'var(--text-secondary)', fontSize: 9, fontFamily: 'IBM Plex Mono'}} domain={['auto', 'auto']} />
                        <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }} itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }} />
                        <Area type="monotone" dataKey="val" stroke="var(--primary-blue)" strokeWidth={2} fill="var(--primary-blue)" fillOpacity={0.08} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="panel-chart h-[340px] flex flex-col justify-between">
                  <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-6 flex items-center gap-2 border-b border-border-hairline pb-2 font-sans">
                    National Monthly Electricity Sales (EIA-861M)
                  </h4>
                  <div className="flex-1 min-h-[220px]">
                    {monthlyTrends ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={monthlyTrends.periods.map((p: string, idx: number) => ({
                          period: p,
                          sales: monthlyTrends.sales[idx] / 1e6,
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
          </SectionWrapper>
        )}

        {/* AI SUMMARY SUB-TAB — 10-SECTION EXECUTIVE INTELLIGENCE REPORT */}
        {subTab === 'ai' && (
          <SectionWrapper title="Executive Energy Intelligence Report" description="Deep, data-grounded market synthesis suitable for utility executives, regulators, and enterprise energy directors.">
            <div className="space-y-8">
              {/* Header Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 text-white p-5 rounded-2xl border border-slate-800 shadow-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0">
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-base font-bold text-white tracking-tight">Regional Intelligence Briefing ({selectedState} Territory)</h2>
                      <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-blue-500/20 text-blue-300 border border-blue-400/30">
                        Senior Analyst Persona
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5 font-medium">Derived from EIA-861M, PJM grid load telemetry, and weather degree day datasets</p>
                  </div>
                </div>

                <button
                  onClick={() => insightsMutation.mutate()}
                  disabled={insightsMutation.isPending || !psegHistory}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50 shadow-md shrink-0 active:scale-95"
                >
                  {insightsMutation.isPending ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  <span>{insightsResult ? 'Re-generate Report' : 'Generate Full Executive Report'}</span>
                </button>
              </div>

              {insightsResult ? (
                <div className="space-y-8">
                  {/* SECTION 1 — Executive Summary */}
                  <div className="workspace-glass rounded-2xl p-6 space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-border-hairline flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 1
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Executive Summary</h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {insightsResult.executive_summary?.overall_health || "Stable Territory"}
                        </span>
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                          {insightsResult.executive_summary?.confidence_level || "94.8% Confidence"}
                        </span>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-900 text-white rounded-xl space-y-2 border border-slate-800">
                      <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest block">Primary Finding</span>
                      <p className="text-sm font-semibold leading-relaxed text-slate-100">
                        {insightsResult.executive_summary?.primary_finding}
                      </p>
                    </div>

                    <p className="text-xs text-slate-700 font-medium leading-relaxed">
                      {insightsResult.executive_summary?.briefing}
                    </p>
                  </div>

                  {/* SECTION 2 — Regional Market Analysis */}
                  {insightsResult.market_analysis && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 2
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Regional Market Analysis</h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-bg-secondary border border-border-hairline space-y-1.5">
                          <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Prices & Trajectory</span>
                          <p className="text-xs font-semibold text-text-primary leading-relaxed">
                            {insightsResult.market_analysis.electricity_prices_summary}
                          </p>
                          <p className="text-[11px] text-text-secondary font-medium">
                            {insightsResult.market_analysis.historical_trajectory}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl bg-bg-secondary border border-border-hairline space-y-1.5">
                          <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Consumption & Seasonality</span>
                          <p className="text-xs font-semibold text-text-primary leading-relaxed">
                            {insightsResult.market_analysis.consumption_trends}
                          </p>
                          <p className="text-[11px] text-text-secondary font-medium">
                            {insightsResult.market_analysis.seasonality}
                          </p>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-primary-blue/10 border border-primary-blue/20 space-y-1">
                        <span className="text-[10px] font-bold text-primary-blue uppercase tracking-wider">Root Cause Attribution</span>
                        <p className="text-xs text-text-primary font-semibold leading-relaxed">
                          {insightsResult.market_analysis.root_causes}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* SECTION 3 — Drivers Behind the Trend */}
                  {insightsResult.market_drivers && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 3
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Drivers Behind the Trend</h3>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-primary-blue">
                            <Activity size={16} />
                            <span className="text-xs font-bold text-text-primary">Weather & Degree Days</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.weather_cdd_hdd}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-warning-amber">
                            <ZapOff size={16} />
                            <span className="text-xs font-bold text-text-primary">Fuel & Marginal Costs</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.fuel_costs}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-alert-red">
                            <Layers size={16} />
                            <span className="text-xs font-bold text-text-primary">Grid Congestion</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.grid_congestion}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-savings-green">
                            <Globe size={16} />
                            <span className="text-xs font-bold text-text-primary">Renewable Contribution</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.renewable_penetration}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-primary-blue">
                            <Building2 size={16} />
                            <span className="text-xs font-bold text-text-primary">Commercial Activity</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.industrial_commercial_activity}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl border border-border-hairline bg-bg-secondary space-y-1.5 shadow-xs">
                          <div className="flex items-center gap-2 text-purple-600">
                            <FileText size={16} />
                            <span className="text-xs font-bold text-text-primary">Tariff Adjustments</span>
                          </div>
                          <p className="text-xs text-text-secondary font-medium leading-relaxed">
                            {insightsResult.market_drivers.tariff_rate_adjustments}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SECTION 4 — Regional Risk Assessment Matrix */}
                  {insightsResult.risk_assessment?.risks && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center justify-between pb-3 border-b border-border-hairline">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                            Section 4
                          </span>
                          <h3 className="text-base font-bold text-text-primary">Regional Risk Assessment Matrix</h3>
                        </div>
                        <span className="text-[11px] text-text-secondary font-semibold">6 Risk Dimensions Evaluated</span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {insightsResult.risk_assessment.risks.map((r: any) => {
                          const badgeClass = r.severity === 'High'
                            ? 'bg-rose-50/10 text-rose-700 border-rose-200/20'
                            : r.severity === 'Medium'
                            ? 'bg-amber-50/10 text-amber-700 border-amber-200/20'
                            : 'bg-emerald-50/10 text-emerald-700 border-emerald-200/20';

                          return (
                            <div key={r.category} className="p-4 rounded-xl border border-border-hairline bg-bg-secondary flex flex-col justify-between space-y-2">
                              <div>
                                <div className="flex items-center justify-between gap-2 mb-1.5">
                                  <span className="text-xs font-bold text-text-primary">{r.category}</span>
                                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${badgeClass}`}>
                                    {r.severity} Risk
                                  </span>
                                </div>
                                <p className="text-xs text-text-secondary font-semibold leading-snug">{r.description}</p>
                              </div>
                              <div className="pt-2 border-t border-border-hairline text-[11px] text-text-secondary font-medium leading-relaxed">
                                <strong className="text-text-primary">Justification:</strong> {r.justification}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* SECTION 5 — Forecast Outlook */}
                  {insightsResult.forecast_outlook?.horizons && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center justify-between pb-3 border-b border-border-hairline">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                            Section 5
                          </span>
                          <h3 className="text-base font-bold text-text-primary">Multi-Horizon Forecast Outlook</h3>
                        </div>
                        <div className="text-[11px] text-text-secondary font-medium">
                          Primary Driver: <strong className="text-text-primary">{insightsResult.forecast_outlook.primary_forecast_driver}</strong>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {insightsResult.forecast_outlook.horizons.map((h: any) => (
                          <div key={h.horizon} className="p-4 rounded-xl bg-slate-900 text-white border border-slate-800 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-extrabold uppercase tracking-widest text-blue-400">{h.horizon}</span>
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                                {h.confidence}
                              </span>
                            </div>
                            <div>
                              <div className="text-sm font-bold text-white">{h.expected_trend}</div>
                              <div className="text-xs font-mono text-amber-300 font-semibold mt-0.5">
                                Change: {h.projected_change_pct > 0 ? `+${h.projected_change_pct}%` : `${h.projected_change_pct}%`}
                              </div>
                            </div>
                            <div className="space-y-1 pt-2 border-t border-slate-800 text-[11px] text-slate-300 font-medium leading-relaxed">
                              <div><strong className="text-slate-400">Assumptions:</strong> {h.key_assumptions}</div>
                              <div><strong className="text-slate-400">Uncertainties:</strong> {h.uncertainties}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* SECTION 6 — Geographic Intelligence */}
                  {insightsResult.geographic_intelligence && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 6
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Geographic Intelligence & Spatial Clusters</h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-bg-secondary border border-border-hairline space-y-2">
                          <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Regional Positioning</span>
                          <p className="text-xs font-semibold text-text-primary leading-relaxed">
                            {insightsResult.geographic_intelligence.regional_comparison}
                          </p>
                          <p className="text-[11px] text-text-secondary font-medium">
                            {insightsResult.geographic_intelligence.spatial_clusters}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl bg-bg-secondary border border-border-hairline space-y-2">
                          <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">High-Cost Hotspots & Territory Variations</span>
                          <div className="flex flex-wrap gap-1.5 my-1">
                            {insightsResult.geographic_intelligence.high_cost_hotspots?.map((hs: string) => (
                              <span key={hs} className="text-[10px] font-extrabold px-2 py-0.5 rounded bg-rose-50/10 text-rose-700 border border-rose-200/20">
                                {hs}
                              </span>
                            ))}
                          </div>
                          <p className="text-[11px] text-text-secondary font-medium">
                            {insightsResult.geographic_intelligence.utility_territory_variations}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SECTION 7 — Economic Impact */}
                  {insightsResult.economic_impact && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 7
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Economic Impact Analysis</h3>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="p-3.5 rounded-xl border border-border-hairline bg-bg-secondary space-y-1">
                          <div className="flex items-center gap-1.5 text-primary-blue font-bold text-xs">
                            <Users size={14} /> Residential
                          </div>
                          <p className="text-xs text-text-secondary leading-relaxed font-medium">
                            {insightsResult.economic_impact.residential}
                          </p>
                        </div>

                        <div className="p-3.5 rounded-xl border border-border-hairline bg-bg-secondary space-y-1">
                          <div className="flex items-center gap-1.5 text-primary-blue font-bold text-xs">
                            <Building size={14} /> Commercial
                          </div>
                          <p className="text-xs text-text-secondary leading-relaxed font-medium">
                            {insightsResult.economic_impact.commercial}
                          </p>
                        </div>

                        <div className="p-3.5 rounded-xl border border-border-hairline bg-bg-secondary space-y-1">
                          <div className="flex items-center gap-1.5 text-purple-600 font-bold text-xs">
                            <Building2 size={14} /> Industrial
                          </div>
                          <p className="text-xs text-text-secondary leading-relaxed font-medium">
                            {insightsResult.economic_impact.industrial}
                          </p>
                        </div>

                        <div className="p-3.5 rounded-xl border border-border-hairline bg-bg-secondary space-y-1">
                          <div className="flex items-center gap-1.5 text-savings-green font-bold text-xs">
                            <Award size={14} /> Utilities & Grid
                          </div>
                          <p className="text-xs text-text-secondary leading-relaxed font-medium">
                            {insightsResult.economic_impact.utilities}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SECTION 8 — Recommendations */}
                  {insightsResult.recommendations && (
                    <div className="workspace-glass rounded-2xl p-6 space-y-4">
                      <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                          Section 8
                        </span>
                        <h3 className="text-base font-bold text-text-primary">Actionable Stakeholder Recommendations</h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-primary-blue/10 border border-primary-blue/20 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-primary-blue uppercase tracking-wider block">For Consumers</span>
                          <p className="text-xs text-text-primary font-semibold leading-relaxed">
                            {insightsResult.recommendations.consumers}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl bg-savings-green/10 border border-savings-green/20 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-savings-green uppercase tracking-wider block">For Businesses</span>
                          <p className="text-xs text-text-primary font-semibold leading-relaxed">
                            {insightsResult.recommendations.businesses}
                          </p>
                        </div>

                        <div className="p-4 rounded-xl bg-purple-50/10 border border-purple-200/20 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-purple-400 uppercase tracking-wider block">For Utilities & Grid Planners</span>
                          <p className="text-xs text-text-primary font-semibold leading-relaxed">
                            {insightsResult.recommendations.utilities}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SECTIONS 9 & 10 — Confidence & Data Limitations */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Section 9: Confidence */}
                    {insightsResult.confidence_assessment && (
                      <div className="workspace-glass rounded-2xl p-6 space-y-4">
                        <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                          <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                            Section 9
                          </span>
                          <h3 className="text-base font-bold text-text-primary">Confidence Assessment</h3>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3 bg-bg-secondary rounded-xl border border-border-hairline">
                            <span className="text-[9px] uppercase font-bold text-text-secondary">Data Completeness</span>
                            <div className="text-lg font-mono font-bold text-text-primary">
                              {insightsResult.confidence_assessment.data_completeness_pct}%
                            </div>
                          </div>
                          <div className="p-3 bg-bg-secondary rounded-xl border border-border-hairline">
                            <span className="text-[9px] uppercase font-bold text-text-secondary">Model Confidence</span>
                            <div className="text-lg font-mono font-bold text-text-primary">
                              {insightsResult.confidence_assessment.model_confidence_pct}%
                            </div>
                          </div>
                        </div>

                        <p className="text-xs text-text-secondary font-medium leading-relaxed">
                          {insightsResult.confidence_assessment.rationale}
                        </p>
                      </div>
                    )}

                    {/* Section 10: Data Limitations */}
                    {insightsResult.data_limitations && (
                      <div className="workspace-glass rounded-2xl p-6 space-y-4">
                        <div className="flex items-center gap-2 pb-3 border-b border-border-hairline">
                          <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-bg-secondary text-text-secondary border border-border-hairline">
                            Section 10
                          </span>
                          <h3 className="text-base font-bold text-text-primary">Data Limitations & Transparency</h3>
                        </div>

                        <div className="space-y-2 text-xs font-medium text-text-secondary">
                          <div>
                            <strong className="text-text-primary">Unobserved Variables:</strong>
                            <ul className="list-disc pl-4 mt-0.5 text-text-secondary">
                              {insightsResult.data_limitations.unobserved_variables?.map((u: string) => (
                                <li key={u}>{u}</li>
                              ))}
                            </ul>
                          </div>

                          <div>
                            <strong className="text-text-primary">Modeling Assumptions:</strong>
                            <ul className="list-disc pl-4 mt-0.5 text-text-secondary">
                              {insightsResult.data_limitations.forecast_assumptions?.map((fa: string) => (
                                <li key={fa}>{fa}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 workspace-glass rounded-2xl space-y-3">
                  <FileText className="mx-auto text-primary-blue/60" size={32} />
                  <h3 className="text-sm font-bold text-text-primary">10-Section Executive Intelligence Suite Ready</h3>
                  <p className="text-xs text-text-secondary max-w-md mx-auto leading-relaxed">
                    Query the regional regression engine and EIA dataset telemetry to build a senior executive intelligence report for {selectedState} territory.
                  </p>
                  <button
                    onClick={() => insightsMutation.mutate()}
                    className="mt-2 inline-flex items-center gap-2 bg-primary-blue hover:opacity-90 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition-all shadow-md active:scale-95 cursor-pointer"
                  >
                    <Sparkles size={14} />
                    <span>Generate AI Regional Report</span>
                  </button>
                </div>
              )}
            </div>
          </SectionWrapper>
        )}

      </div>

      {/* Navigation back deep-link */}
      <div className="flex justify-center mt-6">
        <button
          onClick={() => navigate('Overview')}
          className="text-xs text-text-secondary hover:text-primary-blue transition-colors font-semibold"
        >
          ← Back to Overview
        </button>
      </div>

    </div>
  );
};

export default RegionalPage;
