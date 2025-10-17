// ===================== WAKEUP CLIPS =====================
async function loadWakeupClips() {
    const container = document.getElementById("wakeup-sound-list");
    container.innerHTML = "";
    try {
        const res = await fetch("/wakeup");
        const { clips } = await res.json();
        if (clips.length === 0) {
            const message = document.createElement("div");
            message.className = "text-sm text-zinc-400 italic py-2";
            message.textContent = "No custom wake-up clips added. Using the default sounds.";
            container.appendChild(message);
            return;
        } else {
            const label = document.createElement("label");
            label.className = "flex items-center justify-between font-semibold text-sm text-slate-300 mb-1";
            label.innerHtml = `Words or phrases that Billy will randomly say on activation:`;
            container.appendChild(label);
        }
        clips.sort((a, b) => a.index - b.index).forEach(({ index, phrase, has_audio }) => {
            const row = document.createElement("div");
            row.className = "flex items-center space-x-2";
            row.dataset.index = index;
            row.innerHTML = `
                <input type="text" class="text-input w-full rounded bg-zinc-800 border border-zinc-700 px-2 py-1" value="${phrase}">
                <button type="button" class="wakeup-generate-btn text-white hover:text-amber-400" title="Generate .wav">
                    <i class="material-icons align-middle">auto_fix_high</i>
                </button>
                <button type="button" class="wakeup-play-btn text-white hover:text-emerald-400 ${!has_audio ? 'invisible' : ''}" title="Play .wav">
                    <i class="material-icons align-middle">play_arrow</i>
                </button>
                <button type="button" class="remove-wakeup-row text-rose-500 hover:text-rose-400" title="Remove">
                    <i class="material-icons align-middle">remove_circle_outline</i>
                </button>
            `;
            container.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to load wakeup clips:", err);
        showNotification("Failed to load wakeup clips", "error");
    }
}

function addWakeupSound(index = null, phrase = "", hasAudio = false) {
    const container = document.getElementById("wakeup-sound-list");
    const rows = container.querySelectorAll("div[data-index]");
    const usedIndices = Array.from(rows).map(row => parseInt(row.dataset.index));
    const nextIndex = index ?? (usedIndices.length > 0 ? Math.max(...usedIndices) + 1 : 1);
    const row = document.createElement("div");
    row.className = "flex items-center space-x-2";
    row.dataset.index = nextIndex;
    row.innerHTML = `
        <input type="text" class="text-input w-full rounded bg-zinc-800 border border-zinc-700 px-2 py-1" value="${phrase}" placeholder="word or phrase">
        <button type="button" class="wakeup-generate-btn text-white hover:text-amber-400" title="Generate .wav">
            <i class="material-icons align-middle">auto_fix_high</i>
        </button>
        <button type="button" class="wakeup-play-btn text-white hover:text-emerald-400 ${!hasAudio ? 'invisible' : ''}" title="Play .wav">
            <i class="material-icons align-middle">play_arrow</i>
        </button>
        <button type="button" class="remove-wakeup-row text-rose-500 hover:text-rose-400" title="Remove">
            <i class="material-icons align-middle">remove_circle_outline</i>
        </button>
    `;
    container.appendChild(row);
}

document.getElementById("wakeup-sound-list").addEventListener("click", async (e) => {
    const row = e.target.closest(".flex");
    if (!row) return;
    const clipIndex = row.dataset.index;
    const input = row.querySelector("input[type='text']");
    const phrase = input?.value?.trim();

    if (e.target.closest(".wakeup-play-btn")) {
        const clipIndex = e.target.closest("div[data-index]")?.dataset.index;
        if (!clipIndex) return;
        const tryPlay = async () => {
            const res = await fetch("/wakeup/play", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(clipIndex) }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to play audio");
            showNotification(data.status, "success");
        };
        try {
            await tryPlay();
        } catch (err) {
            console.warn("Initial play failed, trying to stop service and retry:", err.message);
            try {
                await fetch("/service/stop");
                await ServiceStatus.fetchStatus();
                await tryPlay();
                showNotification("Billy was active. Stopped and retried clip.", "warning");
            } catch (retryErr) {
                console.error("Retry failed:", retryErr);
                showNotification("Play failed after retry: " + retryErr.message, "error");
            }
        }
        return;
    }

    if (e.target.closest(".wakeup-generate-btn")) {
        const generateBtn = e.target.closest("button");
        generateBtn.disabled = true;
        generateBtn.classList.add("opacity-50");
        generateBtn.querySelector("i").textContent = "hourglass_empty";
        if (!phrase) {
            showNotification("Please enter a phrase", "warning");
            return;
        }
        try {
            const res = await fetch("/wakeup/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: phrase, index: parseInt(clipIndex) }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || "Failed to generate audio");
            }
            const resPersona = await fetch("/persona/wakeup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: clipIndex, phrase: phrase }),
            });
            if (!resPersona.ok) {
                const err = await resPersona.json();
                throw new Error(err.error || "Failed to update persona");
            }
            showNotification(`Clip ${clipIndex} generated and saved!`, "success");
            await loadWakeupClips();
        } catch (err) {
            console.error("Generate error:", err);
            showNotification("Generate failed: " + err.message, "error");
        } finally {
            generateBtn.disabled = false;
            generateBtn.classList.remove("opacity-50");
            generateBtn.querySelector("i").textContent = "auto_fix_high";
        }
        return;
    }

    if (e.target.closest(".remove-wakeup-row")) {
        const row = e.target.closest("div[data-index]");
        const clipIndex = row?.dataset.index;
        if (!clipIndex) return;
        if (!confirm("Are you sure you want to delete this wake-up clip?")) return;
        try {
            const res = await fetch("/wakeup/remove", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(clipIndex) }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to remove clip");
            showNotification(`Clip ${clipIndex} removed`, "success");
            await loadWakeupClips();
        } catch (err) {
            console.error("Remove error:", err);
            showNotification("Remove failed: " + err.message, "error");
        }
    }
});


