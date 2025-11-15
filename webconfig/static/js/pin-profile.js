// ===================== PIN PROFILE + HARDWARE VISIBILITY =====================
const PinProfile = (() => {
    function syncHardwareVisibility() {
        const pinSelect = document.getElementById('BILLY_PINS_SELECT');
        const modelRow  = document.getElementById('hardware-version-row');
        const modelSel  = document.getElementById('BILLY_MODEL');
        if (!pinSelect || !modelRow || !modelSel) return;

        const isNew = pinSelect.value === 'new';

        if (isNew) {
            modelRow.classList.add('hidden', 'force-hidden');
            if (!modelSel.dataset.prev) modelSel.dataset.prev = modelSel.value;
            modelSel.value = 'modern';
            modelSel.disabled = true;
        } else {
            modelRow.classList.remove('hidden', 'force-hidden');
            modelSel.disabled = false;
            if (modelSel.dataset.prev) modelSel.value = modelSel.dataset.prev;
        }
    }

    function bindUI(cfg = {}) {
        const sel = document.getElementById('BILLY_PINS_SELECT');
        if (!sel) return;

        const mode = String(cfg.BILLY_PINS || 'new').toLowerCase();
        sel.value = mode;
        sel.setAttribute('data-original', mode);

        sel.addEventListener('change', syncHardwareVisibility);
        syncHardwareVisibility();
    }

    return { bindUI };
})();


