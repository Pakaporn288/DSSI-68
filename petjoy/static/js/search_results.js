document.addEventListener("DOMContentLoaded", () => {

    function requireLoginAlert() {
        Swal.fire({
            icon: "warning",
            title: "กรุณาเข้าสู่ระบบ",
            text: "คุณต้องเข้าสู่ระบบก่อนเพิ่มสินค้าลงตะกร้า",
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

    document.querySelectorAll(".add-cart-btn").forEach(btn => {
        btn.addEventListener("click", function (e) {

            const isLoggedIn = this.dataset.loggedIn === "1";

            if (!isLoggedIn) {
                e.preventDefault();
                requireLoginAlert();
            }
        });
    });

});
