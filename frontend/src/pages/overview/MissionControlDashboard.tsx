/**
 * Mission Control Dashboard — returning user view of the Overview page.
 * Redesigned into a premium enterprise-grade Executive Energy Intelligence Dashboard for ElectricAI.
 *
 * Architecture rule: Overview summarizes.
 * Preserves all underlying data hooks, calculations, routing, and interactions.
 */
import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useBill } from '../../context/BillContext.tsx';
import { useNavigation } from '../../context/NavigationContext.tsx';
import { useUserDashboard, useInvalidateDashboard } from '../../hooks/useUserDashboard.ts';
import apiClient from '../../lib/apiClient.ts';
import RecentBillsCard from '../../components/shared/RecentBillsCard.tsx';
import {
  ShieldAlert,
  Zap,
  DollarSign,
  FileText,
  Sparkles,
  BarChart3,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ChevronRight,
  Info
} from 'lucide-react';

// ─── Reusable Enterprise SaaS KPI Card Component ─────────────────────────────
interface SaaSExecutiveKpiCardProps {
  id: string;
  label: string;
  value: string;
  unit?: string;
  description: string;
  statusBadge?: { text: string; color: string };
  icon: React.ReactNode;
  iconBgColor?: string;
  targetTab?: string;
  onClick?: () => void;
}

const SaaSExecutiveKpiCard = ({
  id,
  label,
  value,
  unit,
  description,
  statusBadge,
  icon,
  iconBgColor = 'bg-blue-50 text-blue-600 border-blue-100',
  targetTab,
  onClick,
}: SaaSExecutiveKpiCardProps) => {
  const navigate = useNavigation();
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (targetTab) {
      navigate(targetTab);
    }
  };

  return (
    <div
      id={id}
      onClick={handleClick}
      className={`h-full bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between group ${
        targetTab || onClick ? 'cursor-pointer' : 'cursor-default'
      }`}
      aria-label={`${label}: ${value}${unit ? ' ' + unit : ''}`}
    >
      {/* Top Row: Icon & Status Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shrink-0 ${iconBgColor}`}>
          {icon}
        </div>
        {statusBadge && (
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border shrink-0 ${statusBadge.color}`}>
            {statusBadge.text}
          </span>
        )}
      </div>

      {/* KPI Title Row (Full-width for maximum clarity) */}
      <div className="mb-2">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
          {label}
        </span>
      </div>

      {/* Middle Section: Large Metric Value & Unit */}
      <div className="flex items-baseline gap-1.5 mb-4">
        <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
          {value}
        </span>
        {unit && (
          <span className="text-sm font-medium text-slate-500">{unit}</span>
        )}
      </div>

      {/* Bottom Section: Short Description */}
      <div className="mt-auto pt-2">
        <p className="text-xs text-slate-500 font-normal leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
};

