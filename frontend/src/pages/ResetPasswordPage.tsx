/**
 * ResetPasswordPage — handles the /reset-password?token=<token> route.
 *
 * Presents a form to enter and confirm a new password.
 * On submit: calls POST /auth/reset-password.
 * On success: redirects to login with a success message.
 */
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react';
import apiClient from '../lib/apiClient.ts';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Password strength
  const getStrength = () => {
    if (!newPassword) return 0;
    let score = 0;
    if (newPassword.length >= 8) score++;
    if (newPassword.length >= 12) score++;
    if (/[A-Z]/.test(newPassword) && /[a-z]/.test(newPassword)) score++;
    if (/\d/.test(newPassword) && /[^A-Za-z0-9]/.test(newPassword)) score++;
    return score;
  };
  const strength = getStrength();
  const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong'][strength];
  const strengthColor = ['', 'bg-energy-red', 'bg-amber-500', 'bg-primary-blue', 'bg-savings-green'][strength];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Invalid reset link. Please request a new one.');
      return;
    }
    if (!newPassword) { setError('New password is required.'); return; }
    if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }

    setIsLoading(true);
    try {
      await apiClient.post('/auth/reset-password', {
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '';
      setError(detail || 'Failed to reset password. The link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-bg-surface border border-border-hairline rounded-lg p-8 text-center space-y-4">
          <AlertCircle size={32} className="text-energy-red mx-auto" />
          <h2 className="text-xl font-bold text-text-primary">Invalid Reset Link</h2>
          <p className="text-sm text-text-secondary">This reset link is missing a token. Please request a new one.</p>
          <Link to="/forgot-password" className="text-xs text-primary-blue hover:underline font-semibold">
            Request New Reset Link
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-bg-surface border border-border-hairline rounded-lg shadow-xl p-8 space-y-6">

        {/* Logo */}
        <div className="text-center">
          <Link to="/" className="inline-flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
            <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
          </Link>
        </div>

        {success ? (
          <div className="text-center space-y-4 py-4">
            <div className="w-14 h-14 bg-savings-green/10 rounded-full flex items-center justify-center text-savings-green mx-auto">
              <CheckCircle2 size={32} />
            </div>
            <h2 className="text-xl font-bold text-text-primary">Password Reset!</h2>
            <p className="text-sm text-text-secondary">
              Your password has been updated. All existing sessions have been signed out for security.
              Redirecting to login…
            </p>
            <Link
              to="/login"
              className="inline-block bg-primary-blue text-white hover:bg-primary-blue/90 font-bold px-6 py-2.5 rounded-md text-xs transition-all"
            >
              Go to Login
            </Link>
          </div>
        ) : (
          <>
            <div className="text-center space-y-1">
              <h2 className="text-xl font-bold text-text-primary tracking-tight font-sans">Set New Password</h2>
              <p className="text-xs text-text-secondary">Enter a strong new password for your account</p>
            </div>

            {error && (
              <div className="bg-energy-red/10 border border-energy-red/20 text-energy-red px-4 py-3 rounded-md text-xs font-semibold flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold text-text-primary">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">New Password</label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md pr-10 focus:outline-none focus:border-primary-blue transition-all"
                  />
                  <button type="button" onClick={() => setShowNew(p => !p)}
                    className="absolute right-3 top-3 text-text-secondary hover:text-text-primary">
                    {showNew ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                {/* Strength bar */}
                {newPassword && (
                  <div className="space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map(i => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-all ${i <= strength ? strengthColor : 'bg-bg-primary border border-border-hairline'}`}
                        />
                      ))}
                    </div>
                    <p className={`text-[10px] font-bold ${strength >= 3 ? 'text-savings-green' : strength >= 2 ? 'text-warning-amber' : 'text-energy-red'}`}>
                      {strengthLabel}
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Confirm Password</label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`w-full bg-bg-primary border hover:border-text-secondary px-3 py-2.5 rounded-md pr-10 focus:outline-none transition-all ${
                      confirmPassword && confirmPassword !== newPassword
                        ? 'border-energy-red focus:border-energy-red'
                        : 'border-border-hairline focus:border-primary-blue'
                    }`}
                  />
                  <button type="button" onClick={() => setShowConfirm(p => !p)}
                    className="absolute right-3 top-3 text-text-secondary hover:text-text-primary">
                    {showConfirm ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                {confirmPassword && confirmPassword !== newPassword && (
                  <p className="text-[10px] text-energy-red font-bold">Passwords do not match</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-primary-blue text-white hover:bg-primary-blue/95 py-3 rounded-md text-xs font-bold transition-all shadow-sm disabled:opacity-60"
              >
                {isLoading ? 'Resetting…' : 'Reset Password'}
              </button>
            </form>

            <div className="text-center">
              <Link to="/login" className="text-xs text-text-secondary hover:text-text-primary underline">
                Back to Login
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
