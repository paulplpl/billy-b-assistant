// ===================== INITIALIZE =====================
document.addEventListener("DOMContentLoaded", async () => {
    const cfg = await AppConfig.load();
    LogPanel.bindUI(cfg);
    LogPanel.fetchLogs();
    ServiceStatus.fetchStatus();
    setInterval(LogPanel.fetchLogs, 5000);
    setInterval(ServiceStatus.fetchStatus, 10000);

    AudioPanel.updateDeviceLabels();
    PersonaForm.loadPersona();
    AudioPanel.loadMicGain();
    SettingsForm.handleSettingsSave();
    SettingsForm.saveDropdownSelections();
    SettingsForm.populateDropdowns(cfg);
    SettingsForm.initMouthArticulationSlider();
    PersonaForm.handlePersonaSave();
    PersonaForm.bindPersonaSelector();
    PersonaForm.populatePersonaSelector();
    window.addBackstoryField = PersonaForm.addBackstoryField;
    window.savePersonaAs = PersonaForm.savePersonaAs;
    window.PersonaForm = PersonaForm;
    
    // Sync persona with current user after PersonaForm is ready
    setTimeout(() => {
        if (window.syncPersonaWithCurrentUser) {
            window.syncPersonaWithCurrentUser();
        }
    }, 100);
    MotorPanel.bindUI();
    PinProfile.bindUI(cfg);
        if (window.UserProfilePanel && window.UserProfilePanel.bindUI) {
            window.UserProfilePanel.bindUI();
        }
    Sections.collapsible();
    ReleaseNotes.init();
});