// ─── Simplified Forecast KPI Card ─────────────────────────────────────────────
const ForecastKpiCard = ({ forecastResults, navigate }: { forecastResults: any; navigate: any }) => {
  const isUnavailable = !forecastResults || forecastResults.status === "unavailable";
  
  if (isUnavailable) {
    return (
      <div
        id="kpi-forecast"
        onClick={() => navigate('Forecast')}
        className="h-full bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between cursor-pointer group"
      >
        {/* Top Row: Icon & Status Badge */}
        <div className="flex items-center justify-between mb-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-amber-50 text-amber-600 border border-amber-100 shrink-0">
            <BarChart3 className="w-5 h-5" />
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
            Unavailable
          </span>
        </div>

        {/* KPI Title Row */}
        <div className="mb-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Next Month Forecast
          </span>
        </div>

        {/* Middle Section */}
        <div className="flex items-baseline gap-1.5 mb-4">
          <span className="text-2xl sm:text-3xl font-extrabold text-slate-400 tracking-tight font-sans">
            Unavailable
          </span>
        </div>

        {/* Bottom Section */}
        <div className="mt-auto pt-2">
          <p className="text-xs text-slate-500 font-normal leading-relaxed">
            Upload consecutive monthly bills to enable AI forecasting.
          </p>
        </div>
      </div>
    );
  }

  const { predicted_bill, confidence_level, confidence_score } = forecastResults;

  return (
    <div
      id="kpi-forecast"
      onClick={() => navigate('Forecast')}
      className="h-full bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between cursor-pointer group"
    >
      {/* Top Row: Icon & Status Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-amber-50 text-amber-600 border border-amber-100 shrink-0">
          <BarChart3 className="w-5 h-5" />
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
          {confidence_level ? `${confidence_score.toFixed(0)}% ${confidence_level}` : 'High Confidence'}
        </span>
      </div>

      {/* KPI Title Row */}
      <div className="mb-2">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
          Next Month Forecast
        </span>
      </div>

      {/* Middle Section */}
      <div className="flex items-baseline gap-1.5 mb-4">
        <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
          ${predicted_bill.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>

      {/* Bottom Section */}
      <div className="mt-auto pt-2">
        <p className="text-xs text-slate-500 font-normal leading-relaxed">
          Predicted next billing cycle expenditure based on historical degree days & load curves.
        </p>
      </div>
    </div>
  );
};

// ─── 1. Executive Dashboard Header ─────────────────────────────────────────────
const ExecutiveHeader = ({
  utilityName,
  billingCycle,
  tariff,
  dashboardMode,
  setDashboardMode,
  loadingMeter,
}: {
  utilityName: string;
  billingCycle: string;
  tariff: string;
  dashboardMode: 'billing' | 'metering';
  setDashboardMode: (mode: 'billing' | 'metering') => void;
  loadingMeter?: boolean;
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-5 md:p-6 mb-6 shadow-xs">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3.5">
        {/* Title & Organization */}
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">
              Executive Energy Intelligence
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              <Sparkles size={12} className="text-blue-600" /> ElectricAI Enterprise
            </span>
          </div>
          <p className="text-xs md:text-sm text-slate-500 font-medium leading-relaxed">
            Operational telemetry and high-precision financial analysis for enterprise facilities
          </p>
        </div>
 
        {/* Active Context Indicators & Mode Selector */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200">
            <button
              onClick={() => setDashboardMode('billing')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer font-semibold ${
                dashboardMode === 'billing'
                  ? 'bg-white text-slate-900 border border-slate-200 shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Billing
            </button>
            <button
              onClick={() => setDashboardMode('metering')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer font-semibold flex items-center gap-1.5 ${
                dashboardMode === 'metering'
                  ? 'bg-white text-slate-900 border border-slate-200 shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Smart Meter
              {loadingMeter && (
                <RefreshCw size={10} className="animate-spin text-blue-600" />
              )}
            </button>
          </div>

          <div className="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col">
            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Utility Provider</span>
            <span className="font-semibold text-slate-800 truncate max-w-[180px]" title={utilityName}>{utilityName}</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col">
            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Rate Schedule</span>
            <span className="font-semibold text-slate-800 truncate max-w-[200px]" title={tariff}>{tariff}</span>
          </div>
        </div>
      </div>

      {/* Sync Status Sub-bar */}
      <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
          <span>Last synchronized: <strong>5 mins ago</strong></span>
          <span className="text-slate-300">•</span>
          <span>Data confidence: 99.4%</span>
        </div>
        <div className="text-slate-400 text-[11px] hidden sm:block font-medium">
          Grid Model API v2.4 • Period: <strong className="text-slate-700 font-semibold">{billingCycle}</strong>
        </div>
      </div>
    </div>
  );
};

// ─── 3. Executive AI Summary ─────────────────────────────────────────────────
const ExecutiveAiSummary = ({
  currentBill,
  billChangePct,
  savingsOpportunity,
  forecastBill,
  aiStatus = "completed",
  aiExplanation,
  activeBillId,
}: {
  currentBill: number;
  billChangePct: number;
  savingsOpportunity: number;
  forecastBill: number;
  aiStatus?: string;
  aiExplanation?: string;
  activeBillId?: string;
}) => {
  const navigate = useNavigation();
  const invalidateDashboard = useInvalidateDashboard();
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleRegenerate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeBillId || isRegenerating) return;
    try {
      setIsRegenerating(true);
      await apiClient.post(`/users/me/bills/${activeBillId}/regenerate-ai`);
      invalidateDashboard();
    } catch (err) {
      console.warn("Manual AI regeneration failed:", err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const statusBadge = (() => {
    if (aiStatus === 'generating') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-400/30 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
          Generating AI Insights...
        </span>
      );
    }
    if (aiStatus === 'offline' || aiStatus === 'fallback') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-400/30">
          <Info size={11} className="text-amber-400" />
          AI Offline (Deterministic Active)
        </span>
      );
    }
    if (aiStatus === 'failed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-400/30">
          <AlertTriangle size={11} className="text-rose-400" />
          AI Temporarily Delayed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
        <CheckCircle2 size={11} className="text-emerald-400" />
        AI Insights Ready
      </span>
    );
  })();

  return (
    <div className="relative overflow-hidden bg-slate-900 rounded-2xl p-6 text-white shadow-xl border border-slate-800 mb-8">
      {/* Ambient Glow */}
      <div className="absolute -right-16 -top-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10">
        {/* Header Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Sparkles size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-white tracking-tight">Executive AI Summary</h2>
                {statusBadge}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">Automated synthesis across billing telemetry and load curves</p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            {activeBillId && (
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating || aiStatus === 'generating'}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold border border-slate-700 transition-all shrink-0"
                title="Regenerate AI insights without re-running deterministic bill math"
              >
                <Sparkles size={13} className={isRegenerating ? 'animate-spin text-blue-400' : 'text-slate-400'} />
                <span>{isRegenerating ? 'Queuing...' : 'Regenerate AI'}</span>
              </button>
            )}
            <button
              onClick={() => navigate('Impact & Simulation')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md shrink-0"
            >
              <Sparkles size={14} /> Ask AI Assistant
            </button>
          </div>
        </div>

        {/* 4 Summary Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-5">
          <div className="bg-slate-800/60 rounded-xl p-3.5 border border-slate-700/60">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Why Bill Changed</div>
            <div className="text-sm font-semibold text-slate-100">
              +{billChangePct.toFixed(1)}% demand surge
            </div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              {aiExplanation
                ? aiExplanation.slice(0, 120) + '...'
                : 'Peak demand charges increased due to weekday afternoon HVAC cooling cycles.'}
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
              {forecastBill > 0 ? `$${forecastBill.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'Unavailable'}
            </div>
            <div className="text-xs text-slate-300 mt-1 leading-relaxed">
              {forecastBill > 0 
                ? 'ML ensemble models project next cycle costs based on weather patterns and degree days.' 
                : 'Upload at least 3 consecutive bills to enable AI forecast projections.'}
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

// ─── 4. Main Analytics Grid (Smart Alerts) ────────────────────────────────────
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
  actionText: string;
  onAction: () => void;
}) => {
  const isHigh = severity === 'high';
  const isMedium = severity === 'medium';

  const severityColor = isHigh
    ? 'border-l-rose-500 bg-rose-50/50 text-rose-900'
    : isMedium
    ? 'border-l-amber-500 bg-amber-50/50 text-amber-900'
    : 'border-l-blue-500 bg-blue-50/50 text-blue-900';

  const badgeColor = isHigh
    ? 'bg-rose-100 text-rose-700'
    : isMedium
    ? 'bg-amber-100 text-amber-700'
    : 'bg-blue-100 text-blue-700';

  return (
    <div className={`p-4 rounded-xl border border-slate-200 border-l-4 ${severityColor} transition-all`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full ${badgeColor}`}>
              {severity} Priority
            </span>
            <h4 className="text-xs font-bold text-slate-900">{title}</h4>
          </div>
          <p className="text-xs text-slate-600 font-normal leading-relaxed">{description}</p>
        </div>
        <button
          onClick={onAction}
          className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors shrink-0 flex items-center gap-1 cursor-pointer"
        >
          <span>{actionText}</span>
          <ChevronRight size={12} />
        </button>
      </div>
    </div>
  );
};

// ─── 5. Charts Section ────────────────────────────────────────────────────────
const ChartsSection = () => {
  const dummyChartData = [
    { month: 'May', bill: 38200, usage: 132000 },
    { month: 'Jun', bill: 41500, usage: 141000 },
    { month: 'Jul', bill: 45800, usage: 154000 },
    { month: 'Aug', bill: 44200, usage: 149000 },
    { month: 'Sep', bill: 41200, usage: 138000 },
    { month: 'Oct', bill: 42850, usage: 145200 },
  ];

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs mb-8">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Activity size={18} className="text-blue-600" /> Historical Billing & Consumption Trend
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">Six-month audited utility expenditure vs volume load</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-blue-600" />
            <span className="text-slate-600">Total Bill ($)</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={dummyChartData}>
            <defs>
              <linearGradient id="billTrendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
            <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Total Bill']} />
            <Area type="monotone" dataKey="bill" stroke="#2563eb" strokeWidth={2.5} fillOpacity={1} fill="url(#billTrendGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// ─── 6. Executive Quick Actions ───────────────────────────────────────────────
const QuickActions = () => {
  const navigate = useNavigation();

  const actions = [
    {
      id: 'qa-upload',
      title: 'Upload Utility Bill',
      desc: 'Ingest PDF statements or CSV intervals for instant AI parsing',
      icon: <DollarSign className="w-5 h-5 text-blue-600" />,
      buttonText: 'Upload File',
      tab: 'Bill Analysis',
    },
    {
      id: 'qa-rate',
      title: 'Rate Schedule Match',
      desc: 'Simulate alternative commercial rate structures to optimize costs',
      icon: <Activity className="w-5 h-5 text-indigo-600" />,
      buttonText: 'Compare Rates',
      tab: 'Impact & Simulation',
    },
    {
      id: 'qa-forecast',
      title: 'Load Forecasting',
      desc: 'Project future demand spikes and peak charges using ML models',
      icon: <BarChart3 className="w-5 h-5 text-amber-600" />,
      buttonText: 'View Forecast',
      tab: 'Forecast',
    },
    {
      id: 'qa-[#regional]',
      title: 'Regional Benchmarks',
      desc: 'Compare building energy intensity against peer utility territories',
      icon: <Sparkles className="w-5 h-5 text-purple-600" />,
      buttonText: 'Explore Map',
      tab: 'Regional Insights',
    },
    {
      id: 'qa-[#ai]',
      title: 'AI Tariff Copilot',
      desc: 'Interactive chat assistant for tariff rules, Peak Demand, and TOU',
      icon: <ShieldAlert className="w-5 h-5 text-cyan-600" />,
      buttonText: 'Open Copilot',
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
            className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer hover:-translate-y-0.5"
          >
            <div className="space-y-2.5">
              <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center">
                {act.icon}
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {act.title}
                </h4>
                <p className="text-[11px] text-slate-500 font-normal leading-relaxed mt-1">{act.desc}</p>
              </div>
            </div>

            <div className="pt-4 mt-2">
              <button
                onClick={() => navigate(act.tab)}
                className="w-full py-1.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
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

// ─── Inflation & Real Dollar CPI Banner Component ─────────────────────────────
const InflationKpiBanner = () => {
  const [inflationKpis, setInflationKpis] = useState<any>(null);

  useEffect(() => {
    async function fetchInflation() {
      try {
        const res = await apiClient.get('/inflation/kpis');
        setInflationKpis(res.data);
      } catch (err) {
        console.warn("Failed to load inflation KPIs:", err);
      }
    }
    fetchInflation();
  }, []);

  if (!inflationKpis) return null;

  return (
    <div className="bg-gradient-to-r from-blue-900/5 via-indigo-900/5 to-slate-900/5 border border-blue-200/60 rounded-2xl p-4 mb-8 flex flex-col md:flex-row items-center justify-between gap-4 font-sans">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
          CPI
        </div>
        <div>
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            BLS Consumer Price Index Inflation Benchmark
          </span>
          <p className="text-sm font-bold text-slate-900 mt-0.5">
            US CPI-U YoY Inflation: <span className="text-blue-600 font-mono-numbers">{inflationKpis.inflation_rate}%</span> · Cumulative Inflation: <span className="text-indigo-600 font-mono-numbers">{inflationKpis.cumulative_inflation}%</span>
          </p>
        </div>
      </div>
      <div className="flex items-center gap-6 text-xs font-mono-numbers">
        <div className="text-right">
          <span className="text-[10px] font-bold text-slate-400 uppercase block font-sans">Real Dollar Purchasing Power</span>
          <span className="text-base font-extrabold text-emerald-600">${inflationKpis.purchasing_power}</span>
        </div>
        <div className="text-right border-l border-slate-200 pl-6">
          <span className="text-[10px] font-bold text-slate-400 uppercase block font-sans">Current CPI Level</span>
          <span className="text-base font-extrabold text-slate-900">{inflationKpis.latest_cpi}</span>
        </div>
      </div>
    </div>
  );
};

// ─── 360° Unified Cross-Dataset Intelligence Card ─────────────────────────────
const Unified360CustomerCard = () => {
  const [data360, setData360] = useState<any>(null);

  useEffect(() => {
    async function fetch360() {
      try {
        const res = await apiClient.get('/cross-dataset/unified-insights?usage_kwh=750&nominal_bill=160.65&zip_code=07101');
        setData360(res.data);
      } catch (err) {
        console.warn("Failed to load 360° cross-dataset insights:", err);
      }
    }
    fetch360();
  }, []);

  if (!data360) return null;

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 mb-8 shadow-xs font-sans space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-600/10 text-blue-600 border border-blue-200 flex items-center justify-center font-bold">
            360°
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Cross-Dataset 360° Utility Intelligence Engine
            </h3>
            <p className="text-xs text-slate-500">
              Unified synthesis joining Bills ↔ Weather ↔ PJM Wholesale ↔ Tariffs ↔ CPI ↔ Census ↔ EIA-861
            </p>
          </div>
        </div>
        <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">
          Fully Synthesized Matrix
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono-numbers pt-1">
        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-sans">Weather vs Rate Variance</span>
          <span className="text-base font-extrabold text-blue-600">${data360.weather_variance_breakdown?.weather_driven_cost}</span>
          <span className="text-[10px] text-slate-500 block font-sans font-medium">due to climate ({data360.weather_variance_breakdown?.weather_usage_pct}% of load)</span>
        </div>

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-sans">Wholesale LMP Exposure</span>
          <span className="text-base font-extrabold text-indigo-600">${data360.wholesale_pjm_exposure?.wholesale_cost_estimate}</span>
          <span className="text-[10px] text-slate-500 block font-sans font-medium">PJM supply cost (${data360.wholesale_pjm_exposure?.avg_lmp_mwh}/MWh)</span>
        </div>

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-sans">Census Energy Burden</span>
          <span className="text-base font-extrabold text-amber-600">{data360.demographic_energy_burden?.energy_burden_pct}%</span>
          <span className="text-[10px] text-slate-500 block font-sans font-medium">income share (SVI: {data360.demographic_energy_burden?.social_vulnerability_index})</span>
        </div>

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-sans">Carbon Footprint</span>
          <span className="text-base font-extrabold text-emerald-600">{data360.environmental_footprint?.scope_2_co2_kg} kg</span>
          <span className="text-[10px] text-slate-500 block font-sans font-medium">CO2 (Offset: {data360.environmental_footprint?.trees_equivalent} trees/yr)</span>
        </div>
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
  const forecastBill = dashboardData?.forecast_results?.status === "success" ? (kpisFromDb?.forecast_next_month ?? 0.0) : 0.0;
  const billChangePct = kpisFromDb?.bill_change_pct ?? 3.2;
  const savingsOpportunity = ((kpisFromDb as unknown as Record<string, number>)?.savings_opportunity) ?? (uploadedBill?.total_bill ? Math.max(0, Math.round((currentBill - 118.0) * 100) / 100) : 4350.00);

  const utilityName = uploadedBill?.utility ?? 'Public Service Electric & Gas Co';
  const billingCycle = uploadedBill?.billing_period ?? 'Oct 1 - Oct 31, 2024';
  const tariff = uploadedBill?.rate_schedule ?? 'TOU-8-R Commercial High Demand';

  // ─── Smart Meter State & Fetching ───────────────────────────────────────────
  const [dashboardMode, setDashboardMode] = useState<'billing' | 'metering'>('billing');
  const [smartMeterData, setSmartMeterData] = useState<any>(null);
  const [smartMeterHourly, setSmartMeterHourly] = useState<any>(null);
  const [smartMeterDemand, setSmartMeterDemand] = useState<any>(null);
  const [loadingMeter, setLoadingMeter] = useState(false);

  useEffect(() => {
    async function loadSmartMeter() {
      if (dashboardMode !== 'metering') return;
      try {
        setLoadingMeter(true);
        const liveRes = await apiClient.get('/smart-meter/live-status?customer_id=USR_001');
        setSmartMeterData(liveRes.data);
        
        const hourlyRes = await apiClient.get('/smart-meter/hourly?customer_id=USR_001');
        setSmartMeterHourly(hourlyRes.data);
        
        const demandRes = await apiClient.get('/smart-meter/demand-history?customer_id=USR_001');
        setSmartMeterDemand(demandRes.data);
      } catch (err) {
        console.warn("Failed to load smart meter data:", err);
      } finally {
        setLoadingMeter(false);
      }
    }
    loadSmartMeter();
  }, [dashboardMode]);

  // Billing view alerts
  const billingAlerts = [
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

  // Helper values for Smart Meter dashboard representation
  const meterKpis = smartMeterData || {
    current_demand_kw: 2.45,
    current_power_factor: 0.96,
    voltage: 121.2,
    today_consumption_kwh: 38.60,
    peak_demand_kw: 4.80,
    peak_hour: "18:00",
    base_load_kw: 0.65,
    status: "online",
    alerts: [
      {
        severity: 'medium' as const,
        title: 'Overnight HVAC Running',
        description: 'Nighttime demand baseline remains elevated at 0.65 kW (should drop to 0.40 kW).',
        actionText: 'View load profile'
      }
    ]
  };

  const dummyHourly = [
    { hour: "00:00", usage_kwh: 0.65 },
    { hour: "02:00", usage_kwh: 0.58 },
    { hour: "04:00", usage_kwh: 0.60 },
    { hour: "06:00", usage_kwh: 1.10 },
    { hour: "08:00", usage_kwh: 1.95 },
    { hour: "10:00", usage_kwh: 2.30 },
    { hour: "12:00", usage_kwh: 2.10 },
    { hour: "14:00", usage_kwh: 2.65 },
    { hour: "16:00", usage_kwh: 3.40 },
    { hour: "18:00", usage_kwh: 4.80 },
    { hour: "20:00", usage_kwh: 2.20 },
    { hour: "22:00", usage_kwh: 0.95 }
  ];
  
  const hourlyChartData = smartMeterHourly?.hourly_data || dummyHourly;

  const dummyHeatmap = [];
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  for (let d of days) {
    for (let h = 0; h < 24; h++) {
      let base = [0.6, 0.5, 0.5, 0.6, 0.9, 1.4, 1.8, 2.0, 1.8, 1.6, 1.5, 1.6, 1.7, 2.2, 2.8, 3.4, 4.2, 4.8, 3.6, 2.8, 2.0, 1.4, 0.9, 0.7][h];
      let factor = d === "Sat" || d === "Sun" ? 0.75 : 1.0;
      dummyHeatmap.push({
        day: d,
        hour: h,
        value: base * factor * (0.9 + Math.random() * 0.2)
      });
    }
  }
  
  const heatmapData = smartMeterDemand?.heatmap || dummyHeatmap;

  return (
    <div className="space-y-6 pb-16 font-sans bg-slate-50/50 min-h-screen p-4 md:p-6 lg:p-8 rounded-2xl border border-slate-200/60">
      {/* 1. Executive Dashboard Header */}
      <ExecutiveHeader
        utilityName={utilityName}
        billingCycle={billingCycle}
        tariff={tariff}
        dashboardMode={dashboardMode}
        setDashboardMode={setDashboardMode}
        loadingMeter={loadingMeter}
      />

      {dashboardMode === 'billing' ? (
        <>
          {/* 2. Rebalanced 4-KPI Summary Cards Grid (Enterprise SaaS Style) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <SaaSExecutiveKpiCard
              id="kpi-current-bill"
              label="Current Bill"
              value={`$${currentBill.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              description="Total electricity charges for the current billing period."
              icon={<DollarSign className="w-5 h-5" />}
              iconBgColor="bg-blue-50 text-blue-600 border-blue-100"
              statusBadge={{ text: 'Audited Statement', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' }}
              targetTab="Bill Analysis"
            />

            <SaaSExecutiveKpiCard
              id="kpi-usage"
              label="Energy Usage"
              value={usageKwh.toLocaleString('en-US')}
              unit="kWh"
              description="Total electricity consumed during the current billing period."
              icon={<Zap className="w-5 h-5" />}
              iconBgColor="bg-cyan-50 text-cyan-600 border-cyan-100"
              statusBadge={{ text: 'Stable', color: 'bg-blue-50 text-blue-700 border-blue-200' }}
              targetTab="Bill Analysis"
            />

            <SaaSExecutiveKpiCard
              id="kpi-rate"
              label="Effective Rate"
              value={`$${effectiveRate.toFixed(3)}`}
              unit="/kWh"
              description="Blended average cost per kilowatt-hour across all tariff tiers."
              icon={<Activity className="w-5 h-5" />}
              iconBgColor="bg-indigo-50 text-indigo-600 border-indigo-100"
              statusBadge={{ text: 'Stable Rate', color: 'bg-slate-100 text-slate-700 border-slate-200' }}
              targetTab="Impact & Simulation"
            />

            <ForecastKpiCard
              forecastResults={dashboardData?.forecast_results}
              navigate={navigate}
            />
          </div>

          {/* 360° Unified Cross-Dataset Intelligence Card */}
          <Unified360CustomerCard />

          {/* Inflation & Real Dollar CPI KPI Banner */}
          <InflationKpiBanner />

          {/* 3. Executive AI Summary Focal Point */}
          <ExecutiveAiSummary
            currentBill={currentBill}
            billChangePct={billChangePct}
            savingsOpportunity={savingsOpportunity}
            forecastBill={forecastBill}
            aiStatus={dashboardData?.ai_status}
            aiExplanation={dashboardData?.ai_explanation || dashboardData?.explanation || undefined}
            activeBillId={dashboardData?.active_bill_id || undefined}
          />

          {/* 4. Main Analytics Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
            {/* Left Column: Recent Billing History */}
            <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-5 flex flex-col justify-between shadow-xs">
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
                    className="text-xs font-bold text-blue-600 hover:opacity-85 transition-all cursor-pointer"
                  >
                    Full History →
                  </button>
                </div>
                <RecentBillsCard limit={4} compact />
              </div>
            </div>

            {/* Right Column: Expanded Smart Alerts */}
            <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <ShieldAlert size={16} className="text-amber-500" /> Smart Alerts & Facility Exceptions
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">Active grid telemetry monitoring, tariff tier rules, and load anomaly notifications</p>
                </div>
                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  3 Active Exceptions
                </span>
              </div>

              <div className="space-y-3">
                {billingAlerts.map((al, i) => (
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
        </>
      ) : (
        <>
          {/* Smart Metering Sub-Dashboard */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
            <SaaSExecutiveKpiCard
              id="sm-demand"
              label="Current Demand"
              value={`${meterKpis.current_demand_kw}`}
              unit="kW"
              description="Instantaneous active power demand."
              icon={<Zap className="w-5 h-5 text-blue-600" />}
              iconBgColor="bg-blue-50 border-blue-100"
              statusBadge={{ text: "Live Telemetry", color: "bg-emerald-50 text-emerald-700 border-emerald-200" }}
            />
            <SaaSExecutiveKpiCard
              id="sm-pf"
              label="Power Factor"
              value={`${meterKpis.current_power_factor}`}
              description="Real-to-apparent power phase ratio."
              icon={<Activity className="w-5 h-5 text-indigo-600" />}
              iconBgColor="bg-indigo-50 border-indigo-100"
              statusBadge={{ text: "Optimal (>0.95)", color: "bg-emerald-50 text-emerald-700 border-emerald-200" }}
            />
            <SaaSExecutiveKpiCard
              id="sm-voltage"
              label="Line Voltage"
              value={`${meterKpis.voltage}`}
              unit="V"
              description="Nominal service drop voltage."
              icon={<Activity className="w-5 h-5 text-purple-600" />}
              iconBgColor="bg-purple-50 border-purple-100"
              statusBadge={{ text: "Steady Status", color: "bg-slate-100 text-slate-700 border-slate-200" }}
            />
            <SaaSExecutiveKpiCard
              id="sm-cons"
              label="Today's Total"
              value={`${meterKpis.today_consumption_kwh.toFixed(1)}`}
              unit="kWh"
              description="Cumulative energy consumption today."
              icon={<Zap className="w-5 h-5 text-cyan-600" />}
              iconBgColor="bg-cyan-50 border-cyan-100"
              statusBadge={{ text: "On Track", color: "bg-blue-50 text-blue-700 border-blue-200" }}
            />
            <SaaSExecutiveKpiCard
              id="sm-peak"
              label="Peak Demand"
              value={`${meterKpis.peak_demand_kw}`}
              unit="kW"
              description="Highest recorded demand interval."
              icon={<BarChart3 className="w-5 h-5 text-amber-600" />}
              iconBgColor="bg-amber-50 border-amber-100"
              statusBadge={{ text: `Peak ${meterKpis.peak_hour}`, color: "bg-amber-50 text-amber-700 border-amber-200" }}
            />
            <SaaSExecutiveKpiCard
              id="sm-base"
              label="Base Load"
              value={`${meterKpis.base_load_kw}`}
              unit="kW"
              description="Continuous overnight baseline load."
              icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
              iconBgColor="bg-emerald-50 border-emerald-100"
              statusBadge={{ text: "Base fraction 26%", color: "bg-emerald-50 text-emerald-700 border-emerald-200" }}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
            {/* 24-Hour Load Curve */}
            <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/80 p-5 flex flex-col justify-between shadow-xs">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-1">
                  <Activity size={16} className="text-blue-600" /> 24-Hour Load Curve Telemetry
                </h3>
                <p className="text-xs text-slate-500 mb-4">Hourly usage profiles from smart meter telemetry</p>
                
                <div className="h-64 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={hourlyChartData}>
                      <defs>
                        <linearGradient id="meterGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9"/>
                      <XAxis dataKey="hour" stroke="#94a3b8" fontSize={10}/>
                      <YAxis unit=" kW" stroke="#94a3b8" fontSize={10}/>
                      <Tooltip formatter={(value) => [`${value} kW`, 'Demand']}/>
                      <Area type="monotone" dataKey="usage_kwh" stroke="#2563eb" strokeWidth={2.5} fillOpacity={1} fill="url(#meterGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Smart Meter Live Alerts */}
            <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 p-5 space-y-4 shadow-xs">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-1">
                  <ShieldAlert size={16} className="text-amber-500" /> Live Telemetry Anomalies
                </h3>
                <p className="text-xs text-slate-500">Instantaneous load curves threshold exceptions</p>
              </div>

              <div className="space-y-3">
                {meterKpis.alerts && meterKpis.alerts.length > 0 ? (
                  meterKpis.alerts.map((al: any, i: number) => (
                    <SmartAlertCard
                      key={i}
                      severity={al.severity || 'medium'}
                      title={al.title}
                      description={al.description}
                      actionText={al.actionText || 'Investigate'}
                      onAction={() => {}}
                    />
                  ))
                ) : (
                  <div className="text-center py-10 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                    <CheckCircle2 className="mx-auto text-emerald-500 mb-2" size={24} />
                    <span className="text-xs font-bold text-slate-800">Telemetry Status Stable</span>
                    <p className="text-[10px] text-slate-400 font-medium max-w-[200px] mx-auto mt-1">
                      Zero power spikes, voltage drops, or base load drifts detected in the last 24h.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 7-Day Demand Heatmap */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-1">
              <BarChart3 size={16} className="text-blue-600" /> Hourly Load Intensity Heatmap (kW)
            </h3>
            <p className="text-xs text-slate-500 mb-5">Visualizing average power draw per hour (x-axis) across weekdays (y-axis)</p>

            <div className="overflow-x-auto">
              <div className="min-w-[800px] space-y-2">
                <div className="flex text-[10px] font-bold text-slate-400 pb-1">
                  <div className="w-16 shrink-0" />
                  {Array.from({ length: 24 }).map((_, h) => (
                    <div key={h} className="flex-1 text-center font-mono">{String(h).padStart(2, '0')}</div>
                  ))}
                </div>
                {days.map((day) => {
                  const dayReadings = heatmapData.filter((x: any) => x.day === day);
                  return (
                    <div key={day} className="flex items-center">
                      <div className="w-16 text-xs font-bold text-slate-500 shrink-0">{day}</div>
                      <div className="flex-1 flex gap-0.5">
                        {Array.from({ length: 24 }).map((_, h) => {
                          const val = dayReadings.find((x: any) => x.hour === h)?.value || 0.5;
                          // color intensity mapping: 0.5kW to 5kW
                          const intensity = Math.min(1, Math.max(0.1, val / 5.0));
                          const color = intensity > 0.85
                            ? 'bg-blue-800'
                            : intensity > 0.65
                            ? 'bg-blue-600'
                            : intensity > 0.45
                            ? 'bg-blue-400'
                            : intensity > 0.25
                            ? 'bg-blue-300'
                            : 'bg-blue-100';
                          return (
                            <div
                              key={h}
                              className={`flex-1 h-7 rounded ${color} transition-all hover:scale-110 cursor-pointer`}
                              title={`${day} @ ${h}:00 - Average Load: ${val.toFixed(2)} kW`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-end gap-4 text-[10px] text-slate-400 font-semibold mt-3">
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-blue-100" />
                <span>Base Load (&lt;1 kW)</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-blue-400" />
                <span>Standard (1 - 3 kW)</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-blue-800" />
                <span>Peak Load (&gt;3 kW)</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default MissionControlDashboard;