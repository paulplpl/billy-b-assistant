// ===================== MOTOR TEST PANEL =====================
const MotorPanel = (() => {
    function sendMotorTest(motor) {
        fetch("/test-motor", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({motor})
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    showNotification("Motor error: " + data.error, "error", 4000);
                } else {
                    showNotification(`Tested ${motor}`, "success", 1500);
                    if (data.service_was_active) {
                        showNotification(
                            "Billy was stopped for hardware test. Please restart Billy again when done.",
                            "warning",
                            7000
                        );
                        ServiceStatus.fetchStatus();
                    }
                }
            })
            .catch(err => showNotification("Motor test failed: " + err, "error"));
    }

    function bindUI() {
        ["mouth", "head", "tail"].forEach(motor => {
            const btn = document.getElementById(`test-${motor}-btn`);
            if (btn) {
                btn.addEventListener("click", function () { sendMotorTest(motor); });
            }
        });
    }

    return {bindUI};
})();


