import * as React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'link'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2 cursor-pointer'
    const variants = {
      default: 'bg-blue-600 text-white shadow-md hover:bg-blue-700 active:scale-[0.98]',
      outline: 'border border-border-hairline bg-bg-surface text-text-primary hover:bg-bg-secondary hover:text-text-primary shadow-sm',
      ghost: 'hover:bg-bg-secondary text-text-secondary hover:text-text-primary',
      link: 'text-primary-blue underline-offset-4 hover:underline p-0 h-auto font-normal'
    }

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], className)}
        {...props}
      >
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
