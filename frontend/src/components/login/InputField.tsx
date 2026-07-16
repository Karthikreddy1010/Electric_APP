import React from 'react';

interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const InputField = React.forwardRef<HTMLInputElement, InputFieldProps>(
  ({ label, error, id, type = 'text', className = '', ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="space-y-1.5 text-left w-full">
        <label htmlFor={inputId} className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </label>
        <input
          id={inputId}
          type={type}
          ref={ref}
          className={`w-full bg-[#060a14]/80 border text-sm text-white placeholder-slate-500 rounded-xl px-4 py-3.5 transition-all duration-200 outline-none focus:outline-none focus:ring-1 ${
            error
              ? 'border-red-500/80 focus:border-red-500 focus:ring-red-500'
              : 'border-slate-800 focus:border-[#00f2ff] focus:ring-[#00f2ff] focus:shadow-[0_0_15px_rgba(0,242,255,0.15)]'
          } ${className}`}
          {...props}
        />
        {error && (
          <p className="text-[11px] text-red-400 font-medium mt-1 animate-pulse" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

InputField.displayName = 'InputField';

export default InputField;
