import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { 
  ArrowRight, Activity, Zap, FileText, Compass,
  Globe2, Cpu, CloudSun, MapPin, MonitorPlay, BarChart3, ShieldCheck
} from 'lucide-react';

// ─── Subtle Dev-Tools Grid Background ──────────────────────────────────────────
function DevGridBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none bg-[#09090b]" aria-hidden="true">
      {/* Subtle Grid Pattern */}
      <div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#27272a_1px,transparent_1px),linear-gradient(to_bottom,#27272a_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)] opacity-30" 
      />
      {/* Top subtle glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[300px] bg-blue-500/10 blur-[100px] mix-blend-screen pointer-events-none rounded-[100%]" />
    </div>
  );
}

// ─── Clean Dashboard Mockup ────────────────────────────────────────────────
function MinimalDashboardPreview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
      className="relative w-full max-w-4xl mx-auto mt-16 z-20"
    >
      <div className="rounded-xl border border-[#27272a] bg-[#121214]/80 backdrop-blur-xl shadow-2xl overflow-hidden ring-1 ring-white/5">
        
        {/* Header bar */}
        <div className="h-12 border-b border-[#27272a] flex items-center px-4 gap-4 bg-[#09090b]/50">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ef4444]" />
            <div className="w-3 h-3 rounded-full bg-[#f59e0b]" />
            <div className="w-3 h-3 rounded-full bg-[#10b981]" />
          </div>
          <div className="flex-1 flex justify-center">
            <div className="flex items-center gap-2 px-3 py-1 bg-[#18181b] rounded-md border border-[#27272a] text-xs text-[#a1a1aa] font-mono">
              <Globe2 size={12} /> app.electricai.dev
            </div>
          </div>
          <div className="w-[42px]" /> {/* spacer */}
        </div>

        {/* Mock UI Body */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-6 min-h-[360px]">
          {/* Sidebar */}
          <div className="space-y-4 col-span-1 hidden md:block border-r border-[#27272a] pr-4">
            <div className="space-y-1">
              {['Overview', 'Analysis', 'Simulation', 'Forecast'].map((item, i) => (
                <div key={i} className={`px-3 py-2 rounded-md text-sm font-medium ${i === 0 ? 'bg-[#18181b] text-white border border-[#27272a]' : 'text-[#a1a1aa] hover:text-white'}`}>
                  {item}
                </div>
              ))}
            </div>
          </div>
          
          {/* Main Content */}
          <div className="col-span-3 space-y-6">
            <div className="flex justify-between items-end">
              <div>
                <h3 className="text-white font-semibold text-lg tracking-tight">Predictive Simulation</h3>
                <p className="text-[#a1a1aa] text-sm mt-1">Monte Carlo pathing via PJM variants</p>
              </div>
              <div className="px-2 py-1 bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/20 rounded text-xs font-bold flex items-center gap-1">
                <Activity size={12} /> Live Sync
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-[#18181b] border border-[#27272a]">
                <div className="text-xs text-[#a1a1aa] uppercase tracking-wider mb-1 font-semibold">Load Forecast</div>
                <div className="text-2xl font-mono text-white">42.5<span className="text-sm text-[#a1a1aa] ml-1">kW</span></div>
              </div>
              <div className="p-4 rounded-lg bg-[#18181b] border border-[#27272a]">
                <div className="text-xs text-[#a1a1aa] uppercase tracking-wider mb-1 font-semibold">Variance</div>
                <div className="text-2xl font-mono text-[#3b82f6]">-4.2%</div>
              </div>
              <div className="p-4 rounded-lg bg-[#18181b] border border-[#27272a]">
                <div className="text-xs text-[#a1a1aa] uppercase tracking-wider mb-1 font-semibold">Confidence</div>
                <div className="text-2xl font-mono text-[#10b981]">98.1%</div>
              </div>
            </div>

            {/* Abstract SVG Chart */}
            <div className="h-40 w-full bg-[#18181b] border border-[#27272a] rounded-lg p-4 relative overflow-hidden flex items-end">
              <svg className="w-full h-full" viewBox="0 0 400 100" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M0,100 L0,60 Q 50,70 100,40 T 200,30 T 300,50 T 400,10 L400,100 Z" fill="url(#chartGrad)" />
                <path d="M0,60 Q 50,70 100,40 T 200,30 T 300,50 T 400,10" fill="none" stroke="#3b82f6" strokeWidth="2" />
                <line x1="250" y1="0" x2="250" y2="100" stroke="#a1a1aa" strokeWidth="1" strokeDasharray="4 4" className="opacity-30" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}


// ─── Landing Page Main ────────────────────────────────────────────────────────
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const features = [
    {
      title: 'Neural Bill OCR',
      desc: 'Instant extraction of complex delivery items, public service adjustments, and hidden grid taxes from raw PDF uploads.',
      icon: <FileText size={20} className="text-[#3b82f6]" />
    },
    {
      title: 'Weather-Adjusted Forecasting',
      desc: 'Predict your next 6 months of bills based on 10-year localized historical climate data and household elasticity models.',
      icon: <CloudSun size={20} className="text-[#a1a1aa]" />
    },
    {
      title: 'Real-time Market Telemetry',
      desc: 'Live PJM wholesale market ingestion mapped directly against your retail rate structure to calculate real markups.',
      icon: <Activity size={20} className="text-[#3b82f6]" />
    },
    {
      title: 'BGS Plan Matcher',
      desc: 'Stop guessing. We filter every retail tariff against utility baseline auctions to prove mathematical savings paths.',
      icon: <Compass size={20} className="text-[#a1a1aa]" />
    },
    {
      title: 'Spatial Grid Insights',
      desc: 'Visualize rate disparities across state lines and utility service zones to understand your regional positioning.',
      icon: <MapPin size={20} className="text-[#a1a1aa]" />
    },
    {
      title: 'What-If Simulation Engine',
      desc: 'Calculate the exact ROI of buying an EV or switching to a time-of-use (TOU) plan before making the leap.',
      icon: <Cpu size={20} className="text-[#3b82f6]" />
    }
  ];

  return (
    <div ref={containerRef} className="min-h-screen bg-[#09090b] text-[#fafafa] font-sans selection:bg-[#3b82f6]/30 overflow-hidden relative">
      <DevGridBackground />

      {/* ── Navbar ── */}
      <header className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${scrolled ? 'bg-[#09090b]/80 backdrop-blur-xl border-b border-[#27272a] py-3' : 'bg-transparent py-5'}`}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-7 h-7 rounded-[6px] bg-[#18181b] border border-[#27272a] flex items-center justify-center font-bold text-white group-hover:border-[#3b82f6] transition-colors">
              <Zap size={14} className="fill-[#3b82f6] text-[#3b82f6]" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">ElectricAI</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link to="/login" className="text-sm font-medium text-[#a1a1aa] hover:text-white transition-colors">Sign In</Link>
            <Link to="/signup" className="px-4 py-2 bg-white text-black text-sm font-semibold rounded-md hover:bg-[#e4e4e7] transition-colors shadow-sm">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="relative pt-32 md:pt-44 pb-20 px-6 z-10 flex flex-col items-center text-center">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#27272a] bg-[#18181b]/50 text-[#a1a1aa] text-[11px] font-semibold uppercase tracking-wider mb-8"
        >
          <ShieldCheck size={14} className="text-[#3b82f6]" /> Next-Gen Energy Intelligence
        </motion.div>

        <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tighter text-white max-w-5xl leading-[1.05]">
          Decode your energy. <br />
          <span className="text-[#a1a1aa]">Maximize savings.</span>
        </h1>

        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
          className="mt-6 text-lg md:text-xl text-[#a1a1aa] max-w-2xl font-medium leading-relaxed"
        >
          Stop paying the utility blindly. Our platform ingests your bill, models your usage against live wholesale markets, and finds mathematically proven cheaper rates.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
          className="flex flex-col sm:flex-row gap-4 mt-10"
        >
          <Link to="/signup" className="px-6 py-3 bg-white text-black font-semibold rounded-md transition-all hover:bg-[#e4e4e7] flex items-center justify-center gap-2">
            Start Free Analysis
            <ArrowRight size={16} />
          </Link>
          <Link to="/demo" className="px-6 py-3 bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-white font-semibold rounded-md transition-all flex items-center justify-center gap-2">
            <MonitorPlay size={16} /> View Demo Workspace
          </Link>
        </motion.div>

        {/* Minimal Dashboard Preview */}
        <MinimalDashboardPreview />
      </section>

      {/* ── Features Grid ── */}
      <section className="relative py-24 px-6 z-10 border-t border-[#27272a] bg-[#09090b]">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-white tracking-tight mb-4">A complete power grid in your browser.</h2>
            <p className="text-[#a1a1aa] max-w-2xl text-lg">We don't just read your bill—we rebuild the math that created it.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, idx) => {
              const yOffset = useTransform(scrollYProgress, [0, 1], [0, -20 * (idx % 3)]);
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.5, delay: idx * 0.1 }}
                  style={{ y: yOffset }}
                  className="p-6 rounded-xl bg-[#121214] border border-[#27272a] hover:border-[#3b82f6]/50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-5">
                    {f.icon}
                  </div>
                  <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
                  <p className="text-[#a1a1aa] text-sm leading-relaxed">{f.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="relative py-24 px-6 z-10 border-t border-[#27272a] bg-[#09090b]">
        <div className="max-w-3xl mx-auto text-center">
          <BarChart3 size={32} className="mx-auto text-[#a1a1aa] mb-6" />
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
            Take control of your utility costs.
          </h2>
          <p className="text-[#a1a1aa] text-lg mb-8 max-w-xl mx-auto">
            Join users who have optimized their energy footprint. Upload your first PDF bill in seconds. No credit card required.
          </p>
          <Link to="/signup" className="px-8 py-3 bg-white text-black text-sm font-semibold rounded-md hover:bg-[#e4e4e7] transition-all inline-flex items-center gap-2">
            Create Free Account <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[#27272a] bg-[#09090b] py-8 px-6 relative z-10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-[#a1a1aa]" />
            <span className="font-semibold text-[#a1a1aa] text-sm tracking-tight">ElectricAI</span>
          </div>
          <div className="flex gap-6 text-sm text-[#71717a] font-medium">
            <Link to="/demo" className="hover:text-white transition-colors">Demo</Link>
            <a href="#" className="hover:text-white transition-colors">Features</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
          </div>
          <p className="text-[#71717a] text-xs">© {new Date().getFullYear()} ElectricAI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
