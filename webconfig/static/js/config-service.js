// ===================== CONFIG SERVICE =====================
const ConfigService = (() => {
    let configCache = null;
    let lastFetch = 0;
    const CACHE_DURATION = 2000; // 2 seconds cache

    const fetchConfig = async (forceRefresh = false) => {
        const now = Date.now();
        
        // Return cached data if still fresh
        if (!forceRefresh && configCache && (now - lastFetch) < CACHE_DURATION) {
            return configCache;
        }

        try {
            const res = await fetch("/config");
            const data = await res.json();
            configCache = data;
            lastFetch = now;
            return data;
        } catch (error) {
            console.error("Failed to fetch config:", error);
            return null;
        }
    };

    const getCachedConfig = () => configCache;

    const clearCache = () => {
        configCache = null;
        lastFetch = 0;
    };

    return { fetchConfig, getCachedConfig, clearCache };
})();
