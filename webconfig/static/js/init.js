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
    PersonaForm.handlePersonaSave();
    window.addBackstoryField = PersonaForm.addBackstoryField;
    MotorPanel.bindUI();
    PinProfile.bindUI(cfg);
    Sections.collapsible();
    ReleaseNotes.init();
});


