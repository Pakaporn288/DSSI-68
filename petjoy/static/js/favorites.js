// ===========================
// favorites.js (FULL VERSION)
// ===========================
(function () {

    // ------------------------------------------
    // ดึง CSRF token จาก cookie
    // ------------------------------------------
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    // ------------------------------------------
    // popup แจ้งเตือนให้เข้าสู่ระบบ (มีปุ่มยกเลิก)
    // ------------------------------------------
    function requireLoginAlert() {
        Swal.fire({
            icon: "warning",
            title: "กรุณาเข้าสู่ระบบ",
            text: "คุณต้องเข้าสู่ระบบเพื่อเพิ่มสินค้าลงรายการโปรด",
            showCancelButton: true,
            confirmButtonText: "เข้าสู่ระบบ",
            cancelButtonText: "ยกเลิก",
            reverseButtons: true
        }).then((result) => {
            if (result.isConfirmed) {
                window.location.href = "/login/?next=" + window.location.pathname;
            }
        });
    }

    // ------------------------------------------
    // toggle favorite ด้วย AJAX
    // ------------------------------------------
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

            if (res.redirected || res.status === 403) {
                return requireLoginAlert();
            }

            const data = await res.json();

            if (data.status === "added") {
                el.classList.add("fav-active");
                el.innerHTML = `<i class="fa-solid fa-heart" style="color:#ff3b3b;"></i>`;
            } else {
                el.classList.remove("fav-active");
                el.innerHTML = `<i class="fa-regular fa-heart"></i>`;
            }

        } catch (err) {
            console.error("Favorite toggle failed:", err);
        }
    }

    // ------------------------------------------
    // Event listener ให้ปุ่มหัวใจทุกปุ่ม
    // ------------------------------------------
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".favorite-toggle");
        if (!btn) return;

        const productId = btn.getAttribute("data-product-id");

        if (btn.classList.contains("anonymous-fav")) {
            return requireLoginAlert();
        }

        toggleFavorite(productId, btn);
    });

})();
