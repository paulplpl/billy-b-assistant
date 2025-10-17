// ===================== APP CONFIG (single fetch) =====================
const AppConfig = (() => {
    let cfg = null;
    let promise = null;

    const load = () => {
        if (promise) return promise;
        promise = fetch("/config")
            .then(r => r.json())
            .then(j => (cfg = j))
            .catch(e => {
                console.warn("Failed to load /config:", e);
                cfg = {};
                return cfg;
            });
        return promise;
    };

    const refresh = () => {
        // Force reload configuration from server
        promise = null;
        return load();
    };

    const get = () => cfg || {};
    return { load, refresh, get };
})();


