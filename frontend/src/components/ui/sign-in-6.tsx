import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Zap, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.71 7.31 9.14 5.38 12 5.38Z"
      />
    </svg>
  )
}

const proof = [
  {
    initials: 'JD',
    src: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&facepad=2&w=80&h=80&q=80',
  },
  {
    initials: 'MK',
    src: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&facepad=2&w=80&h=80&q=80',
  },
  {
    initials: 'AR',
    src: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&facepad=2&w=80&h=80&q=80',
  },
]

interface SignIn6Props {
  onSubmit?: (e: React.FormEvent) => void;
  registerEmail?: any;
  registerPassword?: any;
  registerRemember?: any;
  emailError?: string;
  passwordError?: string;
  authError?: string | null;
  isLoading?: boolean;
  onGoogleSignIn?: () => void;
}

export function SignIn6({
  onSubmit,
  registerEmail,
  registerPassword,
  registerRemember,
  emailError,
  passwordError,
  authError,
  isLoading = false,
  onGoogleSignIn,
}: SignIn6Props) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <Card className="grid w-full max-w-4xl grid-cols-1 md:grid-cols-2 gap-0 p-0 overflow-hidden border border-slate-200/80 bg-white shadow-2xl shadow-slate-200/60 rounded-3xl">
      {/* ── LEFT SIDE: Hero Image from img/login.png ── */}
      <div className="relative hidden md:flex flex-col justify-between p-10 min-h-[560px] overflow-hidden text-white group">
        {/* Background Image from img/login.png */}
        <div className="absolute inset-0 z-0 overflow-hidden">
          <img
            src="/login.png"
            alt="Electric AI Grid Background"
            className="w-full h-full object-cover object-center transform transition-transform duration-1000 group-hover:scale-105"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = './login.png';
            }}
          />
          {/* Subtle Dark Gradient Overlay for optimal text readability */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#050711]/90 via-[#050711]/50 to-black/30" />
          <div className="absolute inset-0 bg-gradient-to-r from-blue-950/40 via-transparent to-black/40" />
        </div>

        {/* Ambient Blur Orb */}
        <div className="bg-cyan-500/20 pointer-events-none absolute -top-24 -right-24 w-64 h-64 rounded-full blur-3xl z-1" />

        {/* Top Brand Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="bg-gradient-to-br from-blue-600 to-cyan-400 p-2 rounded-xl shadow-lg shadow-cyan-500/30 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white fill-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white drop-shadow-md">
            ElectricAI
          </span>
        </div>

        {/* Middle Floating Feature Chip */}
        <div className="relative z-10 my-auto py-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-400/30 text-cyan-300 text-xs font-semibold backdrop-blur-md shadow-inner">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            AI Grid Intelligence Platform
          </div>
        </div>

        {/* Bottom Social Proof */}
        <div className="relative z-10 flex items-center gap-3 pt-4 border-t border-white/15">
          <div className="flex -space-x-2.5">
            {proof.map((p) => (
              <Avatar
                key={p.initials}
                className="ring-cyan-500/60 w-8 h-8 ring-2 border border-slate-900"
              >
                <AvatarImage src={p.src} alt="" className="object-cover" />
                <AvatarFallback className="bg-slate-800 text-cyan-400 text-[10px] font-semibold">
                  {p.initials}
                </AvatarFallback>
              </Avatar>
            ))}
          </div>
          <span className="text-slate-200 text-xs font-medium drop-shadow">
            Join <span className="text-cyan-300 font-bold">40,000+</span> teams on ElectricAI
          </span>
        </div>
      </div>

      {/* ── RIGHT SIDE: Login Form (White Background Theme) ── */}
      <div className="flex flex-col justify-center gap-5 p-8 sm:p-10 bg-white">
        <div className="flex flex-col gap-1.5">
          <span className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Welcome back
          </span>
          <span className="text-slate-500 text-xs sm:text-sm">
            Sign in to your ElectricAI workspace.
          </span>
        </div>

        {/* Global Error Banner */}
        {authError && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 flex items-start gap-2.5 text-red-700 text-xs font-medium">
            <AlertCircle size={16} className="shrink-0 text-red-500 mt-0.5" />
            <span>{authError}</span>
          </div>
        )}

        {/* Social SSO Sign In */}
        <Button
          type="button"
          variant="outline"
          onClick={onGoogleSignIn}
          className="w-full justify-center gap-2.5 bg-white border-slate-300 hover:bg-slate-50 text-slate-700 shadow-sm"
        >
          <GoogleIcon />
          <span>Continue with Google</span>
        </Button>

        <div className="flex items-center gap-3">
          <span className="bg-slate-200 h-px flex-1" />
          <span className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
            OR
          </span>
          <span className="bg-slate-200 h-px flex-1" />
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          {/* Email Field */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ss-email" className="text-xs font-semibold text-slate-700">
              Email Address
            </Label>
            <Input
              id="ss-email"
              type="email"
              placeholder="you@acme.com"
              autoComplete="email"
              {...registerEmail}
              className={emailError ? 'border-red-500 focus:ring-red-500' : ''}
            />
            {emailError && (
              <span className="text-[11px] text-red-500 font-medium">{emailError}</span>
            )}
          </div>

          {/* Password Field */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="ss-password" className="text-xs font-semibold text-slate-700">
                Password
              </Label>
              <Link
                to="/forgot-password"
                className="text-blue-600 hover:text-blue-700 text-[11px] font-semibold transition-colors"
              >
                Forgot?
              </Link>
            </div>
            <div className="relative">
              <Input
                id="ss-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                autoComplete="current-password"
                {...registerPassword}
                className={`pr-10 ${passwordError ? 'border-red-500 focus:ring-red-500' : ''}`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {passwordError && (
              <span className="text-[11px] text-red-500 font-medium">{passwordError}</span>
            )}
          </div>

          {/* Remember Me Checkbox */}
          {registerRemember && (
            <div className="flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                id="ss-remember"
                {...registerRemember}
                className="w-4 h-4 rounded border-slate-300 bg-white text-blue-600 focus:ring-blue-500/30 accent-blue-600"
              />
              <label htmlFor="ss-remember" className="text-xs text-slate-600 cursor-pointer select-none">
                Remember me for 30 days
              </label>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold shadow-md shadow-blue-500/20"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Signing in...</span>
              </div>
            ) : (
              'Sign in'
            )}
          </Button>
        </form>

        <p className="text-slate-500 text-center text-xs mt-1">
          No account?{' '}
          <Link to="/signup" className="text-blue-600 font-semibold hover:underline">
            Start free trial
          </Link>
        </p>
      </div>
    </Card>
  )
}

export default SignIn6;
