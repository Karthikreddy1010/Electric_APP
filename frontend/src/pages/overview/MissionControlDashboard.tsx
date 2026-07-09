/**
 * Mission Control Dashboard — returning user view of the Overview page.
 *
 * Architecture rule: Overview summarizes. No charts. No detailed analysis.
 * All items are summary cards that deep-link to the responsible page.
 */
import { useBill } from '../../context/BillContext.tsx';
import { useNavigation } from '../../context/NavigationContext.tsx';
import { useUserDashboard } from '../../hooks/useUserDashboard.ts';
import RecentBillsCard from '../../components/shared/RecentBillsCard.tsx';
import EnergyNetworkSVG from './EnergyNetworkSVG.tsx';
import { TrendingUp, TrendingDown, ArrowUpRight, ShieldAlert, Lightbulb } from 'lucide-react';

// ─── KPI Card ─────────────────────────────────────────────────────────────────
interface KpiCardProps {
  id: string;
  label: string;
  value: string;
  unit?: string;
  changePct?: number;
  changeLabel?: string;
  subtext?: string;
  accentColor?: string;
  targetTab?: string;
}

const KpiCard = ({ id, label, value, unit, changePct, changeLabel, subtext, accentColor = '#2F6BFF', targetTab }: KpiCardProps) => {
  const navigate = useNavigation();
  const isPositive = changePct !== undefined && changePct >= 0;
  const changeColor = changePct === undefined ? '' : isPositive ? 'text-alert-red' : 'text-savings-green';

  return (
    <button
      id={id}
      onClick={() => targetTab && navigate(targetTab)}
      className={`panel-operational text-left space-y-2 group transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${targetTab ? 'cursor-pointer' : 'cursor-default'}`}
      style={{ borderTop: `3px solid ${accentColor}` }}
      aria-label={`${label}: ${value}${unit || ''}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-bold uppercase tracking-widest text-text-secondary">{label}</span>
        {targetTab && (
          <ArrowUpRight
            size={12}
            className="text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity"
          />
        )}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold font-mono-numbers text-text-primary">{value}</span>
        {unit && <span className="text-xs text-text-secondary font-medium">{unit}</span>}
      </div>
      {changePct !== undefined && (
        <div className={`flex items-center gap-1 text-[10px] font-bold ${changeColor}`}>
          {isPositive ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          <span>{Math.abs(changePct).toFixed(1)}% {changeLabel}</span>
        </div>
      )}
      {subtext && <div className="text-[10px] text-text-secondary font-medium">{subtext}</div>}
    </button>
  );
};

// ─── Section Header ────────────────────────────────────────────────────────────
const SectionHeader = ({ title, sub, action, onAction }: {
  title: string; sub?: string; action?: string; onAction?: () => void;
}) => (
  <div className="flex items-end justify-between mb-4">
    <div>
      <h3 className="text-xs font-bold text-text-primary">{title}</h3>
      {sub && <p className="text-[10px] text-text-secondary mt-0.5">{sub}</p>}
    </div>
    {action && (
      <button onClick={onAction}
        className="text-[10px] text-primary-blue font-bold hover:underline transition-all">
        {action} →
      </button>
    )}
  </div>
);

// ─── Alert Item ────────────────────────────────────────────────────────────────
const AlertItem = ({ type, text }: { type: 'warning' | 'info'; text: string }) => (
  <div className={`flex items-start gap-2.5 p-3 rounded-md text-xs ${
    type === 'warning'
      ? 'bg-warning-amber/8 border border-warning-amber/20 text-text-primary'
      : 'bg-primary-blue/5 border border-primary-blue/15 text-text-primary'
  }`}>
    {type === 'warning'
      ? <ShieldAlert size={13} className="text-warning-amber shrink-0 mt-0.5" />
      : <Lightbulb size={13} className="text-primary-blue shrink-0 mt-0.5" />
    }
    <span className="font-medium leading-relaxed">{text}</span>
  </div>
);

// ─── Mini Energy Network ───────────────────────────────────────────────────────
const MiniEnergyNetwork = () => (
  <div
    className="rounded-lg border border-border-hairline overflow-hidden"
    style={{
      background: 'linear-gradient(135deg, #EEF3FB 0%, #F4F7FC 100%)',
      boxShadow: '0 2px 12px rgba(47,107,255,0.06)',
    }}
  >
    <EnergyNetworkSVG />
  </div>
);

// ─── Mission Control Dashboard ─────────────────────────────────────────────────
const MissionControlDashboard = () => {
  const { uploadedBill } = useBill();
  const navigate = useNavigation();

  // DB-backed KPIs for authenticated users (gracefully falls back for guests)
  const { data: dashboardData } = useUserDashboard();
  const kpisFromDb = dashboardData?.kpis;

  // Prioritize local uploadedBill data (either from DB via BillContext or from guest session),
  // then fall back to KPI summaries from the dashboard endpoint
  const currentBill = uploadedBill?.total_bill ?? kpisFromDb?.current_bill ?? 138.90;
  const usageKwh = uploadedBill?.usage_kwh ?? kpisFromDb?.usage_kwh ?? 750;
  const effectiveRate = uploadedBill?.effective_rate ?? kpisFromDb?.effective_rate ?? 0.1852;
  const forecastBill = kpisFromDb?.forecast_next_month ?? (currentBill * 1.04);
  const billChangePct = kpisFromDb?.bill_change_pct ?? 2.4;
  const usageChangePct = kpisFromDb?.usage_change_pct ?? 1.2;
  const rateChangePct = kpisFromDb?.rate_change_pct ?? 0.8;
  const stateRank = kpisFromDb?.state_rank ?? 8;
  const vsPct = 12.3; // regional comparison — will improve with regional endpoint
  const savingsOpportunity = Math.max(0, currentBill - 118.0);

  const insights: string[] = dashboardData?.insights ?? [
    'Supply charges account for 58.3% of your bill.',
    `Your bill ${billChangePct >= 0 ? 'increased' : 'decreased'} by ${Math.abs(billChangePct).toFixed(1)}% vs. last month.`,
    `Your rate is ${Math.abs(vsPct).toFixed(1)}% above the national average.`,
  ];

  const alerts: string[] = [
    'Rates are currently in the standard summer pricing tier.',
    'Consider shifting high-consumption appliances to off-peak hours (10 PM–8 AM).',
  ];

  const KPI_CARDS: KpiCardProps[] = [
    {
      id: 'kpi-current-bill',
      label: 'Current Bill',
      value: `$${currentBill.toFixed(2)}`,
      changePct: billChangePct,
      changeLabel: 'vs. last month',
      accentColor: '#2F6BFF',
      targetTab: 'Bill Analysis',
    },
    {
      id: 'kpi-usage',
      label: 'Usage (kWh)',
      value: usageKwh.toFixed(0),
      unit: 'kWh',
      changePct: usageChangePct,
      changeLabel: 'vs. last month',
      accentColor: '#16A085',
      targetTab: 'Bill Analysis',
    },
    {
      id: 'kpi-rate',
      label: 'Effective Rate',
      value: `$${effectiveRate.toFixed(4)}`,
      unit: '/kWh',
      changePct: rateChangePct,
      changeLabel: 'vs. last month',
      accentColor: '#2CA6FF',
      targetTab: 'Impact & Simulation',
    },
    {
      id: 'kpi-forecast',
      label: 'Next Month Forecast',
      value: `$${forecastBill.toFixed(2)}`,
      subtext: 'ML ensemble estimate',
      accentColor: '#F5B041',
      targetTab: 'Forecast',
    },
    {
      id: 'kpi-savings',
      label: 'Savings Opportunity',
      value: savingsOpportunity > 0 ? `$${savingsOpportunity.toFixed(2)}` : 'Optimized',
      subtext: savingsOpportunity > 0 ? 'vs. state avg baseline' : 'Below state average',
      accentColor: '#27AE60',
      targetTab: 'Plans',
    },
    {
      id: 'kpi-regional-rank',
      label: 'Regional Rank',
      value: `#${stateRank}`,
      unit: `/ 50`,
      subtext: `${vsPct > 0 ? '+' : ''}${vsPct.toFixed(1)}% vs national avg`,
      accentColor: '#D64545',
      targetTab: 'Regional Insights',
    },
  ];

  return (
    <div className="space-y-8 pb-16 font-sans">

      {/* Page title */}
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-6 bg-primary-blue rounded-full" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-text-secondary">
              Mission Control
            </span>
            <div className="flex items-center gap-1 bg-savings-green/10 border border-savings-green/20 text-savings-green text-[8px] font-bold px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-savings-green animate-pulse" />
              Live
            </div>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">
            Electricity Intelligence Dashboard
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            {uploadedBill?.utility ?? 'PSE&G'} · {uploadedBill?.zip_code ?? '07102'} ·
            {' '}{uploadedBill?.billing_period ?? 'Jun 2026'}
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] text-text-secondary font-semibold">
          <span className="w-2 h-2 rounded-full bg-savings-green" />
          All systems operational
        </div>
      </div>

      {/* KPI Row — 6 cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {KPI_CARDS.map(kpi => <KpiCard key={kpi.id} {...kpi} />)}
      </div>

      {/* Middle section: Recent Bills + Compact Network */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-8">

        {/* Recent Bills (shared component, limit=5 compact) */}
        <div className="space-y-4">
          <SectionHeader
            title="Recent billing history"
            sub="Simulated seasonal 12-month history"
            action="Full history"
            onAction={() => navigate('Bill Analysis')}
          />
          <RecentBillsCard limit={5} compact />
        </div>

        {/* Compact Energy Network */}
        <div className="space-y-4">
          <SectionHeader title="Energy network" sub="Your local grid topology" />
          <MiniEnergyNetwork />
        </div>
      </div>

      {/* Alerts + Insights Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Smart Alerts */}
        <div className="panel-operational space-y-4">
          <SectionHeader title="Smart alerts" sub="Conditions affecting your bill" />
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <AlertItem key={i} type="warning" text={a} />
            ))}
          </div>
        </div>

        {/* Smart Insights */}
        <div className="panel-operational space-y-4">
          <SectionHeader
            title="AI insights"
            sub="Driven by bill analysis"
            action="Full analysis"
            onAction={() => navigate('Impact & Simulation')}
          />
          <div className="space-y-2">
            {insights.map((ins, i) => (
              <AlertItem key={i} type="info" text={ins} />
            ))}
          </div>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            id: 'quick-bill',
            title: 'Bill Analysis',
            desc: 'Re-upload or review your bill',
            tab: 'Bill Analysis',
            color: '#2F6BFF',
            icon: (
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            ),
          },
          {
            id: 'quick-impact',
            title: 'Impact & Simulation',
            desc: 'Run what-if rate scenarios',
            tab: 'Impact & Simulation',
            color: '#16A085',
            icon: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
          },
          {
            id: 'quick-forecast',
            title: 'Forecast',
            desc: "Predict next month's bill",
            tab: 'Forecast',
            color: '#F5B041',
            icon: (
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
            ),
          },
          {
            id: 'quick-plans',
            title: 'Energy Plans',
            desc: 'Compare available retail plans',
            tab: 'Plans',
            color: '#27AE60',
            icon: (
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            ),
          },
        ].map(({ id, title, desc, tab, color, icon }) => (
          <button
            key={id}
            id={id}
            onClick={() => navigate(tab)}
            className="panel-operational group text-left hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 space-y-3"
            style={{ borderLeft: `3px solid ${color}` }}
          >
            <div className="w-8 h-8 rounded-md flex items-center justify-center"
              style={{ backgroundColor: `${color}15` }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round">
                {icon}
              </svg>
            </div>
            <div>
              <div className="text-xs font-bold text-text-primary">{title}</div>
              <div className="text-[10px] text-text-secondary mt-0.5">{desc}</div>
            </div>
            <div className="flex items-center gap-1 text-[10px] font-bold opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ color }}>
              Open module →
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default MissionControlDashboard;
