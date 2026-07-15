import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle, Zap, Activity, TrendingUp, Shield, Loader2 } from 'lucide-react';
import { motion, useMotionValue, useTransform, useSpring, AnimatePresence, MotionValue } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════════════════════════
   ANIMATED PARTICLES — Floating electricity motes
   ═══════════════════════════════════════════════════════════════════════════════ */
// Static deterministic particle coordinates to comply with React hook purity rules
const STATIC_PARTICLES = Array.from({ length: 40 }, (_, i) => {
  const seed = (i * 9301 + 49297) % 233280;
  const rand1 = seed / 233280;
  const rand2 = ((seed * 9301 + 49297) % 233280) / 233280;
  const rand3 = ((seed * 12345 + 67890) % 233280) / 233280;
  return {
    id: i,
    x: (rand1 * 100).toFixed(2),
    y: (rand2 * 100).toFixed(2),
    size: (rand3 * 2.5 + 0.5).toFixed(2),
    duration: (rand1 * 20 + 15).toFixed(2),
    delay: (rand2 * 10).toFixed(2),
    opacity: (rand3 * 0.4 + 0.1).toFixed(2),
    offsetY: (-30 - rand1 * 40).toFixed(2),
    offsetX: ((rand2 - 0.5) * 20).toFixed(2),
  };
});

function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {STATIC_PARTICLES.map((p) => {
        const opacityVal = parseFloat(p.opacity);
        return (
          <motion.div
            key={p.id}
            className="absolute rounded-full"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              background: p.id % 3 === 0
                ? 'rgba(6, 182, 212, 0.6)'
                : p.id % 3 === 1
                  ? 'rgba(59, 130, 246, 0.5)'
                  : 'rgba(255, 255, 255, 0.3)',
              boxShadow: p.id % 5 === 0
                ? `0 0 ${parseFloat(p.size) * 4}px rgba(6, 182, 212, 0.4)`
                : 'none',
            }}
            animate={{
              y: [0, parseFloat(p.offsetY), 0],
              x: [0, parseFloat(p.offsetX), 0],
              opacity: [opacityVal, opacityVal * 1.8, opacityVal],
            }}
            transition={{
              duration: parseFloat(p.duration),
              repeat: Infinity,
              delay: parseFloat(p.delay),
              ease: 'easeInOut',
            }}
          />
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   CIRCUIT PATTERN — SVG electricity traces
   ═══════════════════════════════════════════════════════════════════════════════ */
function CircuitPattern() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.04]" aria-hidden="true">
      <svg className="absolute w-full h-full" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice">
        {/* Horizontal circuit traces */}
        <path d="M0,200 H300 L320,180 H500 L520,200 H700 L720,180 H900 L920,200 H1200" stroke="currentColor" strokeWidth="1" fill="none" className="text-cyan-400" />
        <path d="M0,400 H200 L220,420 H400 L420,400 H600 L620,420 H800 L820,400 H1200" stroke="currentColor" strokeWidth="1" fill="none" className="text-blue-400" />
        <path d="M0,600 H350 L370,580 H550 L570,600 H750 L770,580 H1200" stroke="currentColor" strokeWidth="1" fill="none" className="text-cyan-400" />

        {/* Vertical traces */}
        <path d="M300,0 V150 L280,170 V350 L300,370 V500 L280,520 V800" stroke="currentColor" strokeWidth="1" fill="none" className="text-blue-500" />
        <path d="M600,0 V100 L620,120 V300 L600,320 V550 L620,570 V800" stroke="currentColor" strokeWidth="1" fill="none" className="text-cyan-400" />
        <path d="M900,0 V200 L880,220 V400 L900,420 V650 L880,670 V800" stroke="currentColor" strokeWidth="1" fill="none" className="text-blue-400" />

        {/* Junction nodes */}
        {[
          [300, 200], [500, 200], [700, 200], [900, 200],
          [200, 400], [400, 400], [600, 400], [800, 400],
          [350, 600], [550, 600], [750, 600],
          [300, 350], [600, 300], [900, 420],
        ].map(([cx, cy], i) => (
          <g key={i}>
            <circle cx={cx} cy={cy} r="3" fill="none" stroke="currentColor" strokeWidth="1" className="text-cyan-400" />
            <circle cx={cx} cy={cy} r="1" fill="currentColor" className="text-cyan-400" />
          </g>
        ))}
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   IMMERSIVE BACKGROUND — Multi-layered depth system
   ═══════════════════════════════════════════════════════════════════════════════ */
function ImmersiveBackground({ mouseX, mouseY }: { mouseX: MotionValue<number>; mouseY: MotionValue<number> }) {
  const bgX = useTransform(mouseX, [0, 1], [-8, 8]);
  const bgY = useTransform(mouseY, [0, 1], [-6, 6]);
  const springX = useSpring(bgX, { stiffness: 50, damping: 30 });
  const springY = useSpring(bgY, { stiffness: 50, damping: 30 });

  return (
    <div className="fixed inset-0 overflow-hidden" aria-hidden="true">
      {/* Base gradient — deep space blue to black */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#030712] via-[#0a1628] to-[#020617]" />

      {/* Secondary radial gradient — depth layer */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(15,23,42,0.8)_0%,transparent_70%)]" />

      {/* Animated grid — subtle perspective depth */}
      <motion.div
        style={{ x: springX, y: springY }}
        className="absolute inset-[-20px]"
      >
        <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.02)_1px,transparent_1px)] bg-[size:15px_15px]" />
      </motion.div>

      {/* Circuit overlay */}
      <CircuitPattern />

      {/* Central radial glow — hero light behind card */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[700px] bg-[radial-gradient(circle,rgba(6,182,212,0.08)_0%,rgba(37,99,235,0.04)_40%,transparent_70%)] blur-[40px]" />

      {/* Top-left accent glow */}
      <div className="absolute -top-32 -left-32 w-[500px] h-[500px] bg-[radial-gradient(circle,rgba(59,130,246,0.12)_0%,transparent_60%)] blur-[80px]" />

      {/* Bottom-right accent glow */}
      <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] bg-[radial-gradient(circle,rgba(6,182,212,0.08)_0%,transparent_60%)] blur-[80px]" />

      {/* Animated floating particles */}
      <FloatingParticles />

      {/* Vignette — screen edge darkening */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,rgba(0,0,0,0.5)_100%)]" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   SYSTEM HEALTH PANEL — Left floating telemetry
   ═══════════════════════════════════════════════════════════════════════════════ */
