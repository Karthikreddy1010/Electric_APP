import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { MapPin, TrendingDown, TrendingUp, Search } from 'lucide-react';

const GeoTab = () => {
  const [viewMode, setViewMode] = useState<'bill' | 'rate'>('bill');
  const [search, setSearch] = useState('');

  const { data: geoData, isLoading } = useQuery({
    queryKey: ['geo'],
    queryFn: async () => {
      const res = await axios.get('http://localhost:8000/geo');
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500">Loading map data...</div>;

  const filteredData = geoData.data.filter((s: any) => s.state.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Map Side (Placeholder for actual interactive map, or a stylized list) */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex bg-white p-1 rounded-lg border border-border shadow-sm">
            <button 
              onClick={() => setViewMode('bill')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'bill' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              Bill View
            </button>
            <button 
              onClick={() => setViewMode('rate')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'rate' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              Rate View
            </button>
          </div>
          
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search states..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none transition-all"
            />
          </div>
        </div>

        <div className="card h-[600px] overflow-auto">
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-white border-b border-border">
              <tr>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Rank</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">State</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Avg Bill</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Avg Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredData.sort((a: any, b: any) => a.rank - b.rank).map((state: any) => (
                <tr key={state.state} className={`hover:bg-slate-50 transition-colors ${state.state === 'NJ' ? 'bg-blue-50/50' : ''}`}>
                  <td className="px-6 py-4 text-sm font-medium text-slate-500">{state.rank}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <MapPin className={`w-4 h-4 ${state.state === 'NJ' ? 'text-primary' : 'text-slate-300'}`} />
                      <span className="font-semibold text-slate-900">{state.state}</span>
                      {state.state === 'NJ' && <span className="text-[10px] bg-primary text-white px-1.5 py-0.5 rounded uppercase font-bold">Your State</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono font-bold text-slate-900">
                    ${state.avg_bill.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-slate-500">
                    ${state.avg_rate.toFixed(4)}/kWh
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rankings Side */}
      <div className="space-y-6">
        <div className="card border-l-4 border-l-negative">
          <div className="flex items-center gap-2 mb-4 text-negative">
            <TrendingUp className="w-5 h-5" />
            <h4 className="font-bold uppercase text-xs tracking-widest">Most Expensive</h4>
          </div>
          <div className="space-y-4">
            {geoData.top_5_expensive.map((state: any, i: number) => (
              <div key={state.state} className="flex justify-between items-center">
                <span className="text-sm font-medium text-slate-600">{i + 1}. {state.state}</span>
                <span className="font-bold text-slate-900">${state.avg_bill.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card border-l-4 border-l-positive">
          <div className="flex items-center gap-2 mb-4 text-positive">
            <TrendingDown className="w-5 h-5" />
            <h4 className="font-bold uppercase text-xs tracking-widest">Most Affordable</h4>
          </div>
          <div className="space-y-4">
            {geoData.top_5_cheapest.map((state: any, i: number) => (
              <div key={state.state} className="flex justify-between items-center">
                <span className="text-sm font-medium text-slate-600">{i + 1}. {state.state}</span>
                <span className="font-bold text-slate-900">${state.avg_bill.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeoTab;
