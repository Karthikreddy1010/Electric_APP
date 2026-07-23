import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [authError, setAuthError] = useState<string | null>(null);

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
    console.log('Initiating SSO Google Auth...');
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
