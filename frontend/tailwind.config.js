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
        'bg-primary': 'var(--bg-primary)',
        'bg-surface': 'var(--bg-surface)',
        'border-hairline': 'var(--border-hairline)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'primary-blue': 'var(--primary-blue)',
        'energy-teal': 'var(--energy-teal)',
        'electric-cyan': 'var(--electric-cyan)',
        'warning-amber': 'var(--warning-amber)',
        'savings-green': 'var(--savings-green)',
        'alert-red': 'var(--alert-red)',
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      },
      fontFamily: {
        sans: ['Inter', '"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'none': '0px',
        'sm': '2px',
        'DEFAULT': '4px',
        'md': '6px',
        'lg': '6px',
        'xl': '6px',
        '2xl': '6px',
        '3xl': '6px',
        'full': '9999px',
      }
    },
  },
  plugins: [],
}
