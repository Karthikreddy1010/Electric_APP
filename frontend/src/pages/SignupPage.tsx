import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { AlertCircle, Zap, Activity, BarChart3, ShieldCheck, ArrowRight, Eye, EyeOff } from 'lucide-react';

const UTILITIES = [
  { id: 'pseg', name: 'PSE&G' },
  { id: 'jcpl', name: 'JCP&L' },
  { id: 'ace', name: 'Atlantic City Electric' },
  { id: 'reco', name: 'Rockland Electric' }
];

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [zipCode, setZipCode] = useState('');
  const [utility, setUtility] = useState('PSE&G');
  const [terms, setTerms] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);

  // Compute password strength score (0 to 4)
  const getPasswordStrength = () => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
    if (/\d/.test(password) && /[^A-Za-z0-9]/.test(password)) score += 1;
    return score;
  };

  const strengthScore = getPasswordStrength();
  const strengthLabels = ['Too short', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['bg-alert-red', 'bg-alert-red', 'bg-warning-amber', 'bg-primary-blue', 'bg-savings-green'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!firstName) { setError('First name is required.'); return; }
    if (!email) { setError('Email address is required.'); return; }
    if (!/\S+@\S+\.\S+/.test(email)) { setError('Please enter a valid email address.'); return; }
    if (!password) { setError('Password is required.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (!/^\d{5}$/.test(zipCode)) { setError('Please enter a valid 5-digit ZIP code.'); return; }
    if (!terms) { setError('You must agree to the Terms of Service.'); return; }

    setIsLoading(true);
    try {
      await signup({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        zip_code: zipCode,
        utility_provider: utility,
      });
      setVerificationSent(true);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '';
      setError(detail || 'An error occurred during sign up.');
    } finally {
      setIsLoading(false);
    }
  };

  if (verificationSent) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-bg-surface border border-border-hairline rounded-lg p-8 text-center space-y-4 shadow-sm">
          <div className="w-14 h-14 bg-savings-green/10 rounded-full flex items-center justify-center mx-auto text-savings-green">
            <ShieldCheck size={28} />
          </div>
          <h2 className="text-2xl font-bold text-text-primary tracking-tight">Verify your email</h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            We've sent a verification link to <strong className="text-text-primary">{email}</strong>.
            Click the link to activate your account.
          </p>
          <p className="text-xs text-text-secondary">Didn't receive it? Check your spam folder.</p>
          <button
            onClick={() => navigate('/login')}
            className="text-sm text-primary-blue hover:underline font-semibold pt-4 inline-block focus:outline-none"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

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
              Create an account to start analyzing your utility bills and discover actionable savings.
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

      {/* ── Right Panel: Signup Form ────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 overflow-y-auto bg-bg-primary">
        <div className="w-full max-w-sm space-y-8 my-auto">
          
          <div className="lg:hidden text-center">
            <Link to="/" className="inline-flex items-center gap-2">
              <div className="w-8 h-8 rounded-md bg-bg-surface border border-border-hairline flex items-center justify-center text-primary-blue">
                <Zap size={16} />
              </div>
              <span className="font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
            </Link>
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-text-primary tracking-tight">Create your account</h2>
            <p className="text-sm text-text-secondary">Get started with electricity analytics today</p>
          </div>

          {error && (
            <div className="bg-alert-red/10 border border-alert-red/20 text-alert-red px-4 py-3 rounded-md text-sm font-medium flex items-start gap-2">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Sarah"
                  className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Jenkins"
                  className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-text-primary block">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="sarah@company.com"
                className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">ZIP Code</label>
                <input
                  type="text"
                  maxLength={5}
                  value={zipCode}
                  onChange={(e) => setZipCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="07102"
                  className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary font-mono"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">Utility Provider</label>
                <select
                  value={utility}
                  onChange={(e) => setUtility(e.target.value)}
                  className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
                >
                  {UTILITIES.map((u) => (
                    <option key={u.id} value={u.name}>{u.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md pr-10 focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute right-2 top-2 text-text-secondary hover:text-text-primary transition-colors focus:outline-none"
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">Confirm Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-bg-surface border border-border-hairline hover:border-text-secondary px-3 py-2 rounded-md pr-10 focus:outline-none focus:border-primary-blue focus:ring-1 focus:ring-primary-blue text-sm transition-colors text-text-primary"
                  />
                </div>
              </div>
            </div>

            {/* Password strength meter */}
            {password && (
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-xs font-medium text-text-secondary">
                  <span>Password Strength</span>
                  <span className="uppercase text-[10px] tracking-wider font-bold">{strengthLabels[strengthScore]}</span>
                </div>
                <div className="flex gap-1 h-1">
                  {[1, 2, 3, 4].map((idx) => (
                    <div
                      key={idx}
                      className={`flex-1 h-full rounded-full transition-colors ${
                        idx <= strengthScore ? strengthColors[strengthScore] : 'bg-bg-surface border border-border-hairline/50'
                      }`}
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2">
              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={terms}
                  onChange={(e) => setTerms(e.target.checked)}
                  className="rounded border-border-hairline mt-0.5 accent-primary-blue bg-bg-surface w-4 h-4"
                />
                <span className="text-xs text-text-secondary font-medium leading-relaxed">
                  By creating an account, you agree to our{' '}
                  <span className="text-primary-blue hover:underline cursor-pointer">Terms of Service</span> and{' '}
                  <span className="text-primary-blue hover:underline cursor-pointer">Privacy Policy</span>.
                </span>
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
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="text-center text-sm text-text-secondary">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-blue hover:underline font-medium">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
