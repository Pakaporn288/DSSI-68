// ===========================================================
// product_detail.js
// ===========================================================

document.addEventListener("DOMContentLoaded", () => {

    const addToCartBtn = document.getElementById("addToCartBtn");
    const buyNowBtn = document.querySelector(".btn-buy-now");

    const modal = document.getElementById("quantityModal");
    const qtyPlus = document.getElementById("qtyPlus");
    const qtyMinus = document.getElementById("qtyMinus");
    const qtyInput = document.getElementById("modalQtyInput");
    const qtyHidden = document.getElementById("modalQtyHidden");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const confirmBtn = modal ? modal.querySelector(".modal-confirm-btn") : null;

    let purchaseMode = "cart"; // cart | buy

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
    // เพิ่มลงตะกร้า
    // ===========================================================
    if (addToCartBtn) {
        addToCartBtn.addEventListener("click", (event) => {
            const isLoggedIn = addToCartBtn.dataset.loggedIn === "1";
            if (!isLoggedIn) {
                event?.stopPropagation();
                return requireLoginAlert();
            }

            purchaseMode = "cart";
            modal.style.display = "flex";
        });
    }

    // ===========================================================
    // สั่งซื้อสินค้า (เลือกจำนวนก่อน)
    // ===========================================================
    if (buyNowBtn) {
        buyNowBtn.addEventListener("click", (event) => {
            const isLoggedIn = addToCartBtn.dataset.loggedIn === "1";
            if (!isLoggedIn) {
                event?.stopPropagation();
                return requireLoginAlert();
            }

            purchaseMode = "buy";
            modal.style.display = "flex";
        });
    }

    // ===========================================================
    // ปรับจำนวน
    // ===========================================================
    qtyPlus?.addEventListener("click", () => {
        let val = parseInt(qtyInput.value) || 1;
        val++;
        qtyInput.value = val;
        qtyHidden.value = val;
    });

    qtyMinus?.addEventListener("click", () => {
        let val = parseInt(qtyInput.value) || 1;
        val = Math.max(1, val - 1);
        qtyInput.value = val;
        qtyHidden.value = val;
    });

    // ===========================================================
    // ยกเลิก modal
    // ===========================================================
    closeModalBtn?.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // ===========================================================
    // ยืนยันจำนวน
    // ===========================================================
    if (confirmBtn) {
        confirmBtn.addEventListener("click", (event) => {
            event.preventDefault();

            const productId = addToCartBtn.dataset.productId;
            const quantity = qtyHidden.value;
            const csrfToken = document.querySelector("input[name=csrfmiddlewaretoken]").value;

            const form = document.createElement("form");
            form.method = "POST";
            form.action = "/cart/add/";

            form.innerHTML = `
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <input type="hidden" name="product_id" value="${productId}">
                <input type="hidden" name="quantity" value="${quantity}">
            `;

            if (purchaseMode === "buy") {
                const buyNowInput = document.createElement("input");
                buyNowInput.type = "hidden";
                buyNowInput.name = "buy_now";
                buyNowInput.value = "1";
                form.appendChild(buyNowInput);
            }

            document.body.appendChild(form);
            form.submit();
        });
    }

});

// ===========================================================
// REPORT MODAL (แก้: เพิ่มปุ่มยกเลิกกลับมา)
// ===========================================================
window.openReportModal = function () {
    const btn = document.querySelector(".btn-report");
    const isLoggedIn = btn?.dataset.loggedIn === "1";

    if (!isLoggedIn) {
        return Swal.fire({
            icon: "warning",
            title: "กรุณาเข้าสู่ระบบ",
            text: "คุณต้องเข้าสู่ระบบเพื่อรายงานสินค้า",
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

    const modal = document.getElementById("reportModal");
    if (modal) modal.style.display = "flex";
};

window.closeReportModal = function () {
    const modal = document.getElementById("reportModal");
    if (modal) modal.style.display = "none";
};

window.submitReport = function () {
    Swal.fire({
        icon: "success",
        title: "ส่งรายงานเรียบร้อย",
        text: "ขอบคุณที่ช่วยแจ้งปัญหา"
    });
    closeReportModal();
};

document.addEventListener("click", function (e) {
    const modal = document.getElementById("reportModal");
    if (modal && e.target === modal) {
        closeReportModal();
    }
});
