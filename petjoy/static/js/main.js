// Minimal main.js to prevent 404 and provide small UI helpers
document.addEventListener('DOMContentLoaded', () => {
    console.log('main.js loaded');
    const toggle = document.querySelector('.chatbot-toggle-button');
    if (toggle) {
        // Make sure it's keyboard-focusable
        if (!toggle.hasAttribute('tabindex')) toggle.setAttribute('tabindex', '0');
        // Activate on Enter/Space
        toggle.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle.click();
            }
        });
    }
});
