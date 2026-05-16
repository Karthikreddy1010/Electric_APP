import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import USMap from '../USMap.tsx';

const BenchmarkTab = () => {
  const [selectedYear, setSelectedYear] = useState('2025');

  const { data, isLoading } = useQuery({
    queryKey: ['benchmark', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`http://localhost:8000/benchmark?year=${selectedYear}`);
      return res.data;
    }
  });

  if (isLoading) return <div className="text-slate-500 p-8">Loading benchmark data...</div>;

  const nj = data.focus_state;
  const mapData = data.states.map((s: any) => ({
    state: s.state,
    value: s.avg_rate * 100 // convert to cents for display clarity
  }));

  return (
    <div className="space-y-8">
      {/* Header & Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div>
          <h3 className="text-2xl font-bold text-slate-900 mb-2">National Rate Comparison</h3>
          <p className="text-slate-500 leading-relaxed">
            NJ ranks among the higher cost states for electricity. 
            Your current rate of <b>${nj.avg_rate.toFixed(4)}/kWh</b> is 
            <span className={nj.avg_rate > data.national_avg ? 'text-negative font-bold' : 'text-positive font-bold'}>
              {' '}{Math.abs((nj.avg_rate - data.national_avg) / data.national_avg * 100).toFixed(1)}% {nj.avg_rate > data.national_avg ? 'above' : 'below'}
            </span> the national average of ${data.national_avg.toFixed(4)}/kWh.
          </p>
        </div>
        <div className="card bg-slate-50 border-none flex justify-around py-8 text-center">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">NJ Avg Bill</span>
            <p className="text-3xl font-bold text-slate-900 mt-1">${nj.avg_bill.toFixed(2)}</p>
          </div>
          <div className="w-px bg-slate-200"></div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">National Avg Bill</span>
            <p className="text-3xl font-bold text-slate-400 mt-1">$138.20</p>
          </div>
        </div>
      </div>

      {/* Map Section */}
      <div className="card space-y-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Year</label>
            <select 
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-slate-100 border-none rounded-lg px-4 py-2 text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="2025">2025</option>
              <option value="2024">2024</option>
              <option value="2023">2023</option>
            </select>
            <button className="bg-primary text-white px-6 py-2 rounded-lg text-sm font-bold shadow-lg shadow-primary/20 hover:brightness-110 transition-all">
              Compare
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">¢/kWh</span>
            <div className="h-2 w-32 bg-gradient-to-r from-[#BBF7D0] to-[#166534] rounded-full"></div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">High</span>
          </div>
        </div>

        <div className="h-[500px] flex items-center justify-center bg-slate-50/30 rounded-xl relative">
          <USMap 
            data={mapData} 
            colorRange={["#BBF7D0", "#166534"]} 
            selectedState="NJ"
          />
          
          <div className="absolute right-8 bottom-8 card p-4 bg-white/80 backdrop-blur-sm border-none shadow-xl">
             <div className="flex flex-col gap-2 text-xs">
                <div className="flex items-center gap-2">
                   <div className="w-3 h-3 rounded-full bg-[#166534]"></div>
                   <span className="text-slate-600 font-medium">35+ ¢/kWh</span>
                </div>
                <div className="flex items-center gap-2">
                   <div className="w-3 h-3 rounded-full bg-[#4ADE80]"></div>
                   <span className="text-slate-600 font-medium">20-30 ¢/kWh</span>
                </div>
                <div className="flex items-center gap-2">
                   <div className="w-3 h-3 rounded-full bg-[#BBF7D0]"></div>
                   <span className="text-slate-600 font-medium">&lt; 15 ¢/kWh</span>
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BenchmarkTab;
