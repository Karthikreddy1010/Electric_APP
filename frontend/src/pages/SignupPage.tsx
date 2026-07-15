import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { AlertCircle } from 'lucide-react';
import { ParticlesProvider } from '@tsparticles/react';
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';

// ─── Floating Neon Particles ─────────────────────────────────────────────────
function InteractiveBackground() {
  const particlesInit = async (engine: Parameters<typeof loadSlim>[0]) => {
    await loadSlim(engine);
  };

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <div className="absolute inset-0 pointer-events-auto mix-blend-screen opacity-30">
        <ParticlesProvider init={particlesInit}>
          <Particles
            id="signup-tsparticles"
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

      <div className="absolute w-[400px] h-[400px] rounded-full bg-primary-blue/[0.05] blur-[100px] -top-32 -left-32 animate-float-orb pointer-events-none" />
      <div className="absolute w-[300px] h-[300px] rounded-full bg-electric-cyan/[0.05] blur-[80px] bottom-10 -right-20 animate-float-orb-alt pointer-events-none" />
    </div>
  );
}

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
  const strengthColors = ['bg-energy-red', 'bg-energy-red', 'bg-amber-500', 'bg-primary-blue', 'bg-savings-green'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!firstName) return setError('First name is required.');
    if (!email) return setError('Email address is required.');
    if (!/\S+@\S+\.\S+/.test(email)) return setError('Please enter a valid email address.');
    if (!password) return setError('Password is required.');
    if (password.length < 8) return setError('Password must be at least 8 characters.');
    if (password !== confirmPassword) return setError('Passwords do not match.');
    if (!/^\d{5}$/.test(zipCode)) return setError('Please enter a valid 5-digit ZIP code.');
    if (!terms) return setError('You must agree to the Terms of Service.');

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
        <div className="max-w-md w-full bg-bg-surface border border-border-hairline rounded-lg p-8 text-center space-y-4">
          <div className="w-14 h-14 bg-savings-green/10 rounded-full flex items-center justify-center mx-auto">
            <span className="text-2xl">✉️</span>
          </div>
          <h2 className="text-xl font-bold text-text-primary">Verify your email</h2>
          <p className="text-sm text-text-secondary">
            We've sent a verification link to <strong className="text-text-primary">{email}</strong>.
            Click the link to activate your account.
          </p>
          <p className="text-xs text-text-secondary">Didn't receive it? Check your spam folder.</p>
          <button
            onClick={() => navigate('/login')}
            className="text-xs text-primary-blue hover:underline font-semibold"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4 relative overflow-hidden">
      <InteractiveBackground />
      <div className="w-full max-w-md bg-bg-surface border border-border-hairline rounded-lg shadow-xl p-8 space-y-5 relative z-10">
        
        {/* Logo */}
        <div className="text-center space-y-1.5">
          <Link to="/" className="inline-flex items-center gap-2">
            <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
            <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
          </Link>
          <h2 className="text-xl font-bold text-text-primary tracking-tight font-sans">Create your account</h2>
          <p className="text-xs text-text-secondary font-medium">Get started with electricity analytics today</p>
        </div>

        {error && (
          <div className="bg-energy-red/10 border border-energy-red/20 text-energy-red px-4 py-2.5 rounded-md text-xs font-semibold flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs font-semibold text-text-primary">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Sarah"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Jenkins"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Email Address</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="sarah@company.com"
              className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">ZIP Code</label>
              <input
                type="text"
                maxLength={5}
                value={zipCode}
                onChange={(e) => setZipCode(e.target.value.replace(/\D/g, ''))}
                placeholder="07102"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Utility Provider</label>
              <select
                value={utility}
                onChange={(e) => setUtility(e.target.value)}
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
              >
                {UTILITIES.map((u) => (
                  <option key={u.id} value={u.name}>{u.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all"
              />
            </div>
          </div>

          {/* Password strength meter */}
          {password && (
            <div className="space-y-1 pt-1 font-sans">
              <div className="flex justify-between text-[9px] font-bold text-text-secondary">
                <span>Password Strength</span>
                <span className="uppercase">{strengthLabels[strengthScore]}</span>
              </div>
              <div className="flex gap-1 h-1">
                {[1, 2, 3, 4].map((idx) => (
                  <div
                    key={idx}
                    className={`flex-1 h-full rounded-full transition-colors ${
                      idx <= strengthScore ? strengthColors[strengthScore] : 'bg-bg-primary border border-border-hairline/50'
                    }`}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="pt-2">
            <label className="flex items-start gap-2.5 cursor-pointer text-[10px] text-text-secondary select-none font-medium leading-relaxed">
              <input
                type="checkbox"
                checked={terms}
                onChange={(e) => setTerms(e.target.checked)}
                className="rounded border-border-hairline mt-0.5 accent-primary-blue"
              />
              <span>
                By creating an account, you agree to our{' '}
                <span className="text-primary-blue hover:underline cursor-pointer">Terms of Service</span> and{' '}
                <span className="text-primary-blue hover:underline cursor-pointer">Privacy Policy</span>.
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-blue text-white hover:bg-primary-blue/95 py-3 rounded-md text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5"
          >
            {isLoading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="text-center text-[11px] text-text-secondary pt-2">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-blue hover:underline font-bold">
            Sign In
          </Link>
        </div>

      </div>
    </div>
  );
}
