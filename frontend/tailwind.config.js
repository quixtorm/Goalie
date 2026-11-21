/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'] },
      colors: {
        bg: '#0F1115',
        card: '#1B1E24',
        card2: '#242832',
        line: 'rgba(255,255,255,0.08)',
        ink: '#EEF1F6',
        muted: '#9AA3B2',
        brand: { DEFAULT: '#2E7BD6', dark: '#0B2A6F', light: '#5AA2F0' },
      },
      borderRadius: { card: '20px', btn: '16px' },
      boxShadow: { soft: '0 8px 24px rgba(0,0,0,0.35)', glow: '0 10px 30px rgba(46,123,214,0.35)' },
      keyframes: {
        'sheet-up': { from: { transform: 'translateY(100%)' }, to: { transform: 'translateY(0)' } },
        'fade-in': { from: { opacity: 0 }, to: { opacity: 1 } },
        'slide-out': { from: { opacity: 0, transform: 'translateY(48px) scale(.94)' }, to: { opacity: 1, transform: 'none' } },
        'rise': { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'none' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        'card-issue': {
          '0%': { opacity: 0, transform: 'translateY(-130%) rotate(-7deg) scale(.9)' },
          '60%': { opacity: 1, transform: 'translateY(6%) rotate(1.5deg) scale(1.02)' },
          '100%': { opacity: 1, transform: 'none' },
        },
      },
      animation: {
        'sheet-up': 'sheet-up .32s cubic-bezier(.2,.8,.2,1) both',
        'fade-in': 'fade-in .2s ease-out both',
        'slide-out': 'slide-out .38s cubic-bezier(.2,.8,.2,1) both',
        rise: 'rise .3s ease-out both',
        shimmer: 'shimmer 1.4s linear infinite',
        'card-issue': 'card-issue .75s cubic-bezier(.2,.9,.25,1.1) both',
      },
    },
  },
  plugins: [],
}
