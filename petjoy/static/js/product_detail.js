// ===============================
// product_detail.js (FINAL FINAL)
// ===============================

// ทำให้โค้ดรอจน DOM โหลดครบก่อน
document.addEventListener("DOMContentLoaded", () => {

    // -------------------------------
    // ดึงปุ่มต่าง ๆ
    // -------------------------------
    const addToCartBtn = document.getElementById("addToCartBtn");
    const buyNowBtn = document.querySelector(".btn-buy-now");

    const modal = document.getElementById("quantityModal");
    const qtyPlus = document.getElementById("qtyPlus");
    const qtyMinus = document.getElementById("qtyMinus");
    const qtyInput = document.getElementById("modalQtyInput");
    const qtyHidden = document.getElementById("modalQtyHidden");
    const closeModalBtn = document.getElementById("closeModalBtn");

    // -------------------------------
    // popup แจ้งเตือนให้เข้าสู่ระบบ
    // -------------------------------
    function requireLoginAlert() {
        Swal.fire({
            icon: "warning",
            title: "กรุณาเข้าสู่ระบบ",
            text: "คุณต้องเข้าสู่ระบบเพื่อทำรายการนี้",
            showCancelButton: true,
            confirmButtonText: "เข้าสู่ระบบ",
            cancelButtonText: "ยกเลิก",
            reverseButtons: true
        }).then(result => {
            if (result.isConfirmed) {
                window.location.href = `/login/?next=${window.location.pathname}`;
            }
        });
    }


    // ===========================================================
    // ⭐ ปุ่ม "เพิ่มลงตะกร้า"
    // ===========================================================
    if (addToCartBtn) {
        addToCartBtn.addEventListener("click", () => {

            // ตรวจว่าล็อกอินหรือไม่
            const isLoggedIn = addToCartBtn.dataset.loggedIn === "1";

            if (!isLoggedIn) {
                // ⭐⭐ ป้องกันไม่ให้ favorites.js ทำงานแทน
                if (event.stopPropagation) event.stopPropagation();

                return requireLoginAlert();
            }

            // ถ้าล็อกอินแล้ว → เปิด modal
            modal.style.display = "flex";
        });
    }


    // ===========================================================
    // ⭐ ปุ่ม "ยกเลิก" ของ modal
    // ===========================================================
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }


    // ===========================================================
    // ⭐ เพิ่มจำนวนสินค้า
    // ===========================================================
    if (qtyPlus) {
        qtyPlus.addEventListener("click", () => {
            let value = parseInt(qtyInput.value) || 1;
            value++;
            qtyInput.value = value;
            qtyHidden.value = value;
        });
    }

    // ===========================================================
    // ⭐ ลดจำนวนสินค้า
    // ===========================================================
    if (qtyMinus) {
        qtyMinus.addEventListener("click", () => {
            let value = parseInt(qtyInput.value) || 1;
            value = Math.max(1, value - 1);
            qtyInput.value = value;
            qtyHidden.value = value;
        });
    }


    // ===========================================================
    // ⭐ ปุ่ม "สั่งซื้อสินค้า"
    // ===========================================================
    if (buyNowBtn) {
        buyNowBtn.addEventListener("click", () => {

            const isLoggedIn = addToCartBtn.dataset.loggedIn === "1";

            if (!isLoggedIn) {
                // ⭐⭐ ป้องกัน favorites.js intercept
                if (event.stopPropagation) event.stopPropagation();

                return requireLoginAlert();
            }

            // ถ้าล็อกอินแล้ว → TODO: Redirect ไป checkout ได้เลย
            Swal.fire({
                icon: "info",
                title: "ระบบกำลังพัฒนา",
                text: "คุณสามารถเพิ่มสินค้าลงตะกร้าแล้วไปที่หน้า Checkout ได้ค่ะ"
            });
        });
    }

});
