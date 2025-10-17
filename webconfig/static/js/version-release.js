// ===================== VERSION & UPDATE =====================
(() => {
    fetch("/version")
        .then(res => res.json())
        .then(data => {
            const currentBtn = document.getElementById("current-version");
            if (currentBtn) {
                const label = currentBtn.querySelector(".label");
                if (label) label.textContent = `${data.current}`;
            }
            if (data.update_available) {
                const latestSpan = document.getElementById("latest-version");
                const updateBtn = document.getElementById("update-btn");
                if (latestSpan) {
                    latestSpan.textContent = `Update to: ${data.latest}`;
                    latestSpan.classList.remove("hidden");
                }
                if (updateBtn) {
                    updateBtn.classList.add('flex');
                    updateBtn.classList.remove("hidden");
                }
            }
        })
        .catch(err => { console.error("Failed to load version info", err); });

    document.getElementById("update-btn").addEventListener("click", () => {
        if (!confirm("Are you sure you want to update Billy to the latest version?")) return;
        showNotification("Update started");
        fetch("/update", {method: "POST"})
            .then(res => res.json())
            .then(data => {
                if (data.message) { showNotification(data.message); }
                let attempts = 0, maxAttempts = 24;
                const checkForUpdate = async () => {
                    try {
                        const res = await fetch("/version");
                        const data = await res.json();
                        if (data.update_available === false) {
                            showNotification("Update complete. Reloading...", "info");
                            setTimeout(() => location.reload(), 1500);
                            return;
                        }
                    } catch (err) {
                        console.error("Version check failed:", err);
                    }
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkForUpdate, 5000);
                    } else {
                        showNotification("Update timed out after 2 minutes. Reloading");
                        setTimeout(() => location.reload(), 1500);
                    }
                };
                setTimeout(checkForUpdate, 5000);
            })
            .catch(err => {
                console.error("Failed to update:", err);
                showNotification("Failed to update", "error");
            });
    });
})();

// ===================== RELEASE NOTES =====================
const ReleaseNotes = (() => {
    const keyFor = (tag) => `release_notice_read_${tag}`;
    const els = {
        panel:       () => document.getElementById("release-panel"),
        title:       () => document.getElementById("release-title"),
        body:        () => document.getElementById("release-body"),
        link:        () => document.getElementById("release-link"),
        markReadBtn: () => document.getElementById("release-mark-read"),
        closeBtn:    () => document.getElementById("release-close"),
        badge:       () => document.getElementById("release-badge"),
        toggleBtn:   () => document.getElementById("current-version"),
    };

    async function fetchNote() {
        const res = await fetch("/release-note");
        if (!res.ok) throw new Error("Failed to fetch /release-note");
        return res.json();
    }
    function isRead(tag) { return localStorage.getItem(keyFor(tag)) === "1"; }
    function markRead(tag) {
        localStorage.setItem(keyFor(tag), "1");
        const badge = els.badge(); if (badge) badge.classList.add("!hidden");
        const mark = els.markReadBtn(); if (mark) mark.classList.add("!hidden");
        showNotification("Marked release notes as read", "success");
    }
    function render(note) {
        const t = els.title(); const b = els.body(); const l = els.link();
        const mark = els.markReadBtn(); const badge = els.badge();
        if (t) t.textContent = `Release Notes – ${note.tag}`;
        if (b) b.innerHTML = marked.parse(note.body || "No content.");
        if (l) {
            if (note.url) { l.href = note.url; l.classList.remove("hidden"); }
            else { l.classList.add("hidden"); }
        }
        const read = isRead(note.tag);
        if (badge) badge.classList.toggle("!hidden", read);
        if (mark) mark.classList.toggle("!hidden", read);
        if (mark && !read) { mark.onclick = () => markRead(note.tag); }
        const close = els.closeBtn();
        if (close) {
            close.onclick = () => {
                const panel = els.panel(); const btn = els.toggleBtn();
                if (panel) panel.classList.add("hidden");
                if (btn) { btn.classList.remove("bg-emerald-500", "hover:bg-emerald-400", "text-black"); btn.classList.add("bg-zinc-700", "hover:bg-zinc-600"); }
            };
        }
    }
    async function init() {
        try { const note = await fetchNote(); render(note); }
        catch (e) { console.warn("Release notes unavailable:", e); const badge = els.badge(); if (badge) badge.classList.add("hidden"); }
    }
    return { init };
})();


