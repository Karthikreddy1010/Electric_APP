import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, CheckCircle2, ArrowLeft, AlertCircle } from 'lucide-react';
import apiClient from '../lib/apiClient.ts';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError('Please enter your email address.');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post('/auth/forgot-password', { email });
      setSuccess(true);
    } catch {
      // Still show success to prevent email enumeration
      setSuccess(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-bg-surface border border-border-hairline rounded-lg shadow-xl p-8 space-y-6">
        
        {/* Logo */}
        <div className="text-center">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
            <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
          </Link>
        </div>

        {success ? (
          <div className="text-center space-y-4 py-4">
            <div className="w-12 h-12 bg-savings-green/10 rounded-full flex items-center justify-center text-savings-green mx-auto">
              <CheckCircle2 size={28} />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-text-primary tracking-tight font-sans">Check your email</h2>
              <p className="text-xs text-text-secondary leading-relaxed max-w-sm mx-auto">
                We sent a secure link to reset your password to <br />
                <span className="text-text-primary font-mono font-bold text-[11px]">{email}</span>
              </p>
            </div>
            <div className="pt-2">
              <Link
                to="/login"
                className="bg-bg-primary hover:bg-bg-surface border border-border-hairline text-text-primary font-bold px-4 py-2.5 rounded-md text-xs transition-all shadow-sm inline-flex items-center gap-1.5"
              >
                <ArrowLeft size={13} /> Back to Login
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-bold text-text-primary tracking-tight font-sans">Reset your password</h2>
              <p className="text-xs text-text-secondary">Enter your email and we'll send you a password recovery link</p>
            </div>

            {error && (
              <div className="bg-energy-red/10 border border-energy-red/20 text-energy-red px-4 py-2.5 rounded-md text-xs font-semibold flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold text-text-primary">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Email Address</label>
                <div className="relative">
                  <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="sarah@company.com"
                    className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md pl-10 focus:outline-none focus:border-primary-blue transition-all"
                  />
                  <Mail size={14} className="absolute left-3.5 top-3 text-text-secondary" />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-primary-blue text-white hover:bg-primary-blue/95 py-3 rounded-md text-xs font-bold transition-all shadow-sm"
              >
                {isLoading ? 'Sending link...' : 'Send Recovery Link'}
              </button>
            </form>

            <div className="text-center pt-2">
              <Link to="/login" className="inline-flex items-center gap-1.5 text-[11px] text-text-secondary hover:text-text-primary font-bold">
                <ArrowLeft size={13} /> Back to Sign In
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
