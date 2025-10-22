/**
 * User Profile Panel Management
 */
class UserProfilePanel {
    constructor() {
        this.panel = null;
        this.currentUser = null;
        this.profiles = [];
        this.personas = [];
        this.lastStatus = null;
        this.statusInterval = null;
        this.pendingDisplayName = null; // Store pending display name changes
        this.lastLoadTime = 0;
        this.loadDebounceMs = 100; // Debounce loadAllData calls
    }

    bindUI() {
        this.panel = document.getElementById('user-profile-panel');
        if (!this.panel) return;

        // User profile button click handler
        const userProfileBtn = document.getElementById('user-profile-btn');
        if (userProfileBtn) {
            userProfileBtn.addEventListener('click', () => this.showPanel());
        }

        // Close panel button
        const closeBtn = document.getElementById('close-user-panel');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hidePanel());
        }

        // Click outside to close
        this.panel.addEventListener('click', (e) => {
            if (e.target === this.panel) {
                this.hidePanel();
            }
        });

        // Set guest button
        const setGuestBtn = document.getElementById('set-guest-btn');
        if (setGuestBtn) {
            setGuestBtn.addEventListener('click', () => this.setAsGuest());
        }

        // Default user select
        const defaultUserSelect = document.getElementById('default-user-select');
        if (defaultUserSelect) {
            defaultUserSelect.addEventListener('change', (e) => this.updateDefaultUser(e.target.value));
        }

        // Persona select
        const personaSelect = document.getElementById('persona-select');
        const updatePersonaBtn = document.getElementById('update-persona-btn');
        if (personaSelect && updatePersonaBtn) {
            updatePersonaBtn.addEventListener('click', () => this.updatePersona());
            personaSelect.addEventListener('change', () => {
                updatePersonaBtn.disabled = false;
            });
        }

        // Load initial data
        this.loadAllData();
        
        // Start monitoring status for changes
        this.startStatusMonitoring();
        
        // Bind profile settings toggle
        this.bindProfileSettingsToggle();
        
        // Bind profile action buttons
        this.bindProfileActionButtons();
        
        // Bind display name management
        this.bindDisplayNameManagement();
    }

    async loadAllData(force = false) {
        // Debounce repeated calls, but allow forced reloads
        const now = Date.now();
        if (!force && now - this.lastLoadTime < this.loadDebounceMs) {
            return;
        }
        this.lastLoadTime = now;
        
        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                
                // Load current user - handle both object and string formats
                console.log('loadAllData - data.CURRENT_USER:', data.CURRENT_USER, 'type:', typeof data.CURRENT_USER);
                if (data.CURRENT_USER && typeof data.CURRENT_USER === 'object') {
                    // User is loaded and we have full user data
                    this.currentUser = data.CURRENT_USER.name;
                    console.log('Set currentUser from object:', this.currentUser);
                } else if (typeof data.CURRENT_USER === 'string' && data.CURRENT_USER.trim()) {
                    // User name from .env but profile not loaded
                    this.currentUser = data.CURRENT_USER.trim();
                    console.log('Set currentUser from string:', this.currentUser);
                } else {
                    // No current user set
                    this.currentUser = null;
                    console.log('Set currentUser to null');
                }
                
                // Load profiles
                this.profiles = data.AVAILABLE_PROFILES || [];
                
                // Load personas
                this.personas = (data.AVAILABLE_PERSONAS || []).map(p => ({
                    id: p.name,
                    name: p.description || p.name
                }));
                this.updatePersonaSelect();
                
                // Load default user
                this.defaultUser = data.DEFAULT_USER || 'guest';
                this.updateProfileList();
                
        // Load memories for current user
        await this.loadMemories();
        
        // Update profile settings visibility based on current user
        this.updateProfileSettingsVisibility();
        
        // Update current user display in header
        this.updateCurrentUserDisplay();
        
        // Load display name for current user
        await this.loadDisplayName();
        
        // Update persona selector to show user's preferred persona
        await this.updatePersonaSelectorForCurrentUser();
                
                // Load user persona if current user exists
                if (this.currentUser && data.CURRENT_USER) {
                    const preferredPersona = data.CURRENT_USER.data?.USER_INFO?.preferred_persona || 'default';
                    const personaSelect = document.getElementById('persona-select');
                    if (personaSelect) {
                        personaSelect.value = preferredPersona;
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load all data:', error);
        }
    }

    // Helper function to get display name for a profile
    getDisplayName(profileName, profileData = null) {
        if (profileName === 'guest') {
            return 'Guest';
        }
        
        // If we have profile data, check for display_name
        if (profileData && profileData.data && profileData.data.USER_INFO && profileData.data.USER_INFO.display_name) {
            return profileData.data.USER_INFO.display_name;
        }
        
        // Fallback to profile name
        return profileName;
    }

    // Update current user display in header
    updateCurrentUserDisplay() {
        const currentUserDisplay = document.getElementById('current-user-display');
        if (currentUserDisplay) {
            if (this.currentUser && this.currentUser !== 'guest') {
                // Try to get display name for current user
                this.getCurrentUserDisplayName().then(displayName => {
                    currentUserDisplay.textContent = displayName;
                }).catch(() => {
                    currentUserDisplay.textContent = this.currentUser;
                });
            } else {
                currentUserDisplay.textContent = 'Guest';
            }
        }
    }

    // Get display name for current user
    async getCurrentUserDisplayName() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data && data.CURRENT_USER && data.CURRENT_USER.data && data.CURRENT_USER.data.USER_INFO && data.CURRENT_USER.data.USER_INFO.display_name) {
                return data.CURRENT_USER.data.USER_INFO.display_name;
            }
            return this.currentUser;
        } catch (error) {
            console.error('Failed to get current user display name:', error);
            return this.currentUser;
        }
    }

    showPanel() {
        if (this.panel) {
            this.panel.classList.remove('hidden');
            // Refresh all data when showing
            this.loadAllData();
        }
    }

    hidePanel() {
        if (this.panel) {
            this.panel.classList.add('hidden');
        }
    }

    async loadCurrentUser() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                this.currentUser = data.CURRENT_USER?.name || null;
            } else {
                this.currentUser = null;
            }
        } catch (error) {
            console.error('Failed to load current user:', error);
            this.currentUser = null;
        }
    }


    async loadProfiles() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                this.profiles = data.AVAILABLE_PROFILES || [];
                // updateProfileList will be called after loadDefaultUser completes
            }
        } catch (error) {
            console.error('Failed to load profiles:', error);
        }
    }

    updateProfileList() {
        const profileTiles = document.getElementById('profile-tiles');
        if (!profileTiles) return;

        // Note: Loading states are now cleared manually after success notifications
        // This ensures the loading spinner stays visible until the operation is complete

        // Get current user and default user
        const currentUser = this.currentUser || 'guest';
        const currentDefault = this.defaultUser || 'guest';
        
        console.log('updateProfileList - currentUser:', currentUser, 'currentDefault:', currentDefault);

        // Update guest tile active state and default status
        const guestTile = profileTiles.querySelector('[data-profile="guest"]');
        if (guestTile) {
            const isGuestDefault = currentDefault === 'guest';
            const isGuestActive = currentUser === 'guest' || currentUser === null;
            
            // Update tile styling
            if (isGuestActive) {
                guestTile.className = 'relative bg-zinc-600 rounded-lg p-4 cursor-pointer transition-all duration-200 hover:bg-zinc-600 border-2 border-emerald-500 min-h-[120px] flex flex-col justify-center group';
                console.log('Guest tile set to active');
            } else {
                guestTile.className = 'relative bg-zinc-700 rounded-lg p-4 cursor-pointer transition-all duration-200 hover:bg-zinc-600 border-2 border-transparent min-h-[120px] flex flex-col justify-center group';
                console.log('Guest tile set to inactive');
            }
            
            // Update guest tile text to show "Default" or "Anonymous"
            const guestStatusText = guestTile.querySelector('.text-zinc-400.text-xs');
            if (guestStatusText) {
                guestStatusText.textContent = isGuestDefault ? 'Default' : 'Anonymous';
            }
            
            // Update star button to show filled or outline
            const starButton = guestTile.querySelector('button[title="Set as default"] span');
            if (starButton) {
                starButton.textContent = isGuestDefault ? 'star' : 'star_border';
            }
        }

        // Remove existing profile tiles (keep guest tile)
        const existingProfileTiles = profileTiles.querySelectorAll('[data-profile]:not([data-profile="guest"])');
        existingProfileTiles.forEach(tile => tile.remove());

        // Add profile tiles for each user
        this.profiles.forEach(profile => {
            // Handle both old format (string) and new format (object)
            const profileName = typeof profile === 'string' ? profile : profile.name;
            const isCurrent = profileName === currentUser;
            const isDefault = profileName === currentDefault;
            
            // Get display name for the profile
            const displayName = this.getDisplayName(profileName, profile);
            
            
            const tile = document.createElement('div');
            const baseClasses = 'relative rounded-lg p-4 cursor-pointer transition-all duration-200 hover:bg-zinc-600 border-2 min-h-[120px] flex flex-col justify-center group';
            const activeClasses = 'bg-zinc-600 border-emerald-500';
            const inactiveClasses = 'bg-zinc-700 border-transparent';
            
            tile.className = `${baseClasses} ${isCurrent ? activeClasses : inactiveClasses}`;
            tile.setAttribute('data-profile', profileName);
            tile.onclick = () => this.setAsCurrentUser(profileName);
            
            tile.innerHTML = `
                <div class="text-center">
                    <div class="mb-3 flex justify-center">
                        <span class="material-icons text-6xl text-emerald-400">person</span>
                    </div>
                    <div class="text-white font-medium text-sm mb-1">${displayName}</div>
                    <div class="text-zinc-400 text-xs">${isDefault ? 'Default' : 'User'}</div>
                </div>
                <div class="absolute top-2 right-2">
                    <button class="text-amber-400 hover:text-amber-300 transition-colors" onclick="event.stopPropagation(); window.UserProfilePanel.setAsDefault('${profileName}')" title="Set as default">
                        <span class="material-icons text-sm">${isDefault ? 'star' : 'star_border'}</span>
                    </button>
                </div>
            `;
            
            profileTiles.appendChild(tile);
        });
    }

    async loadPersonas() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                this.personas = (data.AVAILABLE_PERSONAS || []).map(p => ({
                    id: p.name,
                    name: p.description || p.name
                }));
                this.updatePersonaSelect();
            }
        } catch (error) {
            console.error('Failed to load personas:', error);
        }
    }

    updatePersonaSelect() {
        const personaSelect = document.getElementById('persona-select');
        if (!personaSelect) return;

        personaSelect.innerHTML = this.personas.map(persona => `
            <option value="${persona.id}">${persona.name}</option>
        `).join('');

        // Set current user's preferred persona if available
        if (this.currentUser) {
            this.loadUserPersona();
        }
    }

    async loadUserPersona() {
        if (!this.currentUser) return;

        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                const currentUserData = data.CURRENT_USER;
                if (currentUserData && currentUserData.name === this.currentUser) {
                    const preferredPersona = currentUserData.data?.USER_INFO?.preferred_persona || 'default';
                    
                    const personaSelect = document.getElementById('persona-select');
                    if (personaSelect) {
                        personaSelect.value = preferredPersona;
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load user persona:', error);
        }
    }

    async loadMemories() {
        try {
            const data = await ConfigService.fetchConfig();
            const memoriesList = document.getElementById('memories-list');
            if (!memoriesList) return;

            // Don't load memories for guest mode
            if (this.currentUser === 'guest' || this.currentUser === null) {
                memoriesList.innerHTML = '<p class="text-sm text-zinc-400 italic">No memories in guest mode</p>';
                return;
            }

            if (data && data.CURRENT_USER && data.CURRENT_USER.data && data.CURRENT_USER.data.core_memories) {
                const memories = data.CURRENT_USER.data.core_memories;
                if (memories && memories.length > 0) {
                    // Show recent memories (last 5)
                    const recentMemories = memories.slice(-5).reverse();
                    memoriesList.innerHTML = recentMemories.map(memory => `
                        <div class="flex items-start justify-between p-2 bg-zinc-800 rounded-lg">
                            <div class="flex-1">
                                <p class="text-sm text-zinc-200">${memory.memory}</p>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="text-xs text-zinc-400">${memory.category}</span>
                                    <span class="text-xs text-zinc-500">•</span>
                                    <span class="text-xs text-zinc-400">${memory.importance}</span>
                                    <span class="text-xs text-zinc-500">•</span>
                                    <span class="text-xs text-zinc-400">${new Date(memory.date).toLocaleDateString()}</span>
                                </div>
                            </div>
                            <button class="ml-2 text-rose-400 hover:text-rose-300 transition-colors" onclick="window.UserProfilePanel.deleteMemory('${memory.date}')" title="Delete memory">
                                <span class="material-icons text-sm">delete</span>
                            </button>
                        </div>
                    `).join('');
                } else {
                    memoriesList.innerHTML = '<p class="text-sm text-zinc-400 italic">No memories yet</p>';
                }
            } else {
                memoriesList.innerHTML = '<p class="text-sm text-zinc-400 italic">No memories yet</p>';
            }
        } catch (error) {
            console.error('Failed to load memories:', error);
            const memoriesList = document.getElementById('memories-list');
            if (memoriesList) {
                memoriesList.innerHTML = '<p class="text-sm text-zinc-400 italic">Error loading memories</p>';
            }
        }
    }

    bindProfileSettingsToggle() {
        const toggle = document.getElementById('profile-settings-toggle');
        const content = document.getElementById('profile-settings-content');
        const chevron = document.getElementById('profile-settings-chevron');
        
        if (toggle && content && chevron) {
            toggle.addEventListener('click', () => {
                const isHidden = content.classList.contains('hidden');
                
                if (isHidden) {
                    content.classList.remove('hidden');
                    chevron.style.transform = 'rotate(180deg)';
                    const textSpan = toggle.querySelector('span:first-child');
                    textSpan.innerHTML = '<span class="material-icons mr-2 text-emerald-400">settings</span>Hide profile settings';
                    // Update button styling for expanded state
                    toggle.classList.remove('rounded-t-lg');
                    toggle.classList.add('rounded-none');
                } else {
                    content.classList.add('hidden');
                    chevron.style.transform = 'rotate(0deg)';
                    const textSpan = toggle.querySelector('span:first-child');
                    textSpan.innerHTML = '<span class="material-icons mr-2 text-emerald-400">settings</span>Show profile settings';
                    // Update button styling for collapsed state
                    toggle.classList.remove('rounded-none');
                    toggle.classList.add('rounded-t-lg');
                }
            });
        }
    }

    updateProfileSettingsVisibility() {
        const toggle = document.getElementById('profile-settings-toggle');
        const content = document.getElementById('profile-settings-content');
        
        if (toggle && content) {
            // Hide profile settings for guest mode
            if (this.currentUser === 'guest' || this.currentUser === null) {
                toggle.style.display = 'none';
                content.classList.add('hidden');
            } else {
                toggle.style.display = 'flex';
                // Keep content hidden by default (collapsed)
                content.classList.add('hidden');
            }
        }
    }

    // Bind profile action buttons
    bindProfileActionButtons() {
        const editProfileBtn = document.getElementById('edit-profile-btn');
        const deleteProfileBtn = document.getElementById('delete-profile-btn');
        
        if (editProfileBtn) {
            editProfileBtn.addEventListener('click', () => {
                if (this.currentUser && this.currentUser !== 'guest') {
                    this.editProfile(this.currentUser);
                } else {
                    this.showNotification('No profile selected to edit', 'warning');
                }
            });
        }
        
        if (deleteProfileBtn) {
            deleteProfileBtn.addEventListener('click', () => {
                if (this.currentUser && this.currentUser !== 'guest') {
                    this.deleteProfile(this.currentUser);
                } else {
                    this.showNotification('No profile selected to delete', 'warning');
                }
            });
        }
    }

    // Bind display name management
    bindDisplayNameManagement() {
        const displayNameInput = document.getElementById('display-name-input');
        if (displayNameInput) {
            displayNameInput.addEventListener('input', () => this.onDisplayNameChange());
        }
    }

    // Load display name for current user
    async loadDisplayName() {
        try {
            const displayNameInput = document.getElementById('display-name-input');
            if (!displayNameInput) return;

            // Don't load display name for guest mode
            if (this.currentUser === 'guest' || this.currentUser === null) {
                displayNameInput.value = '';
                displayNameInput.disabled = true;
                displayNameInput.placeholder = 'No display name in guest mode';
                return;
            }

            displayNameInput.disabled = false;
            displayNameInput.placeholder = 'Enter display name';

            // Use pending display name if it exists, otherwise load from server
            if (this.pendingDisplayName !== null) {
                displayNameInput.value = this.pendingDisplayName;
            } else {
                // Load from server
                const data = await ConfigService.fetchConfig();
                if (data && data.CURRENT_USER && data.CURRENT_USER.data && data.CURRENT_USER.data.USER_INFO && data.CURRENT_USER.data.USER_INFO.display_name) {
                    const displayName = data.CURRENT_USER.data.USER_INFO.display_name;
                    displayNameInput.value = displayName;
                } else {
                    // Fallback to user name if no display name set
                    displayNameInput.value = this.currentUser;
                }
            }
        } catch (error) {
            console.error('Failed to load display name:', error);
            const displayNameInput = document.getElementById('display-name-input');
            if (displayNameInput) {
                displayNameInput.value = '';
                displayNameInput.placeholder = 'Error loading display name';
            }
        }
    }

    // Handle display name change
    onDisplayNameChange() {
        if (this.currentUser === 'guest' || this.currentUser === null) {
            return;
        }

        const displayNameInput = document.getElementById('display-name-input');
        if (!displayNameInput) return;

        const newDisplayName = displayNameInput.value.trim();
        
        // Store pending display name
        this.pendingDisplayName = newDisplayName;
        
        // Enable save button when display name is modified
        this.enableSaveButton();
        
    }


    async loadDefaultUser() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data) {
                this.defaultUser = data.DEFAULT_USER || 'guest';
            }
        } catch (error) {
            console.error('Failed to load default user:', error);
            this.defaultUser = 'guest';
        }
    }

    async setAsCurrentUser(profileName) {
        try {
            // Show loading state for the clicked profile
            this.showProfileLoading(profileName);
            
            // First, set the current user in the user manager
            const response = await fetch('/current-user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: profileName })
            });

            if (response.ok) {
                // Then, save the current user to .env file
                await fetch('/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        CURRENT_USER: profileName
                    })
                });

                // Refresh all data to ensure UI is in sync with .env
                console.log('Refreshing data after setting current user to:', profileName);
                // Small delay to ensure .env file is written and backend processed it
                await new Promise(resolve => setTimeout(resolve, 100));
                await this.loadAllData(true);
                
                // Force update the profile list to show active state
                this.updateProfileList();
                
                 // Load the user's preferred persona in the persona form (non-blocking)
                 this.loadUserPreferredPersona(profileName);
                
                // Show success notification with display name
                const displayName = this.getDisplayName(profileName, this.profiles.find(p => (typeof p === 'string' ? p : p.name) === profileName));
                this.showNotification(`Set ${displayName} as current user`, 'success');
                
                 // Hide loading state immediately - UI updates are synchronous
                 this.hideProfileLoading(profileName);
            } else {
                this.hideProfileLoading(profileName);
                this.showNotification('Failed to set current user', 'error');
            }
        } catch (error) {
            console.error('Failed to set current user:', error);
            this.hideProfileLoading(profileName);
            this.showNotification('Failed to set current user', 'error');
        }
    }

    async setAsGuest() {
        try {
            // Show loading state for guest profile
            this.showProfileLoading('guest');
            
            const response = await fetch('/current-user', {
                method: 'DELETE'
            });

            if (response.ok) {
                // Save "guest" to .env file
                await fetch('/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        CURRENT_USER: 'guest'
                    })
                });

                // Refresh all data to ensure UI is in sync with .env
                console.log('Refreshing data after setting guest user');
                // Small delay to ensure .env file is written and backend processed it
                await new Promise(resolve => setTimeout(resolve, 100));
                await this.loadAllData(true);
                
                // Force update the profile list to show active state
                this.updateProfileList();
                
                 // Load the default persona for guest mode (non-blocking)
                 this.loadUserPreferredPersona('guest');
                
                // Show success notification
                this.showNotification('Set as guest user', 'success');
                
                 // Hide loading state immediately - UI updates are synchronous
                 this.hideProfileLoading('guest');
            } else {
                this.hideProfileLoading('guest');
                this.showNotification('Failed to set as guest', 'error');
            }
        } catch (error) {
            console.error('Failed to set as guest:', error);
            this.hideProfileLoading('guest');
            this.showNotification('Failed to set as guest', 'error');
        }
    }

    async deleteProfile(profileName) {
        if (!confirm(`Are you sure you want to delete the profile for ${profileName}?`)) {
            return;
        }

        try {
            const response = await fetch(`/profiles/${profileName}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification(`Deleted profile for ${profileName}`, 'success');
                
                // If this was the current user, set to guest first
                if (this.currentUser === profileName) {
                    await this.setAsGuest();
                }
                
                // Refresh all data to update the UI
                await this.loadAllData();
            } else {
                this.showNotification('Failed to delete profile', 'error');
            }
        } catch (error) {
            console.error('Failed to delete profile:', error);
            this.showNotification('Failed to delete profile', 'error');
        }
    }

    async deleteMemory(memoryDate) {
        if (!confirm('Are you sure you want to delete this memory? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/profiles/delete-memory', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    user: this.currentUser,
                    memoryDate: memoryDate 
                })
            });

            if (response.ok) {
                this.showNotification('Memory deleted successfully', 'success');
                await this.loadMemories();
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Failed to delete memory', 'error');
            }
        } catch (error) {
            console.error('Failed to delete memory:', error);
            this.showNotification('Failed to delete memory', 'error');
        }
    }

    async editProfile(profileName) {
        const newName = prompt(`Enter new name for profile "${profileName}":`, profileName);
        if (!newName || newName.trim() === '' || newName === profileName) {
            return;
        }

        try {
            const response = await fetch('/profiles/rename', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    oldName: profileName,
                    newName: newName.trim()
                })
            });

            if (response.ok) {
                // Get display names for notification
                const oldDisplayName = this.getDisplayName(profileName);
                this.showNotification(`Profile renamed from "${oldDisplayName}" to "${newName}"`, 'success');
                await this.loadAllData();
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Failed to rename profile', 'error');
            }
        } catch (error) {
            console.error('Failed to rename profile:', error);
            this.showNotification('Failed to rename profile', 'error');
        }
    }

    async setAsDefault(userName) {
        try {
            const response = await fetch('/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    DEFAULT_USER: userName
                })
            });

            if (response.ok) {
                this.defaultUser = userName;
                this.updateProfileList(); // Refresh the profile list to update star colors
                this.showNotification(`Set ${userName} as default user`, 'success');
            } else {
                this.showNotification('Failed to update default user', 'error');
            }
        } catch (error) {
            console.error('Failed to update default user:', error);
            this.showNotification('Failed to update default user', 'error');
        }
    }

    async updatePersona() {
        if (!this.currentUser) {
            this.showNotification('No current user selected', 'error');
            return;
        }

        const personaSelect = document.getElementById('persona-select');
        if (!personaSelect) return;

        const selectedPersona = personaSelect.value;

        try {
            // Save persona preference
            const personaResponse = await fetch('/profiles/current-user', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    action: 'switch_persona',
                    preferred_persona: selectedPersona
                })
            });

            if (!personaResponse.ok) {
                this.showNotification('Failed to update persona', 'error');
                return;
            }

            // Save pending display name if any
            if (this.pendingDisplayName !== null) {
                const displayNameResponse = await fetch('/profiles/update-display-name', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        user: this.currentUser,
                        display_name: this.pendingDisplayName
                    })
                });

                if (displayNameResponse.ok) {
                    this.pendingDisplayName = null; // Clear pending display name
                    this.showNotification(`Updated ${this.currentUser}'s profile (persona + display name)`, 'success');
                } else {
                    this.showNotification('Updated persona but failed to save display name', 'warning');
                }
            } else {
                this.showNotification(`Updated ${this.currentUser}'s preferred persona`, 'success');
            }

            const updateBtn = document.getElementById('update-persona-btn');
            if (updateBtn) updateBtn.disabled = true;

        } catch (error) {
            console.error('Failed to update profile:', error);
            this.showNotification('Failed to update profile', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Use the existing notification system
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    enableSaveButton() {
        const updateBtn = document.getElementById('update-persona-btn');
        if (updateBtn) {
            updateBtn.disabled = false;
        }
    }

    startStatusMonitoring() {
        // Check for status changes every 3 seconds
        this.statusInterval = setInterval(async () => {
            await this.checkStatus();
        }, 3000);
    }

    stopStatusMonitoring() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
    }

    async checkStatus() {
        try {
            const status = await ServiceStatus.fetchStatus();
            if (status) {
                
                // Check if anything has changed
                if (this.lastStatus) {
                    let hasChanges = false;
                    
                    // Check for user changes
                    if (this.lastStatus.current_user !== status.current_user) {
                        console.log('User change detected:', {
                            from: this.lastStatus.current_user,
                            to: status.current_user
                        });
                        hasChanges = true;
                        
                        // Show notification
                        if (status.current_user && status.current_user !== 'guest') {
                            // Get display name for notification
                            const displayName = this.getDisplayName(status.current_user);
                            this.showNotification(`Switched to ${displayName} profile`, 'info');
                        } else {
                            this.showNotification('Switched to guest mode', 'info');
                        }
                    }
                    
                    // Check for .env file changes
                    if (this.lastStatus.env_file && status.env_file &&
                        this.lastStatus.env_file.modified !== status.env_file.modified) {
                        console.log('Environment file change detected');
                        hasChanges = true;
                    }
                    
                    // Check for profile/persona changes
                    if (JSON.stringify(this.lastStatus.available_profiles) !== JSON.stringify(status.available_profiles) ||
                        JSON.stringify(this.lastStatus.available_personas) !== JSON.stringify(status.available_personas)) {
                        console.log('Profiles or personas changed');
                        hasChanges = true;
                    }
                    
                    if (hasChanges) {
                        // For user changes, add a small delay to ensure data is loaded
                        if (this.lastStatus.current_user !== status.current_user) {
                            console.log('User change detected, waiting for data to load...');
                            await new Promise(resolve => setTimeout(resolve, 200));
                            // Force reload for user changes
                            await this.loadAllData(true);
                        } else {
                            // Refresh the UI
                            await this.loadAllData();
                        }
                        
                        // Notify other components if they exist
                        if (window.SettingsForm && window.SettingsForm.refreshFromConfig) {
                            // Get fresh config data
                            const configData = await ConfigService.fetchConfig();
                            if (configData) {
                                window.SettingsForm.refreshFromConfig(configData);
                            }
                        }
                        
                        // Update persona selector if PersonaForm is available
                        if (window.PersonaForm && window.PersonaForm.updatePersonaListSelection) {
                            await this.updatePersonaSelectorForCurrentUser();
                        }
                    }
                }
                
                this.lastStatus = status;
            }
        } catch (error) {
            console.error('Failed to check status:', error);
        }
    }

    // Update persona selector to show user's preferred persona
    async updatePersonaSelectorForCurrentUser() {
        try {
            // Wait for PersonaForm to be available with retry
            let retries = 0;
            const maxRetries = 10;
            
            while (!window.PersonaForm || !window.PersonaForm.loadPersona) {
                if (retries >= maxRetries) {
                    console.warn('PersonaForm not available after retries, skipping persona loading');
                    return;
                }
                console.log(`Waiting for PersonaForm to be available... (attempt ${retries + 1})`);
                await new Promise(resolve => setTimeout(resolve, 100));
                retries++;
            }

            // Update the persona selector dropdown in the user profile modal
            const personaSelect = document.getElementById('persona-select');
            if (personaSelect) {
                // Only update if we have a current user and PersonaForm is available
                if (this.currentUser && this.currentUser !== 'guest') {
                    // Get the user's preferred persona from the current data
                    const currentUserData = await this.getCurrentUserData();
                    if (currentUserData && currentUserData.data && currentUserData.data.USER_INFO) {
                        const preferredPersona = currentUserData.data.USER_INFO.preferred_persona || 'default';
                        if (personaSelect.value !== preferredPersona) {
                            console.log(`Setting persona selector to ${preferredPersona} for user ${this.currentUser}`);
                            personaSelect.value = preferredPersona;
                        }
                    }
                } else {
                    // For guest mode or no user, set to default
                    if (personaSelect.value !== 'default') {
                        console.log('Setting persona selector to default for guest mode');
                        personaSelect.value = 'default';
                    }
                }
            }
        } catch (error) {
            console.error('Failed to update persona selector for current user:', error);
        }
    }

    // Helper method to get current user data
    async getCurrentUserData() {
        try {
            const data = await ConfigService.fetchConfig();
            if (data && data.CURRENT_USER && typeof data.CURRENT_USER === 'object') {
                return data.CURRENT_USER;
            }
            return null;
        } catch (error) {
            console.error('Failed to get current user data:', error);
            return null;
        }
    }

    // Show loading state for a profile
    showProfileLoading(profileName) {
        const profileTile = document.querySelector(`[data-profile="${profileName}"]`);
        if (profileTile) {
            // Add loading class and disable interaction
            profileTile.classList.add('opacity-50', 'pointer-events-none');
            
            // Add loading spinner
            const loadingSpinner = document.createElement('div');
            loadingSpinner.className = 'absolute inset-0 flex items-center justify-center bg-zinc-800/80 rounded-lg';
            loadingSpinner.innerHTML = `
                <div class="flex flex-col items-center">
                    <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-400"></div>
                    <span class="text-xs text-emerald-400 mt-1">Loading...</span>
                </div>
            `;
            loadingSpinner.id = `loading-${profileName}`;
            profileTile.appendChild(loadingSpinner);
        }
    }

    // Hide loading state for a profile
    hideProfileLoading(profileName) {
        const profileTile = document.querySelector(`[data-profile="${profileName}"]`);
        if (profileTile) {
            // Remove loading class and re-enable interaction
            profileTile.classList.remove('opacity-50', 'pointer-events-none');
            
            // Remove loading spinner
            const loadingSpinner = document.getElementById(`loading-${profileName}`);
            if (loadingSpinner) {
                loadingSpinner.remove();
            }
        }
    }


     // Load the user's preferred persona in the persona form
     async loadUserPreferredPersona(userName) {
         try {
             // Quick check if PersonaForm is available, skip if not
             if (!window.PersonaForm || !window.PersonaForm.loadPersona) {
                 console.warn('PersonaForm not available, skipping persona loading');
                 return;
             }

            let personaToLoad = 'default'; // Default for guest mode
            
            if (userName && userName !== 'guest') {
                // Get the user's preferred persona
                const data = await ConfigService.fetchConfig();
                if (data && data.CURRENT_USER && data.CURRENT_USER.data && data.CURRENT_USER.data.USER_INFO) {
                    personaToLoad = data.CURRENT_USER.data.USER_INFO.preferred_persona || 'default';
                }
            }
            
             // Load the persona in the persona form
             await window.PersonaForm.loadPersona(personaToLoad);
             
             // Update the persona list to show the loaded persona as active
             if (window.PersonaForm.updatePersonaListSelection) {
                 window.PersonaForm.updatePersonaListSelection(personaToLoad);
             }
            
        } catch (error) {
            console.error('Failed to load user preferred persona:', error);
        }
    }

    // Global refresh method that can be called from other modules
    async refreshUserProfile() {
        await this.loadAllData();
    }
}

// Make it globally available
window.UserProfilePanel = new UserProfilePanel();

// Make the refresh method globally accessible
window.refreshUserProfile = () => {
    if (window.UserProfilePanel && window.UserProfilePanel.refreshUserProfile) {
        return window.UserProfilePanel.refreshUserProfile();
    }
};

// Make the persona sync method globally accessible
window.syncPersonaWithCurrentUser = () => {
    if (window.UserProfilePanel && window.UserProfilePanel.updatePersonaSelectorForCurrentUser) {
        return window.UserProfilePanel.updatePersonaSelectorForCurrentUser();
    }
};

// Make functions globally available for onclick handlers
window.setAsDefault = (userName) => {
    window.UserProfilePanel.setAsDefault(userName);
};

window.setAsCurrentUser = (profileName) => {
    window.UserProfilePanel.setAsCurrentUser(profileName);
};

window.setAsGuest = () => {
    window.UserProfilePanel.setAsGuest();
};

window.deleteProfile = (profileName) => {
    window.UserProfilePanel.deleteProfile(profileName);
};

window.deleteMemory = (memoryDate) => {
    window.UserProfilePanel.deleteMemory(memoryDate);
};

window.editProfile = (profileName) => {
    window.UserProfilePanel.editProfile(profileName);
};

