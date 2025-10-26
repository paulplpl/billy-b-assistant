// ===================== AUDIO =====================
const AudioPanel = (() => {
    let micCheckSource = null;
    let serviceWasRunning = false; // Track if service was running before mic test

    const micCheckBtn = document.getElementById("mic-check-btn");
    if (micCheckBtn) {
        micCheckBtn.addEventListener("click", toggleMicCheck);
    }

    const speakerCheckBtn = document.getElementById("speaker-check-btn");
    if (speakerCheckBtn) {
        speakerCheckBtn.addEventListener("click", async () => {
        try {
            const data = await ServiceStatus.fetchStatus();
            if (data.status === "active") {
                showNotification("🛑 Stopping Billy service for speaker test...", "warning");
                
                // Stop the Billy service
                const stopResponse = await fetch("/restart", {method: "POST"});
                if (!stopResponse.ok) {
                    throw new Error("Failed to stop Billy service");
                }
                
                // Wait a moment for the service to stop
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                showNotification("✅ Billy service stopped. Running speaker test...", "success");
            }
            
            await fetch("/speaker-test", {method: "POST"});
            showNotification("🔊 Speaker test triggered");
        } catch (err) {
            console.error("Failed to trigger speaker test:", err);
            showNotification("Failed to trigger speaker test: " + err.message, "error");
        }
        });
    }

    async function toggleMicCheck() {
        const btn = micCheckBtn;
        const isActive = btn.classList.contains("bg-emerald-600");
        if (isActive) {
            stopMicCheck();
            btn.classList.remove("bg-emerald-600");
            btn.classList.add("bg-zinc-800");
            showNotification("Mic check stopped");
            
            // Restart service if it was running before
            if (serviceWasRunning) {
                try {
                    showNotification("🔄 Restarting Billy service...", "warning");
                    await fetch("/restart", {method: "POST"});
                    showNotification("✅ Billy service restarted", "success");
                    ServiceStatus.fetchStatus();
                } catch (err) {
                    console.error("Failed to restart Billy service:", err);
                    showNotification("❌ Failed to restart Billy service. Please restart manually.", "error");
                }
            }
        } else {
            try {
                const data = await ServiceStatus.fetchStatus();
                serviceWasRunning = (data.status === "active");
                
                if (serviceWasRunning) {
                    showNotification("🛑 Stopping Billy service for mic test...", "warning");
                    await fetch("/restart", {method: "POST"});
                    // Wait a moment for the service to stop
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    showNotification("✅ Billy service stopped. Starting mic test...", "success");
                }
                
                startMicCheck();
                btn.classList.remove("bg-zinc-800");
                btn.classList.add("bg-emerald-600");
                showNotification("🎤 Mic check started");
            } catch (err) {
                console.error("Failed to toggle mic check:", err);
                showNotification("Mic check failed: " + err.message, "error");
            }
        }
    }

    function stopMicCheck() {
        if (micCheckSource) micCheckSource.close();
        fetch("/mic-check/stop");
        micCheckSource = null;
        updateMicBar(0);
    }

    function startMicCheck() {
        let maxRms = 0;
        const SCALING_FACTOR = 32768;
        micCheckSource = new EventSource("/mic-check");
        micCheckSource.onmessage = (e) => {
            let data;
            try { data = JSON.parse(e.data); }
            catch (err) { console.error("Invalid JSON from /mic-check:", e.data); return; }
            if (data.error) { console.error("Mic check error:", data.error); return; }
            const rms = data.rms * SCALING_FACTOR;
            const threshold = data.threshold;
            maxRms = Math.max(maxRms, rms);
            const percent = Math.min((rms / threshold) * 100, 100);
            const thresholdPercent = Math.min((threshold / SCALING_FACTOR) * 100, 100);
            updateMicBar(percent, thresholdPercent);
        };
        micCheckSource.onerror = () => { console.error("Mic check connection error."); stopMicCheck(); };
    }

    function updateMicBar(percentage, thresholdPercent = 0) {
        const bar = document.getElementById("mic-level-bar");
        bar.style.width = `${percentage}%`;
        bar.classList.toggle("bg-zinc-500", percentage < thresholdPercent);
        bar.classList.toggle("bg-emerald-500", percentage < 70);
        bar.classList.toggle("bg-amber-500", percentage >= 70 && percentage < 90);
        bar.classList.toggle("bg-red-500", percentage >= 90);
    }

    async function loadMicGain() {
        const label = document.getElementById("mic-gain-value");
        const slider = document.getElementById("mic-gain");
        const fill = document.getElementById("mic-gain-fill");
        try {
            const res = await fetch("/mic-gain");
            const data = await res.json();
            if (data.gain !== undefined) {
                slider.value = data.gain;
                label.textContent = data.gain;
                const percent = (data.gain / 16) * 100;
                fill.style.width = `${percent}%`;
                fill.dataset.value = data.gain;
            } else {
                label.textContent = "Unavailable";
            }
        } catch (err) {
            label.textContent = "Error";
        }
    }

    const micGainElement = document.getElementById("mic-gain");
    if (micGainElement) {
        micGainElement.addEventListener("input", async () => {
            const value = parseInt(micGainElement.value, 10);
            await fetch("/mic-gain", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({value})
            });
            const micGainValue = document.getElementById("mic-gain-value");
            if (micGainValue) {
                micGainValue.textContent = value;
            }
        });
    }

    let micBar = document.getElementById("mic-bar-container");
    let thresholdLine = document.getElementById("threshold-line");
    let silenceThresholdInput = document.getElementById("SILENCE_THRESHOLD");
    
    if (thresholdLine && micBar && silenceThresholdInput) {
        let dragging = false;
        thresholdLine.addEventListener("mousedown", (e) => { dragging = true; e.preventDefault(); });
        document.addEventListener("mousemove", (e) => {
            if (!dragging) return;
            const rect = micBar.getBoundingClientRect();
            if (rect.width === 0) return;
            let offsetX = e.clientX - rect.left;
            offsetX = Math.max(0, Math.min(offsetX, rect.width));
            const percent = offsetX / rect.width;
            const scaledThreshold = Math.round(percent * 32768); // Convert to int16 range (0-32768)
            thresholdLine.style.left = `${percent * 100}%`;
            silenceThresholdInput.value = scaledThreshold;
        });
        document.addEventListener("mouseup", () => { dragging = false; });
        window.addEventListener("load", () => {
            const threshold = parseInt(silenceThresholdInput.value || "1000", 10);
            thresholdLine.style.left = `${(threshold / 32768) * 100}%`;
        });
    }

    const speakerSlider = document.getElementById("speaker-volume");
    if (speakerSlider) {
        fetch("/volume")
            .then(res => res.json())
            .then(data => {
                if (data.volume !== undefined) {
                    speakerSlider.value = data.volume;
                    const fill = document.getElementById("speaker-volume-fill");
                    if (fill) {
                        const percent = (data.volume / 100) * 100;
                        fill.style.width = `${percent}%`;
                        fill.dataset.value = data.volume;
                    }
                }
            });
        let volumeDebounceTimeout;
        speakerSlider.addEventListener("input", () => {
        clearTimeout(volumeDebounceTimeout);
        volumeDebounceTimeout = setTimeout(() => {
            fetch("/volume", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({volume: parseInt(speakerSlider.value)})
            }).catch(err => console.error("Failed to set speaker volume:", err));
        }, 500);
        });
    }

    async function updateDeviceLabels() {
        try {
            const res = await fetch("/device-info");
            const data = await res.json();
            const updateParentClass = (id, value) => {
                const el = document.getElementById(id);
                if (el && el.parentElement) {
                    el.textContent = value;
                    el.parentElement.classList.add("text-emerald-500");
                }
            };
            updateParentClass("mic-label", data.mic);
            updateParentClass("speaker-label", data.speaker);
        } catch (error) {
            console.error("Failed to fetch device info:", error);
        }
    }

    return {loadMicGain, updateDeviceLabels};
})();

// Make AudioPanel globally available
window.AudioPanel = AudioPanel;


