import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Search, MapPin, Users, Sun, Settings, TrendingUp, ShieldCheck, Activity } from 'lucide-react';

const UtilityTab = () => {
  const [selectedState, setSelectedState] = useState<string>('NJ');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedUtilityId, setSelectedUtilityId] = useState<number | null>(null);
  const [granularity, setGranularity] = useState<'annual' | 'monthly'>('annual');

  // Fetch EIA-861M Monthly State Trends
  const { data: stateMonthlyData, isLoading: isMonthlyLoading } = useQuery({
    queryKey: ['eia861m_state_monthly', selectedState],
    queryFn: async () => {
      const res = await axios.get(`/eia861m/state/${selectedState}`);
      return res.data;
    },
    enabled: granularity === 'monthly'
  });

  // 1. Fetch available states
  const { data: statesData } = useQuery({
    queryKey: ['eia861_states'],
    queryFn: async () => {
      const res = await axios.get('/eia861/states');
      return res.data.states as string[];
    }
  });

  // 2. Fetch utilities in the selected state
  const { data: utilitiesData, isLoading: isUtilsLoading } = useQuery({
    queryKey: ['eia861_utilities', selectedState],
    queryFn: async () => {
      const res = await axios.get(`/eia861/utilities?state=${selectedState}`);
      return res.data.utilities as any[];
    }
  });

  // Filter utilities based on search term
  const filteredUtilities = useMemo(() => {
    if (!utilitiesData) return [];
    return utilitiesData.filter(u =>
      u.utility_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [utilitiesData, searchTerm]);

  // Handle setting default utility when state or list changes
  useMemo(() => {
    if (filteredUtilities.length > 0) {
      const njDefault = filteredUtilities.find(u => u.utility_name.includes('Public Service') || u.utility_name.includes('PSE&G'));
      setSelectedUtilityId(njDefault ? njDefault.utility_id : filteredUtilities[0].utility_id);
    } else {
      setSelectedUtilityId(null);
    }
  }, [filteredUtilities]);

  // 3. Fetch utility historical details
  const { data: utilityDetail, isLoading: isDetailLoading } = useQuery({
    queryKey: ['eia861_utility', selectedUtilityId, selectedState],
    queryFn: async () => {
      if (!selectedUtilityId) return null;
      const res = await axios.get(`/eia861/utility/${selectedUtilityId}?state=${selectedState}`);
      return res.data;
    },
    enabled: !!selectedUtilityId
  });

  // Derived metrics for latest year
  const latestData = useMemo(() => {
    if (!utilityDetail || !utilityDetail.history || utilityDetail.history.length === 0) return null;
    return utilityDetail.history[utilityDetail.history.length - 1];
  }, [utilityDetail]);

  const historyData = useMemo(() => {
    if (!utilityDetail || !utilityDetail.history) return [];
    return utilityDetail.history.map((h: any) => ({
      ...h,
      avg_price_cents: h.avg_price ? h.avg_price / 10 : 0
    }));
  }, [utilityDetail]);

  return (
    <div className="space-y-6 font-sans">
      
      {/* Title block */}
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          Utility telemetry
        </span>
        <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Utility intelligence</h2>
        <p className="text-xs text-text-secondary mt-1">EIA-861 profile tracking and dynamic rate classifications.</p>
      </div>

      {/* Filter / Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 panel-operational">
        <div>
          <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5">Select state</label>
          <select
            value={selectedState}
            onChange={(e) => {
              setSelectedState(e.target.value);
              setSearchTerm('');
            }}
            className="w-full bg-bg-primary border border-border-hairline rounded-md px-3 py-2 text-xs font-bold text-text-primary outline-none focus:border-primary-blue"
            aria-label="Select state"
          >
            {statesData?.map(st => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-[10px] font-bold uppercase text-text-secondary tracking-widest mb-1.5">Search utility</label>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 text-text-secondary" size={14} />
            <input
              type="text"
              placeholder="Search by utility name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-bg-primary border border-border-hairline rounded-md pl-9 pr-4 py-2 text-xs font-medium text-text-primary outline-none focus:border-primary-blue"
              aria-label="Search utility"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Utilities Selection List */}
        <div className="lg:col-span-1 panel-operational p-4 flex flex-col max-h-[600px]">
          <h4 className="text-[10px] font-bold uppercase text-text-secondary px-1 mb-3">Utilities found ({filteredUtilities.length})</h4>
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
                  className={`w-full text-left px-3 py-2 rounded-md transition-all block truncate ${
                    selectedUtilityId === u.utility_id
                      ? 'bg-primary-blue text-white shadow-sm font-bold'
                      : 'text-text-primary hover:bg-bg-primary/50'
                  }`}
                >
                  {u.utility_name}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Utility Details Dashboard */}
        <div className="lg:col-span-3 space-y-6">
          {isDetailLoading || !latestData ? (
            <div className="panel-operational p-12 text-center text-text-secondary">
              <RefreshCw size={24} className="animate-spin text-primary-blue mx-auto mb-4" />
              Loading utility performance analytics...
            </div>
          ) : (
            <>
              {/* Header Card */}
              <div className="panel-operational bg-bg-surface border border-border-hairline shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[9px] font-bold uppercase bg-primary-blue/10 text-primary-blue px-2 py-0.5 rounded-[4px] border border-primary-blue/20">
                      {selectedState} utility network
                    </span>
                    <div className="flex bg-bg-primary p-0.5 rounded-md border border-border-hairline text-[8px] font-bold uppercase">
                      <button
                        onClick={() => setGranularity('annual')}
                        className={`px-2 py-0.5 rounded-sm transition-all ${granularity === 'annual' ? 'bg-bg-surface text-primary-blue shadow-sm border border-border-hairline' : 'text-text-secondary'}`}
                      >
                        Annual
                      </button>
                      <button
                        onClick={() => setGranularity('monthly')}
                        className={`px-2 py-0.5 rounded-sm transition-all ${granularity === 'monthly' ? 'bg-bg-surface text-primary-blue shadow-sm border border-border-hairline' : 'text-text-secondary'}`}
                      >
                        Monthly (EIA-861M)
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-primary-blue mb-1">
                    <MapPin size={12} /> {utilityDetail.state} utility profile
                  </div>
                  <h3 className="text-xl font-bold text-text-primary">{utilityDetail.utility_name}</h3>
                  <p className="text-[10px] text-text-secondary mt-1 font-mono-numbers">Utility ID: {utilityDetail.utility_id} • Year: {historyData[0]?.year} - {latestData.year}</p>
                </div>

                {/* Program Flags */}
                <div className="flex flex-wrap gap-2 text-[10px] font-bold">
                  <div className={`px-2.5 py-1 rounded-[4px] flex items-center gap-1 ${
                    latestData.demand_response_flag 
                      ? 'bg-savings-green/10 text-savings-green border border-savings-green/20' 
                      : 'bg-bg-primary text-text-secondary border border-border-hairline'
                  }`}>
                    <ShieldCheck size={12} /> Demand response: {latestData.demand_response_flag ? 'Yes' : 'No'}
                  </div>
                  <div className={`px-2.5 py-1 rounded-[4px] flex items-center gap-1 ${
                    latestData.dynamic_pricing_flag 
                      ? 'bg-savings-green/10 text-savings-green border border-savings-green/20' 
                      : 'bg-bg-primary text-text-secondary border border-border-hairline'
                  }`}>
                    <Settings size={12} /> Dynamic pricing: {latestData.dynamic_pricing_flag ? 'Yes' : 'No'}
                  </div>
                </div>
              </div>

              {/* KPI Grid */}
              {granularity === 'monthly' ? (
                // ── MONTHLY GRANULARITY VIEWS (EIA-861M) ──
                isMonthlyLoading || !stateMonthlyData ? (
                  <div className="panel-operational p-12 text-center text-text-secondary">
                    <RefreshCw size={24} className="animate-spin text-primary-blue mx-auto mb-4" />
                    Loading monthly state trends...
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    {/* Monthly Sales Trend */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <TrendingUp size={14} className="text-primary-blue" /> State monthly sales (MWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({
                            period: p,
                            sales: stateMonthlyData.sales[idx],
                          })).slice(-24)} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} MWh`, 'Sales']} />
                            <Line type="monotone" dataKey="sales" stroke="var(--primary-blue)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Monthly Price Trend */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <TrendingUp size={14} className="text-energy-teal" /> State average retail price (¢/kWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({
                            period: p,
                            price: stateMonthlyData.prices[idx],
                          })).slice(-24)} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}¢/kWh`, 'Price']} />
                            <Line type="monotone" dataKey="price" stroke="var(--energy-teal)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Monthly Customer Count Trend */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <Users size={14} className="text-electric-cyan" /> Total active customers (state count)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({
                            period: p,
                            customers: stateMonthlyData.customers[idx],
                          })).slice(-24)} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip formatter={(v) => [Number(v).toLocaleString(), 'Customers']} />
                            <Line type="monotone" dataKey="customers" stroke="var(--electric-cyan)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Monthly Revenue Trend */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <Activity size={14} className="text-warning-amber" /> Total utility revenue ($K)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={stateMonthlyData.periods.map((p: string, idx: number) => ({
                            period: p,
                            revenue: stateMonthlyData.revenue[idx],
                          })).slice(-24)} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="period" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip formatter={(v) => [`$${Number(v).toLocaleString()}K`, 'Revenue']} />
                            <Line type="monotone" dataKey="revenue" stroke="var(--warning-amber)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                )
              ) : (
                // ── ANNUAL GRANULARITY VIEWS (EIA-861 Original Dashboard) ──
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono-numbers text-text-primary text-xs">
                    <div className="panel-operational">
                      <p className="text-[10px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Residential rate ({latestData.year})</p>
                      <h4 className="text-xl font-bold">
                        {latestData.avg_price ? `${(latestData.avg_price / 10).toFixed(2)}¢` : 'N/A'}
                      </h4>
                      <p className="text-[9px] text-text-secondary mt-1 font-sans">cents/kWh average</p>
                    </div>
                    <div className="panel-operational">
                      <p className="text-[10px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Customers served</p>
                      <h4 className="text-xl font-bold">
                        {latestData.total_customers ? latestData.total_customers.toLocaleString() : 'N/A'}
                      </h4>
                      <p className="text-[9px] text-text-secondary mt-1 font-sans">active accounts</p>
                    </div>
                    <div className="panel-operational">
                      <p className="text-[10px] text-text-secondary font-bold font-sans mb-1 uppercase tracking-wider">Summer peak demand</p>
                      <h4 className="text-xl font-bold">
                        {latestData.peak_demand ? `${latestData.peak_demand.toLocaleString()} MW` : 'N/A'}
                      </h4>
                      <p className="text-[9px] text-text-secondary mt-1 font-sans">grid peak requirement</p>
                    </div>
                    <div className="panel-operational bg-primary-blue/5 border-primary-blue/20">
                      <p className="text-[10px] text-primary-blue font-bold font-sans mb-1 uppercase tracking-wider">Net metering accounts</p>
                      <h4 className="text-xl font-bold text-primary-blue">
                        {latestData.nm_customers ? latestData.nm_customers.toLocaleString() : '0'}
                      </h4>
                      <p className="text-[9px] text-primary-blue/80 mt-1 font-sans font-semibold">distributed energy users</p>
                    </div>
                  </div>

                  {/* Graphs Section */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    {/* 1. Price trend */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <TrendingUp size={14} className="text-primary-blue" /> Historical price trend (cents/kWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={historyData} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}¢/kWh`, 'Price']} />
                            <Line type="monotone" dataKey="avg_price_cents" stroke="var(--primary-blue)" strokeWidth={2} dot={{ r: 3, fill: 'var(--primary-blue)', strokeWidth: 0 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* 2. Customer vs Load */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <Activity size={14} className="text-warning-amber" /> Customers vs energy sold (MWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={historyData} margin={{ left: -25, right: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip />
                            <Legend wrapperStyle={{ fontSize: '9px' }} />
                            <Bar dataKey="total_customers" name="Customers" fill="var(--primary-blue)" radius={[2, 2, 0, 0]} />
                            <Bar dataKey="total_sales_mwh" name="Sales (MWh)" fill="var(--energy-teal)" radius={[2, 2, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* 3. Peak Demand vs Load */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <Users size={14} className="text-electric-cyan" /> Peak summer demand vs total load (MWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={historyData} margin={{ left: -25, right: 30 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                            <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <YAxis yAxisId="left" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                            <Tooltip />
                            <Legend wrapperStyle={{ fontSize: '9px' }} />
                            <Line yAxisId="left" type="monotone" dataKey="peak_demand" name="Peak Demand (MW)" stroke="var(--alert-red)" strokeWidth={2} dot={false} />
                            <Line yAxisId="right" type="monotone" dataKey="total_load" name="Total Load (MWh)" stroke="var(--primary-blue)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* 4. Solar Net Metering Adoption */}
                    <div className="panel-chart h-[320px] flex flex-col justify-between">
                      <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-border-hairline pb-2">
                        <Sun size={14} className="text-savings-green" /> Solar net metering energy (MWh)
                      </h4>
                      <div className="flex-1 min-h-[220px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={historyData} margin={{ left: -25, right: 10 }}>
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
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// Internal custom helpers to avoid duplicates
const RefreshCw = ({ size, className }: { size?: number; className?: string }) => (
  <svg className={`animate-spin ${className}`} style={{ width: size, height: size }} fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

export default UtilityTab;
