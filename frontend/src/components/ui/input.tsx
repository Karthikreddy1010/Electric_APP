import * as React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-xl border border-border-hairline bg-bg-surface px-3.5 py-2 text-sm text-text-primary placeholder:text-text-secondary focus:border-primary-blue focus:outline-none focus:ring-1 focus:ring-primary-blue transition-colors disabled:cursor-not-allowed disabled:opacity-50 shadow-sm',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'
