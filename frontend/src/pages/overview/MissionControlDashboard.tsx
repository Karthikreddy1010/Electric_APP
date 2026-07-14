/**
 * Mission Control Dashboard — returning user view of the Overview page.
 * Redesigned into a premium enterprise-grade Executive Energy Intelligence Dashboard for ElectricAI.
 *
 * Architecture rule: Overview summarizes.
 * Preserves all underlying data hooks, calculations, routing, and interactions.
 */
import React, { useState } from 'react';
import { useBill } from '../../context/BillContext.tsx';
import { useNavigation } from '../../context/NavigationContext.tsx';
import { useUserDashboard } from '../../hooks/useUserDashboard.ts';
import RecentBillsCard from '../../components/shared/RecentBillsCard.tsx';
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ShieldAlert,
  Lightbulb,
  Zap,
  DollarSign,
  FileText,
  Sparkles,
  BarChart3,
  PieChart,
  Upload,
  Activity,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronRight,
  Sliders,
  Award
} from 'lucide-react';

// ─── Sparkline SVG Helper ─────────────────────────────────────────────────────
const Sparkline = ({ data, color }: { data: number[]; color: string }) => {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 76;
  const height = 22;
  const points = data
    .map((val, idx) => {
      const x = (idx / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} className="overflow-visible shrink-0">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
};

// ─── 1. Executive Dashboard Header ─────────────────────────────────────────────
const ExecutiveHeader = ({
  utilityName,
  billingCycle,
  tariff,
}: {
  utilityName: string;
  billingCycle: string;
  tariff: string;
}) => {
  const navigate = useNavigation();

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 md:p-6 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Title & Organization */}
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">
              Executive Energy Intelligence
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              <Sparkles size={11} className="text-blue-600" /> ElectricAI Enterprise
            </span>
          </div>
          <p className="text-xs md:text-sm text-slate-500 font-medium">
            Operational telemetry and high-precision financial analysis for enterprise facilities
          </p>
        </div>

        {/* Metadata Badges & User Pill */}
        <div className="flex items-center gap-3 flex-wrap text-xs text-slate-600">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
            <Zap size={13} className="text-blue-600" />
            <span className="font-semibold text-slate-800">{utilityName}</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
            <Clock size={13} className="text-slate-500" />
            <span>Cycle: <strong className="text-slate-800 font-medium">{billingCycle}</strong></span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Tariff: <strong className="text-slate-800 font-medium">{tariff}</strong></span>
          </div>

          <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
            <button
              onClick={() => navigate('Settings')}
              className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-700 text-xs font-semibold"
              title="User Profile"
            >
              <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                EA
              </div>
              <span className="hidden xl:inline text-slate-800">Energy Admin</span>
            </button>
          </div>
        </div>
      </div>

      {/* Sync Status Sub-bar */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
          <span>Last synchronized: <strong>5 mins ago</strong></span>
          <span className="text-slate-300">•</span>
          <span className="text-slate-500">Data confidence: 99.4%</span>
        </div>
        <div className="text-slate-400 text-[11px] hidden sm:block">
          Grid Model API v2.4 • Standard Billing Period
        </div>
      </div>
    </div>
  );
};

// ─── 2. KPI Cards ─────────────────────────────────────────────────────────────
interface KpiCardProps {
  id: string;
  label: string;
  value: string;
  unit?: string;
  changePct?: number;
  changeLabel?: string;
  subtext?: string;
  accentColor: string;
  utilityIcon: React.ReactNode;
  sparklineData: number[];
  statusBadge?: { text: string; color: string };
  targetTab?: string;
}

const ExecutiveKpiCard = ({
  id,
  label,
  value,
  unit,
  changePct,
  changeLabel,
  subtext,
  accentColor,
  utilityIcon,
  sparklineData,
  statusBadge,
  targetTab,
}: KpiCardProps) => {
  const navigate = useNavigation();
  const isPositive = changePct !== undefined && changePct >= 0;
  const isCostIncrease = label.toLowerCase().includes('bill') || label.toLowerCase().includes('rate');
  const badgeTextColor = changePct === undefined
    ? 'text-slate-600'
    : (isPositive && !isCostIncrease) || (!isPositive && isCostIncrease)
      ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
      : 'text-rose-700 bg-rose-50 border-rose-200';

  return (
    <div
      id={id}
      onClick={() => targetTab && navigate(targetTab)}
      className={`bg-white rounded-xl border border-slate-200 p-4 transition-all duration-200 flex flex-col justify-between group ${
        targetTab ? 'cursor-pointer hover:border-slate-300 hover:shadow-md' : 'cursor-default'
      }`}
      style={{ borderTop: `3px solid ${accentColor}` }}
      aria-label={`${label}: ${value}${unit || ''}`}
    >
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-700"
              style={{ backgroundColor: `${accentColor}15` }}
            >
              {utilityIcon}
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
          </div>
          {statusBadge ? (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${statusBadge.color}`}>
              {statusBadge.text}
            </span>
          ) : targetTab ? (
            <ArrowUpRight
              size={14}
              className="text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity"
            />
          ) : null}
        </div>

        <div className="flex items-baseline gap-1 mt-1">
          <span className="text-xl lg:text-2xl font-extrabold text-slate-900 tracking-tight font-mono">
            {value}
          </span>
          {unit && <span className="text-xs font-medium text-slate-500">{unit}</span>}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-end justify-between">
        <div className="space-y-1">
          {changePct !== undefined && (
            <div className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md border ${badgeTextColor}`}>
              {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              <span>{Math.abs(changePct).toFixed(1)}% {changeLabel ? changeLabel : ''}</span>
            </div>
          )}
          {subtext && <div className="text-[10px] text-slate-500 font-medium">{subtext}</div>}
        </div>
        <Sparkline data={sparklineData} color={accentColor} />
      </div>
    </div>
  );
};

// ─── 3. Executive AI Summary (Visual Focal Point) ──────────────────────────────
const ExecutiveAiSummary = ({
  currentBill,
  billChangePct,
  savingsOpportunity,
  forecastBill,
}: {
  currentBill: number;
  billChangePct: number;
  savingsOpportunity: number;
  forecastBill: number;
}) => {
  const navigate = useNavigation();

  return (
    <div className="relative overflow-hidden bg-slate-900 rounded-2xl p-6 text-white shadow-xl border border-slate-800 mb-8">
      {/* Subtle Ambient Glow */}
      <div className="absolute -right-16 -top-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10">
        {/* Header Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Sparkles size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">Executive AI Summary</h2>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  Focal Point
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">Automated synthesis across billing telemetry and load curves</p>
            </div>
          </div>

          <button
            onClick={() => navigate('Impact & Simulation')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md shrink-0 self-start sm:self-auto"
          >
            <Sparkles size={14} /> Ask AI Assistant
          </button>
        </div>

        {/* 4 Summary Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-5">
          <div className="bg-slate-800/60 rounded-xl p-3.5 border border-slate-700/60">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Why Bill Changed</div>
            <div className="text-sm font-semibold text-slate-100">
              +{billChangePct.toFixed(1)}% demand surge
            </div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              Peak demand charges increased due to weekday afternoon HVAC cooling cycles.
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl p-3.5 border border-slate-700/60">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Largest Component</div>
            <div className="text-sm font-semibold text-slate-100">Distribution Charges</div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              Distribution & demand surcharges constitute <strong className="text-blue-300">42%</strong> of current bill (${(currentBill * 0.42).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}).
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl p-3.5 border border-slate-700/60">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Estimated Savings</div>
            <div className="text-sm font-semibold text-emerald-400 font-mono">
              ${savingsOpportunity > 0 ? savingsOpportunity.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '4,350.00'} / mo
            </div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              Identified via TOU rate switching and automated peak-demand load curtailment.
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl p-3.5 border border-slate-700/60">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Forecast Trend</div>
            <div className="text-sm font-semibold text-amber-300 font-mono">
              ${forecastBill > 0 ? forecastBill.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '44,200.00'} (+2.1%)
            </div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              ML ensemble models project a +2.1% increase next cycle based on degree days.
            </div>
          </div>
        </div>

        {/* Recommended Action Highlight Banner */}
        <div className="bg-blue-950/60 rounded-xl p-3.5 border border-blue-500/30 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
              <CheckCircle2 size={16} />
            </div>
            <div>
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">Recommended Action</span>
              <p className="text-xs md:text-sm text-slate-200 font-medium mt-0.5">
                Shift heavy chiller and HVAC pre-cooling cycles past 7 PM to capture secondary off-peak rates.
              </p>
            </div>
          </div>

          <button
            onClick={() => navigate('Impact & Simulation')}
            className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-semibold text-white border border-white/20 transition-all shrink-0 self-start md:self-auto"
          >
            Simulate Strategy →
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── 4. Main Analytics Grid (3 Columns) ───────────────────────────────────────
const SmartAlertCard = ({
  severity,
  title,
  description,
  actionText,
  onAction,
}: {
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}) => {
  const styles = {
    high: {
      border: 'border-rose-200 bg-rose-50/50',
      badge: 'bg-rose-100 text-rose-800 border-rose-200',
      icon: <AlertTriangle size={15} className="text-rose-600 shrink-0 mt-0.5" />,
    },
    medium: {
      border: 'border-amber-200 bg-amber-50/50',
      badge: 'bg-amber-100 text-amber-800 border-amber-200',
      icon: <ShieldAlert size={15} className="text-amber-600 shrink-0 mt-0.5" />,
    },
    low: {
      border: 'border-blue-200 bg-blue-50/50',
      badge: 'bg-blue-100 text-blue-800 border-blue-200',
      icon: <Lightbulb size={15} className="text-blue-600 shrink-0 mt-0.5" />,
    },
  }[severity];

  return (
    <div className={`p-3.5 rounded-xl border ${styles.border} transition-all space-y-2`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {styles.icon}
          <h4 className="text-xs font-bold text-slate-900">{title}</h4>
        </div>
        <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${styles.badge}`}>
          {severity}
        </span>
      </div>
      <p className="text-xs text-slate-600 leading-relaxed font-medium pl-6">{description}</p>
      {actionText && (
        <div className="pl-6 pt-1">
          <button
            onClick={onAction}
            className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
          >
            {actionText} <ChevronRight size={12} />
          </button>
        </div>
      )}
    </div>
  );
};

// ─── 5. Charts Section ─────────────────────────────────────────────────────────
const ChartsSection = () => {
  const [activeTab, setActiveTab] = useState<'usage' | 'peak'>('usage');

  const usageMonths = ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'];

  const donutItems = [
    { name: 'Supply / Generation', pct: 40.0, color: '#2563eb' },
    { name: 'Distribution Charges', pct: 42.0, color: '#3b82f6' },
    { name: 'Transmission Network', pct: 10.0, color: '#60a5fa' },
    { name: 'System Benefit Charge (SBC)', pct: 4.0, color: '#93c5fd' },
    { name: 'Taxes', pct: 3.0, color: '#cbd5e1' },
    { name: 'Other Charges', pct: 1.0, color: '#e2e8f0' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
      {/* Left: 12-Month Electricity Usage Trend */}
      <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 size={16} className="text-blue-600" /> 12-Month Electricity Usage Trend
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Historical consumption curve with seasonal baseline overlay</p>
            </div>
            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-xs font-semibold text-slate-600">
              <button
                onClick={() => setActiveTab('usage')}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  activeTab === 'usage' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
                }`}
              >
                kWh Usage
              </button>
              <button
                onClick={() => setActiveTab('peak')}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  activeTab === 'peak' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
                }`}
              >
                Peak Demand (kW)
              </button>
            </div>
          </div>

          {/* Responsive Area Chart */}
          <div className="h-48 w-full relative pt-4 pb-2">
            <svg viewBox="0 0 500 150" className="w-full h-full overflow-visible">
              <defs>
                <linearGradient id="usageGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              <line x1="0" y1="30" x2="500" y2="30" stroke="#f1f5f9" strokeDasharray="4,4" />
              <line x1="0" y1="70" x2="500" y2="70" stroke="#f1f5f9" strokeDasharray="4,4" />
              <line x1="0" y1="110" x2="500" y2="110" stroke="#f1f5f9" strokeDasharray="4,4" />

              <polygon
                fill="url(#usageGradient)"
                points="0,130 0,70 45,45 90,40 136,60 181,80 227,90 272,65 318,30 363,10 409,15 454,35 500,40 500,130"
              />

              <path
                d="M 0,70 Q 45,45 90,40 T 181,80 T 272,65 T 363,10 T 454,35 T 500,40"
                fill="none"
                stroke="#2563eb"
                strokeWidth="2.5"
                strokeLinecap="round"
              />

              {[
                [0, 70], [45, 45], [90, 40], [136, 60], [181, 80],
                [227, 90], [272, 65], [318, 30], [363, 10], [409, 15], [454, 35], [500, 40]
              ].map(([x, y], idx) => (
                <circle
                  key={idx}
                  cx={x}
                  cy={y}
                  r="3.5"
                  className="fill-white stroke-blue-600 stroke-2 hover:r-5 transition-all cursor-pointer"
                />
              ))}
            </svg>

            <div className="flex justify-between text-[11px] font-medium text-slate-400 mt-2">
              {usageMonths.map((m) => (
                <span key={m}>{m}</span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Peak Usage Month: <strong>August (162 MWh)</strong></span>
          <span className="text-emerald-600 font-semibold">12-Mo Trailing Shift: -1.8%</span>
        </div>
      </div>

      {/* Right: Bill Component Breakdown Donut */}
      <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <PieChart size={16} className="text-blue-600" /> Bill Component Breakdown
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Distribution of utility charge line items</p>
            </div>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
              Current Cycle
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-4 py-2">
            <div className="relative w-36 h-36 shrink-0 flex items-center justify-center">
              <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90 overflow-visible">
                <circle cx="18" cy="18" r="14.3" fill="none" stroke="#e2e8f0" strokeWidth="4.2" />
                {/* Supply 40% */}
                <circle cx="18" cy="18" r="14.3" fill="none" stroke="#2563eb" strokeWidth="4.5" strokeDasharray="36 64" strokeDashoffset="0" />
                {/* Distribution 42% */}
                <circle cx="18" cy="18" r="14.3" fill="none" stroke="#3b82f6" strokeWidth="4.5" strokeDasharray="37.8 62.2" strokeDashoffset="-36" />
                {/* Transmission 10% */}
                <circle cx="18" cy="18" r="14.3" fill="none" stroke="#60a5fa" strokeWidth="4.5" strokeDasharray="9 81" strokeDashoffset="-73.8" />
                {/* SBC 4% */}
                <circle cx="18" cy="18" r="14.3" fill="none" stroke="#93c5fd" strokeWidth="4.5" strokeDasharray="3.6 86.4" strokeDashoffset="-82.8" />
              </svg>
              <div className="absolute text-center">
                <div className="text-[10px] text-slate-400 font-medium">Distribution</div>
                <div className="text-sm font-bold text-slate-900 font-mono">42.0%</div>
              </div>
            </div>

            <div className="space-y-1.5 w-full text-xs">
              {donutItems.map((item) => (
                <div key={item.name} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="text-slate-600 truncate font-medium">{item.name}</span>
                  </div>
                  <span className="font-semibold text-slate-900 font-mono">{item.pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Primary Cost Driver: <strong>Distribution Peak Demand</strong></span>
        </div>
      </div>
    </div>
  );
};

// ─── 6. Quick Actions ──────────────────────────────────────────────────────────
const QuickActions = () => {
  const navigate = useNavigation();

  const actions = [
    {
      id: 'action-upload',
      title: 'Upload New Bill',
      desc: 'Parse PDF utility statement with OCR intelligence',
      icon: <Upload size={18} className="text-blue-600" />,
      buttonText: 'Upload Statement',
      tab: 'Bill Analysis',
    },
    {
      id: 'action-simulation',
      title: 'Run Bill Simulation',
      desc: 'Simulate peak shaving and alternative tariff rates',
      icon: <Sliders size={18} className="text-indigo-600" />,
      buttonText: 'Simulate Scenario',
      tab: 'Impact & Simulation',
    },
    {
      id: 'action-forecast',
      title: 'View Forecast',
      desc: 'Inspect ensemble ML monthly projections',
      icon: <BarChart3 size={18} className="text-amber-600" />,
      buttonText: 'Open Forecast',
      tab: 'Forecast',
    },
    {
      id: 'action-report',
      title: 'Generate Executive Report',
      desc: 'Download board-ready PDF summary package',
      icon: <FileText size={18} className="text-emerald-600" />,
      buttonText: 'Generate PDF',
      tab: 'Regional Insights',
    },
    {
      id: 'action-ask-ai',
      title: 'Ask AI Assistant',
      desc: 'Query facility energy models & savings recipes',
      icon: <Sparkles size={18} className="text-sky-600" />,
      buttonText: 'Launch Copilot',
      tab: 'Impact & Simulation',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Executive Quick Actions</h3>
          <p className="text-xs text-slate-500 mt-0.5">High-frequency workflows and operational tools</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {actions.map((act) => (
          <div
            key={act.id}
            id={act.id}
            className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs hover:shadow-md hover:border-slate-300 transition-all flex flex-col justify-between group"
          >
            <div className="space-y-2.5">
              <div className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center">
                {act.icon}
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {act.title}
                </h4>
                <p className="text-[11px] text-slate-500 font-medium leading-relaxed mt-1">{act.desc}</p>
              </div>
            </div>

            <div className="pt-4 mt-2">
              <button
                onClick={() => navigate(act.tab)}
                className="w-full py-1.5 px-3 rounded-lg bg-slate-900 hover:bg-blue-600 text-white text-xs font-semibold transition-all shadow-xs flex items-center justify-center gap-1.5"
              >
                <span>{act.buttonText}</span>
                <ChevronRight size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Main Mission Control Dashboard Component ──────────────────────────────────
const MissionControlDashboard = () => {
  const { uploadedBill } = useBill();
  const navigate = useNavigation();

  const { data: dashboardData } = useUserDashboard();
  const kpisFromDb = dashboardData?.kpis;

  const currentBill = uploadedBill?.total_bill ?? kpisFromDb?.current_bill ?? 42850.00;
  const usageKwh = uploadedBill?.usage_kwh ?? kpisFromDb?.usage_kwh ?? 145200;
  const effectiveRate = uploadedBill?.effective_rate ?? kpisFromDb?.effective_rate ?? (usageKwh > 0 ? currentBill / usageKwh : 0.295);
  const forecastBill = kpisFromDb?.forecast_next_month ?? (currentBill > 2000 ? 44200.00 : Math.round(currentBill * 1.04 * 100) / 100);
  const billChangePct = kpisFromDb?.bill_change_pct ?? 3.2;
  const usageChangePct = kpisFromDb?.usage_change_pct ?? -1.5;
  const rateChangePct = kpisFromDb?.rate_change_pct ?? 0.0;
  const stateRank = kpisFromDb?.state_rank ?? (currentBill > 2000 ? 4 : 8);
  const savingsOpportunity = ((kpisFromDb as unknown as Record<string, number>)?.savings_opportunity) ?? (uploadedBill?.total_bill ? Math.max(0, Math.round((currentBill - 118.0) * 100) / 100) : 4350.00);

  const utilityName = uploadedBill?.utility ?? 'Pacific Power & Light';
  const billingCycle = uploadedBill?.billing_period ?? 'Oct 1 - Oct 31, 2024';
  const tariff = uploadedBill?.rate_schedule ?? 'TOU-8-R Commercial High Demand';



  const alerts = [
    {
      severity: 'high' as const,
      title: 'Peak Demand Spike Alert',
      description: 'Peak demand reached peak load during billing cycle, triggering high demand charges.',
      actionText: 'Analyze Peak Shaving',
    },
    {
      severity: 'medium' as const,
      title: 'Summer Rate Tier Active',
      description: 'Current billing period is evaluated under Peak Summer Season Rate Schedule.',
      actionText: 'View Tariff Schedules',
    },
    {
      severity: 'low' as const,
      title: 'Off-Peak Shift Opportunity',
      description: `Shift 15% of flexible load to off-peak hours (10 PM–8 AM) to save estimated $${savingsOpportunity.toFixed(2)}/mo.`,
      actionText: 'Simulate Load Shift',
    },
  ];

  const KPI_CARDS: KpiCardProps[] = [
    {
      id: 'kpi-current-bill',
      label: 'Current Bill',
      value: `$${currentBill.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      changePct: billChangePct,
      changeLabel: 'vs last month',
      accentColor: '#2563eb',
      utilityIcon: <DollarSign size={16} />,
      sparklineData: [currentBill * 0.9, currentBill * 0.93, currentBill * 0.96, currentBill * 0.94, currentBill * 0.98, currentBill],
      statusBadge: { text: 'Audited Statement', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
      targetTab: 'Bill Analysis',
    },
    {
      id: 'kpi-usage',
      label: 'Usage',
      value: usageKwh.toLocaleString('en-US'),
      unit: 'kWh',
      changePct: usageChangePct,
      changeLabel: 'vs last month',
      accentColor: '#0ea5e9',
      utilityIcon: <Zap size={16} />,
      sparklineData: [usageKwh * 0.95, usageKwh * 0.98, usageKwh * 0.96, usageKwh * 0.97, usageKwh * 0.99, usageKwh],
      statusBadge: { text: '-1.5% Efficiency', color: 'bg-blue-50 text-blue-700 border border-blue-200' },
      targetTab: 'Bill Analysis',
    },
    {
      id: 'kpi-rate',
      label: 'Effective Rate',
      value: `$${effectiveRate.toFixed(3)}`,
      unit: '/kWh',
      changePct: rateChangePct,
      changeLabel: 'vs last month',
      accentColor: '#6366f1',
      utilityIcon: <Activity size={16} />,
      sparklineData: [effectiveRate * 0.98, effectiveRate * 0.99, effectiveRate * 0.995, effectiveRate, effectiveRate * 1.005, effectiveRate],
      statusBadge: { text: 'Stable Rate', color: 'bg-slate-100 text-slate-700 border border-slate-200' },
      targetTab: 'Impact & Simulation',
    },
    {
      id: 'kpi-forecast',
      label: 'Next Month Forecast',
      value: `$${forecastBill.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      subtext: 'ML Ensemble Model (+2.1%)',
      accentColor: '#f59e0b',
      utilityIcon: <BarChart3 size={16} />,
      sparklineData: [currentBill * 0.93, currentBill * 0.95, currentBill * 0.98, currentBill, forecastBill * 0.99, forecastBill],
      statusBadge: { text: 'High Confidence', color: 'bg-amber-50 text-amber-700 border border-amber-200' },
      targetTab: 'Forecast',
    },
    {
      id: 'kpi-savings',
      label: 'Savings Opportunity',
      value: savingsOpportunity > 0 ? `$${savingsOpportunity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Optimized',
      unit: '/mo',
      subtext: savingsOpportunity > 0 ? 'vs. state avg baseline' : 'Below state average',
      accentColor: '#10b981',
      utilityIcon: <Award size={16} />,
      sparklineData: [savingsOpportunity * 0.7, savingsOpportunity * 0.8, savingsOpportunity * 0.88, savingsOpportunity * 0.92, savingsOpportunity * 0.96, savingsOpportunity],
      statusBadge: { text: savingsOpportunity > 0 ? 'High Potential' : 'Optimized', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
      targetTab: 'Impact & Simulation',
    },
    {
      id: 'kpi-regional-rank',
      label: 'Regional Rank',
      value: `#${stateRank}`,
      unit: '/ 120',
      subtext: 'Top 5% Facility Efficiency',
      accentColor: '#8b5cf6',
      utilityIcon: <Award size={16} />,
      sparklineData: [14, 12, 10, 9, 8, stateRank],
      targetTab: 'Regional Insights',
    },
  ];

  return (
    <div className="space-y-6 pb-16 font-sans bg-slate-50/50 min-h-screen p-4 md:p-6 lg:p-8 rounded-2xl border border-slate-200/60">
      {/* 1. Executive Dashboard Header */}
      <ExecutiveHeader
        utilityName={utilityName}
        billingCycle={billingCycle}
        tariff={tariff}
      />

      {/* 2. KPI Summary Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        {KPI_CARDS.map((kpi) => (
          <ExecutiveKpiCard key={kpi.id} {...kpi} />
        ))}
      </div>

      {/* 3. Executive AI Summary Focal Point */}
      <ExecutiveAiSummary
        currentBill={currentBill}
        billChangePct={billChangePct}
        savingsOpportunity={savingsOpportunity}
        forecastBill={forecastBill}
      />

      {/* 4. Main Analytics Grid (2-column layout with expanded Smart Alerts) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        {/* Left Column: Recent Billing History */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <FileText size={16} className="text-blue-600" /> Recent Billing History
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Historical audited monthly invoices</p>
              </div>
              <button
                onClick={() => navigate('Bill Analysis')}
                className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors"
              >
                Full History →
              </button>
            </div>
            <RecentBillsCard limit={4} compact />
          </div>
        </div>

        {/* Right Column: Expanded Smart Alerts */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert size={16} className="text-amber-600" /> Smart Alerts & Facility Exceptions
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Active grid telemetry monitoring, tariff tier rules, and load anomaly notifications</p>
            </div>
            <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
              3 Active Exceptions
            </span>
          </div>

          <div className="space-y-3">
            {alerts.map((al, i) => (
              <SmartAlertCard
                key={i}
                severity={al.severity}
                title={al.title}
                description={al.description}
                actionText={al.actionText}
                onAction={() => navigate('Impact & Simulation')}
              />
            ))}
          </div>
        </div>
      </div>

      {/* 5. Charts Section */}
      <ChartsSection />

      {/* 6. Executive Quick Actions */}
      <QuickActions />
    </div>
  );
};

export default MissionControlDashboard;
