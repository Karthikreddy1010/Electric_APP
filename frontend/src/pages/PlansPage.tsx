/**
 * Plans Page
 *
 * Architecture rule: Plans recommends.
 * This page owns: retail plan Monte Carlo comparison, BGS history,
 * and URDB tariff details.
 *
 * Changes from PlansTab:
 * - Fixed RefreshCw: imported from lucide-react (was re-declared as inline SVG)
 * - setActiveTab replaced with useNavigation()
 */
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, Cell
} from 'recharts';
import { ShieldCheck, Activity, ArrowRight, TrendingUp, RefreshCw } from 'lucide-react';
import { useBill } from '../context/BillContext.tsx';
import { useNavigation } from '../context/NavigationContext.tsx';
import EmptyBillState from '../components/shared/EmptyBillState.tsx';

const PlansPage = () => {
  const { uploadedBill } = useBill();
  const navigate = useNavigation();

  const { data, isLoading } = useQuery({
    queryKey: ['plans', uploadedBill?.usage_kwh],
    queryFn: async () => {
      const res = await axios.post('/plan-simulation', {
        monthly_usage_kwh: uploadedBill?.usage_kwh || 750,
        usage_growth_pct: 0.0,
        horizon_months: 12,
        n_simulations: 10000
      });
      return res.data;
    },
    enabled: !!uploadedBill
  });

  const { data: bgsData } = useQuery({
    queryKey: ['bgs-rates'],
    queryFn: async () => (await axios.get('/bgs/rates')).data
  });

  const { data: defaultTariff } = useQuery({
    queryKey: ['default-tariff'],
    queryFn: async () => (await axios.get('/tariffs/default?utility_id=15477')).data
  });

  if (!uploadedBill) {
    return (
      <EmptyBillState
        title="Retail plans locked"
        description="Upload and analyze an electricity bill to generate retail plan savings opportunities."
        ctaLabel="Go to Bill Analysis"
        ctaTab="Bill Analysis"
      />
    );
  }

  if (isLoading) return (
    <div className="panel-operational flex flex-col items-center justify-center p-20 space-y-4">
      <RefreshCw size={24} className="animate-spin text-primary-blue" />
      <p className="text-text-secondary font-semibold animate-pulse text-xs">Running Monte Carlo simulations...</p>
    </div>
  );

  if (!data || !data.comparison || data.comparison.length === 0) {
    return (
      <div className="panel-operational p-12 text-center border-dashed border border-border-hairline">
        <h3 className="text-sm font-bold text-text-primary mb-2">Analysis unavailable</h3>
        <p className="text-xs text-text-secondary">Could not retrieve plan comparison data. Ensure the backend is active.</p>
      </div>
    );
  }

  const bestPlan = data.comparison[0];
  const savings = data.savings_vs_default || 0;
  const currentCost = (bestPlan?.expected_annual_cost || 0) + savings;
  const savingsPct = currentCost > 0 ? (savings / currentCost * 100).toFixed(1) : '0.0';

  return (
    <div className="space-y-6 font-sans">

      {/* Title block */}
      <div className="flex justify-between items-end gap-4">
        <div>
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
            Tariff benchmarking
          </span>
          <h2 className="text-2xl font-bold text-text-primary tracking-tight mt-2">Retail plans</h2>
          <p className="text-xs text-text-secondary mt-1">Personalized simulation based on 12 months of historical consumption.</p>
        </div>
        <div className="hidden md:block bg-primary-blue/10 text-primary-blue border border-primary-blue/20 px-3 py-1 rounded-[6px] text-[10px] font-bold uppercase tracking-wider">
          Live analysis
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Annual Projections chart */}
        <div className="lg:col-span-2 panel-chart h-[440px] flex flex-col justify-between">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Annual cost projections</h3>
            <div className="flex items-center gap-1.5 text-[10px] text-text-secondary font-bold uppercase">
              <span className="w-2.5 h-2.5 rounded-full bg-primary-blue" />
              <span>Simulated mean</span>
            </div>
          </div>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.comparison} layout="vertical" margin={{ left: -10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis type="number" hide domain={[0, 'auto']} />
                <YAxis dataKey="provider" type="category" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-primary)', fontSize: 10, fontWeight: 'bold' }} width={110} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '6px' }} itemStyle={{ fontSize: '11px', color: 'var(--text-primary)' }} />
                <Bar dataKey="expected_annual_cost" radius={[0, 2, 2, 0]} barSize={24}>
                  {data.comparison.map((_: any, idx: number) => (
                    <Cell key={idx} fill={idx === 0 ? 'var(--primary-blue)' : '#E6EAF0'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sidebar: Best value + analysis */}
        <div className="space-y-6">
          <div className="panel-operational relative overflow-hidden bg-bg-surface border-primary-blue/30 shadow-md">
            <div className="relative z-10 space-y-4">
              <div className="flex items-center gap-2 border-b border-border-hairline pb-3 mb-2">
                <ShieldCheck className="text-primary-blue" size={18} />
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary-blue">Best value pick</span>
              </div>
              <h3 className="text-2xl font-bold tracking-tight text-text-primary">{bestPlan?.provider}</h3>
              <p className="text-[10px] font-bold text-text-secondary uppercase tracking-widest leading-none">{bestPlan?.plan_type}</p>
              <div className="space-y-4 pt-6 border-t border-border-hairline font-mono-numbers text-text-primary">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest font-sans">Est. Monthly</span>
                  <span className="text-2xl font-bold">${((bestPlan?.expected_annual_cost || 0) / 12).toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center text-savings-green">
                  <span className="text-[10px] font-bold uppercase tracking-widest font-sans">Yearly Savings</span>
                  <span className="text-base font-bold">+${savings.toFixed(2)}</span>
                </div>
                <button className="w-full bg-primary-blue text-white py-3 rounded-md font-semibold flex items-center justify-center gap-2 hover:bg-primary-blue/90 transition-all shadow-sm mt-4 text-xs font-sans">
                  Enroll today <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>

          <div className="panel-operational shadow-sm">
            <div className="flex items-center gap-2 mb-3 border-b border-border-hairline pb-2">
              <Activity className="text-warning-amber" size={16} />
              <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">Analysis result</h4>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed font-semibold">
              Switching from the standard default BGS tariff to <span className="text-text-primary font-bold">{bestPlan?.provider}</span> is projected to reduce your annual cost by <span className="text-savings-green font-bold">{savingsPct}%</span>.
            </p>
          </div>
        </div>
      </div>

      {/* Active Utility Tariff Details */}
      {defaultTariff && (
        <div className="panel-operational space-y-6 bg-bg-surface">
          <div>
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-2 border-b border-border-hairline pb-2.5">
              <Activity size={14} className="text-primary-blue" /> Active utility tariff parameters
            </h3>
            <p className="text-[10px] text-text-secondary mt-1">Real-time parameters from OpenEI Utility Rate Database (URDB)</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono-numbers text-text-primary">
            <div className="p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider font-sans">Utility & tariff name</span>
              <p className="text-sm font-bold text-text-primary mt-1 font-sans">PSE&G</p>
              <p className="text-[10px] text-text-secondary font-medium font-sans mt-0.5">{defaultTariff.name}</p>
            </div>
            <div className="p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider font-sans">Fixed monthly charge</span>
              <p className="text-xl font-bold text-text-primary mt-1">${defaultTariff.fixed_charge?.toFixed(2) || '0.00'}</p>
              <p className="text-[10px] text-text-secondary font-medium font-sans mt-0.5">{defaultTariff.fixed_charge_units || 'per month'}</p>
            </div>
            <div className="p-4 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider font-sans">Effective energy charge</span>
              <p className="text-xl font-bold text-text-primary mt-1">${defaultTariff.energy_rate?.toFixed(5)} <span className="text-xs font-normal font-sans">/kWh</span></p>
              <p className="text-[10px] text-text-secondary font-medium font-sans mt-0.5">Service Type: {defaultTariff.service_type || 'Bundled'}</p>
            </div>
          </div>
          <div className="p-4 bg-bg-primary rounded-md border border-border-hairline space-y-2 text-xs">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Rate structure & comments</span>
            <p className="text-[11px] text-text-secondary leading-relaxed font-semibold">{defaultTariff.energy_comments || 'No comments available.'}</p>
            <div className="flex gap-4 text-[10px] font-bold text-text-secondary pt-2 border-t border-border-hairline">
              <span>Start: {defaultTariff.start_date || 'N/A'}</span>
              <span>End: {defaultTariff.end_date || 'Present'}</span>
              <span className={defaultTariff.approved ? 'text-savings-green' : 'text-warning-amber'}>
                {defaultTariff.approved ? 'Approved' : 'Pending'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* BGS Auction Rates History */}
      {bgsData?.data && (
        <div className="panel-chart h-[420px] flex flex-col justify-between bg-bg-surface">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-2 border-b border-border-hairline pb-2">
                <TrendingUp size={14} className="text-primary-blue" /> NJ BGS auction RSCP rates history
              </h3>
              <p className="text-xs text-text-secondary mt-1">Historical Basic Generation Service default supply rates (cents/kWh)</p>
            </div>
            <div className="text-[9px] font-bold text-text-secondary uppercase tracking-wider font-mono-numbers">2002 – 2026 reference</div>
          </div>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={bgsData.data} margin={{ top: 10, right: 30, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-hairline)" opacity={0.5} />
                <XAxis dataKey="year" tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 9, fill: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono' }} tickFormatter={(v) => `${v}¢`} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any) => [`${Number(v).toFixed(3)}¢/kWh`]} />
                <Legend wrapperStyle={{ fontSize: '9px' }} />
                <Line type="monotone" dataKey="PSE&G" stroke="#2F6BFF" strokeWidth={2} activeDot={{ r: 6 }} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="JCP&L" stroke="#2CA6FF" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="ACE"   stroke="#16A085" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="RECO"  stroke="#D64545" strokeWidth={2} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Deep-link to Bill Analysis if needed */}
      <div className="flex justify-center">
        <button
          onClick={() => navigate('Bill Analysis')}
          className="text-xs text-text-secondary hover:text-primary-blue transition-colors font-semibold"
        >
          ← Back to Bill Analysis
        </button>
      </div>
    </div>
  );
};

export default PlansPage;
