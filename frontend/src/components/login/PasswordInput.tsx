import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, id, className = '', ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const inputId = id || props.name;

    return (
      <div className="space-y-1.5 text-left w-full">
        <label htmlFor={inputId} className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </label>
        <div className="relative">
          <input
            id={inputId}
            type={showPassword ? 'text' : 'password'}
            ref={ref}
            className={`w-full bg-[#060a14]/80 border text-sm text-white placeholder-slate-500 rounded-xl px-4 py-3.5 pr-11 transition-all duration-200 outline-none focus:outline-none focus:ring-1 ${
              error
                ? 'border-red-500/80 focus:border-red-500 focus:ring-red-500'
                : 'border-slate-800 focus:border-[#00f2ff] focus:ring-[#00f2ff] focus:shadow-[0_0_15px_rgba(0,242,255,0.15)]'
            } ${className}`}
            {...props}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-200 transition-colors cursor-pointer"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {error && (
          <p className="text-[11px] text-red-400 font-medium mt-1 animate-pulse" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

PasswordInput.displayName = 'PasswordInput';

export default PasswordInput;
