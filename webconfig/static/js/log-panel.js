// ===================== Header Secondary Actions (Log Panel) =====================
const LogPanel = (() => {
    let autoScrollEnabled = false;
    let isLogHidden = true;
    let isEnvHidden = true;
    let isReleaseHidden = true;

    const rebootBilly = async () => {
        if (!confirm("Are you sure you want to reboot Billy? This will reboot the whole system.")) return;
        try {
            const res = await fetch('/reboot', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is rebooting!", "success");
                setTimeout(() => { location.reload(); }, 15000);
            } else {
                showNotification(data.error || "Reboot failed", "error");
            }
        } catch (err) {
            console.error("Failed to reboot Billy:", err);
            showNotification("Failed to reboot Billy", "error");
        }
    };

    const shutdownBilly = async () => {
        if (!confirm("Are you sure you want to shutdown Billy?\n\nThis will power off the Raspberry Pi but one or more of the motors may remain engaged.\nTo fully power down, make sure to also switch off or unplug the power supply after shutdown.")) return;
        try {
            const res = await fetch('/shutdown', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is shutting down!", "success");
                setTimeout(() => { location.reload(); }, 3000);
            } else {
                showNotification(data.error || "Shutdown failed", "error");
            }
        } catch (err) {
            console.error("Failed to shutdown Billy:", err);
            showNotification("Failed to shutdown Billy", "error");
        }
    };

    const restartUI = async () => {
        try {
            const res = await fetch('/restart', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Restarting UI…", "success");
                setTimeout(() => location.reload(), 3000);
            } else {
                showNotification(data.error || "Restart failed", "error");
            }
        } catch (err) {
            showNotification(err.message, "error");
        }
    };

    const changePassword = async (newPassword, confirmPassword) => {
        try {
            const res = await fetch('/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    new_password: newPassword,
                    confirm_password: confirmPassword
                })
            });
            
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Password changed successfully! Reloading page...", "success");
                // Reload page to pick up the new CHANGED_DEFAULT_PASS config
                setTimeout(() => location.reload(), 2000);
                return true;
            } else {
                showNotification(data.error || "Password change failed", "error");
                return false;
            }
        } catch (err) {
            console.error("Failed to change password:", err);
            showNotification("Failed to change password", "error");
            return false;
        }
    };

    const showPasswordModal = () => {
        const modal = document.getElementById("password-modal");
        const form = document.getElementById("password-form");
        const closeBtn = document.getElementById("close-password-modal");
        
        // Clear form
        form.reset();
        
        // Show modal
        modal.classList.remove("hidden");
        
        // Close modal handlers
        const closeModal = () => {
            modal.classList.add("hidden");
            form.reset();
        };
        
        closeBtn.addEventListener("click", closeModal);
        
        // Close on backdrop click
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        // Handle form submission
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const newPassword = formData.get("new_password");
            const confirmPassword = formData.get("confirm_password");
            
            // Validate passwords match
            if (newPassword !== confirmPassword) {
                showNotification("New passwords do not match", "error");
                return;
            }
            
            // Validate password length
            if (newPassword.length < 8) {
                showNotification("New password must be at least 8 characters long", "error");
                return;
            }
            
            // Change password
            const success = await changePassword(newPassword, confirmPassword);
            if (success) {
                closeModal();
            }
        });
    };

    const checkAndShowPasswordModal = (cfg) => {
        // Show modal automatically if FORCE_PASS_CHANGE is true
        if (cfg.FORCE_PASS_CHANGE === 'True' || cfg.FORCE_PASS_CHANGE === 'true' || cfg.FORCE_PASS_CHANGE === true) {
            setTimeout(() => {
                showPasswordModal();
            }, 1000); // Small delay to let page load
        }
    };



    const applyLogLevel = async () => {
        const logLevelSelect = document.getElementById("log-level-select");
        const selectedLevel = logLevelSelect.value;

        try {
            const res = await fetch("/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({LOG_LEVEL: selectedLevel})
            });
            const data = await res.json();
            if (data.status === "ok") {
                showNotification(`Log level changed to ${selectedLevel}. Restarting Billy`, "success");
                
                // Restart both Billy service and webconfig service
                setTimeout(async () => {
                    try {
                        // Restart both services
                        await fetch("/restart", {method: "POST"});
                        
                    } catch (restartErr) {
                        console.error("Failed to restart services:", restartErr);
                        showNotification("Log level saved but restart failed. Please restart manually.", "warning");
                    }
                }, 1000);
                
            } else {
                showNotification(data.error || "Failed to change log level", "error");
            }
        } catch (err) {
            console.error("Failed to change log level:", err);
            showNotification("Failed to change log level", "error");
        }
    };

    const fetchLogs = async () => {
        const res = await fetch("/logs");
        const data = await res.json();
        const logOutput = document.getElementById("log-output");
        const logContainer = document.getElementById("log-container");
        logOutput.textContent = data.logs || "No logs found.";
        if (autoScrollEnabled) {
            requestAnimationFrame(() => {
                logContainer.scrollTop = logContainer.scrollHeight;
            });
        }
    };

    const toggleLogPanel = () => {
        isLogHidden = !isLogHidden;
        elements.logPanel.classList.toggle("hidden", isLogHidden);
        elements.toggleBtn.classList.toggle("bg-cyan-500", !isLogHidden);
        elements.toggleBtn.classList.toggle("bg-zinc-700", isLogHidden);
    };

    const toggleEnvPanel = () => {
        isEnvHidden = !isEnvHidden;
        elements.envPanel.classList.toggle("hidden", isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-amber-500", !isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-zinc-700", isEnvHidden);
        if (!isEnvHidden) {
            fetch('/get-env')
                .then(res => res.text())
                .then(text => elements.envTextarea.value = text.trim())
                .catch(() => showNotification("An error occurred while loading .env", "error"));
        }
    };


    const toggleReleasePanel = () => {
        isReleaseHidden = !isReleaseHidden;
        elements.releasePanel.classList.toggle("hidden", isReleaseHidden);
        elements.toggleReleaseBtn.classList.toggle("bg-emerald-500", !isReleaseHidden);
        elements.toggleReleaseBtn.classList.toggle("hover:bg-emerald-400", !isReleaseHidden);
        elements.toggleReleaseBtn.classList.toggle("text-black", !isReleaseHidden);
        elements.toggleReleaseBtn.classList.toggle("bg-zinc-700", isReleaseHidden);
        elements.toggleReleaseBtn.classList.toggle("hover:bg-zinc-600", isReleaseHidden);
    };

    const toggleMotion = () => {
        const btn = elements.toggleMotionBtn;
        const icon = btn.querySelector(".material-icons");
        btn.classList.toggle("bg-zinc-700");
        document.documentElement.classList.toggle("reduce-motion");
        const isReduced = document.documentElement.classList.contains("reduce-motion");
        localStorage.setItem("reduceMotion", isReduced ? "1" : "0");
        if (icon) icon.textContent = isReduced ? "blur_off" : "blur_on";
    };

    const toggleFullscreenLog = () => {
        const icon = document.getElementById("fullscreen-icon");
        const isFullscreen = elements.logContainer.classList.toggle("log-fullscreen");
        icon.textContent = isFullscreen ? "fullscreen_exit" : "fullscreen";
    };

    const toggleAutoScroll = () => {
        autoScrollEnabled = !autoScrollEnabled;
        elements.scrollBtn.classList.toggle("bg-cyan-500", autoScrollEnabled);
        elements.scrollBtn.classList.toggle("bg-zinc-800", !autoScrollEnabled);
        elements.scrollBtn.title = autoScrollEnabled ? "Auto-scroll ON" : "Auto-scroll OFF";
        if (autoScrollEnabled) {
            elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
        }
    };

    const saveEnv = async () => {
        if (!confirm("Are you sure you want to overwrite the .env file? This may affect how Billy runs.")) return;
        try {
            const res = await fetch('/save-env', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: elements.envTextarea.value})
            });
            const data = await res.json();
            if (data.status === "ok") {
                fetch('/restart', {method: 'POST'})
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "ok") {
                            showNotification(".env saved. Restarting", "success");
                            setTimeout(() => location.reload(), 3000);
                        } else {
                            showNotification(data.error || "Restart failed", "error");
                        }
                    })
                    .catch(err => showNotification(err.message, "error"));
            } else {
                showNotification(data.error || "Unknown error", "error");
            }
        } catch (err) {
            showNotification(err.message, "error");
        }
    };

    const hideSupportPanelIfDisabled = (cfg) => {
        // Hide support section if SHOW_SUPPORT is false
        const show = String(cfg.SHOW_SUPPORT || "").toLowerCase() === "true";
        const supportSection = document.getElementById("support-section");
        
        if (supportSection) {
            if (show) {
                supportSection.style.display = "block";
            } else {
                supportSection.style.display = "none";
            }
        }
    };

    let elements = {};
    const bindUI = (cfg = {}) => {
        elements = {
            logOutput: document.getElementById("log-output"),
            logContainer: document.getElementById("log-container"),
            toggleFullscreenBtn: document.getElementById("toggle-fullscreen-btn"),
            scrollBtn: document.getElementById("scroll-bottom-btn"),
            toggleBtn: document.getElementById("toggle-log-btn"),
            logPanel: document.getElementById("log-panel"),
            toggleEnvBtn: document.getElementById("toggle-env-btn"),
            envPanel: document.getElementById("env-panel"),
            envTextarea: document.getElementById("env-textarea"),
            saveEnvBtn: document.getElementById("save-env-btn"),
            toggleMotionBtn: document.getElementById("toggle-motion-btn"),
            powerBtn: document.getElementById("power-btn"),
            powerDropdown: document.getElementById("power-dropdown"),
            rebootBillyBtn: document.getElementById("reboot-billy-btn"),
            restartUIBtn: document.getElementById("restart-ui-btn"),
            shutdownBillyBtn: document.getElementById("shutdown-billy-btn"),
            toggleReleaseBtn: document.getElementById("current-version"),
            releasePanel: document.getElementById("release-panel"),
            releaseTitle: document.getElementById("release-title"),
            releaseBody: document.getElementById("release-body"),
            releaseLink: document.getElementById("release-link"),
            releaseClose: document.getElementById("release-close"),
            releaseMarkRead: document.getElementById("release-mark-read"),
            releaseBadge: document.getElementById("release-badge"),
        };


        elements.powerBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            elements.powerDropdown?.classList.toggle("hidden");
        });

        document.addEventListener("click", (e) => {
            const menu = document.getElementById("power-menu");
            if (!menu?.contains(e.target)) {
                elements.powerDropdown?.classList.add("hidden");
            }
        });

        elements.toggleBtn.addEventListener("click", toggleLogPanel);
        elements.toggleFullscreenBtn.addEventListener("click", toggleFullscreenLog);
        elements.scrollBtn.addEventListener("click", toggleAutoScroll);
        elements.toggleEnvBtn.addEventListener("click", toggleEnvPanel);
        elements.toggleMotionBtn.addEventListener("click", toggleMotion);
        elements.saveEnvBtn.addEventListener("click", saveEnv);
        elements.rebootBillyBtn.addEventListener("click", rebootBilly);
        elements.restartUIBtn.addEventListener("click", restartUI);
        elements.shutdownBillyBtn.addEventListener("click", shutdownBilly);
        
        // Log level control
        const applyLogLevelBtn = document.getElementById("apply-log-level-btn");
        applyLogLevelBtn?.addEventListener("click", applyLogLevel);
        
        // Set current log level in dropdown
        const logLevelSelect = document.getElementById("log-level-select");
        if (logLevelSelect && cfg.LOG_LEVEL) {
            logLevelSelect.value = cfg.LOG_LEVEL;
        }
        elements.toggleReleaseBtn?.addEventListener("click", toggleReleasePanel);
        elements.releaseClose?.addEventListener("click", () => {
            isReleaseHidden = true;
            elements.releasePanel.classList.add("hidden");
            elements.toggleReleaseBtn.classList.remove("bg-emerald-500","hover:bg-emerald-400","text-black");
            elements.toggleReleaseBtn.classList.add("bg-zinc-700","hover:bg-zinc-600","text-white");
        });

        if (localStorage.getItem("reduceMotion") === "1") {
            document.documentElement.classList.add("reduce-motion");
            const btn = elements.toggleMotionBtn;
            const icon = btn.querySelector(".material-icons");
            btn.classList.remove("bg-zinc-700");
            if (icon) icon.textContent = "blur_off";
        }

        // Handle password change modal and button visibility
        checkAndShowPasswordModal(cfg);
        
        // Handle support panel visibility
        hideSupportPanelIfDisabled(cfg);
    };

    return {fetchLogs, bindUI, changePassword, showPasswordModal, checkAndShowPasswordModal, hideSupportPanelIfDisabled};
})();

// Make LogPanel available globally
window.LogPanel = LogPanel;


