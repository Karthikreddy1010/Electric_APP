import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Zap, ArrowRight, Activity, TrendingUp,
  ChevronRight, Database
} from 'lucide-react';

// ─── Glowing Neon Background Gradient ─────────────────────────────────────────
function AmbientGlowBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none bg-[#09090B]" aria-hidden="true">
      {/* Grid pattern overlay */}
      <div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_85%)] opacity-20" 
      />
      {/* Left top purple/cyan ambient glow */}
      <div className="absolute -top-40 left-1/4 w-[600px] h-[500px] bg-purple-600/15 blur-[140px] rounded-full mix-blend-screen" />
      <div className="absolute top-20 left-1/3 w-[500px] h-[400px] bg-cyan-500/20 blur-[130px] rounded-full mix-blend-screen" />
      {/* Right hero blue ambient glow */}
      <div className="absolute top-10 right-10 w-[650px] h-[550px] bg-blue-600/15 blur-[150px] rounded-full mix-blend-screen" />
    </div>
  );
}

// ─── Hero Operational Dashboard Graphic ──────────────────────────────────────
function HeroDashboardGraphic() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
      className="relative w-full rounded-2xl border border-border-hairline bg-[#0E0E11]/90 backdrop-blur-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.8)] overflow-hidden ring-1 ring-white/10"
    >
      {/* Window bar */}
      <div className="h-10 border-b border-border-hairline bg-[#121214] px-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
          <span className="text-[11px] text-text-secondary font-mono ml-2">Energy Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-savings-green/10 text-savings-green border border-savings-green/20">
            Live Market Sync
          </span>
        </div>
      </div>

      {/* Content grid inside mock app */}
      <div className="p-5 space-y-4">
        {/* Navigation tabs */}
        <div className="flex gap-4 border-b border-border-hairline pb-2 text-[11px] font-semibold text-text-secondary font-mono">
          <span className="text-primary-blue border-b-2 border-primary-blue pb-2 -mb-2.5">Overview</span>
          <span>Bill Ingestion</span>
          <span>Monte Carlo Risk</span>
          <span>PJM Forecast</span>
        </div>

        {/* Real-time demand graph */}
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2 p-4 bg-[#141417] border border-border-hairline rounded-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider">Hourly Load Curves (kWh)</span>
              <span className="text-xs font-mono font-bold text-primary-blue">$0.1052/kWh</span>
            </div>
            {/* Chart SVG */}
            <div className="h-28 w-full relative">
              <svg className="w-full h-full" viewBox="0 0 300 80" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="heroGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path d="M0,80 L0,50 Q 40,20 80,60 T 160,30 T 240,45 T 300,10 L300,80 Z" fill="url(#heroGradient)" />
                <path d="M0,50 Q 40,20 80,60 T 160,30 T 240,45 T 300,10" fill="none" stroke="#3B82F6" strokeWidth="2" />
                <path d="M0,65 Q 40,40 80,70 T 160,50 T 240,60 T 300,30" fill="none" stroke="#06B6D4" strokeWidth="1.5" strokeDasharray="3 3" />
              </svg>
            </div>
          </div>

          {/* Right card */}
          <div className="p-4 bg-[#141417] border border-border-hairline rounded-xl flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Projected Monthly Savings</span>
              <div className="text-2xl font-bold font-mono text-savings-green mt-1">+$428.50</div>
              <span className="text-[10px] text-text-secondary">Optimal Tariff Routing</span>
            </div>
            <div className="w-full bg-savings-green/10 text-savings-green border border-savings-green/20 rounded p-2 text-center text-[10px] font-bold">
              99.2% Proven ROI
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Core Features Showcase Grid (Neon Cyan Accent Cards) ────────────────────
function NeonFeatureShowcase() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-6xl mx-auto">

      {/* Large Featured Left Card: Neural OCR */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="lg:col-span-6 p-7 rounded-2xl bg-[#0F1115] border-2 border-electric-cyan/40 shadow-[0_0_30px_rgba(6,182,212,0.15)] flex flex-col justify-between relative group overflow-hidden"
      >
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-white tracking-tight">Neural OCR</h3>
          <div className="w-7 h-7 rounded-full bg-electric-cyan/10 border border-electric-cyan/30 flex items-center justify-center text-electric-cyan group-hover:scale-110 transition-transform">
            <ChevronRight size={16} />
          </div>
        </div>

        {/* Mock Document Processing Animation */}
        <div className="my-4 p-5 bg-[#14171D] rounded-xl border border-border-hairline flex items-center gap-4 relative overflow-hidden">
          <div className="w-24 h-32 bg-white/5 rounded border border-white/10 p-2 flex flex-col justify-between shrink-0 shadow-md">
            <div className="w-8 h-2 bg-primary-blue/60 rounded" />
            <div className="space-y-1">
              <div className="w-full h-1 bg-white/20 rounded" />
              <div className="w-4/5 h-1 bg-white/20 rounded" />
              <div className="w-3/5 h-1 bg-white/20 rounded" />
            </div>
            <div className="w-full h-2 bg-savings-green/60 rounded" />
          </div>

          {/* Extraction Badges */}
          <div className="space-y-2 flex-1 text-[11px] font-mono">
            <div className="p-2 rounded bg-bg-surface border border-border-hairline flex justify-between">
              <span className="text-text-secondary">BGS Supply:</span>
              <span className="font-bold text-text-primary">$81.00</span>
            </div>
            <div className="p-2 rounded bg-bg-surface border border-border-hairline flex justify-between">
              <span className="text-text-secondary">Distribution:</span>
              <span className="font-bold text-text-primary">$41.25</span>
            </div>
            <div className="p-2 rounded bg-bg-surface border border-border-hairline flex justify-between">
              <span className="text-text-secondary">NJ Tax (6.625%):</span>
              <span className="font-bold text-primary-blue">$9.98</span>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-base font-bold text-white mb-1">Data Extraction</h4>
          <p className="text-xs text-text-secondary leading-relaxed">
            Parsing extraction of complex line-item vector components, grid tariffs, and mandatory sales taxes from any raw PDF bill uploads.
          </p>
        </div>
      </motion.div>

      {/* Right Column Stacked Cards */}
      <div className="lg:col-span-6 space-y-6 flex flex-col justify-between">

        {/* Forecast Trends Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="p-6 rounded-2xl bg-[#0F1115] border-2 border-electric-cyan/40 shadow-[0_0_30px_rgba(6,182,212,0.15)] flex flex-col justify-between group"
        >
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-base font-bold text-white">Forecast Trends</h3>
            <div className="w-6 h-6 rounded-full bg-electric-cyan/10 border border-electric-cyan/30 flex items-center justify-center text-electric-cyan group-hover:scale-110 transition-transform">
              <ChevronRight size={14} />
            </div>
          </div>

          <div className="h-24 w-full my-2">
            <svg className="w-full h-full" viewBox="0 0 240 60" preserveAspectRatio="none">
              <path d="M0,50 Q 30,20 60,40 T 120,15 T 180,35 T 240,10" fill="none" stroke="#3B82F6" strokeWidth="2" />
              <path d="M0,40 Q 30,55 60,25 T 120,40 T 180,20 T 240,30" fill="none" stroke="#06B6D4" strokeWidth="1.5" />
            </svg>
          </div>
        </motion.div>

        {/* 2-Column Bottom Cards: Market Data & Savings ROI */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Market Data Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="p-5 rounded-2xl bg-[#0F1115] border-2 border-electric-cyan/40 shadow-[0_0_30px_rgba(6,182,212,0.15)] flex flex-col justify-between group"
          >
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-bold text-white">Market Data</h3>
              <div className="w-5 h-5 rounded-full bg-electric-cyan/10 border border-electric-cyan/30 flex items-center justify-center text-electric-cyan group-hover:scale-110 transition-transform">
                <ChevronRight size={12} />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 my-2 text-center">
              <div className="p-2 rounded bg-[#14171D] border border-border-hairline flex flex-col items-center">
                <Database size={14} className="text-primary-blue mb-1" />
                <span className="text-[9px] text-text-secondary">Grid Data</span>
              </div>
              <div className="p-2 rounded bg-[#14171D] border border-border-hairline flex flex-col items-center">
                <Activity size={14} className="text-electric-cyan mb-1" />
                <span className="text-[9px] text-text-secondary">Real LMPs</span>
              </div>
              <div className="p-2 rounded bg-[#14171D] border border-border-hairline flex flex-col items-center">
                <TrendingUp size={14} className="text-savings-green mb-1" />
                <span className="text-[9px] text-text-secondary">Market Data</span>
              </div>
            </div>
          </motion.div>

          {/* Savings ROI Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="p-5 rounded-2xl bg-[#0F1115] border-2 border-electric-cyan/40 shadow-[0_0_30px_rgba(6,182,212,0.15)] flex flex-col items-center justify-between text-center group"
          >
            <div className="w-full flex justify-between items-center mb-1">
              <h3 className="text-sm font-bold text-white">Savings ROI</h3>
              <div className="w-5 h-5 rounded-full bg-electric-cyan/10 border border-electric-cyan/30 flex items-center justify-center text-electric-cyan group-hover:scale-110 transition-transform">
                <ChevronRight size={12} />
              </div>
            </div>

            {/* Radial ROI graphic */}
            <div className="relative w-16 h-16 flex items-center justify-center my-1">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-white/10" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="text-electric-cyan" strokeDasharray="50, 100" strokeWidth="3.5" strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span className="absolute font-mono font-bold text-sm text-white">50%</span>
            </div>

            <span className="text-[10px] text-text-secondary font-medium">Confirmed Savings ROI</span>
          </motion.div>

        </div>

      </div>

    </div>
  );
}

// ─── Trusted By Sponsor Logos Strip ──────────────────────────────────────────
function TrustedByStrip() {
  const sponsors = ['GridSync', 'PowerLink', 'EnergyFlow', 'Wattsource', 'CurrentEra', 'UtilityPrime'];

  return (
    <div className="py-12 border-t border-border-hairline bg-[#0B0D10] text-center">
      <span className="text-[11px] font-bold uppercase tracking-widest text-text-secondary block mb-6">Trusted By Enterprise Utilities</span>
      <div className="flex flex-wrap items-center justify-center gap-8 md:gap-14 max-w-5xl mx-auto px-6 opacity-60">
        {sponsors.map((name, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm font-semibold tracking-tight text-white/70 hover:opacity-100 transition-opacity cursor-pointer">
            <Zap size={14} className="text-primary-blue" />
            <span>{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Landing Page Component Main ──────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090B] text-text-primary font-sans selection:bg-primary-blue/30 overflow-x-hidden relative">
      <AmbientGlowBackground />

      {/* ── Navbar ── */}
      <header className="fixed top-0 left-0 w-full z-50 bg-[#09090B]/80 backdrop-blur-xl border-b border-border-hairline py-4 px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-primary-blue/10 border border-primary-blue/30 flex items-center justify-center text-primary-blue group-hover:border-primary-blue transition-colors">
              <Zap size={16} className="fill-primary-blue" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white font-sans">Electric.AI</span>
          </Link>

          {/* Middle Nav */}
          <nav className="hidden md:flex items-center gap-8 text-xs font-semibold text-text-secondary">
            <a href="#product" className="hover:text-white transition-colors">Product</a>
            <a href="#solutions" className="hover:text-white transition-colors">Solutions</a>
            <a href="#customers" className="hover:text-white transition-colors">Customers</a>
            <a href="#resources" className="hover:text-white transition-colors">Resources</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </nav>

          {/* Right Action buttons */}
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-xs font-semibold text-text-secondary hover:text-white transition-colors">
              Sign in
            </Link>
            <Link to="/signup" className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold px-4 py-2 rounded-lg text-xs transition-all shadow-md shadow-primary-blue/20 active:scale-[0.98]">
              Request Demo
            </Link>
          </div>

        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="relative pt-32 md:pt-40 pb-20 px-6 max-w-7xl mx-auto z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

          {/* Left Headline & Copy */}
          <div className="lg:col-span-6 space-y-6">
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.08]"
            >
              Decode your energy. <br />
              <span className="text-text-primary">Maximize savings.</span>
            </motion.h1>

            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-sm md:text-base text-text-secondary font-medium leading-relaxed max-w-xl"
            >
              Enterprise AI electricity intelligence platform for utility analytics. Stop paying blindly. Our platform ingests your data, models usage against live markets, and delivers proven savings.
            </motion.p>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex items-center gap-4 pt-2"
            >
              <Link to="/signup" className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold px-6 py-3 rounded-lg text-xs transition-all shadow-lg shadow-primary-blue/30 active:scale-[0.98] flex items-center gap-2">
                Request Demo <ArrowRight size={14} />
              </Link>
              <Link to="/overview" className="bg-[#18181B] hover:bg-[#27272A] text-text-primary border border-border-hairline px-6 py-3 rounded-lg text-xs font-semibold transition-all">
                Explore Platform
              </Link>
            </motion.div>
          </div>

          {/* Right Hero Dashboard Preview */}
          <div className="lg:col-span-6">
            <HeroDashboardGraphic />
          </div>

        </div>
      </section>

      {/* ── Feature Cards Section ── */}
      <section className="py-20 px-6 relative z-10 border-t border-border-hairline">
        <NeonFeatureShowcase />
      </section>

      {/* ── Trusted By Sponsor Logos ── */}
      <TrustedByStrip />

      {/* ── Footer ── */}
      <footer className="border-t border-border-hairline bg-[#09090B] py-8 px-6 relative z-10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-medium text-text-secondary">
          <div className="flex items-center gap-6">
            <Link to="/overview" className="hover:text-white transition-colors">Demo</Link>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#privacy" className="hover:text-white transition-colors">Privacy</a>
            <a href="#terms" className="hover:text-white transition-colors">Terms</a>
          </div>
          <div>
            © 2026 ElectricAI. All rights reserved.
          </div>
        </div>
      </footer>

    </div>
  );
}
