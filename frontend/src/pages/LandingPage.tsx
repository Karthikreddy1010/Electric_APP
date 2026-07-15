import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion';
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import { 
  Sparkles, ArrowRight, Activity, Zap, FileText, Compass,
  Globe2, Cpu, CloudSun, MapPin
} from 'lucide-react';

import { ParticlesProvider } from '@tsparticles/react';

// ─── Floating Neon Particles ─────────────────────────────────────────────────
function InteractiveBackground() {
  const particlesInit = async (engine: any) => {
    await loadSlim(engine);
  };

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none bg-[#030712]" aria-hidden="true">
      <div className="absolute inset-0 pointer-events-auto">
        <ParticlesProvider init={particlesInit}>
          <Particles
            id="tsparticles"
            options={{
              background: { color: { value: "transparent" } },
              fpsLimit: 60,
              interactivity: {
                events: {
                  onHover: { enable: true, mode: "grab" },
                },
                modes: {
                  grab: { distance: 150, links: { opacity: 0.5 } },
                },
              },
              particles: {
                color: { value: ["#3b82f6", "#06b6d4", "#6366f1"] },
                links: {
                  color: "#ffffff",
                  distance: 150,
                  enable: true,
                  opacity: 0.1,
                  width: 1,
                },
                move: {
                  enable: true,
                  speed: 0.8,
                  direction: "none",
                  random: true,
                  straight: false,
                  outModes: { default: "bounce" },
                },
                number: { density: { enable: true }, value: 60 },
                opacity: { value: 0.3 },
                shape: { type: "circle" },
                size: { value: { min: 1, max: 3 } },
              },
              detectRetina: true,
            }}
          />
        </ParticlesProvider>
      </div>
      
      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
      
      {/* Massive Glowing Orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-blue-600/20 blur-[120px] mix-blend-screen animate-float-orb pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-teal-500/10 blur-[100px] mix-blend-screen animate-float-orb-alt pointer-events-none" style={{ animationDelay: '2s' }} />
      <div className="absolute top-[30%] left-[40%] w-[30vw] h-[30vw] rounded-full bg-indigo-500/10 blur-[90px] mix-blend-screen animate-float-orb pointer-events-none" style={{ animationDelay: '4s' }} />
    </div>
  );
}

// ─── Holographic Dashboard Preview ──────────────────────────────────────────
function HolographicDashboard() {
  const [power, setPower] = useState(42.5);
  useEffect(() => {
    const int = setInterval(() => setPower(p => Number((p + (Math.random() - 0.5)).toFixed(1))), 1000);
    return () => clearInterval(int);
  }, []);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [15, -15]), { damping: 40, stiffness: 150 });
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-15, 15]), { damping: 40, stiffness: 150 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    mouseX.set(x / rect.width - 0.5);
    mouseY.set(y / rect.height - 0.5);
  };
  
  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 1, delay: 0.7, type: 'spring', damping: 20 }}
      style={{ perspective: 1500 }}
      className="relative w-full max-w-4xl mx-auto mt-16 group cursor-crosshair z-20"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div style={{ rotateX, rotateY, transformStyle: "preserve-3d" }} className="w-full h-full relative">
        <div className="absolute inset-0 bg-gradient-to-t from-[#030712] via-transparent to-transparent z-20 top-1/2 pointer-events-none" style={{ transform: "translateZ(20px)" }} />
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-3xl overflow-hidden shadow-[0_0_50px_rgba(37,99,235,0.15)] relative z-10" style={{ transform: "translateZ(0px)" }}>
        
        {/* Header bar */}
        <div className="h-10 border-b border-white/10 flex items-center px-4 gap-2 bg-black/20">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
          </div>
          <div className="mx-auto flex items-center gap-2 px-3 py-1 bg-white/5 rounded-md border border-white/5 text-[10px] text-white/50 font-mono">
            <Globe2 size={12} /> app.electricai.dev/overview
          </div>
        </div>

        {/* Mock UI Body */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6 h-[400px]">
          {/* Left panel */}
          <div className="space-y-4">
            <div className="h-24 rounded-lg bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/20 p-4 flex flex-col justify-center">
              <span className="text-blue-400 text-[10px] font-bold uppercase tracking-wider">Live Load Forecast</span>
              <div className="text-3xl font-mono text-white flex items-baseline gap-1 mt-1">
                {power} <span className="text-sm text-white/40">kW</span>
              </div>
            </div>
            <div className="h-48 rounded-lg bg-white/[0.03] border border-white/5 p-4 space-y-3">
              <div className="h-3 w-1/3 bg-white/10 rounded-full" />
              <div className="space-y-2 mt-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-8 rounded bg-white/5 border border-white/5 flex items-center px-3 justify-between">
                    <div className="h-2 w-16 bg-white/20 rounded-full" />
                    <div className="h-2 w-8 bg-blue-500/50 rounded-full" />
                  </div>
                ))}
              </div>
            </div>
          </div>
          {/* Center Chart */}
          <div className="col-span-2 rounded-lg bg-white/[0.03] border border-white/5 p-4 flex flex-col relative overflow-hidden">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="text-white/80 font-semibold text-sm">Predictive Bill Simulation</h3>
                <p className="text-white/40 text-[10px] mt-1">Monte Carlo pathing using PJM market variants</p>
              </div>
              <div className="px-2 py-1 bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded text-[10px] font-bold flex items-center gap-1">
                <Activity size={10} /> Active
              </div>
            </div>
            
            {/* Abstract SVG Chart */}
            <svg className="w-full flex-1" viewBox="0 0 400 150" preserveAspectRatio="none">
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d="M0,150 L0,100 Q 50,120 100,80 T 200,60 T 300,90 T 400,30 L400,150 Z" fill="url(#chartGrad)" />
              <path d="M0,100 Q 50,120 100,80 T 200,60 T 300,90 T 400,30" fill="none" stroke="#3b82f6" strokeWidth="2" filter="drop-shadow(0 0 6px rgba(59,130,246,0.8))" />
              {/* Animated scanning line */}
              <motion.line 
                x1="0" y1="0" x2="0" y2="150" 
                stroke="#06b6d4" strokeWidth="1" strokeDasharray="4 4"
                animate={{ x1: [0, 400, 0], x2: [0, 400, 0] }}
                transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
              />
            </svg>
          </div>
        </div>
        </div>
      </motion.div>
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
      icon: <FileText size={24} className="text-blue-400" />
    },
    {
      title: 'Weather-Adjusted Forecasting',
      desc: 'Predict your next 6 months of bills based on 10-year localized historical climate data and household elasticity models.',
      icon: <CloudSun size={24} className="text-teal-400" />
    },
    {
      title: 'Real-time Market Telemetry',
      desc: 'Live PJM wholesale market ingestion mapped directly against your retail rate structure to calculate real markups.',
      icon: <Activity size={24} className="text-indigo-400" />
    },
    {
      title: 'BGS Plan Matcher',
      desc: 'Stop guessing. We filter every retail tariff against utility baseline auctions to prove mathematical savings paths.',
      icon: <Compass size={24} className="text-emerald-400" />
    },
    {
      title: 'Spatial Grid Insights',
      desc: 'Visualize rate disparities across state lines and utility service zones to understand your regional positioning.',
      icon: <MapPin size={24} className="text-amber-400" />
    },
    {
      title: 'What-If Simulation Engine',
      desc: 'Calculate the exact ROI of buying an EV or switching to a time-of-use (TOU) plan before making the leap.',
      icon: <Cpu size={24} className="text-rose-400" />
    }
  ];

  const heroText = "Decode your energy.";

  return (
    <div ref={containerRef} className="min-h-screen bg-[#030712] text-slate-300 font-sans selection:bg-blue-500/30 overflow-hidden relative">
      <InteractiveBackground />

      {/* ── Navbar ── */}
      <header className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${scrolled ? 'bg-[#030712]/80 backdrop-blur-xl border-b border-white/5 py-4' : 'bg-transparent py-6'}`}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] group-hover:shadow-[0_0_25px_rgba(59,130,246,0.8)] transition-all">
              <Zap size={16} className="fill-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">ElectricAI</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">Sign In</Link>
            <Link to="/signup" className="px-5 py-2.5 bg-white text-black text-sm font-bold rounded-full hover:bg-slate-200 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.2)]">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="relative pt-32 md:pt-48 pb-20 px-6 z-10 flex flex-col items-center text-center">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-semibold uppercase tracking-widest mb-8 shadow-[0_0_15px_rgba(59,130,246,0.2)]"
        >
          <Sparkles size={14} className="animate-pulse" /> Next-Gen Energy Intelligence
        </motion.div>

        <h1 className="text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tighter text-white max-w-5xl leading-[1.1]">
          <span className="inline-block relative">
            {heroText.split("").map((char, index) => (
              <motion.span
                key={index}
                initial={{ opacity: 0, y: 20, filter: 'blur(10px)' }}
                animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                transition={{ duration: 0.5, delay: index * 0.03, type: 'spring', damping: 15 }}
                className="inline-block"
              >
                {char === " " ? "\u00A0" : char}
              </motion.span>
            ))}
          </span>
          <br />
          <motion.span 
            initial={{ opacity: 0, y: 30, scale: 0.95, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
            className="inline-block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-teal-300 to-indigo-400 animate-shimmer" 
            style={{ backgroundSize: '200% auto' }}>
            Maximize your savings.
          </motion.span>
        </h1>

        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
          className="mt-6 text-lg md:text-xl text-slate-400 max-w-2xl font-medium leading-relaxed"
        >
          Stop paying the utility blindly. Our platform ingests your bill, models your usage against live wholesale markets, and finds mathematically proven cheaper rates.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
          className="flex flex-col sm:flex-row gap-4 mt-10"
        >
          <Link to="/signup" className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-full transition-all shadow-[0_0_30px_rgba(59,130,246,0.4)] flex items-center justify-center gap-2 group">
            Start Free Analysis
            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link to="/demo" className="px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold rounded-full transition-all flex items-center justify-center gap-2">
            <MonitorPlayIcon size={18} /> View Demo Workspace
          </Link>
        </motion.div>

        {/* Floating Dashboard Preview */}
        <HolographicDashboard />
      </section>

      {/* ── Features Grid ── */}
      <section className="relative py-32 px-6 z-10 border-t border-white/5 bg-black/40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight mb-4">A complete power grid in your browser.</h2>
            <p className="text-slate-400 max-w-2xl mx-auto text-lg">We don't just read your bill—we rebuild the math that created it.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, idx) => {
              const yOffset = useTransform(scrollYProgress, [0, 1], [0, -30 * (idx % 3)]);
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.7, delay: idx * 0.1, type: 'spring', damping: 20 }}
                  style={{ y: yOffset }}
                  className="group relative p-8 rounded-2xl bg-white/[0.02] border border-white/10 hover:bg-white/[0.04] transition-colors"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl pointer-events-none" />
                  <div className="w-12 h-12 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(255,255,255,0.05)] group-hover:scale-110 group-hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] transition-all duration-300">
                    {f.icon}
                  </div>
                  <h3 className="text-xl font-bold text-white mb-3">{f.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="relative py-32 px-6 z-10 overflow-hidden">
        <div className="absolute inset-0 bg-blue-600/10 blur-[100px] pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center border border-white/10 bg-white/[0.02] backdrop-blur-xl p-12 md:p-20 rounded-3xl shadow-2xl relative">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent rotate-45 pointer-events-none" />
          <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-6 relative z-10">
            Take control of your utility costs.
          </h2>
          <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto relative z-10">
            Join thousands of users who have optimized their energy footprint. Upload your first PDF bill in seconds. No credit card required.
          </p>
          <Link to="/signup" className="px-10 py-5 bg-white text-black text-lg font-bold rounded-full hover:bg-slate-200 transition-all shadow-[0_0_40px_rgba(255,255,255,0.3)] hover:scale-105 inline-flex items-center gap-2 relative z-10">
            Create Free Account <ArrowRight size={20} />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/10 bg-black/50 py-12 px-6 relative z-10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <Zap size={20} className="text-blue-500 fill-blue-500" />
            <span className="font-bold text-white text-lg tracking-tight">ElectricAI</span>
          </div>
          <div className="flex gap-8 text-sm text-slate-500 font-medium">
            <Link to="/demo" className="hover:text-white transition-colors">Demo</Link>
            <a href="#" className="hover:text-white transition-colors">Features</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
          </div>
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} ElectricAI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function MonitorPlayIcon({ size = 24, ...props }: React.SVGProps<SVGSVGElement> & { size?: number | string }) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="14" x="2" y="3" rx="2" />
      <line x1="8" x2="16" y1="21" y2="21" />
      <line x1="12" x2="12" y1="17" y2="21" />
      <polygon points="10 7 15 10 10 13 10 7" />
    </svg>
  );
}
