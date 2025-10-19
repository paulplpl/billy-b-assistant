// ===================== SETTINGS FORM =====================
const SettingsForm = (() => {
    const populateDropdowns = (cfg) => {
        // Populate dropdown values with saved configuration
        const dropdowns = [
            { id: 'OPENAI_MODEL', key: 'OPENAI_MODEL' },
            { id: 'VOICE', key: 'VOICE' },
            { id: 'RUN_MODE', key: 'RUN_MODE' },
            { id: 'TURN_EAGERNESS', key: 'TURN_EAGERNESS' },
            { id: 'BILLY_MODEL', key: 'BILLY_MODEL' },
            { id: 'BILLY_PINS_SELECT', key: 'BILLY_PINS' },
            { id: 'HA_LANG', key: 'HA_LANG' }
        ];

        dropdowns.forEach(({ id, key }) => {
            const element = document.getElementById(id);
            if (element) {
                // First try to get from localStorage (user's last selection)
                const savedValue = localStorage.getItem(`dropdown_${id}`);
                // Then fall back to config value
                const configValue = cfg[key];
                // Use saved value if it exists, otherwise use config value
                const valueToSet = savedValue || configValue;
                
                if (valueToSet) {
                    element.value = valueToSet;
                }
            }
        });
    };

    const saveDropdownSelections = () => {
        // Save dropdown selections to localStorage when they change
        const dropdowns = [
            'OPENAI_MODEL', 'VOICE', 'RUN_MODE', 'TURN_EAGERNESS', 
            'BILLY_MODEL', 'BILLY_PINS_SELECT', 'HA_LANG'
        ];

        dropdowns.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    localStorage.setItem(`dropdown_${id}`, element.value);
                });
            }
        });
    };

    const handleSettingsSave = () => {
        document.getElementById("config-form").addEventListener("submit", async function (e) {
            e.preventDefault();

            const resStatus = await fetch("/service/status");
            await resStatus.json(); // Check service status

            const formData = new FormData(this);
            const payload = Object.fromEntries(formData.entries());

            const flaskPortInput = document.getElementById("FLASK_PORT");
            const oldPort = parseInt(flaskPortInput.getAttribute("data-original")) || 80;
            const newPort = parseInt(payload["FLASK_PORT"] || "80");

            const hostnameInput = document.getElementById("hostname");
            const oldHostname = (hostnameInput.getAttribute("data-original") || hostnameInput.defaultValue || "").trim();
            const newHostname = (formData.get("hostname") || "").trim();

            const pinSelect = document.getElementById("BILLY_PINS_SELECT");
            if (pinSelect) {
                payload.BILLY_PINS = pinSelect.value; // "new" | "legacy"
            }

            // Manually add MOUTH_ARTICULATION value
            const mouthArticulationInput = document.getElementById("MOUTH_ARTICULATION");
            if (mouthArticulationInput) {
                payload.MOUTH_ARTICULATION = mouthArticulationInput.value;
            }

            let hostnameChanged = false;

            const saveResponse = await fetch("/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const saveResult = await saveResponse.json();
            const portChanged = saveResult.port_changed || (oldPort !== newPort);

            if (newHostname && newHostname !== oldHostname) {
                const hostResponse = await fetch("/hostname", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({hostname: newHostname})
                });
                const hostResult = await hostResponse.json();
                if (hostResult.hostname) {
                    hostnameChanged = true;
                    showNotification(`Hostname updated to ${hostResult.hostname}.local`, "success", 5000);
                }
            }

            await fetch("/service/restart");
            showNotification("Settings saved – Billy restarted", "success");
            
            // Clear localStorage since server values are now saved
            const dropdowns = [
                'OPENAI_MODEL', 'VOICE', 'RUN_MODE', 'TURN_EAGERNESS', 
                'BILLY_MODEL', 'BILLY_PINS_SELECT', 'HA_LANG'
            ];
            dropdowns.forEach(id => {
                localStorage.removeItem(`dropdown_${id}`);
            });
            
            // Simulate "Restart UI" button behavior for software settings
            try {
                const res = await fetch('/restart', {method: 'POST'});
                const data = await res.json();
                if (data.status === "ok") {
                    showNotification("Restarting UI to apply settings changes…", "success");
                    setTimeout(() => location.reload(), 3000);
                } else {
                    showNotification(data.error || "Restart failed", "error");
                }
            } catch (err) {
                showNotification(err.message, "error");
            }

            if (portChanged || hostnameChanged) {
                const targetHost = hostnameChanged ? `${newHostname}.local` : window.location.hostname;
                const targetPort = portChanged ? newPort : (window.location.port || 80);

                showNotification(`Redirecting to http://${targetHost}:${targetPort}/...`, "warning", 5000);
                setTimeout(() => {
                    window.location.href = `http://${targetHost}:${targetPort}/`;
                }, 3000);
            }
        });
    };

    fetch('/hostname')
        .then(res => res.json())
        .then(data => {
            if (data.hostname) {
                const input = document.getElementById('hostname');
                input.value = data.hostname;
                input.setAttribute('data-original', data.hostname);
            }
        });

    const flaskPortInput = document.getElementById("FLASK_PORT");
    if (flaskPortInput) {
        flaskPortInput.setAttribute("data-original", flaskPortInput.value);
    }

    const initMouthArticulationSlider = () => {
        // Use the same slider pattern as mic gain
        setupSlider("mouth-articulation-bar", "mouth-articulation-fill", "MOUTH_ARTICULATION", 1, 10);
    };

    function setupSlider(barId, fillId, inputId, min, max) {
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        const input = document.getElementById(inputId);

        if (!bar || !fill || !input) return;

        let isDragging = false;
        const updateUI = (val) => {
            const percent = ((val - min) / (max - min)) * 100;
            fill.style.width = `${percent}%`;
            fill.dataset.value = val;
            // Ensure input value is set for form submission
            input.value = val;
            input.setAttribute('value', val);
            // Update the value display
            const valueDisplay = document.getElementById("mouth-articulation-value");
            if (valueDisplay) {
                valueDisplay.textContent = val;
            }
        };
        const updateFromMouse = (e) => {
            const rect = bar.getBoundingClientRect();
            const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
            const val = Math.round(min + percent * (max - min));
            input.value = val;
            // Ensure the input value is properly set for form submission
            input.setAttribute('value', val);
            input.dispatchEvent(new Event("input", {bubbles: true}));
            updateUI(val);
        };
        bar.addEventListener("mousedown", (e) => { isDragging = true; updateFromMouse(e); });
        document.addEventListener("mousemove", (e) => { if (isDragging) updateFromMouse(e); });
        document.addEventListener("mouseup", () => { isDragging = false; });
        input.addEventListener("input", () => updateUI(Number(input.value)));
        updateUI(Number(input.value));
    }

    return {handleSettingsSave, populateDropdowns, saveDropdownSelections, initMouthArticulationSlider};
})();


