import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

// ─── Glowing Connected Neural Network Graphic ─────────────────────────────────
function NetworkConstellationSVG() {
  return (
    <div className="relative w-full max-w-sm aspect-square flex items-center justify-center pointer-events-none">
      {/* Background radial glow */}
      <div className="absolute w-72 h-72 bg-blue-500/20 blur-[90px] rounded-full" />
      <div className="absolute w-48 h-48 bg-cyan-400/25 blur-[70px] rounded-full" />

      {/* SVG Network Lines & Nodes */}
      <svg className="w-full h-full relative z-10" viewBox="0 0 300 300" fill="none">
        <defs>
          <radialGradient id="centerNodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="40%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Outer connecting rays */}
        <g stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1.5">
          <line x1="150" y1="150" x2="60" y2="90" />
          <line x1="150" y1="150" x2="240" y2="80" />
          <line x1="150" y1="150" x2="230" y2="210" />
          <line x1="150" y1="150" x2="80" y2="220" />
          <line x1="150" y1="150" x2="150" y2="40" />
          <line x1="150" y1="150" x2="160" y2="260" />
          <line x1="60" y1="90" x2="150" y2="40" />
          <line x1="240" y1="80" x2="150" y2="40" />
          <line x1="240" y1="80" x2="270" y2="150" />
          <line x1="230" y1="210" x2="270" y2="150" />
          <line x1="230" y1="210" x2="160" y2="260" />
          <line x1="80" y1="220" x2="160" y2="260" />
          <line x1="80" y1="220" x2="30" y2="160" />
          <line x1="60" y1="90" x2="30" y2="160" />
        </g>

        {/* Outer Nodes */}
        <circle cx="60" cy="90" r="5" fill="#3B82F6" />
        <circle cx="240" cy="80" r="6" fill="#3B82F6" />
        <circle cx="230" cy="210" r="5" fill="#06B6D4" />
        <circle cx="80" cy="220" r="6" fill="#3B82F6" />
        <circle cx="150" cy="40" r="6" fill="#06B6D4" />
        <circle cx="160" cy="260" r="5" fill="#3B82F6" />
        <circle cx="270" cy="150" r="4" fill="#06B6D4" />
        <circle cx="30" cy="160" r="4" fill="#3B82F6" />

        {/* Pulsing Central Core Node */}
        <circle cx="150" cy="150" r="24" fill="url(#centerNodeGlow)" opacity="0.6" className="animate-pulse" />
        <circle cx="150" cy="150" r="8" fill="#FFFFFF" />
        <circle cx="150" cy="150" r="14" fill="none" stroke="#06B6D4" strokeWidth="2" />
      </svg>
    </div>
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

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
    <div className="min-h-screen flex w-full font-sans overflow-hidden">

      {/* ── Left Half: Dark Navy Brand & Neural Graphic ── */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#060D20] relative flex-col justify-between p-12 overflow-hidden border-r border-blue-900/20">
        {/* Brand logo top left */}
        <Link to="/" className="flex items-center gap-2 group z-10">
          <span className="font-bold text-2xl tracking-tight text-white font-sans">ElectricAI</span>
        </Link>

        {/* Center Constellation Graphic */}
        <div className="flex-1 flex items-center justify-center z-10">
          <NetworkConstellationSVG />
        </div>

        {/* Bottom subtle brand baseline */}
        <div className="z-10 text-[11px] text-blue-300/40 font-mono tracking-widest uppercase">
          Enterprise Utility Intelligence Platform
        </div>
      </div>

      {/* ── Right Half: Clean White Form & Grid Backdrop ── */}
      <div className="w-full lg:w-1/2 bg-[#F8FAFC] relative flex items-center justify-center p-6 sm:p-12 overflow-y-auto">

        {/* Grid pattern background */}
        <div 
          className="absolute inset-0 bg-[linear-gradient(to_right,#E2E8F0_1px,transparent_1px),linear-gradient(to_bottom,#E2E8F0_1px,transparent_1px)] bg-[size:24px_24px] opacity-60 pointer-events-none" 
        />

        {/* White Card Container */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-100 p-8 sm:p-10 relative z-10 space-y-6"
        >
          {/* Header */}
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sign in to your account</h1>
            <p className="text-xs text-slate-500 font-medium">Enter your credentials to access the energy workspace</p>
          </div>

          {/* Form Error Notice */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600 text-xs font-semibold">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">EMAIL ADDRESS</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-white text-slate-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/10 transition-all font-sans"
              />
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">PASSWORD</label>
                <Link to="/forgot-password" className="text-xs font-semibold text-blue-600 hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-[#EEF2FF] text-slate-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/10 transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"
              />
              <label htmlFor="rememberMe" className="text-xs font-medium text-slate-600 cursor-pointer select-none">
                Remember me
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold py-3 rounded-lg text-sm transition-all shadow-md shadow-blue-500/20 active:scale-[0.99] disabled:opacity-50 mt-2"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative flex items-center justify-center my-4">
            <div className="w-full border-t border-slate-200" />
            <span className="bg-white px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest absolute">OR</span>
          </div>

          {/* Social / SSO Auth Buttons */}
          <div className="space-y-2.5">
            <button
              type="button"
              className="w-full bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold py-2.5 rounded-lg text-xs flex items-center justify-center gap-2.5 transition-all shadow-sm"
            >
              <svg className="w-4 h-4 text-[#0078D4]" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z" />
              </svg>
              Sign in with Azure
            </button>

            <button
              type="button"
              className="w-full bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold py-2.5 rounded-lg text-xs flex items-center justify-center gap-2.5 transition-all shadow-sm"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              Sign in with Google
            </button>
          </div>

          {/* Footer Navigation */}
          <div className="text-center text-xs text-slate-500 font-medium pt-2">
            New to ElectricAI?{' '}
            <Link to="/signup" className="font-bold text-blue-600 hover:underline">
              Create Account
            </Link>
          </div>
        </motion.div>

      </div>

    </div>
  );
}
