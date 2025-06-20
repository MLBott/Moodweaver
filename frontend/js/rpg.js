/**
 * RPG character management functionality
 */

// Load all characters
function loadCharacters() {
    console.log('Loading characters from API...');
    fetch(`${API_BASE_URL}/characters`)
        .then(response => {
            console.log('Characters API response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Characters loaded:', data);
            const characterList = document.getElementById('characterList');
            characterList.innerHTML = '';
            
            if (!data.characters || data.characters.length === 0) {
                const noCharactersMessage = document.createElement('li');
                noCharactersMessage.textContent = 'No characters yet';
                noCharactersMessage.className = 'no-characters';
                characterList.appendChild(noCharactersMessage);
                return;
            }
            
            data.characters.forEach(character => {
                const characterItem = document.createElement('li');
                characterItem.innerHTML = `
                    <span class="character-name">${character.name}</span>
                    <div class="character-actions">
                        <button class="small-btn edit-btn" data-id="${character.id}">Edit</button>
                        <button class="small-btn chat-btn" data-id="${character.id}">Chat</button>
                        <button class="small-btn delete-btn" data-id="${character.id}">
                            <svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="vertical-align:middle;">
                                <path d="M6 7v7a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V7M4 7h12M9 3h2a1 1 0 0 1 1 1v1H8V4a1 1 0 0 1 1-1zM5 7V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1" stroke="#b33a3a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                `;
                
                characterList.appendChild(characterItem);
                
                // Add event listeners
                characterItem.querySelector('.edit-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    editCharacter(character.id);
                });
                
                characterItem.querySelector('.chat-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    startRPGChat(character.id);
                });
                
                characterItem.querySelector('.delete-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteCharacter(character.id);
                });
            });
        })
        .catch(error => {
            console.error('Error loading characters:', error);
            showNotification('Failed to load characters. Is the backend running?', 'error');
        });
}

// Open the character modal for creation
function openCharacterModal() {
    console.log('Opening character modal for creation');
    // Reset form
    document.getElementById('characterId').value = '';
    document.getElementById('characterName').value = '';
    document.getElementById('characterDescription').value = '';
    document.getElementById('characterModalTitle').textContent = 'Create Character';
    
    // Show modal
    document.getElementById('characterModal').style.display = 'block';
}

// Open the character modal for editing
function editCharacter(characterId) {
    console.log('Loading character for editing:', characterId);
    fetch(`${API_BASE_URL}/characters`)
        .then(response => {
            console.log('Characters API response status:', response.status);
            return response.json();
        })
        .then(data => {
            const character = data.characters.find(c => c.id === characterId);
            if (!character) {
                showNotification('Character not found', 'error');
                return;
            }
            
            console.log('Character data loaded for edit:', character);
            
            // Fill form with character data
            document.getElementById('characterId').value = character.id;
            document.getElementById('characterName').value = character.name;
            document.getElementById('characterDescription').value = character.description;
            document.getElementById('characterModalTitle').textContent = 'Edit Character';
            
            // Show modal
            document.getElementById('characterModal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error loading character:', error);
            showNotification('Failed to load character. Is the backend running?', 'error');
        });
}

// Save a character (create or update)
function saveCharacter(e) {
    console.log('Saving character...');
    e.preventDefault();
    
    // Get form values
    const characterId = document.getElementById('characterId').value;
    const characterName = document.getElementById('characterName').value.trim();
    const characterDescription = document.getElementById('characterDescription').value.trim();
    
    // Validate input
    if (!characterName) {
        showNotification('Character name is required', 'error');
        return;
    }
    
    if (!characterDescription) {
        showNotification('Character description is required', 'error');
        return;
    }
    
    const character = {
        name: characterName,
        description: characterDescription
    };
    
    console.log('Character data to save:', character, 'ID:', characterId || 'new');
    
    if (characterId) {
        // Update existing character
        character.id = characterId;
        
        console.log('Updating existing character with ID:', characterId);
        fetch(`${API_BASE_URL}/characters`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(character)
        })
        .then(response => {
            console.log('Character update response status:', response.status);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Character updated successfully:', data);
            document.getElementById('characterModal').style.display = 'none';
            loadCharacters();
            showNotification('Character updated');
        })
        .catch(error => {
            console.error('Error updating character:', error);
            showNotification('Failed to update character. Is the backend running?', 'error');
        });
    } else {
        // Create new character
        console.log('Creating new character');
        fetch(`${API_BASE_URL}/characters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(character)
        })
        .then(response => {
            console.log('Character creation response status:', response.status);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Character created successfully:', data);
            document.getElementById('characterModal').style.display = 'none';
            loadCharacters();
            showNotification('Character created');
        })
        .catch(error => {
            console.error('Error creating character:', error);
            showNotification('Failed to create character. Is the backend running?', 'error');
        });
    }
}

// Delete a character
function deleteCharacter(characterId) {
    if (!confirm('Are you sure you want to delete this character?')) {
        return;
    }
    
    console.log('Deleting character with ID:', characterId);
    fetch(`${API_BASE_URL}/characters?id=${characterId}`, {
        method: 'DELETE'
    })
    .then(response => {
        console.log('Character deletion response status:', response.status);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Character deleted successfully:', data);
        loadCharacters();
        showNotification('Character deleted');
    })
    .catch(error => {
        console.error('Error deleting character:', error);
        showNotification('Failed to delete character. Is the backend running?', 'error');
    });
}

// Start a chat with a character
function startRPGChat(characterId) {
    console.log('Starting RPG chat with character ID:', characterId);
    fetch(`${API_BASE_URL}/characters`)
        .then(response => {
            console.log('Characters API response status:', response.status);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const character = data.characters.find(c => c.id === characterId);
            if (!character) {
                showNotification('Character not found', 'error');
                return;
            }
            
            console.log('Starting chat with character:', character);
            
            // Start a new chat with this character
            startNewChat(characterId);
            document.getElementById('chatTitle').textContent = `Chat with ${character.name}`;
            
            // Update the active mode display
            updateActiveModeDisplay();
            
            // Optional: Show a welcome message from the character
            const welcomeMessage = {
                role: 'assistant',
                content: `*You are now chatting with ${character.name}*`,
                timestamp: Math.floor(Date.now() / 1000)
            };
            displayMessage(welcomeMessage);
        })
        .catch(error => {
            console.error('Error loading character for chat:', error);
            showNotification('Failed to load character. Is the backend running?', 'error');
        });
}