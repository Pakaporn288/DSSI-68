// =========================
//  ตรวจสอบสถานะล็อกอิน
// =========================
document.addEventListener("DOMContentLoaded", () => {
    const addToCartBtn = document.getElementById("addToCartBtn");
    const modal = document.getElementById("quantityModal");
    const modalInput = document.getElementById("modalQtyInput");
    const modalHidden = document.getElementById("modalQtyHidden");
    const qtyPlus = document.getElementById("qtyPlus");
    const qtyMinus = document.getElementById("qtyMinus");
    const closeModalBtn = document.getElementById("closeModalBtn");

    addToCartBtn.addEventListener("click", () => {
        const isLoggedIn = addToCartBtn.dataset.loggedIn === "1";

        if (!isLoggedIn) {
            Swal.fire({
                icon: "warning",
                title: "กรุณาเข้าสู่ระบบ",
                text: "คุณต้องเข้าสู่ระบบก่อนเพิ่มสินค้าลงตะกร้า",
                confirmButtonText: "เข้าสู่ระบบ",
            }).then(() => {
                window.location.href = `/login/?next=${window.location.pathname}`;
            });
            return;
        }

        // เปิด modal
        modal.style.display = "flex";
    });

    // เพิ่มจำนวน
    qtyPlus.addEventListener("click", () => {
        let value = parseInt(modalInput.value) || 1;
        value++;
        modalInput.value = value;
        modalHidden.value = value;
    });

    // ลดจำนวน
    qtyMinus.addEventListener("click", () => {
        let value = parseInt(modalInput.value) || 1;
        value--;
        if (value < 1) value = 1;
        modalInput.value = value;
        modalHidden.value = value;
    });

    // ปิด modal
    closeModalBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });
});
