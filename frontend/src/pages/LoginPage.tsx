import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext.tsx';

// ── Redesigned UI Components ──────────────────────────────────────────────
import Background3D from '../components/login/Background3D.tsx';
import SystemHealthCard from '../components/login/SystemHealthCard.tsx';
import LiveGridLoadCard from '../components/login/LiveGridLoadCard.tsx';
import LoginCard from '../components/login/LoginCard.tsx';
import InputField from '../components/login/InputField.tsx';
import PasswordInput from '../components/login/PasswordInput.tsx';
import RememberMe from '../components/login/RememberMe.tsx';
import AuthButton from '../components/login/AuthButton.tsx';
import Footer from '../components/login/Footer.tsx';

// ── Zod Schema Validation (Preserved) ──────────────────────────────────────
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

  // ── React Hook Form Setup (Preserved) ────────────────────────────────────
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

  // ── TanStack Query Mutation (Preserved) ──────────────────────────────────
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

  const handleAzureSignIn = () => {
    console.log('Initiating SSO Azure AD Auth...');
  };

  return (
    <div className="relative min-h-screen w-full bg-[#050711] font-sans flex items-center justify-center p-4 sm:p-8 overflow-hidden select-none">
      {/* 1. Full-screen 3D Perspective Grid and Cyber-Orb background */}
      <Background3D />

      {/* 2. Three-Panel Dashboard login row (centered on mobile, floating on desktop) */}
      <div className="relative flex items-center justify-center w-full max-w-[460px] z-10">
        
        {/* Left Telemetry Card (System Health) */}
        <div className="hidden xl:block absolute -left-[315px] top-[12%]">
          <SystemHealthCard />
        </div>

        {/* Center Login Card Container */}
        <LoginCard error={authError}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {/* Email Address */}
            <InputField
              label="Email Address"
              type="email"
              placeholder="Email Address"
              error={errors.email?.message}
              autoComplete="email"
              {...register('email')}
            />

            {/* Password */}
            <PasswordInput
              label="Password"
              placeholder="Password"
              error={errors.password?.message}
              autoComplete="current-password"
              {...register('password')}
            />

            {/* Remember Me and Forgot Password */}
            <RememberMe {...register('rememberMe')} />

            {/* Submit Auth Button */}
            <AuthButton isLoading={loginMutation.isPending}>
              Sign In
            </AuthButton>
          </form>

          {/* OAuth Buttons and Footer links */}
          <Footer
            onGoogleSignIn={handleGoogleSignIn}
            onAzureSignIn={handleAzureSignIn}
          />
        </LoginCard>

        {/* Right Telemetry Card (Live Grid Load) */}
        <div className="hidden xl:block absolute -right-[325px] top-[18%]">
          <LiveGridLoadCard />
        </div>
      </div>
    </div>
  );
}
