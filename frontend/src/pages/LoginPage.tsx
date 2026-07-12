import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle, Zap, Activity, BarChart3, ShieldCheck, ArrowRight } from 'lucide-react';

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

  const sellingPoints = [
    { icon: <Zap size={16} />, title: 'AI Bill Analysis', desc: 'Instant OCR extraction and explanation' },
    { icon: <BarChart3 size={16} />, title: 'ML Forecasting', desc: 'Predict future bills with weather data' },
    { icon: <Activity size={16} />, title: 'Cost Simulation', desc: 'What-if scenarios for rate optimization' },
    { icon: <ShieldCheck size={16} />, title: 'Secure & Private', desc: 'PII-compliant, no permanent file storage' },
  ];

  return (
    <div className="min-h-screen flex bg-bg-primary font-sans">
      {/* ── Left Panel: Brand Identity ──────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-between p-12 bg-bg-surface border-r border-border-hairline">
        <div className="relative z-10 h-full flex flex-col justify-between">
          <div>
            <Link to="/" className="inline-flex items-center gap-2.5 group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue rounded-md">
              <div className="w-8 h-8 rounded-md bg-bg-primary border border-border-hairline flex items-center justify-center font-bold text-primary-blue">
                <Zap size={16} />
              </div>
              <span className="font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
            </Link>
          </div>

          <div className="max-w-md space-y-6">
            <h2 className="text-3xl font-bold text-text-primary tracking-tight leading-tight">
              Operational intelligence for your energy spend.
            </h2>
            <p className="text-text-secondary text-sm leading-relaxed">
              Access your personalized bill analytics, load forecasts, and rate optimization tools.
            </p>

            <div className="space-y-4 pt-6 border-t border-border-hairline">
              {sellingPoints.map((point, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-md bg-bg-primary border border-border-hairline flex items-center justify-center text-primary-blue shrink-0">
                    {point.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary">{point.title}</h4>
                    <p className="text-xs text-text-secondary mt-0.5">{point.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-text-secondary font-medium">
            <ShieldCheck size={14} className="text-text-secondary" />
            <span>Trusted by energy analysts across New Jersey utilities</span>
          </div>
        </div>
      </div>

      {/* ── Right Panel: Login Form ────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 relative bg-bg-primary">
        <div className="w-full max-w-sm space-y-8">
          
          <div className="lg:hidden text-center">
            <Link to="/" className="inline-flex items-center gap-2">
              <div className="w-8 h-8 rounded-md bg-bg-surface border border-border-hairline flex items-center justify-center text-primary-blue">
                <Zap size={16} />
              </div>
              <span className="font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
            </Link>
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-text-primary tracking-tight">Sign in to your account</h2>
            <p className="text-sm text-text-secondary">Enter your credentials to access the energy workspace</p>
          </div>

          {error && (
            <div className="bg-alert-red/10 border border-alert-red/20 text-alert-red px-4 py-3 rounded-md text-sm font-medium flex items-start gap-2">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-text-primary block">Email Address</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors"
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-baseline">
                <label className="text-xs font-semibold text-text-primary block">Password</label>
                <Link to="/forgot-password" className="text-xs text-primary-blue hover:underline font-medium">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md pr-10 focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3 top-2.5 text-text-secondary hover:text-text-primary transition-colors focus:outline-none"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="flex items-center">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded border-border-hairline bg-bg-surface accent-primary-blue w-4 h-4"
                />
                <span className="text-xs font-medium text-text-secondary hover:text-text-primary transition-colors">Remember me</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-text-primary text-bg-primary hover:bg-text-secondary py-2.5 rounded-md text-sm font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="flex items-center gap-4">
            <div className="flex-1 h-px bg-border-hairline" />
            <span className="text-xs text-text-secondary font-medium">or</span>
            <div className="flex-1 h-px bg-border-hairline" />
          </div>

          <div>
            <Link
              to="/demo"
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-bg-surface border border-border-hairline hover:border-text-secondary rounded-md text-sm font-medium text-text-primary transition-colors group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue"
            >
              <Zap size={16} className="text-primary-blue" />
              Explore Demo Workspace
              <ArrowRight size={14} className="text-text-secondary group-hover:text-primary-blue group-hover:translate-x-0.5 transition-all" />
            </Link>
          </div>

          <div className="text-center text-sm text-text-secondary">
            New to ElectricAI?{' '}
            <Link to="/signup" className="text-primary-blue hover:underline font-medium">
              Create Account
            </Link>
          </div>
        </div>
      </div>
  );
}
