import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import globalEnergyGridBanner from '../assets/global_energy_grid_banner.png';

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
    <div className="min-h-screen w-full bg-[#080B12] flex items-center justify-center p-4 sm:p-6 lg:p-10 font-sans selection:bg-blue-500 selection:text-white">
      {/* Container Card matching Modern Enterprise Login Experience design */}
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.99 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
        className="w-full max-w-[1140px] min-h-[640px] lg:h-[700px] bg-[#0E1322] rounded-[24px] border border-[#1E273E] shadow-[0_25px_70px_-15px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col lg:flex-row relative"
      >
        {/* ── Left Half: High-Resolution 3D Digital Energy Network Image Banner ── */}
        <div className="hidden lg:block lg:w-1/2 relative overflow-hidden bg-[#0A0D18]">
          {/* Cover Background Image Asset */}
          <img
            src={globalEnergyGridBanner}
            alt="Global Digital Energy Grid Network"
            className="w-full h-full object-cover object-center scale-[1.02] transition-transform duration-700 hover:scale-105"
          />
          
          {/* Subtle Ambient Color Overlay Gradients for Depth */}
          <div className="absolute inset-0 bg-gradient-to-tr from-[#080B12]/80 via-transparent to-blue-900/20 pointer-events-none" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#0E1322]/90 pointer-events-none" />

          {/* Floating Live Grid Status Badge */}
          <div className="absolute bottom-6 left-6 z-10 flex items-center gap-2.5 px-3.5 py-2 rounded-full bg-[#080B12]/75 backdrop-blur-md border border-blue-500/30 text-xs font-medium text-slate-300 shadow-lg">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span className="font-mono text-[11px] text-cyan-300 tracking-wide uppercase">PJM & Global Nodes Active</span>
          </div>
        </div>

        {/* ── Right Half: Modern Enterprise Dark Form ── */}
        <div className="w-full lg:w-1/2 bg-[#0E1322] flex flex-col justify-between p-8 sm:p-12 lg:p-14 z-10 relative overflow-y-auto">
          {/* Top Branding & Support Bar */}
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-blue-500/30 group-hover:from-blue-500 group-hover:to-cyan-400 transition-all">
                <Zap size={20} className="fill-current text-white" />
              </div>
              <span className="font-bold text-2xl tracking-tight text-white font-sans">ElectricAI</span>
            </Link>

            <a
              href="mailto:support@electricai.io"
              className="text-xs font-medium text-slate-400 hover:text-white transition-colors"
            >
              Contact Support
            </a>
          </div>

          {/* Form Content Area */}
          <div className="max-w-[380px] w-full mx-auto my-auto py-6 space-y-6">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight font-sans">
                Sign in to ElectricAI
              </h1>
            </div>

            {/* Error Message Box */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3.5 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 text-red-400 text-xs font-medium"
              >
                <AlertCircle size={16} className="shrink-0 text-red-400" />
                <span>{error}</span>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email Address"
                  className="w-full px-4 py-3 rounded-xl bg-[#141C30] border border-[#232E4A] text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-sans"
                />
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="w-full px-4 py-3 rounded-xl bg-[#141C30] border border-[#232E4A] text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-sans"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Remember Me Checkbox & Forgot Password Link */}
              <div className="flex items-center justify-between pt-1 text-xs">
                <label className="flex items-center gap-2 text-slate-400 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-[#232E4A] bg-[#141C30] text-blue-600 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                  />
                  <span>Remember me</span>
                </label>

                <Link
                  to="/forgot-password"
                  className="font-medium text-[#3B82F6] hover:text-blue-400 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Primary Action Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-[#2563EB] hover:bg-[#3B82F6] active:bg-[#1D4ED8] text-white font-semibold py-3.5 rounded-xl text-sm transition-all shadow-[0_4px_20px_rgba(37,99,235,0.35)] hover:shadow-[0_6px_25px_rgba(59,130,246,0.45)] active:scale-[0.99] disabled:opacity-50 mt-3"
              >
                {isLoading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Separator Divider */}
            <div className="relative flex items-center justify-center my-5">
              <div className="w-full border-t border-[#1E273E]" />
              <span className="bg-[#0E1322] px-3 text-xs text-slate-500 font-medium absolute">or</span>
            </div>

            {/* Identity Providers (SSO) */}
            <div className="space-y-3">
              <button
                type="button"
                className="w-full bg-[#141C30] hover:bg-[#1D2844] border border-[#232E4A] text-slate-200 font-medium py-3 rounded-xl text-xs flex items-center justify-center gap-2.5 transition-all shadow-sm"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>Sign in with Google</span>
              </button>

              <button
                type="button"
                className="w-full bg-[#141C30] hover:bg-[#1D2844] border border-[#232E4A] text-slate-200 font-medium py-3 rounded-xl text-xs flex items-center justify-center gap-2.5 transition-all shadow-sm"
              >
                <svg className="w-4 h-4 text-[#0078D4]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z" />
                </svg>
                <span>Sign in with Azure AD</span>
              </button>
            </div>
          </div>

          {/* Footer Navigation Links */}
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium pt-4">
            <div className="flex gap-4">
              <a href="#" className="hover:text-slate-400 transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-slate-400 transition-colors">Terms of Service</a>
            </div>
            <div>
              <Link to="/signup" className="text-[#3B82F6] hover:text-blue-400 font-semibold transition-colors">
                Create Account
              </Link>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
