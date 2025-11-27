(function(){
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    async function toggleFavorite(productId, el) {
        const csrftoken = getCookie("csrftoken");
        const url = "/favorites/toggle/";

        try {
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({ product_id: productId })
            });

            if (res.status === 403) {
                Swal.fire({
                    icon: "warning",
                    title: "กรุณาเข้าสู่ระบบ",
                    text: "คุณต้องเข้าสู่ระบบเพื่อเพิ่มรายการโปรด",
                }).then(() => {
                    window.location.href = "/login/?next=" + window.location.pathname;
                });
                return;
            }

            const data = await res.json();

            // เปลี่ยนหัวใจ + animation
            if (data.status === "added") {
                el.classList.add("fav-active");
                el.innerHTML = "❤️";
            } else {
                el.classList.remove("fav-active");
                el.innerHTML = "♡";
            }

        } catch (err) {
            console.error("Favorite toggle failed:", err);
        }
    }

    document.addEventListener("click", function(e){
        const btn = e.target.closest(".favorite-toggle");
        if (!btn) return;

        const productId = btn.getAttribute("data-product-id");
        toggleFavorite(productId, btn);
    });
})();
