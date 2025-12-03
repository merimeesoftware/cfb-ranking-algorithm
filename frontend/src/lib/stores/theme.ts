import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { Theme } from '$lib/types';

// Get initial theme from localStorage or default to system
function getInitialTheme(): Theme {
	if (!browser) return 'system';
	
	const stored = localStorage.getItem('theme') as Theme | null;
	if (stored && ['light', 'dark', 'system'].includes(stored)) {
		return stored;
	}
	return 'system';
}

// Create the theme store
export const theme = writable<Theme>(getInitialTheme());

// Derived value for whether dark mode is active
export function isDarkMode(themeValue: Theme): boolean {
	if (!browser) return false;
	
	if (themeValue === 'system') {
		return window.matchMedia('(prefers-color-scheme: dark)').matches;
	}
	return themeValue === 'dark';
}

// Apply theme to document
export function applyTheme(themeValue: Theme): void {
	if (!browser) return;
	
	const dark = isDarkMode(themeValue);
	
	if (dark) {
		document.documentElement.classList.add('dark');
	} else {
		document.documentElement.classList.remove('dark');
	}
	
	// Store preference
	localStorage.setItem('theme', themeValue);
}

// Toggle between light and dark (ignoring system)
export function toggleTheme(): void {
	theme.update(current => {
		const dark = isDarkMode(current);
		return dark ? 'light' : 'dark';
	});
}

// Set theme explicitly
export function setTheme(newTheme: Theme): void {
	theme.set(newTheme);
}

// Initialize theme on load
if (browser) {
	// Apply initial theme
	theme.subscribe(applyTheme);
	
	// Listen for system theme changes
	const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
	mediaQuery.addEventListener('change', () => {
		theme.update(current => {
			if (current === 'system') {
				applyTheme('system');
			}
			return current;
		});
	});
}
