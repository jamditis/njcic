// Shared Tailwind configuration for NJCIC Dashboard
// Colors match CSS custom properties in css/styles.css
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'njcic-teal': '#2dc8d2',
                'njcic-orange': '#f34213',
                'njcic-dark': '#183642',
                'njcic-gray': '#2b3436',
                'njcic-light': '#e8f9fa',
                primary: { DEFAULT: '#0e7c86', light: '#2dc8d2', dark: '#095057' },
            }
        }
    }
}
