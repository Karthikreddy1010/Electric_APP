import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle, Zap, ShieldCheck, BarChart3, Activity, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring } from 'framer-motion';
import { ParticlesProvider } from '@tsparticles/react';
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';

// ─── Floating Neon Particles ─────────────────────────────────────────────────
function InteractiveBackground() {
  const particlesInit = async (engine: any) => {
    await loadSlim(engine);
  };

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <div className="absolute inset-0 pointer-events-auto mix-blend-screen opacity-50">
        <ParticlesProvider init={particlesInit}>
          <Particles
            id="login-tsparticles"
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
                color: { value: ["#3b82f6", "#06b6d4"] },
                links: {
                  color: "#ffffff",
                  distance: 150,
                  enable: true,
                  opacity: 0.1,
                  width: 1,
                },
                move: {
                  enable: true,
                  speed: 0.5,
                  direction: "none",
                  random: true,
                  straight: false,
                  outModes: { default: "bounce" },
                },
                number: { density: { enable: true }, value: 30 },
                opacity: { value: 0.2 },
                shape: { type: "circle" },
                size: { value: { min: 1, max: 2 } },
              },
              detectRetina: true,
            }}
          />
        </ParticlesProvider>
      </div>

      {/* Large ambient gradient orbs */}
      <div className="absolute w-[400px] h-[400px] rounded-full bg-primary-blue/[0.12] blur-[100px] -top-32 -left-32 animate-float-orb pointer-events-none" />
      <div className="absolute w-[300px] h-[300px] rounded-full bg-electric-cyan/[0.10] blur-[80px] bottom-10 -right-20 animate-float-orb-alt pointer-events-none" />
      <div className="absolute w-[250px] h-[250px] rounded-full bg-energy-teal/[0.08] blur-[70px] top-1/2 left-1/4 animate-float-orb pointer-events-none" style={{ animationDelay: '5s' }} />

      {/* Animated grid lines */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.04] pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="login-grid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke="white" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#login-grid)" />
      </svg>
    </div>
  );
}

// ─── Framer-motion variants ───────────────────────────────────────────────────
const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.15 } }
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

const slideLeft = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.7, ease: 'easeOut' as const } }
};

