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

        // Define the core personality traits with descriptions
        const coreTraits = {
            'humor': 'Humor',
            'confidence': 'Confidence', 
            'warmth': 'Warmth',
            'curiosity': 'Curiosity',
            'verbosity': 'Talkative',
            'formality': 'Formal',
            'sarcasm': 'Sarcastic',
            'honesty': 'Honest'
        };

        // Default values for missing traits
        const defaultTraitValues = {
            'humor': 70,
            'confidence': 40,
            'warmth': 60,
            'curiosity': 50,
            'verbosity': 20,
            'formality': 50,
            'sarcasm': 60,
            'honesty': 100,
        };

        // Use core traits if personality is empty, otherwise filter to only include valid traits
        let traitsToRender = coreTraits;
        if (Object.keys(personality).length > 0) {
            // Filter personality to only include traits that are in our core set
            traitsToRender = {};
            for (const [key, value] of Object.entries(personality)) {
                if (coreTraits.hasOwnProperty(key)) {
                    traitsToRender[key] = value;
                }
            }
            // Add any missing core traits with default values
            for (const [key, displayName] of Object.entries(coreTraits)) {
                if (!traitsToRender.hasOwnProperty(key)) {
                    traitsToRender[key] = defaultTraitValues[key] || 50; // Use specific default or fallback
                }
            }
        }
        
        for (const [key, value] of Object.entries(traitsToRender)) {
            const wrapper = document.createElement("div");
            wrapper.className = "flex gap-2 space-y-1";

            const label = document.createElement("div");
            label.className = "flex w-36 justify-between items-center text-sm text-slate-300 font-semibold";
            const displayName = coreTraits[key] || key;
            label.innerHTML = `<span>${displayName}</span>`;

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

    const loadPersona = async (personaName = null) => {
        // If no persona specified, try to get current user's preferred persona
        if (!personaName) {
            try {
                const configData = await ConfigService.fetchConfig();
                if (configData && configData.CURRENT_USER && configData.CURRENT_USER.data && configData.CURRENT_USER.data.USER_INFO) {
                    personaName = configData.CURRENT_USER.data.USER_INFO.preferred_persona || 'default';
                } else {
                    personaName = 'default';
                }
            } catch (error) {
                console.error('Failed to get current user persona:', error);
                personaName = 'default';
            }
        }

        // Update the persona list to show the loaded persona
        updatePersonaListSelection(personaName);

        // Load the persona data
        const res = await fetch(`/persona/${personaName}`);
        const data = await res.json();
        
        if (data.error) {
            showNotification(`Failed to load persona: ${data.error}`, 'error');
            return;
        }

        renderPersonalitySliders(data.PERSONALITY);
        renderBackstoryFields(data.BACKSTORY);
        document.getElementById("meta-text").value = data.META?.instructions || "";
        
        // Load voice setting
        const voiceSelect = document.getElementById("VOICE");
        if (voiceSelect) {
            // Set voice from persona data, or default to 'ballad' if not specified
            const voice = data.META?.voice || 'ballad';
            voiceSelect.value = voice;
            console.log(`Loaded voice for ${personaName}: ${voice}`);
        }

        
        await loadWakeupClips();
    };


    const handlePersonaSave = () => {
        document.getElementById("persona-form").addEventListener("submit", async (e) => {
            e.preventDefault();

            // Check if the save button is disabled
            const saveButton = document.getElementById("save-persona-btn");
            if (saveButton && saveButton.disabled) {
                console.log("Save button is disabled, ignoring form submission");
                return;
            }

            // Check if the form submission was triggered by a disabled delete button
            const activeElement = document.activeElement;
            if (activeElement && activeElement.classList.contains('cursor-not-allowed') && 
                activeElement.classList.contains('opacity-50')) {
                console.log("Form submission triggered by disabled delete button, ignoring");
                return;
            }

            // Also check the event target for disabled delete buttons
            if (e.target && e.target.classList.contains('cursor-not-allowed') && 
                e.target.classList.contains('opacity-50')) {
                console.log("Form submission triggered by disabled delete button (event target), ignoring");
                return;
            }

            const statusData = await ServiceStatus.fetchStatus();
            const wasActive = statusData.status;

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
            const voice = document.getElementById("VOICE").value;

            const wakeup = {};
            const rows = document.querySelectorAll("#wakeup-sound-list .flex[data-index]");
            let currentIndex = 1;
            rows.forEach((row) => {
                const phrase = row.querySelector("input[type='text']")?.value?.trim();
                if (phrase) { wakeup[currentIndex++] = phrase; }
            });

            // Get the currently selected persona from the list
            const selectedRow = document.querySelector('#persona-list [data-persona].border-emerald-500');
            const personaName = selectedRow?.getAttribute('data-persona') || 'default';
            
            console.log('Saving persona:', personaName);
            console.log('Wake-up data:', wakeup);
            
            await fetch("/persona", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    persona_name: personaName,
                    PERSONALITY: personality, 
                    BACKSTORY: backstory, 
                    META: meta, 
                    VOICE: voice,
                    WAKEUP: wakeup 
                })
            });

            showNotification(`Persona "${personaName}" saved`, "success");
            
            // Refresh the persona list to show updated voice summary
            await populatePersonaSelector();
            
            // Always refresh the persona form to show updated values
            await loadPersona(personaName);
            
            if (wasActive === "active") {
                // Auto-refresh configuration instead of restarting services
                try {
                    const refreshResponse = await fetch("/config/auto-refresh", {method: "POST"});
                    const refreshData = await refreshResponse.json();
                    
                    if (refreshData.status === "ok") {
                        showNotification("Persona saved and applied", "success");
                        ServiceStatus.fetchStatus();
                    } else {
                        throw new Error(refreshData.error || "Auto-refresh failed");
                    }
                } catch (error) {
                    console.error("Auto-refresh failed, falling back to restart:", error);
                    // Fallback to restart if auto-refresh fails
                    await fetch("/restart", {method: "POST"});
                    showNotification("Persona saved – service restarted", "success");
                    ServiceStatus.fetchStatus();
                }
            }
        });
    };

    let isPopulatingPersonas = false;

    const populatePersonaSelector = async () => {
        const personaList = document.getElementById("persona-list");
        if (!personaList) return;

        // Prevent multiple simultaneous calls
        if (isPopulatingPersonas) {
            console.log('populatePersonaSelector already in progress, skipping...');
            return;
        }

        isPopulatingPersonas = true;
        console.log('Starting populatePersonaSelector...');

        try {
            const configData = await ConfigService.fetchConfig();
            if (configData && configData.AVAILABLE_PERSONAS) {
                personaList.innerHTML = '';
                
                // No guest mode restrictions - anyone with web UI access can manage personas
                
                // Get currently selected persona - check both user preference and form state
                let currentPersona = null;
                
                // First check if there's a currently selected persona in the form
                const selectedRow = document.querySelector('#persona-list [data-persona].border-emerald-500');
                if (selectedRow) {
                    currentPersona = selectedRow.getAttribute('data-persona');
                }
                
                // Fallback to user's preferred persona or default for guest mode
                if (!currentPersona) {
                    if (configData && configData.CURRENT_USER && typeof configData.CURRENT_USER === 'object' && configData.CURRENT_USER.data && configData.CURRENT_USER.data.USER_INFO) {
                        currentPersona = configData.CURRENT_USER.data.USER_INFO.preferred_persona || 'default';
                    } else {
                        // Guest mode or no current user - use default persona
                        currentPersona = 'default';
                    }
                }
                
                console.log('Current persona for delete button logic:', currentPersona);
                
                // Sort personas: default first, then custom ones
                const sortedPersonas = configData.AVAILABLE_PERSONAS.sort((a, b) => {
                    if (a.name === 'default') return -1;
                    if (b.name === 'default') return 1;
                    return a.name.localeCompare(b.name);
                });
                
                // Load voice information for each persona
                const personasWithVoice = await Promise.all(sortedPersonas.map(async (persona) => {
                    try {
                        const response = await fetch(`/persona/${persona.name}`);
                        const data = await response.json();
                        return {
                            ...persona,
                            voice: data.META?.voice || 'ballad'
                        };
                    } catch (error) {
                        console.error(`Failed to load voice for ${persona.name}:`, error);
                        return {
                            ...persona,
                            voice: 'ballad'
                        };
                    }
                }));
                
                personasWithVoice.forEach(persona => {
                    const row = document.createElement('div');
                    row.className = 'flex items-center justify-between p-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors cursor-pointer border border-zinc-700';
                    row.setAttribute('data-persona', persona.name);
                    
                    const isDefault = persona.name === 'default';
                    const isCurrentPersona = persona.name === currentPersona;
                    
                    // Check if this persona is preferred by any user across all profiles
                    let isPreferredPersona = false;
                    if (configData && configData.AVAILABLE_PROFILES) {
                        isPreferredPersona = configData.AVAILABLE_PROFILES.some(profile => 
                            profile.data && profile.data.USER_INFO && 
                            profile.data.USER_INFO.preferred_persona === persona.name
                        );
                    }
                    
                    console.log(`Persona ${persona.name}: isDefault=${isDefault}, isCurrentPersona=${isCurrentPersona}, isPreferredPersona=${isPreferredPersona}, currentPersona=${currentPersona}`);
                    console.log('Available profiles data:', configData.AVAILABLE_PROFILES);
                    
                    row.innerHTML = `
                        <div class="flex items-center space-x-3">
                            <span class="material-icons ${isCurrentPersona ? 'text-emerald-400' : 'text-zinc-400'}">set_meal</span>
                            <div>
                                <div class="text-white font-medium">${persona.description || persona.name}</div>
                                <div class="text-xs text-zinc-400">${persona.name} • Voice: ${persona.voice}</div>
                            </div>
                        </div>
                        <div class="flex items-center space-x-2">
        ${!isDefault ? `
          <button class="${isCurrentPersona || isPreferredPersona ? 'text-gray-400 cursor-not-allowed opacity-50' : 'text-rose-400 hover:text-rose-300'} p-1 rounded transition-colors" 
                  onclick="event.stopPropagation(); ${isCurrentPersona || isPreferredPersona ? 'window.PersonaForm.showPreferredPersonaDeleteMessage()' : `window.PersonaForm.deletePersona('${persona.name}')`}" 
                  title="${isCurrentPersona || isPreferredPersona ? 'Cannot delete preferred persona' : 'Delete persona'}">
              <span class="material-icons text-sm">delete</span>
          </button>
      ` : ''}
                            <span class="material-icons text-zinc-400 text-sm">chevron_right</span>
                        </div>
                    `;
                    
                    // Add click handler to load persona
                    row.addEventListener('click', async () => {
                        await loadPersona(persona.name);
                    });
                    
                    personaList.appendChild(row);
                });
                
                // Update the selection to show the current persona as active
                updatePersonaListSelection(currentPersona);
            }
        } catch (error) {
            console.error('Failed to load available personas:', error);
        } finally {
            isPopulatingPersonas = false;
            console.log('Finished populatePersonaSelector');
        }
    };

    const deletePersona = async (personaName) => {
        if (personaName === 'default') {
            showNotification('Cannot delete the default persona', 'error');
            return;
        }

        if (!confirm(`Are you sure you want to delete the "${personaName}" persona? This action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`/persona/${personaName}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showNotification(`Persona deleted: ${personaName}`, 'success');
                // Clear persona cache to ensure fresh data
                if (window.PersonaForm && window.PersonaForm.clearPersonaCache) {
                    window.PersonaForm.clearPersonaCache();
                }
                // Reload the persona list
                await populatePersonaSelector();
                // Load default persona if the deleted one was currently loaded
                await loadPersona('default');
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to delete persona', 'error');
            }
        } catch (error) {
            console.error('Failed to delete persona:', error);
            showNotification('Failed to delete persona', 'error');
        }
    };

    const updatePersonaListSelection = (selectedPersonaName) => {
        const personaList = document.getElementById("persona-list");
        if (!personaList) return;

        // Remove active class from all rows
        const rows = personaList.querySelectorAll('[data-persona]');
        rows.forEach(row => {
            row.classList.remove('border-emerald-500', 'bg-emerald-900/20');
            row.classList.add('border-zinc-700');
        });

        // Add active class to selected row
        const selectedRow = personaList.querySelector(`[data-persona="${selectedPersonaName}"]`);
        if (selectedRow) {
            selectedRow.classList.remove('border-zinc-700');
            selectedRow.classList.add('border-emerald-500', 'bg-emerald-900/20');
        }
    };

    const bindPersonaSelector = () => {
        // No longer needed since personas are loaded on click
        // But keeping the function for consistency
    };

    const savePersonaAs = async () => {
        const personaName = prompt('Enter a name for the new persona:\n(This will create a copy of the current persona)');
        if (!personaName || personaName.trim() === '') {
            return;
        }

        // Clean the name: lowercase and remove special characters except hyphens and underscores
        const cleanName = personaName.trim().toLowerCase().replace(/[^a-z0-9\-_]/g, '');
        
        if (cleanName === '') {
            showNotification('Invalid persona name. Please use only letters, numbers, hyphens, and underscores.', 'error');
            return;
        }

        // Check if persona already exists
        try {
            const response = await fetch(`/persona/${cleanName}`);
            if (response.ok) {
                if (!confirm(`A persona named "${cleanName}" already exists. Do you want to overwrite it?`)) {
                    return;
                }
            }
        } catch (error) {
            // Persona doesn't exist, which is fine
        }

        try {
            // Show loading state
            const saveButton = document.getElementById('save-persona-btn');
            const originalText = saveButton.innerHTML;
            saveButton.innerHTML = '<span class="material-icons animate-spin">refresh</span> Saving...';
            saveButton.disabled = true;
            
            // Get current persona data using the same logic as handlePersonaSave
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
            const voice = document.getElementById("VOICE").value;

            const wakeup = {};
            const rows = document.querySelectorAll("#wakeup-sound-list .flex[data-index]");
            let currentIndex = 1;
            rows.forEach((row) => {
                const phrase = row.querySelector("input[type='text']")?.value?.trim();
                if (phrase) { wakeup[currentIndex++] = phrase; }
            });

            const personaData = {
                PERSONALITY: personality,
                BACKSTORY: backstory,
                META: {
                    name: cleanName,
                    description: personaName.trim(),
                    instructions: meta,
                    voice: voice
                },
                VOICE: voice,
                WAKEUP: wakeup
            };

            // Ensure VOICE is at the top level for backend compatibility

            // Save the persona
            const saveResponse = await fetch('/persona', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...personaData,
                    persona_name: cleanName,
                    VOICE: voice
                })
            });

            if (saveResponse.ok) {
                showNotification(`Persona "${personaName}" saved successfully!`, 'success');
                
                // Refresh the persona selector to show the new persona
                await populatePersonaSelector();
                
                // Load the new persona (this will switch to it and show it as active)
                await loadPersona(cleanName);
                
                // Show additional notification that we're now editing the new persona
                setTimeout(() => {
                    showNotification(`Now editing "${personaName}" - you can make further adjustments`, 'info');
                }, 500);
            } else {
                const error = await saveResponse.json();
                showNotification(error.error || 'Failed to save persona', 'error');
            }
        } catch (error) {
            console.error('Failed to save persona as:', error);
            showNotification('Failed to save persona', 'error');
        } finally {
            // Restore button state
            saveButton.innerHTML = originalText;
            saveButton.disabled = false;
        }
    };

    // Show message for why active persona can't be deleted
    const showActivePersonaDeleteMessage = () => {
        showNotification('Cannot delete active persona - it is currently linked to a user profile. Switch to a different persona first, then delete this one.', 'warning');
    };

    // Show message for why preferred persona can't be deleted
    const showPreferredPersonaDeleteMessage = () => {
        showNotification('Cannot delete preferred persona - it is currently set as a user\'s preferred persona. Change the user\'s preferred persona first, then delete this one.', 'error');
    };

    // Clear persona cache
    const clearPersonaCache = () => {
        // Clear any cached persona data
        console.log('Clearing persona cache');
    };

    return {addBackstoryField, loadPersona, handlePersonaSave, bindPersonaSelector, populatePersonaSelector, deletePersona, savePersonaAs, showActivePersonaDeleteMessage, showPreferredPersonaDeleteMessage, clearPersonaCache, updatePersonaListSelection};
})();


