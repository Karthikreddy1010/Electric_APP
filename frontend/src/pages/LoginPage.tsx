import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext.tsx';

// ── UI Components & Login Card ──────────────────────────────────────────────
import { SignIn6 } from '../components/ui/sign-in-6.tsx';

// ── Zod Schema Validation ────────────────────────────────────────────────────
const loginSchema = z.object({
  email: z.string().min(1, 'Email address is required').email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;


// The OAuth callback is a browser redirect, so failures come back as a short
// code in the URL rather than a JSON body. Details stay in the server log.
const GOOGLE_ERRORS: Record<string, string> = {
  google_not_configured:
    'Google sign-in is not configured on this server yet. Please sign in with your email and password.',
  google_denied: 'Google sign-in was cancelled.',
  google_state_mismatch: 'Google sign-in expired or was interrupted. Please try again.',
  google_no_code: 'Google sign-in did not complete. Please try again.',
  google_unreachable: 'Could not reach Google. Please check your connection and try again.',
  google_token_exchange: 'Google rejected the sign-in attempt. Please try again.',
  google_no_id_token: 'Google sign-in did not complete. Please try again.',
  google_invalid_token: 'Google sign-in could not be verified. Please try again.',
  google_no_email: 'Google did not share an email address for this account.',
  google_email_unverified: 'That Google account has an unverified email address.',
  google_link_requires_verified_account:
    'An account already exists for that email. Sign in with your password and verify your email address first, then Google sign-in will work.',
  account_not_active: 'This account is locked or suspended. Please contact support.',
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [authError, setAuthError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Surface a failed Google round trip, then drop the code from the URL so a
  // refresh does not show a stale error.
  useEffect(() => {
    const code = searchParams.get('error');
    if (!code) return;
    setAuthError(GOOGLE_ERRORS[code] ?? 'Google sign-in failed. Please try again.');
    searchParams.delete('error');
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // ── React Hook Form Setup ──────────────────────────────────────────────────
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  // ── TanStack Query Mutation ────────────────────────────────────────────────
  const loginMutation = useMutation({
    mutationFn: async (data: LoginFormData) => {
      setAuthError(null);
      await login(data.email, data.password, data.rememberMe);
    },
    onSuccess: () => {
      navigate('/overview');
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      const detail = data?.detail || data?.message || '';
      if (detail === 'email_not_verified') {
        navigate('/verify-pending');
      } else {
        setAuthError(detail || 'Invalid email or password. Please check your credentials.');
      }
    },
  });

  const onSubmit = (data: LoginFormData) => {
    loginMutation.mutate(data);
  };

  const handleGoogleSignIn = () => {
    // Full-page navigation, not fetch: the OAuth flow is a browser redirect to
    // Google and back, and the server sets session cookies on the way through.
    window.location.href = '/auth/google/login';
  };

  return (
    <div className="relative min-h-screen w-full bg-white font-sans flex items-center justify-center p-4 sm:p-8 overflow-hidden select-none">
      {/* Subtle Ambient Background Orbs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-50 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-50 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Main Login Container */}
      <div className="relative flex items-center justify-center w-full max-w-4xl z-10 my-auto">
        <SignIn6
          onSubmit={handleSubmit(onSubmit)}
          registerEmail={register('email')}
          registerPassword={register('password')}
          registerRemember={register('rememberMe')}
          emailError={errors.email?.message}
          passwordError={errors.password?.message}
          authError={authError}
          isLoading={loginMutation.isPending}
          onGoogleSignIn={handleGoogleSignIn}
        />
      </div>
    </div>
  );
}
