/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#303133',
        secondary: '#1272FF',
        disabled: '#A8ABB2',
        regular: '#606266',
        gray1: '#EEF3FF',
        gray2: '#EBEEF5',
        gray3: '#F0F2F5',
        gray4: '#7588A3',
        gray5: '#909399',
        gray7: '#DCDFE6',
        gray8: '#F5F7FA',
        black1: '#1E252E'

      },
      boxShadow: {
        tableShadow: 'inset 0px -1px 0px 0px #EBEEF5'
      },
      backgroundImage: {
        'filter-icon': 'url("../assets/filter.png")'
      }
    },
  },
  plugins: [],
}

