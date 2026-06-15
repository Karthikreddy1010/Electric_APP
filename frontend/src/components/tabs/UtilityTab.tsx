import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Search, MapPin, Zap, Users, Sun, Settings, TrendingUp, ShieldCheck } from 'lucide-react';

const UtilityTab = () => {
  const [selectedState, setSelectedState] = useState<string>('NJ');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedUtilityId, setSelectedUtilityId] = useState<number | null>(null);

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
      // Find PSE&G or similar in NJ as default, else first
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
      // Convert avg_price $/MWh to cents/kWh for readability
      avg_price_cents: h.avg_price ? h.avg_price / 10 : 0
    }));
  }, [utilityDetail]);

  return (
    <div className="space-y-6">
      {/* ── Filter / Search Bar ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 card p-6">
        <div>
          <label className="block text-xs font-black uppercase text-slate-400 mb-2">Select State</label>
          <select
            value={selectedState}
            onChange={(e) => {
              setSelectedState(e.target.value);
              setSearchTerm('');
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500"
          >
            {statesData?.map(st => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-xs font-black uppercase text-slate-400 mb-2">Search Utility</label>
          <div className="relative">
            <Search className="absolute left-3 top-3.5 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search by utility name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-3 text-sm font-medium text-slate-800 outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* ── Utilities Selection List ────────────────────────────────────── */}
        <div className="lg:col-span-1 card p-4 flex flex-col max-h-[600px]">
          <h4 className="text-xs font-black uppercase text-slate-400 px-2 mb-3">Utilities Found ({filteredUtilities.length})</h4>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {isUtilsLoading ? (
              <div className="text-xs text-slate-400 p-4">Loading utilities...</div>
            ) : filteredUtilities.length === 0 ? (
              <div className="text-xs text-slate-400 p-4">No utilities match your search.</div>
            ) : (
              filteredUtilities.map(u => (
                <button
                  key={u.utility_id}
                  onClick={() => setSelectedUtilityId(u.utility_id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-bold transition-all block truncate ${
                    selectedUtilityId === u.utility_id
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {u.utility_name}
                </button>
              ))
            )}
          </div>
        </div>

        {/* ── Utility Details Dashboard ──────────────────────────────────── */}
        <div className="lg:col-span-3 space-y-6">
          {isDetailLoading || !latestData ? (
            <div className="card p-12 text-center text-slate-400">
              <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
              Loading utility performance analytics...
            </div>
          ) : (
            <>
              {/* Header Card */}
              <div className="card p-6 bg-gradient-to-r from-slate-900 to-indigo-950 text-white flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-black uppercase text-blue-400 mb-1">
                    <MapPin size={12} /> {utilityDetail.state} Utility profile
                  </div>
                  <h3 className="text-2xl font-black">{utilityDetail.utility_name}</h3>
                  <p className="text-xs text-slate-400 mt-1">Utility ID: {utilityDetail.utility_id} • Year Tracked: {historyData[0]?.year} - {latestData.year}</p>
                </div>

                {/* Program Flags */}
                <div className="flex flex-wrap gap-2">
                  <div className={`px-3 py-1.5 rounded-full text-xs font-black flex items-center gap-1 ${
                    latestData.demand_response_flag 
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    <ShieldCheck size={14} /> Demand Response: {latestData.demand_response_flag ? 'Yes' : 'No'}
                  </div>
                  <div className={`px-3 py-1.5 rounded-full text-xs font-black flex items-center gap-1 ${
                    latestData.dynamic_pricing_flag 
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    <Settings size={14} /> Dynamic Pricing: {latestData.dynamic_pricing_flag ? 'Yes' : 'No'}
                  </div>
                </div>
              </div>

              {/* KPI Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="card p-4">
                  <p className="text-xs text-slate-400 font-bold mb-1">Residential Rate ({latestData.year})</p>
                  <h4 className="text-2xl font-black text-slate-900">
                    {latestData.avg_price ? `${(latestData.avg_price / 10).toFixed(2)}¢` : 'N/A'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1">cents/kWh average</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-slate-400 font-bold mb-1">Customers Served</p>
                  <h4 className="text-2xl font-black text-slate-900">
                    {latestData.total_customers ? latestData.total_customers.toLocaleString() : 'N/A'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1">active accounts</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-slate-400 font-bold mb-1">Summer Peak Demand</p>
                  <h4 className="text-2xl font-black text-slate-900">
                    {latestData.peak_demand ? `${latestData.peak_demand.toLocaleString()} MW` : 'N/A'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1">grid peak requirement</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-slate-400 font-bold mb-1">Net Metering Accounts</p>
                  <h4 className="text-2xl font-black text-blue-600">
                    {latestData.nm_customers ? latestData.nm_customers.toLocaleString() : '0'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1">distributed energy users</p>
                </div>
              </div>

              {/* Graphs Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. Price trend */}
                <div className="card p-6">
                  <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
                    <TrendingUp size={16} className="text-blue-600" /> Historical Price Trend (cents/kWh)
                  </h4>
                  <div className="h-[260px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}¢/kWh`, 'Price']} />
                        <Line type="monotone" dataKey="avg_price_cents" stroke="#2563EB" strokeWidth={3} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 2. Customer vs Load */}
                <div className="card p-6">
                  <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
                    <Zap size={16} className="text-amber-500" /> Customers vs Energy Sold (MWh)
                  </h4>
                  <div className="h-[260px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={historyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '10px' }} />
                        <Bar dataKey="total_customers" name="Customers" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="total_sales_mwh" name="Sales (MWh)" fill="#10B981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 3. Peak Demand vs Load */}
                <div className="card p-6">
                  <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
                    <Users size={16} className="text-indigo-600" /> Peak Summer Demand vs Total Load (MWh)
                  </h4>
                  <div className="h-[260px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '10px' }} />
                        <Line yAxisId="left" type="monotone" dataKey="peak_demand" name="Peak Demand (MW)" stroke="#EF4444" strokeWidth={2} />
                        <Line yAxisId="right" type="monotone" dataKey="total_load" name="Total Load (MWh)" stroke="#6366F1" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 4. Solar Net Metering Adoption */}
                <div className="card p-6">
                  <h4 className="text-sm font-black text-slate-900 mb-4 flex items-center gap-2">
                    <Sun size={16} className="text-emerald-500" /> Solar Net Metering Energy (MWh)
                  </h4>
                  <div className="h-[260px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip formatter={(v) => [`${Number(v).toLocaleString()} MWh`, 'Energy Sold Back']} />
                        <Line type="monotone" dataKey="nm_energy_mwh" name="Energy Sold Back (MWh)" stroke="#10B981" strokeWidth={2} activeDot={{ r: 8 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default UtilityTab;
