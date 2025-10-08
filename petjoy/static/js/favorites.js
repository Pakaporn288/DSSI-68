(function(){
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function getCSRF() {
        // try cookie first
        const csrftoken = getCookie('csrftoken');
        if (csrftoken) return csrftoken;
        // fallback to hidden form
        const form = document.getElementById('csrf-form');
        if (!form) return null;
        const input = form.querySelector('input[name=csrfmiddlewaretoken]');
        return input ? input.value : null;
    }

    async function toggleFavorite(productId, el) {
        const url = '/favorites/toggle/';
        const csrftoken = getCSRF();
        const body = JSON.stringify({ product_id: productId });
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken || ''
                },
                body
            });
            if (!res.ok) {
                if (res.status === 403) {
                    // Not authenticated or CSRF failure
                    window.location.href = '/login/?next=' + window.location.pathname;
                    return;
                }
                console.error('Favorite toggle failed', res.status);
                return;
            }
            const data = await res.json();
            if (data.status === 'added') {
                if (el) el.textContent = '❤️';
                el && el.setAttribute('aria-pressed', 'true');
            } else {
                if (el) el.textContent = '♡';
                el && el.setAttribute('aria-pressed', 'false');
            }
        } catch (err) {
            console.error('Error toggling favorite', err);
        }
    }

    document.addEventListener('click', function(e){
        const btn = e.target.closest && e.target.closest('.favorite-toggle');
        if (!btn) return;
        e.preventDefault();
        const productId = btn.getAttribute('data-product-id');
        if (!productId) return;
        toggleFavorite(productId, btn);
    });
})();
