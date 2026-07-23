import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { 
  Sparkles, ArrowRight, Activity, Zap, FileText, Compass,
  Cpu, CloudSun, MapPin
} from 'lucide-react';

// ─── Aurora-Inspired Electric Particle Canvas ─────────────────────────────────
// Replaces @tsparticles with a lightweight GPU-accelerated canvas engine
// Architecture: requestAnimationFrame loop + sinusoidal interpolation
// All animation uses transform/opacity only — zero layout thrashing

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  pulseSpeed: number;
  pulseOffset: number;
  color: string;
}

interface NetworkNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
}

function useElectricCanvas(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  const particlesRef = useRef<Particle[]>([]);
  const nodesRef = useRef<NetworkNode[]>([]);
  const animationRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  const initParticles = useCallback((width: number, height: number) => {
    const colors = ['#00D4FF', '#2EF2D4', '#4CC9F0', '#00D4FF80', '#2EF2D480'];
    
    // Floating electric particles
    particlesRef.current = Array.from({ length: 35 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.2,
      size: Math.random() * 2.5 + 0.5,
      opacity: Math.random() * 0.4 + 0.1,
      pulseSpeed: Math.random() * 0.002 + 0.001,
      pulseOffset: Math.random() * Math.PI * 2,
      color: colors[Math.floor(Math.random() * colors.length)],
    }));

    // Network nodes (larger, slower, with connecting lines)
    nodesRef.current = Array.from({ length: 12 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.15,
      vy: (Math.random() - 0.5) * 0.1,
      size: Math.random() * 3 + 2,
      opacity: Math.random() * 0.25 + 0.08,
    }));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      initParticles(rect.width, rect.height);
    };

    resize();
    let resizeTimer: ReturnType<typeof setTimeout>;
    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 150);
    };
    window.addEventListener('resize', handleResize);

    const animate = () => {
      timeRef.current += 0.016; // ~60fps timestep
      const { width, height } = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, width, height);

      // Draw network connections first (behind particles)
      const nodes = nodesRef.current;
      const connectionDist = 200;
      ctx.lineWidth = 0.5;

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < connectionDist) {
            const alpha = (1 - dist / connectionDist) * 0.08;
            ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Update and draw network nodes
      for (const node of nodes) {
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        const pulse = Math.sin(timeRef.current * 0.5 + node.x * 0.01) * 0.1;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 212, 255, ${node.opacity + pulse})`;
        ctx.fill();

        // Soft glow
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.size * 3, 0, Math.PI * 2);
        const grd = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, node.size * 3
        );
        grd.addColorStop(0, `rgba(0, 212, 255, ${(node.opacity + pulse) * 0.3})`);
        grd.addColorStop(1, 'rgba(0, 212, 255, 0)');
        ctx.fillStyle = grd;
        ctx.fill();
      }

      // Update and draw floating electric particles
      for (const p of particlesRef.current) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        const pulse = Math.sin(timeRef.current * p.pulseSpeed * 100 + p.pulseOffset);
        const currentOpacity = p.opacity + pulse * 0.15;

        // Particle core
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(/[\d.]+\)$/, `${Math.max(0, currentOpacity)})`).includes('rgba')
          ? p.color
          : p.color;
        ctx.globalAlpha = Math.max(0, currentOpacity);
        ctx.fill();

        // Particle glow
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 4, 0, Math.PI * 2);
        const pgrd = ctx.createRadialGradient(
          p.x, p.y, 0,
          p.x, p.y, p.size * 4
        );
        pgrd.addColorStop(0, `rgba(0, 212, 255, ${Math.max(0, currentOpacity * 0.15)})`);
        pgrd.addColorStop(1, 'rgba(0, 212, 255, 0)');
        ctx.fillStyle = pgrd;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Soft energy flow wave
      const waveY = height * 0.6;
      ctx.beginPath();
      ctx.moveTo(0, waveY);
      for (let x = 0; x <= width; x += 4) {
        const y = waveY + Math.sin((x * 0.003) + timeRef.current * 0.3) * 30
                        + Math.sin((x * 0.007) + timeRef.current * 0.15) * 15;
        ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(0, 212, 255, 0.03)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimer);
    };
  }, [canvasRef, initParticles]);
}


// ─── Aurora Hero Background System ───────────────────────────────────────────
// 6-layer cinematic background inspired by Aurora Hero architecture:
// L0: Deep navy base  |  L1: Hero image  |  L2: Dark overlay
// L3: Directional gradient  |  L4: Vignette  |  L5: Canvas particles
// L6: Atmospheric glow orbs  |  L7: Light ray sweep

function AuroraHeroBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  useElectricCanvas(canvasRef);

  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* L0 — Deep Navy Base */}
      <div className="absolute inset-0 bg-[#07111F]" />

      {/* L1 — Hero Image (lazy-loaded) */}
      <img
        src={`${import.meta.env.BASE_URL}hero-bg.png`}
        alt=""
        loading="lazy"
        onLoad={() => setImageLoaded(true)}
        className={`absolute inset-0 w-full h-full object-cover object-center transition-opacity duration-1000 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
        style={{ willChange: 'opacity' }}
      />

      {/* L2 — Dark Navy Overlay */}
      <div
        className="absolute inset-0"
        style={{ backgroundColor: 'rgba(5, 12, 24, 0.55)' }}
      />

      {/* L3 — Left-to-Right Directional Gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(to right, rgba(5,12,24,0.68), rgba(5,12,24,0.25))',
        }}
      />

      {/* L4 — Soft Vignette */}
      <div className="absolute inset-0 hero-vignette" />

      {/* L5 — Electric Particle Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ mixBlendMode: 'screen' }}
      />

      {/* L6 — Atmospheric Glow Orbs */}
      <div
        className="absolute top-[-15%] left-[-8%] w-[45vw] h-[45vw] rounded-full animate-aurora-drift pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />
      <div
        className="absolute bottom-[-10%] right-[-5%] w-[35vw] h-[35vw] rounded-full animate-aurora-drift-alt pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(46,242,212,0.08) 0%, transparent 70%)',
          filter: 'blur(60px)',
          animationDelay: '3s',
        }}
      />
      <div
        className="absolute top-[25%] right-[15%] w-[25vw] h-[25vw] rounded-full animate-electric-pulse pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(76,201,240,0.06) 0%, transparent 70%)',
          filter: 'blur(50px)',
          animationDelay: '6s',
        }}
      />

      {/* L7 — Sweeping Light Ray */}
      <div
        className="absolute inset-0 animate-light-ray pointer-events-none"
        style={{
          background: 'linear-gradient(105deg, transparent 40%, rgba(0,212,255,0.04) 50%, transparent 60%)',
          width: '100%',
          height: '100%',
        }}
      />

      {/* L8 — Bottom Fade Blend */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, transparent 60%, #07111F 100%)',
        }}
      />
    </div>
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
      icon: <FileText size={24} className="text-[#00D4FF]" />
    },
    {
      title: 'Weather-Adjusted Forecasting',
      desc: 'Predict your next 6 months of bills based on 10-year localized historical climate data and household elasticity models.',
      icon: <CloudSun size={24} className="text-[#2EF2D4]" />
    },
    {
      title: 'Real-time Market Telemetry',
      desc: 'Live PJM wholesale market ingestion mapped directly against your retail rate structure to calculate real markups.',
      icon: <Activity size={24} className="text-[#4CC9F0]" />
    },
    {
      title: 'BGS Plan Matcher',
      desc: 'Stop guessing. We filter every retail tariff against utility baseline auctions to prove mathematical savings paths.',
      icon: <Compass size={24} className="text-[#2EF2D4]" />
    },
    {
      title: 'Spatial Grid Insights',
      desc: 'Visualize rate disparities across state lines and utility service zones to understand your regional positioning.',
      icon: <MapPin size={24} className="text-[#00D4FF]" />
    },
    {
      title: 'What-If Simulation Engine',
      desc: 'Calculate the exact ROI of buying an EV or switching to a time-of-use (TOU) plan before making the leap.',
      icon: <Cpu size={24} className="text-[#4CC9F0]" />
    }
  ];

  const heroText = "Decode your energy.";

  return (
    <div ref={containerRef} className="min-h-screen bg-[#07111F] text-slate-300 font-sans selection:bg-[#00D4FF]/20 overflow-hidden relative">
      {/* ── Premium Navbar ── */}
      <header
        className={`fixed top-0 left-0 w-full z-50 transition-all duration-500 ease-out ${
          scrolled
            ? 'py-3'
            : 'bg-transparent py-6'
        }`}
      >
        <div
          className={`max-w-7xl mx-auto px-6 flex items-center justify-between transition-all duration-500 ${
            scrolled
              ? 'mx-4 lg:mx-auto rounded-2xl py-3 px-6'
              : ''
          }`}
          style={scrolled ? {
            background: 'rgba(7, 17, 31, 0.75)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          } : {}}
        >
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#00D4FF] to-[#4CC9F0] flex items-center justify-center font-bold text-white shadow-[0_0_20px_rgba(0,212,255,0.4)] group-hover:shadow-[0_0_30px_rgba(0,212,255,0.6)] transition-all duration-300">
              <Zap size={18} className="fill-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">ElectricAI</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-sm font-semibold text-[#B7C2D0] hover:text-white transition-colors duration-200">Sign In</Link>
            <Link
              to="/signup"
              className="px-5 py-2.5 text-sm font-bold rounded-full transition-all duration-300 hero-btn-glow"
              style={{
                background: 'linear-gradient(135deg, rgba(0,212,255,0.15), rgba(76,201,240,0.1))',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(0,212,255,0.3)',
                color: '#ffffff',
                boxShadow: '0 0 20px rgba(0,212,255,0.15)',
              }}
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-32 pb-24 px-6 overflow-hidden text-center">
        <AuroraHeroBackground />

        {/* Badge */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-[#00D4FF] text-xs font-semibold uppercase tracking-widest mb-10 animate-glow-pulse"
          style={{
            background: 'rgba(0, 212, 255, 0.08)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(0, 212, 255, 0.2)',
          }}
        >
          <Sparkles size={14} className="animate-pulse" /> Next-Gen Energy Intelligence
        </motion.div>

        {/* Heading */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-[84px] font-extrabold tracking-tighter text-white max-w-5xl leading-[1.05]">
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
            className="inline-block text-transparent bg-clip-text bg-gradient-to-r from-[#00D4FF] via-[#2EF2D4] to-[#4CC9F0] animate-shimmer" 
            style={{ backgroundSize: '200% auto' }}>
            Maximize your savings.
          </motion.span>
        </h1>

        {/* Description */}
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
          className="mt-8 text-lg md:text-xl text-[#B7C2D0] max-w-2xl font-medium leading-relaxed"
        >
          Stop paying the utility blindly. Our platform ingests your bill, models your usage against live wholesale markets, and finds mathematically proven cheaper rates.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
          className="flex flex-col sm:flex-row gap-4 mt-12"
        >
          <Link
            to="/signup"
            className="px-8 py-4 text-white font-bold rounded-full transition-all duration-300 flex items-center justify-center gap-2 group hero-btn-glow"
            style={{
              background: 'linear-gradient(135deg, #00D4FF, #4CC9F0)',
              boxShadow: '0 0 30px rgba(0,212,255,0.3), 0 4px 20px rgba(0,0,0,0.3)',
            }}
          >
            Start Free Analysis
            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            to="/demo"
            className="px-8 py-4 text-white font-bold rounded-full transition-all duration-300 flex items-center justify-center gap-2 hero-btn-glow"
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              backdropFilter: 'blur(16px)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
            }}
          >
            <MonitorPlayIcon size={18} /> View Demo Workspace
          </Link>
        </motion.div>
      </section>

      {/* ── Features Grid ── */}
      <section className="relative py-32 px-6 z-10 border-t border-white/5" style={{ background: 'linear-gradient(180deg, rgba(7,17,31,0.95), #07111F)' }}>
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 pointer-events-none opacity-30" style={{ backgroundImage: 'linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />
        
        <div className="max-w-7xl mx-auto relative">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight mb-4">A complete power grid in your browser.</h2>
            <p className="text-[#B7C2D0] max-w-2xl mx-auto text-lg">We don't just read your bill—we rebuild the math that created it.</p>
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
                  className="group relative p-8 rounded-2xl transition-all duration-300 hover:-translate-y-1"
                  onMouseEnter={(e) => {
                    const el = e.currentTarget;
                    el.style.background = 'rgba(255, 255, 255, 0.05)';
                    el.style.borderColor = 'rgba(0, 212, 255, 0.2)';
                    el.style.boxShadow = '0 0 30px rgba(0, 212, 255, 0.08), 0 8px 25px rgba(0, 0, 0, 0.2)';
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget;
                    el.style.background = 'rgba(255, 255, 255, 0.02)';
                    el.style.borderColor = 'rgba(255, 255, 255, 0.06)';
                    el.style.boxShadow = 'none';
                  }}
                >
                  <div
                    className="absolute inset-0 rounded-2xl pointer-events-none"
                    style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      backdropFilter: 'blur(8px)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  />
                  <div className="relative z-10">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-6 transition-all duration-300 group-hover:scale-110" style={{ background: 'rgba(0, 212, 255, 0.08)', border: '1px solid rgba(0, 212, 255, 0.15)' }}>
                      {f.icon}
                    </div>
                    <h3 className="text-xl font-bold text-white mb-3">{f.title}</h3>
                    <p className="text-[#B7C2D0] text-sm leading-relaxed">{f.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="relative py-32 px-6 z-10 overflow-hidden">
        {/* Atmospheric glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[40vw] rounded-full animate-electric-pulse" style={{ background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%)', filter: 'blur(60px)' }} />
        </div>
        
        <div className="max-w-4xl mx-auto text-center relative p-12 md:p-20 rounded-3xl shadow-2xl" style={{
          background: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 0 40px rgba(0, 212, 255, 0.05), 0 24px 48px rgba(0, 0, 0, 0.3)',
        }}>
          {/* Decorative shine */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.03] to-transparent rotate-12 pointer-events-none rounded-3xl overflow-hidden" />
          
          <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-6 relative z-10">
            Take control of your utility costs.
          </h2>
          <p className="text-[#B7C2D0] text-lg mb-10 max-w-xl mx-auto relative z-10">
            Join thousands of users who have optimized their energy footprint. Upload your first PDF bill in seconds. No credit card required.
          </p>
          <Link
            to="/signup"
            className="px-10 py-5 text-lg font-bold rounded-full transition-all duration-300 hover:scale-105 inline-flex items-center gap-2 relative z-10 hero-btn-glow"
            style={{
              background: 'linear-gradient(135deg, #ffffff, #e2e8f0)',
              color: '#07111F',
              boxShadow: '0 0 40px rgba(255,255,255,0.2), 0 8px 25px rgba(0,0,0,0.3)',
            }}
          >
            Create Free Account <ArrowRight size={20} />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/[0.06] py-12 px-6 relative z-10" style={{ background: 'rgba(7, 17, 31, 0.8)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <Zap size={20} className="text-[#00D4FF] fill-[#00D4FF]" />
            <span className="font-bold text-white text-lg tracking-tight">ElectricAI</span>
          </div>
          <div className="flex gap-8 text-sm text-[#B7C2D0] opacity-75 font-medium">
            <Link to="/demo" className="hover:text-white transition-colors duration-200">Demo</Link>
            <a href="#" className="hover:text-white transition-colors duration-200">Features</a>
            <a href="#" className="hover:text-white transition-colors duration-200">Privacy</a>
            <a href="#" className="hover:text-white transition-colors duration-200">Terms</a>
          </div>
          <p className="text-[#B7C2D0] opacity-50 text-xs">&copy; {new Date().getFullYear()} ElectricAI. All rights reserved.</p>
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
