/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F8FAFC',
        primary: '#2563EB',
        positive: '#16A34A',
        negative: '#DC2626',
        neutral: '#64748B',
        border: '#E5E7EB',
        // Channel form so opacity modifiers work: bg-primary-blue/10 compiles
        // to rgb(var(--primary-blue-rgb) / 0.1). A bare var() holding a hex
        // cannot take an alpha modifier — those utilities emitted no CSS at all.
        'bg-primary': 'rgb(var(--bg-primary-rgb) / <alpha-value>)',
        'bg-secondary': 'rgb(var(--bg-secondary-rgb) / <alpha-value>)',
        'text-primary': 'rgb(var(--text-primary-rgb) / <alpha-value>)',
        'text-secondary': 'rgb(var(--text-secondary-rgb) / <alpha-value>)',
        'primary-blue': 'rgb(var(--primary-blue-rgb) / <alpha-value>)',
        'energy-teal': 'rgb(var(--energy-teal-rgb) / <alpha-value>)',
        'electric-cyan': 'rgb(var(--electric-cyan-rgb) / <alpha-value>)',
        'warning-amber': 'rgb(var(--warning-amber-rgb) / <alpha-value>)',
        'savings-green': 'rgb(var(--savings-green-rgb) / <alpha-value>)',
        'alert-red': 'rgb(var(--alert-red-rgb) / <alpha-value>)',
        // These two carry their own alpha, so they stay as plain vars and do
        // not accept an opacity modifier.
        'bg-surface': 'var(--bg-surface)',
        'border-hairline': 'var(--border-hairline)',
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      },
      fontFamily: {
        sans: ['"Fira Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"Fira Code"', 'monospace'],
      },
      borderRadius: {
        'none': '0px',
        'sm': '4px',
        'DEFAULT': '6px',
        'md': '8px',
        'lg': '8px',
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
        'full': '9999px',
      }
    },
  },
  plugins: [],
}