const slideRight = {
  hidden: { opacity: 0, x: 40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.7, ease: 'easeOut' as const } }
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasShake, setHasShake] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email) { triggerError('Email address is required.'); return; }
    if (!/\S+@\S+\.\S+/.test(email)) { triggerError('Please enter a valid email address.'); return; }
    if (!password) { triggerError('Password is required.'); return; }
    if (password.length < 8) { triggerError('Password must be at least 8 characters.'); return; }

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
        triggerError(detail || 'Invalid email or password. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const triggerError = (msg: string) => {
    setError(msg);
    setHasShake(true);
    setTimeout(() => setHasShake(false), 600);
  };

  const sellingPoints = [
    { icon: <Zap size={16} />, title: 'AI Bill Analysis', desc: 'Instant OCR extraction and explanation' },
    { icon: <BarChart3 size={16} />, title: 'ML Forecasting', desc: 'Predict future bills with weather data' },
    { icon: <Activity size={16} />, title: 'Cost Simulation', desc: 'What-if scenarios for rate optimization' },
    { icon: <ShieldCheck size={16} />, title: 'Secure & Private', desc: 'PII-compliant, no permanent file storage' },
  ];

  // 3D Parallax Tilt variables
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [5, -5]), { damping: 40, stiffness: 150 });
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-5, 5]), { damping: 40, stiffness: 150 });

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

  const welcomeText = "Welcome back to your";

  return (
    <div className="min-h-screen flex bg-bg-primary relative overflow-hidden">
      {/* Interactive Background covering entire screen */}
      <div className="absolute inset-0 z-0">
        <InteractiveBackground />
      </div>

      {/* ── Left Panel: Brand Identity ──────────────────────────────────── */}
      <motion.div
        variants={slideLeft}
        initial="hidden"
        animate="visible"
        style={{ perspective: 1500 }}
        className="hidden lg:flex lg:w-[48%] relative overflow-hidden flex-col justify-between p-12 bg-gradient-to-br from-[#0f1b3d]/90 via-[#152354]/90 to-[#0d2847]/90 backdrop-blur-sm z-10"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >

        <motion.div style={{ rotateX, rotateY, transformStyle: "preserve-3d" }} className="relative z-10 h-full flex flex-col justify-between pointer-events-none">
          <div className="pointer-events-auto">
            {/* Top: Logo */}
            <Link to="/" className="inline-flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-lg shadow-lg shadow-primary-blue/40 group-hover:shadow-primary-blue/60 transition-shadow">
                E
              </div>
              <span className="font-sans font-bold text-xl tracking-tight text-white">ElectricAI</span>
            </Link>
          </div>

        {/* Middle: Hero message */}
        <motion.div
          className="relative z-10 space-y-6 max-w-md"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={fadeUp}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-primary-blue/80 bg-primary-blue/10 px-3 py-1 rounded-[4px] inline-flex items-center gap-1.5 border border-primary-blue/20">
              <Activity size={10} className="animate-pulse" /> Electricity Intelligence Platform
            </span>
          </motion.div>

          <motion.h2 variants={fadeUp} className="text-3xl font-extrabold text-white tracking-tight leading-tight font-sans mt-6">
            <span className="inline-block relative">
              {welcomeText.split("").map((char, index) => (
                <motion.span
                  key={index}
                  initial={{ opacity: 0, y: 10, filter: 'blur(5px)' }}
                  animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  transition={{ duration: 0.4, delay: 0.3 + index * 0.02, type: 'spring', damping: 15 }}
                  className="inline-block"
                >
                  {char === " " ? "\u00A0" : char}
                </motion.span>
              ))}
            </span>{' '}
            <motion.span 
              initial={{ opacity: 0, scale: 0.95, filter: 'blur(5px)' }}
              animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
              transition={{ duration: 0.6, delay: 0.8, ease: "easeOut" }}
              className="inline-block bg-clip-text text-transparent bg-gradient-to-r from-electric-cyan via-primary-blue to-electric-cyan animate-shimmer" 
              style={{ backgroundSize: '200% auto' }}
            >
              energy command center.
            </motion.span>
          </motion.h2>

          <motion.p variants={fadeUp} className="text-white/60 text-sm leading-relaxed">
            Access your personalized bill analytics, load forecasts, and rate optimization tools.
          </motion.p>

          {/* Selling Points */}
          <motion.div variants={fadeUp} className="space-y-3 pt-2">
            {sellingPoints.map((point, idx) => (
              <motion.div
                key={idx}
                variants={fadeUp}
                className="flex items-start gap-3 group"
              >
                <div className="w-8 h-8 rounded-[5px] bg-white/[0.06] border border-white/10 flex items-center justify-center text-primary-blue shrink-0 group-hover:bg-primary-blue/20 group-hover:border-primary-blue/30 transition-all duration-300">
                  {point.icon}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white/90 font-sans">{point.title}</h4>
                  <p className="text-[10px] text-white/40 font-medium">{point.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>

        {/* Bottom: Trust line */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="relative z-10 flex items-center gap-2 text-[10px] text-white/30 font-medium font-sans pointer-events-auto"
        >
          <ShieldCheck size={12} className="text-primary-blue/60" />
          <span>Trusted by energy analysts across New Jersey utilities</span>
        </motion.div>
        
        </motion.div>
      </motion.div>

      {/* ── Right Panel: Login Form ────────────────────────────────────── */}
      <motion.div
        variants={slideRight}
        initial="hidden"
        animate="visible"
        className="flex-1 flex items-center justify-center p-6 md:p-12 relative z-10 bg-bg-primary/90 backdrop-blur-sm shadow-2xl lg:shadow-none"
      >
        {/* Subtle background texture */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute w-[300px] h-[300px] rounded-full bg-primary-blue/[0.02] blur-[80px] -top-20 right-0" />
          <div className="absolute w-[200px] h-[200px] rounded-full bg-electric-cyan/[0.02] blur-[60px] bottom-10 -left-10" />
        </div>

        <motion.div
          className={`w-full max-w-md space-y-7 relative z-10 ${hasShake ? 'animate-shake' : ''}`}
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          {/* Mobile logo (hidden on desktop) */}
          <motion.div variants={fadeUp} className="lg:hidden text-center">
            <Link to="/" className="inline-flex items-center gap-2">
              <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
              <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
            </Link>
          </motion.div>

          {/* Title */}
          <motion.div variants={fadeUp} className="space-y-2">
            <h2 className="text-2xl font-extrabold text-text-primary tracking-tight font-sans">
              Sign in to your account
            </h2>
            <p className="text-xs text-text-secondary font-medium">
              Enter your credentials to access the energy workspace
            </p>
          </motion.div>

          {/* Error alert */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -10, height: 0 }}
                transition={{ duration: 0.3 }}
                className="bg-alert-red/8 border border-alert-red/20 text-alert-red px-4 py-3 rounded-md text-xs font-semibold flex items-center gap-2 overflow-hidden"
              >
                <AlertCircle size={14} className="shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Form */}
          <motion.form variants={fadeUp} onSubmit={handleSubmit} className="space-y-5 text-xs font-semibold text-text-primary">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Email Address</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary/50 px-4 py-3 rounded-md focus:outline-none focus:border-primary-blue focus:ring-2 focus:ring-primary-blue/10 transition-all duration-200"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Password</label>
                <Link to="/forgot-password" className="text-[10px] font-sans text-primary-blue hover:underline font-semibold">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary/50 px-4 py-3 rounded-md pr-11 focus:outline-none focus:border-primary-blue focus:ring-2 focus:ring-primary-blue/10 transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3.5 top-3.5 text-text-secondary hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] font-medium text-text-secondary">
              <label className="flex items-center gap-2.5 cursor-pointer select-none group">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded border-border-hairline accent-primary-blue"
                />
                <span className="group-hover:text-text-primary transition-colors">Remember me</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full bg-primary-blue text-white hover:bg-primary-blue/90 py-3.5 rounded-md text-xs font-bold transition-all shadow-md hover:shadow-lg hover:shadow-primary-blue/25 flex items-center justify-center gap-2 overflow-hidden disabled:opacity-60 disabled:pointer-events-none"
            >
              <span className="relative z-10 flex items-center gap-2">
                {isLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight size={13} className="group-hover:translate-x-0.5 transition-transform" />
                  </>
                )}
              </span>
              {/* Shimmer sweep on hover */}
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent opacity-0 group-hover:opacity-100" style={{ animation: 'sweep-btn 2s infinite' }} />
            </button>
          </motion.form>

          {/* Divider */}
          <motion.div variants={fadeUp} className="flex items-center gap-4">
            <div className="flex-1 h-px bg-border-hairline" />
            <span className="text-[10px] text-text-secondary font-semibold uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-border-hairline" />
          </motion.div>

          {/* Demo access */}
          <motion.div variants={fadeUp}>
            <Link
              to="/demo"
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-bg-surface border border-border-hairline hover:border-primary-blue/30 rounded-md text-xs font-semibold text-text-primary hover:text-primary-blue transition-all shadow-sm hover:shadow-md group"
            >
              <Zap size={13} className="text-primary-blue" />
              Explore Demo Workspace
              <ArrowRight size={12} className="text-text-secondary group-hover:text-primary-blue group-hover:translate-x-0.5 transition-all" />
            </Link>
          </motion.div>

          {/* Sign up link */}
          <motion.div variants={fadeUp} className="text-center text-[11px] text-text-secondary">
            New to ElectricAI?{' '}
            <Link to="/signup" className="text-primary-blue hover:underline font-bold">
              Create Account
            </Link>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
}
