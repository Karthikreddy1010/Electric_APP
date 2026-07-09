/**
 * VerifyEmailPage — handles the /verify-email?token=<token> route.
 *
 * On mount, extracts the token from the URL and calls POST /auth/verify-email.
 * On success: shows confirmation + link to login.
 * On failure: shows error + option to resend.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import apiClient from '../lib/apiClient.ts';

type VerifyState = 'verifying' | 'success' | 'error' | 'already_verified';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [state, setState] = useState<VerifyState>('verifying');
  const [errorMsg, setErrorMsg] = useState('');
  const [resendEmail, setResendEmail] = useState('');
  const [resendSent, setResendSent] = useState(false);

  useEffect(() => {
    if (!token) {
      setErrorMsg('Verification link is missing a token. Please check your email and try again.');
      setState('error');
      return;
    }

    apiClient.post('/auth/verify-email', { token })
      .then(() => {
        setState('success');
        // Auto-redirect to login after 3 seconds
        setTimeout(() => navigate('/login'), 3000);
      })
      .catch((err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '';
        if (detail.includes('already')) {
          setState('already_verified');
        } else {
          setErrorMsg(detail || 'The verification link is invalid or has expired.');
          setState('error');
        }
      });
  }, [token, navigate]);

  const handleResend = async () => {
    if (!resendEmail) return;
    try {
      await apiClient.post('/auth/resend-verification', { email: resendEmail });
      setResendSent(true);
    } catch {
      setResendSent(true); // Silent — always show success to prevent enumeration
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-bg-surface border border-border-hairline rounded-lg shadow-xl p-8 space-y-6 text-center">

        {/* Logo */}
        <Link to="/" className="inline-flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-[5px] bg-primary-blue flex items-center justify-center font-bold text-white text-base shadow-md">E</div>
          <span className="font-sans font-bold text-lg tracking-tight text-text-primary">ElectricAI</span>
        </Link>

        {/* Verifying */}
        {state === 'verifying' && (
          <div className="space-y-3 py-4">
            <RefreshCw size={32} className="text-primary-blue animate-spin mx-auto" />
            <p className="text-sm font-semibold text-text-primary">Verifying your email…</p>
            <p className="text-xs text-text-secondary">Please wait.</p>
          </div>
        )}

        {/* Success */}
        {(state === 'success' || state === 'already_verified') && (
          <div className="space-y-4">
            <div className="w-14 h-14 bg-savings-green/10 rounded-full flex items-center justify-center text-savings-green mx-auto">
              <CheckCircle2 size={32} />
            </div>
            <h2 className="text-xl font-bold text-text-primary">Email Verified!</h2>
            <p className="text-sm text-text-secondary">
              {state === 'already_verified'
                ? 'Your email was already verified. You can log in.'
                : 'Your account is now active. Redirecting to login…'}
            </p>
            <Link
              to="/login"
              className="inline-block bg-primary-blue text-white hover:bg-primary-blue/90 font-bold px-6 py-2.5 rounded-md text-xs transition-all"
            >
              Go to Login
            </Link>
          </div>
        )}

        {/* Error */}
        {state === 'error' && (
          <div className="space-y-4">
            <div className="w-14 h-14 bg-energy-red/10 rounded-full flex items-center justify-center text-energy-red mx-auto">
              <AlertCircle size={32} />
            </div>
            <h2 className="text-xl font-bold text-text-primary">Verification Failed</h2>
            <p className="text-sm text-text-secondary">{errorMsg}</p>

            {!resendSent ? (
              <div className="space-y-2 pt-2">
                <p className="text-xs text-text-secondary font-semibold">Resend a new verification link:</p>
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full bg-bg-primary border border-border-hairline px-3 py-2.5 rounded-md text-xs text-text-primary focus:outline-none focus:border-primary-blue"
                />
                <button
                  onClick={handleResend}
                  disabled={!resendEmail}
                  className="w-full bg-primary-blue text-white hover:bg-primary-blue/90 font-bold py-2.5 rounded-md text-xs transition-all disabled:opacity-50"
                >
                  Resend Verification Email
                </button>
              </div>
            ) : (
              <p className="text-xs text-savings-green font-semibold">
                ✓ Verification email resent. Check your inbox.
              </p>
            )}

            <Link to="/login" className="block text-xs text-text-secondary hover:text-text-primary underline">
              Back to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
