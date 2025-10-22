// ===================== SERVICE STATUS =====================
const ServiceStatus = (() => {
    let statusCache = null;
    let lastFetch = 0;
    const CACHE_DURATION = 2000; // 2 seconds cache

    const fetchStatus = async (forceRefresh = false) => {
        const now = Date.now();
        
        // Return cached data if still fresh
        if (!forceRefresh && statusCache && (now - lastFetch) < CACHE_DURATION) {
            updateServiceStatusUI(statusCache.status);
            return statusCache;
        }

        const res = await fetch("/service/status");
        const data = await res.json();
        statusCache = data;
        lastFetch = now;
        updateServiceStatusUI(data.status);
        return data;
    };

    const updateServiceStatusUI = (status) => {
        const statusEl = document.getElementById("service-status");
        const controlsEl = document.getElementById("service-controls");
        const logoEl = document.getElementById("status-logo");

        statusEl.textContent = `(${status})`;
        statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");

        let logoSrc = "/static/images/status-inactive.png";
        if (status === "active") {
            statusEl.classList.add("text-emerald-500");
            logoSrc = "/static/images/status-active.png";
        } else if (status === "inactive") {
            statusEl.classList.add("text-amber-500");
            logoSrc = "/static/images/status-inactive.png";
        } else if (status === "failed") {
            statusEl.classList.add("text-rose-500");
            logoSrc = "/static/images/status-inactive.png"; // fallback
        }

        if (logoEl) logoEl.src = logoSrc;

        controlsEl.innerHTML = "";
        const createButton = (label, action, color, iconName) => {
            const btn = document.createElement("button");
            btn.className = `flex items-center transition-all gap-1 bg-${color}-500 hover:bg-${color}-400 text-zinc-800 font-semibold py-1 px-2 rounded`;

            const icon = document.createElement("i");
            icon.className = "material-icons";
            icon.textContent = iconName;
            btn.appendChild(icon);

            const labelSpan = document.createElement("span");
            labelSpan.className = "hidden md:inline";
            labelSpan.textContent = label;
            btn.appendChild(labelSpan);

            btn.onclick = () => handleServiceAction(action);
            return btn;
        };

        if (status === "inactive" || status === "failed") {
            controlsEl.appendChild(createButton("Start", "start", "emerald", "play_arrow"));
        } else if (status === "active") {
            controlsEl.appendChild(createButton("Restart", "restart", "amber", "restart_alt"));
            controlsEl.appendChild(createButton("Stop", "stop", "rose", "stop"));
        } else {
            controlsEl.textContent = "Unknown status.";
        }
    };

    const handleServiceAction = async (action) => {
        const statusEl = document.getElementById("service-status");
        const logoEl = document.getElementById("status-logo");

        const statusMap = {
            restart: {text: "restarting", color: "text-amber-500", logo: "/static/images/status-starting.png"},
            stop:    {text: "stopping",   color: "text-rose-500",   logo: "/static/images/status-stopping.png"},
            start:   {text: "starting",   color: "text-emerald-500",logo: "/static/images/status-starting.png"}
        };

        if (statusMap[action]) {
            const {text, color, logo} = statusMap[action];
            statusEl.textContent = text;
            statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");
            statusEl.classList.add(color);
            if (logoEl) logoEl.src = logo;
        }

        try {
            await fetch(`/service/${action}`);
        } catch (err) {
            console.error(`Failed to ${action} service:`, err);
        }

        fetchStatus();
        LogPanel.fetchLogs();
    };

    const getCachedStatus = () => statusCache;

    return {fetchStatus, updateServiceStatusUI, getCachedStatus};
})();


