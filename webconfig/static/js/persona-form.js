// ===================== PERSONA FORM =====================
const PersonaForm = (() => {
    const addBackstoryField = (key = "", value = "") => {
        const wrapper = document.createElement("div");
        wrapper.className = "flex items-center space-x-2";

        const keyInput = Object.assign(document.createElement("input"), {
            type: "text",
            value: key,
            placeholder: "Key",
            className: "w-1/3 p-1 bg-zinc-800 text-white rounded"
        });

        const valInput = Object.assign(document.createElement("input"), {
            type: "text",
            value: value,
            placeholder: "Value",
            className: "flex-1 p-1 bg-zinc-800 text-white rounded"
        });

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "text-rose-500 hover:text-rose-400 cursor-pointer";
        const icon = document.createElement("span");
        icon.className = "material-icons align-middle";
        icon.textContent = "remove_circle_outline";
        removeBtn.appendChild(icon);
        removeBtn.onclick = () => wrapper.remove();

        wrapper.append(keyInput, valInput, removeBtn);
        document.getElementById("backstory-fields").appendChild(wrapper);
    };

    const renderPersonalitySliders = (personality) => {
        const container = document.getElementById("personality-sliders");
        container.innerHTML = "";

        for (const [key, value] of Object.entries(personality)) {
            const wrapper = document.createElement("div");
            wrapper.className = "flex gap-2 space-y-1";

            const label = document.createElement("div");
            label.className = "flex w-36 justify-between items-center text-sm text-slate-300 font-semibold";
            label.innerHTML = `<span>${key}</span>`;

            const barContainer = document.createElement("div");
            barContainer.className = "relative w-full rounded-full bg-zinc-700 overflow-hidden cursor-pointer";
            barContainer.style.userSelect = "none";

            const fillBar = document.createElement("div");
            fillBar.className = "absolute left-0 top-0 h-full bg-emerald-500 transition-all duration-100";
            fillBar.style.width = `${value}%`;
            fillBar.dataset.fillFor = key;

            barContainer.appendChild(fillBar);

            const valueLabel = document.createElement("span");
            valueLabel.id = `${key}-value`;
            valueLabel.className = "text-zinc-400 w-4";
            valueLabel.textContent = value;

            let isDragging = false;
            const updateValue = (e) => {
                const rect = barContainer.getBoundingClientRect();
                const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
                const newVal = Math.round(percent * 100);
                fillBar.style.width = `${newVal}%`;
                valueLabel.textContent = newVal;
                fillBar.setAttribute("data-value", newVal);
            };

            barContainer.addEventListener("mousedown", (e) => {
                isDragging = true;
                updateValue(e);
            });
            document.addEventListener("mousemove", (e) => { if (isDragging) updateValue(e); });
            document.addEventListener("mouseup", () => { isDragging = false; });

            wrapper.appendChild(label);
            wrapper.appendChild(barContainer);
            wrapper.appendChild(valueLabel);
            container.appendChild(wrapper);
        }
    };

    function setupSlider(barId, fillId, inputId, min, max) {
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        const input = document.getElementById(inputId);

        let isDragging = false;
        const updateUI = (val) => {
            const percent = ((val - min) / (max - min)) * 100;
            fill.style.width = `${percent}%`;
            fill.dataset.value = val;
        };
        const updateFromMouse = (e) => {
            const rect = bar.getBoundingClientRect();
            const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
            const val = Math.round(min + percent * (max - min));
            input.value = val;
            input.dispatchEvent(new Event("input", {bubbles: true}));
            updateUI(val);
        };
        bar.addEventListener("mousedown", (e) => { isDragging = true; updateFromMouse(e); });
        document.addEventListener("mousemove", (e) => { if (isDragging) updateFromMouse(e); });
        document.addEventListener("mouseup", () => { isDragging = false; });
        input.addEventListener("input", () => updateUI(Number(input.value)));
        updateUI(Number(input.value));
    }

    setupSlider("mic-gain-bar", "mic-gain-fill", "mic-gain", 0, 16);
    setupSlider("speaker-volume-bar", "speaker-volume-fill",  "speaker-volume", 0, 100);

    const renderBackstoryFields = (backstory) => {
        const container = document.getElementById("backstory-fields");
        container.innerHTML = "";
        Object.entries(backstory).forEach(([k, v]) => addBackstoryField(k, v));
    };

    const loadPersona = async () => {
        const res = await fetch("/persona");
        const data = await res.json();
        renderPersonalitySliders(data.PERSONALITY);
        renderBackstoryFields(data.BACKSTORY);
        document.getElementById("meta-text").value = data.META || "";
        await loadWakeupClips();
    };

    const handlePersonaSave = () => {
        document.getElementById("persona-form").addEventListener("submit", async (e) => {
            e.preventDefault();

            const res = await fetch("/service/status");
            const {status: wasActive} = await res.json();

            const personality = {};
            document.querySelectorAll("#personality-sliders div[data-fill-for]").forEach((bar) => {
                const trait = bar.dataset.fillFor;
                personality[trait] = parseInt(bar.style.width);
            });

            const backstory = {};
            document.querySelectorAll("#backstory-fields > div").forEach((row) => {
                const [keyInput, valInput] = row.querySelectorAll("input");
                if (keyInput.value.trim() !== "") {
                    backstory[keyInput.value.trim()] = valInput.value.trim();
                }
            });

            const meta = document.getElementById("meta-text").value.trim();

            const wakeup = {};
            const rows = document.querySelectorAll("#wakeup-sound-list .flex[data-index]");
            let currentIndex = 1;
            rows.forEach((row) => {
                const phrase = row.querySelector("input[type='text']")?.value?.trim();
                if (phrase) { wakeup[currentIndex++] = phrase; }
            });

            await fetch("/persona", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({PERSONALITY: personality, BACKSTORY: backstory, META: meta, WAKEUP: wakeup })
            });

            showNotification("Persona saved", "success");
            
            if (wasActive === "active") {
                await fetch("/service/restart");
                showNotification("Persona saved – service restarted", "success");
                ServiceStatus.fetchStatus();
            }
            
            // Simulate "Restart UI" button behavior for persona changes
            try {
                const res = await fetch('/restart', {method: 'POST'});
                const data = await res.json();
                if (data.status === "ok") {
                    showNotification("Restarting UI to apply persona changes…", "success");
                    setTimeout(() => location.reload(), 3000);
                } else {
                    showNotification(data.error || "Restart failed", "error");
                }
            } catch (err) {
                showNotification(err.message, "error");
            }
        });
    };

    return {addBackstoryField, loadPersona, handlePersonaSave};
})();


