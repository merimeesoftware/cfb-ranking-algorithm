/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				primary: {
					50: '#f0f5f2',
					100: '#dce8e1',
					200: '#b8d1c4',
					300: '#8fb5a2',
					400: '#5f9179',
					500: '#3d7359',
					600: '#2d5a45',
					700: '#1a3d2e',
					800: '#153226',
					900: '#0f241b',
					950: '#081410'
				},
				cfb: {
					gold: '#c9a227',
					'gold-bright': '#e8c547',
					green: '#1a3d2e',
					field: '#243f32',
					chalk: '#eef1ee',
					ink: '#14241c',
					red: '#C41E3A'
				}
			},
			fontFamily: {
				display: ['Oswald', 'Impact', 'sans-serif'],
				sans: ['"Source Sans 3"', 'Segoe UI', 'sans-serif']
			},
			backgroundImage: {
				'field-haze':
					'radial-gradient(ellipse 90% 60% at 50% -10%, rgba(201,162,39,0.12), transparent 55%), linear-gradient(165deg, #0f241b 0%, #1a3d2e 42%, #243f32 78%, #153226 100%)',
				'chalk-grain':
					'linear-gradient(180deg, #f5f7f5 0%, #eef1ee 100%)'
			},
			keyframes: {
				'hero-rise': {
					'0%': { opacity: '0', transform: 'translateY(0.75rem)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				},
				'stripe-pulse': {
					'0%, 100%': { opacity: '0.35' },
					'50%': { opacity: '0.7' }
				}
			},
			animation: {
				'hero-rise': 'hero-rise 0.7s ease-out both',
				'stripe-pulse': 'stripe-pulse 4s ease-in-out infinite'
			}
		}
	},
	plugins: [require('@tailwindcss/forms')]
};
