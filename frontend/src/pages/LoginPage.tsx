import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

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
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }

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
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-bg-surface border border-border-hairline rounded-lg shadow-xl p-8 space-y-6">
        
        {/* Logo and title */}
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2">
            <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
            <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
          </Link>
          <h2 className="text-xl font-bold text-text-primary tracking-tight font-sans">Sign in to your account</h2>
          <p className="text-xs text-text-secondary">Enter your email and password to access the workspace</p>
        </div>

        {error && (
          <div className="bg-energy-red/10 border border-energy-red/20 text-energy-red px-4 py-3 rounded-md text-xs font-semibold flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold text-text-primary">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Email Address</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-baseline">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Password</label>
              <Link to="/forgot-password" className="text-[10px] font-sans text-primary-blue hover:underline">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md pr-10 focus:outline-none focus:border-primary-blue transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                className="absolute right-3 top-3 text-text-secondary hover:text-text-primary"
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] font-medium text-text-secondary pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded border-border-hairline accent-primary-blue"
              />
              Remember me
            </label>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-blue text-white hover:bg-primary-blue/95 py-3 rounded-md text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>


        <div className="text-center text-[11px] text-text-secondary pt-2">
          New to ElectricAI?{' '}
          <Link to="/signup" className="text-primary-blue hover:underline font-bold">
            Create Account
          </Link>
        </div>

      </div>
    </div>
  );
}
