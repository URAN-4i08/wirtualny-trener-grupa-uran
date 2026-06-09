/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#0B1426',
        background: '#1c110b',
        surface: '#1c110b',
        'surface-dim': '#1c110b',
        'surface-container': '#291d16',
        'surface-container-low': '#251913',
        'surface-container-high': '#352720',
        'surface-container-highest': '#40322a',
        'surface-variant': '#40322a',
        'on-surface': '#f6ded3',
        'on-surface-variant': '#e0c0b1',
        'on-background': '#f6ded3',
        primary: '#ffb690',
        'primary-container': '#f97316',
        'on-primary': '#552100',
        'on-primary-container': '#582200',
        secondary: '#7bd0ff',
        'secondary-container': '#00a6e0',
        tertiary: '#d3bbff',
        'tertiary-container': '#ad83ff',
        outline: '#a78b7d',
        'outline-variant': '#584237',
        error: '#ffb4ab',
        'error-container': '#93000a',
        'on-error': '#690005',
        success: '#22c55e',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
      },
      fontSize: {
        'headline-xl': ['48px', { lineHeight: '56px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'headline-lg': ['32px', { lineHeight: '40px', fontWeight: '600' }],
        'headline-md': ['20px', { lineHeight: '28px', fontWeight: '500' }],
        'kpi-value': ['36px', { lineHeight: '44px', fontWeight: '700' }],
      },
      spacing: {
        sidebar: '260px',
        'sidebar-collapsed': '80px',
      },
      maxWidth: {
        container: '1440px',
      },
      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        'orange-glow': '0 0 20px rgba(249, 115, 22, 0.35)',
        'nav-active': '-4px 0 12px -2px rgba(255, 182, 144, 0.6)',
      },
    },
  },
  plugins: [],
};
