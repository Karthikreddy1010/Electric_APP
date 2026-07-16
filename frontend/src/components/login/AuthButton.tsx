import React from 'react';
import { Loader2 } from 'lucide-react';

interface AuthButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  loadingText?: string;
}

export default function AuthButton({
  children,
  isLoading = false,
  loadingText = 'Signing In...',
  className = '',
  disabled,
  ...props
}: AuthButtonProps) {
  return (
    <button
      type={props.type || "submit"}
      disabled={isLoading || disabled}
      className={`w-full mt-2 gradient-button text-white font-semibold py-3.5 px-4 rounded-xl shadow-lg transition-all text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 size={18} className="animate-spin text-white" />
          <span>{loadingText}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