function SystemHealthPanel() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setTick((t) => t + 1), 2000);
    return () => clearInterval(iv);
  }, []);

  const healthPct = 94 + (tick % 4);
  const circumference = 2 * Math.PI * 38;

  return (
    <motion.div
      initial={{ opacity: 0, x: -60, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -4, transition: { duration: 0.3 } }}
      className="hidden xl:flex flex-col w-[280px] rounded-[20px] border border-white/[0.08] bg-white/[0.03] backdrop-blur-[28px] shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_0_1px_rgba(255,255,255,0.03),inset_0_1px_0_rgba(255,255,255,0.04)] overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Shield size={13} className="text-emerald-400" />
            </div>
            <span className="text-[11px] font-semibold text-slate-200 tracking-wide">System Health</span>
          </div>
          <div className="flex items-center gap-1.5">
            <motion.div
              animate={{ scale: [1, 1.4, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"
            />
            <span className="text-[9px] font-medium text-emerald-400 uppercase tracking-wider">Live</span>
          </div>
        </div>
      </div>

      {/* Health Ring + Metrics */}
      <div className="px-5 py-4 flex gap-4 items-center">
        <div className="relative w-[88px] h-[88px] flex-shrink-0">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 88 88">
            {/* Background track */}
            <circle cx="44" cy="44" r="38" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="4" />
            {/* Outer ring — health */}
            <motion.circle
              cx="44" cy="44" r="38" fill="none"
              stroke="url(#healthGrad)" strokeWidth="4" strokeLinecap="round"
              strokeDasharray={circumference}
              animate={{ strokeDashoffset: circumference * (1 - healthPct / 100) }}
              transition={{ duration: 1.5, ease: 'easeInOut' }}
            />
            {/* Inner ring — secondary metric */}
            <circle cx="44" cy="44" r="30" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="3" />
            <motion.circle
              cx="44" cy="44" r="30" fill="none"
              stroke="rgba(6,182,212,0.6)" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 30}
              animate={{ strokeDashoffset: 2 * Math.PI * 30 * 0.28 }}
              transition={{ duration: 1.5, ease: 'easeInOut' }}
            />
            <defs>
              <linearGradient id="healthGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="100%" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              key={healthPct}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-lg font-bold text-white tabular-nums"
            >
              {healthPct}%
            </motion.span>
            <span className="text-[8px] text-slate-500 uppercase tracking-widest font-medium">Health</span>
          </div>
        </div>

        {/* Mini sparklines */}
        <div className="flex-1 space-y-3">
          {[
            { label: 'Uptime', value: '99.97%', color: '#10b981', path: 'M0,12 Q5,4 10,8 T20,6 T30,4 T40,7 T50,3' },
            { label: 'Latency', value: '12ms', color: '#06b6d4', path: 'M0,10 Q8,5 15,8 T25,6 T35,9 T45,5 T50,7' },
            { label: 'Throughput', value: '2.4k/s', color: '#3b82f6', path: 'M0,14 Q10,6 18,10 T28,4 T38,8 T50,5' },
          ].map((m) => (
            <div key={m.label} className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">{m.label}</div>
                <div className="text-[10px] font-semibold text-slate-300 tabular-nums">{m.value}</div>
              </div>
              <svg className="w-[50px] h-[16px] flex-shrink-0" viewBox="0 0 50 16">
                <motion.path
                  d={m.path}
                  fill="none"
                  stroke={m.color}
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 2, delay: 0.5 }}
                />
              </svg>
            </div>
          ))}
        </div>
      </div>

      {/* Footer status bar */}
      <div className="px-5 py-3 border-t border-white/[0.04] bg-white/[0.01]">
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-slate-500">Status</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[10px] font-semibold text-emerald-400">Optimal</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   LIVE GRID LOAD PANEL — Right floating telemetry
   ═══════════════════════════════════════════════════════════════════════════════ */
function LiveGridLoadPanel() {
  const [loadPct, setLoadPct] = useState(84);
  useEffect(() => {
    const iv = setInterval(() => setLoadPct((v) => Math.min(99, Math.max(70, v + (Math.random() > 0.5 ? 1 : -1)))), 3000);
    return () => clearInterval(iv);
  }, []);

  const chartPoints = '0,28 8,22 16,25 24,18 32,20 40,12 48,16 56,8 64,14 72,10 80,16 88,12 96,18 100,15';
  const areaPoints = `0,32 ${chartPoints} 100,32`;

  return (
    <motion.div
      initial={{ opacity: 0, x: 60, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -4, transition: { duration: 0.3 } }}
      className="hidden xl:flex flex-col w-[280px] rounded-[20px] border border-white/[0.08] bg-white/[0.03] backdrop-blur-[28px] shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_0_1px_rgba(255,255,255,0.03),inset_0_1px_0_rgba(255,255,255,0.04)] overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Activity size={13} className="text-blue-400" />
            </div>
            <span className="text-[11px] font-semibold text-slate-200 tracking-wide">Live Grid Load</span>
          </div>
          <span className="text-[9px] font-semibold text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full">Peak</span>
        </div>
      </div>

      {/* Chart */}
      <div className="px-5 py-4">
        <div className="relative h-[80px] w-full">
          <svg className="w-full h-full" viewBox="0 0 100 32" preserveAspectRatio="none">
            {/* Grid lines */}
            {[8, 16, 24].map((y) => (
              <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="rgba(255,255,255,0.03)" strokeDasharray="2 4" />
            ))}
            {/* Area fill */}
            <defs>
              <linearGradient id="gridLoadGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(59,130,246,0.25)" />
                <stop offset="100%" stopColor="rgba(59,130,246,0)" />
              </linearGradient>
            </defs>
            <motion.polygon
              points={areaPoints}
              fill="url(#gridLoadGrad)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.5, delay: 0.6 }}
            />
            {/* Main line */}
            <motion.polyline
              points={chartPoints}
              fill="none"
              stroke="url(#lineGrad)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 2, delay: 0.6, ease: 'easeOut' }}
            />
            <defs>
              <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="100%" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
            {/* Peak dot */}
            <motion.circle
              cx="56" cy="8" r="2.5"
              fill="#06b6d4"
              initial={{ scale: 0 }}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: 1.5 }}
            />
            <circle cx="56" cy="8" r="5" fill="none" stroke="rgba(6,182,212,0.3)" strokeWidth="0.5" />
          </svg>
        </div>

        {/* Time axis */}
        <div className="flex justify-between text-[8px] text-slate-600 font-mono mt-1 px-0.5">
          {['00:00', '06:00', '12:00', '18:00', 'Now'].map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </div>

      {/* Metrics footer */}
      <div className="px-5 py-3 border-t border-white/[0.04] bg-white/[0.01]">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[8px] text-slate-500 uppercase tracking-wider">Current Load</div>
            <div className="flex items-center gap-1.5">
              <motion.span
                key={loadPct}
                initial={{ opacity: 0, y: 3 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm font-bold text-white tabular-nums"
              >
                {loadPct}%
              </motion.span>
              <TrendingUp size={11} className="text-amber-400" />
            </div>
          </div>
          <div className="w-24 h-2 rounded-full bg-white/[0.04] overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400"
              animate={{ width: `${loadPct}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   MAIN LOGIN PAGE
   ═══════════════════════════════════════════════════════════════════════════════ */
export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Cursor parallax
  const mouseX = useMotionValue<number>(0.5);
  const mouseY = useMotionValue<number>(0.5);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseX.set(e.clientX / window.innerWidth);
      mouseY.set(e.clientY / window.innerHeight);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email) { setError('Email address is required.'); return; }
    if (!/\S+@\S+\.\S+/.test(email)) { setError('Please enter a valid email address.'); return; }
    if (!password) { setError('Password is required.'); return; }

    setIsLoading(true);
    try {
      await login(email, password, rememberMe);
      navigate('/overview');
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      const detail = data?.detail || data?.message || '';
      if (detail === 'email_not_verified') {
        navigate('/verify-pending');
      } else {
        setError(detail || 'Invalid email or password. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className="min-h-screen w-full flex items-center justify-center relative overflow-hidden font-sans selection:bg-cyan-500/30"
    >
      {/* ── Immersive Background ── */}
      <ImmersiveBackground mouseX={mouseX} mouseY={mouseY} />

      {/* ── Content Layer ── */}
      <div className="relative z-10 w-full max-w-[1200px] mx-auto px-4 sm:px-6 flex items-center justify-center gap-8 xl:gap-12 py-8">

        {/* Left Panel — System Health */}
        <SystemHealthPanel />

        {/* ── Central Login Card ── */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="relative w-full max-w-[420px] flex-shrink-0"
        >
          {/* Card glow halo */}
          <div className="absolute -inset-[1px] rounded-[25px] bg-gradient-to-b from-cyan-500/20 via-blue-500/10 to-transparent opacity-60 blur-[1px]" />
          <motion.div
            animate={{ opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -inset-8 rounded-[40px] bg-[radial-gradient(circle,rgba(6,182,212,0.06)_0%,transparent_70%)]"
          />

          {/* Glass card */}
          <div className="relative rounded-3xl border border-white/[0.08] bg-[rgba(8,12,24,0.75)] backdrop-blur-[32px] shadow-[0_24px_80px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.03),inset_0_1px_0_rgba(255,255,255,0.05)] overflow-hidden">
            {/* Top accent line */}
            <div className="h-[1px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

            <div className="px-8 sm:px-10 py-10 sm:py-12">
              {/* ── Branding ── */}
              <div className="text-center mb-8">
                <Link to="/" className="inline-flex items-center gap-2.5 group mb-5">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-white/10 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.15)] group-hover:shadow-[0_0_24px_rgba(59,130,246,0.25)] transition-shadow">
                    <Zap size={18} className="text-blue-400 fill-blue-400/30" />
                  </div>
                  <span className="text-lg font-bold tracking-tight text-white">ElectricAI</span>
                </Link>
                <h1 className="text-[22px] sm:text-2xl font-bold text-white tracking-tight leading-snug">
                  Sign in to ElectricAI<br />Command Center
                </h1>
                <p className="text-xs text-slate-500 mt-2 font-medium">
                  Secure access to enterprise electricity intelligence.
                </p>
              </div>

              {/* ── Error ── */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: -8, height: 0 }}
                    className="mb-5 p-3.5 rounded-xl bg-red-500/[0.08] border border-red-500/20 flex items-center gap-2.5 text-red-400 text-xs font-medium overflow-hidden"
                  >
                    <AlertCircle size={14} className="shrink-0" />
                    <span>{error}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Form ── */}
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Email */}
                <div className="space-y-2">
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Email Address
                  </label>
                  <div className="relative group">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@company.com"
                      className="w-full px-4 py-3.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white text-sm placeholder:text-slate-600 font-medium
                        focus:outline-none focus:border-cyan-500/50 focus:bg-white/[0.05]
                        focus:shadow-[0_0_0_3px_rgba(6,182,212,0.08),0_0_20px_rgba(6,182,212,0.06)]
                        hover:border-white/[0.15] hover:bg-white/[0.04]
                        transition-all duration-300"
                    />
                    <div className="absolute inset-0 rounded-xl opacity-0 group-focus-within:opacity-100 pointer-events-none transition-opacity duration-500 bg-gradient-to-b from-cyan-500/[0.03] to-transparent" />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Password
                  </label>
                  <div className="relative group">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter your password"
                      className="w-full px-4 py-3.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white text-sm placeholder:text-slate-600 font-medium pr-12
                        focus:outline-none focus:border-cyan-500/50 focus:bg-white/[0.05]
                        focus:shadow-[0_0_0_3px_rgba(6,182,212,0.08),0_0_20px_rgba(6,182,212,0.06)]
                        hover:border-white/[0.15] hover:bg-white/[0.04]
                        transition-all duration-300"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition-all"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                    <div className="absolute inset-0 rounded-xl opacity-0 group-focus-within:opacity-100 pointer-events-none transition-opacity duration-500 bg-gradient-to-b from-cyan-500/[0.03] to-transparent" />
                  </div>
                </div>

                {/* Remember Me + Forgot Password */}
                <div className="flex items-center justify-between text-xs pt-0.5">
                  <label className="flex items-center gap-2.5 cursor-pointer select-none group/check">
                    <div className="relative">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="peer sr-only"
                      />
                      <div className="w-4 h-4 rounded-[5px] border border-white/[0.12] bg-white/[0.03] peer-checked:bg-blue-600/80 peer-checked:border-blue-500/50 transition-all flex items-center justify-center group-hover/check:border-white/20">
                        {rememberMe && (
                          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 12 12">
                            <path d="M2 6l3 3 5-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </div>
                    </div>
                    <span className="text-slate-400 font-medium group-hover/check:text-slate-300 transition-colors">
                      Remember me
                    </span>
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>

                {/* ── Submit Button ── */}
                <motion.button
                  type="submit"
                  disabled={isLoading}
                  whileHover={{ scale: 1.01, y: -1 }}
                  whileTap={{ scale: 0.985 }}
                  className="relative w-full mt-3 py-3.5 rounded-xl font-semibold text-sm text-white overflow-hidden
                    bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500
                    shadow-[0_4px_24px_rgba(37,99,235,0.3),0_1px_3px_rgba(0,0,0,0.2)]
                    hover:shadow-[0_8px_32px_rgba(37,99,235,0.4),0_2px_4px_rgba(0,0,0,0.2)]
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-shadow duration-300
                    group/btn"
                >
                  {/* Button shimmer */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.08] to-transparent translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700" />

                  <span className="relative flex items-center justify-center gap-2">
                    {isLoading ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Signing in…
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </span>
                </motion.button>
              </form>

              {/* ── Footer links ── */}
              <div className="mt-8 pt-6 border-t border-white/[0.04] flex items-center justify-between text-[11px]">
                <div className="flex gap-4 text-slate-600">
                  <a href="#" className="hover:text-slate-400 transition-colors">Privacy</a>
                  <a href="#" className="hover:text-slate-400 transition-colors">Terms</a>
                </div>
                <Link to="/signup" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
                  Create Account →
                </Link>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right Panel — Live Grid Load */}
        <LiveGridLoadPanel />
      </div>
    </div>
  );
}
