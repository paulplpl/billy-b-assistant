// ===================== CONSOLIDATED POLLING =====================
let lastKnownPersona = null;
let lastKnownPersonality = null;
let isInitialLoad = true;

const startConsolidatedPolling = () => {
    // Single polling system that handles all updates
    setInterval(async () => {
        try {
            // Use status endpoint for all polling needs
            const response = await fetch('/service/status');
            const status = await response.json();
            
            // Handle persona changes (skip on initial load to avoid conflicts)
            if (status.current_persona && status.current_persona !== lastKnownPersona) {
                // Only trigger notification if this is not the initial load
                // Initial load is handled by loadUserPersona() in settings-panel.js
                if (!isInitialLoad && window.PersonaForm && window.PersonaForm.handlePersonaChangeNotification) {
                    window.PersonaForm.handlePersonaChangeNotification(status.current_persona);
                }
                lastKnownPersona = status.current_persona;
                isInitialLoad = false;
            }
            
            // Handle personality changes
            if (status.current_personality && JSON.stringify(status.current_personality) !== JSON.stringify(lastKnownPersonality)) {
                // Only trigger notification if this is not the initial load
                if (!isInitialLoad && window.PersonaForm && window.PersonaForm.handlePersonalityChange) {
                    window.PersonaForm.handlePersonalityChange(status.current_personality);
                }
                lastKnownPersonality = status.current_personality;
                isInitialLoad = false;
            }
            
            // Update service status UI
            if (window.ServiceStatus && window.ServiceStatus.updateServiceStatusUI) {
                window.ServiceStatus.updateServiceStatusUI(status.status);
            }
            
            // Let other components handle their own updates via status
            if (window.UserProfilePanel && window.UserProfilePanel.checkStatus) {
                await window.UserProfilePanel.checkStatus(status);
            }
            
        } catch (error) {
            console.error('Failed to poll for changes:', error);
        }
    }, 3000); // Poll every 3 seconds instead of 1 second
};

// ===================== INITIALIZE =====================
document.addEventListener("DOMContentLoaded", async () => {
    const cfg = await AppConfig.load();
    LogPanel.bindUI(cfg);
    LogPanel.fetchLogs();
    ServiceStatus.fetchStatus();
    setInterval(LogPanel.fetchLogs, 10000); // Reduced frequency: every 10 seconds
    // ServiceStatus polling is now handled by consolidated polling

    if (typeof AudioPanel !== 'undefined') {
        AudioPanel.updateDeviceLabels();
        AudioPanel.loadMicGain();
    }
    PersonaForm.loadPersona();
    SettingsForm.handleSettingsSave();
    SettingsForm.saveDropdownSelections();
    SettingsForm.populateDropdowns(cfg);
    SettingsForm.initMouthArticulationSlider();
    PersonaForm.handlePersonaSave();
    PersonaForm.bindPersonaSelector();
    PersonaForm.populatePersonaSelector();
    PersonaForm.initPersonaMouthArticulationSlider();
    window.addBackstoryField = PersonaForm.addBackstoryField;
    window.savePersonaAs = PersonaForm.savePersonaAs;
    window.PersonaForm = PersonaForm;
    
    // Sync persona with current user after PersonaForm is ready
    setTimeout(() => {
        if (window.syncPersonaWithCurrentUser) {
            window.syncPersonaWithCurrentUser();
        }
    }, 100);
    
    // Start consolidated polling for all changes
    startConsolidatedPolling();
    MotorPanel.bindUI();
    PinProfile.bindUI(cfg);
        if (window.UserProfilePanel && window.UserProfilePanel.bindUI) {
            window.UserProfilePanel.bindUI();
        }
    Sections.collapsible();
    ReleaseNotes.init();
    SongsManager.init();
    
    // Initialize Create Persona Modal
    if (window.PersonaForm && window.PersonaForm.initCreatePersonaModal) {
        window.PersonaForm.initCreatePersonaModal();
    }
});


