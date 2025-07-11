/**
 * Chat functionality including loading chats, sending messages, and displaying messages
 */

function updateActiveModeDisplay() {
  const modeDisplay = document.getElementById("activeModeDisplay");

  if (currentCharacterId) {
    fetch(`${API_BASE_URL}/characters`)
      .then((response) => response.json())
      .then((data) => {
        const character = data.characters.find(
          (c) => c.id === currentCharacterId
        );
        if (character) {
          modeDisplay.textContent = `Persona: ${character.name}`;
          modeDisplay.style.display = "block";
        } else {
          modeDisplay.style.display = "none";
        }
      })
      .catch((error) => {
        console.error("Error loading character for active mode display:", error);
        modeDisplay.style.display = "none";
      });
  } else {
    modeDisplay.style.display = "none";
  }
}




// Load all chats
function loadChats() {
  console.log("Loading chats from API...");
  window.currentPlayerCoords = [1, 1];
  fetch(`${API_BASE_URL}/chats`)
    .then((response) => {
      console.log("Chats API response status:", response.status);
      console.log("Response headers:", response.headers);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("Chats loaded:", data);
      const chatList = document.getElementById("chatList");
      chatList.innerHTML = "";

      if (!data.chats || data.chats.length === 0) {
        const noChatsMessage = document.createElement("li");
        noChatsMessage.textContent = "No chats yet";
        noChatsMessage.className = "no-chats";
        chatList.appendChild(noChatsMessage);
        return;
      }

      // Sort chats by most recent first
      data.chats.sort((a, b) => b.created_at - a.created_at);

      data.chats.forEach((chat) => {
        const chatItem = document.createElement("li");

        const titleSpan = document.createElement("span");
        titleSpan.textContent = chat.title;
        titleSpan.className = "chat-title";
        chatItem.appendChild(titleSpan);

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "small-btn delete-btn";
        deleteBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="vertical-align:middle;">
          <path d="M6 7v7a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V7M4 7h12M9 3h2a1 1 0 0 1 1 1v1H8V4a1 1 0 0 1 1-1zM5 7V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1" stroke="#b33a3a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteChat(chat.id);
        });
        chatItem.appendChild(deleteBtn);

        chatItem.dataset.id = chat.id;
        chatItem.addEventListener("click", () => loadChat(chat.id));

        if (chat.id === currentChatId) {
          chatItem.classList.add("active");
        }

        chatList.appendChild(chatItem);
      });
    })
    .catch((error) => {
      console.error("Error loading chats:", error);
      console.error("Error name:", error.name);
      console.error("Error message:", error.message);
      console.error("Error stack:", error.stack);
      showNotification("Failed to load chats. Is the backend running?", "error");

      // More specific error messages
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        showNotification("Cannot connect to backend. Check if server is running and URL is correct.", "error");
      } else if (error.message.includes('CORS')) {
        showNotification("CORS error. Check backend CORS configuration.", "error");
      } else {
        showNotification(`Backend error: ${error.message}`, "error");
      }
    });
}

// Summarize the current chat
document.getElementById("summarizeBtn").addEventListener("click", () => {
  if (!currentChatId) return;
  fetch(`${API_BASE_URL}/chat/${currentChatId}/summarize`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      if (data.summary) {
        showNotification("Summary added to chat!", "success");
        loadChat(currentChatId);
      } else {
        showNotification(data.error || "Summarization failed.", "error");
      }
    })
    .catch((err) => {
      showNotification("Summarization failed.", "error");
      console.error(err);
    });
});

// Start a new chat
function startNewChat(characterId = null) {
  console.log(
    "Starting new chat",
    characterId ? `with character ${characterId}` : "without character"
  );
  currentChatId = null;
  currentCharacterId = characterId;
  window.currentCharacterId = characterId;

  document.getElementById("chatMessages").innerHTML = "";
  document.getElementById("chatTitle").textContent = "New Chat";
  updateActiveModeDisplay();

  document.querySelectorAll("#chatList li").forEach((li) => {
    li.classList.remove("active");
  });

  document.getElementById("userInput").focus();

  if (moodColorInterval) clearInterval(moodColorInterval);
    updateMoodColor(); // This will clear the color
    updateBodyLanguageState();
  
  updatePlayerDot(1, 1); // Reset to starting node
}

// Load a specific chat
function loadChat(chatId) {
  console.log("Loading chat with ID:", chatId);
  currentChatId = chatId;

  const genderToggle = document.getElementById("bodyGenderToggle");
  

  fetch(`${API_BASE_URL}/chats`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      const chat = data.chats.find((c) => c.id === chatId);
      if (!chat) {
        showNotification("Chat not found", "error");
        return;
      }

      console.log("Chat data loaded:", chat);

      document.getElementById("chatTitle").textContent = chat.title;
      currentCharacterId = chat.character_id || null;
      window.currentCharacterId = currentCharacterId;
      updateActiveModeDisplay();

      const chatMessages = document.getElementById("chatMessages");
      chatMessages.innerHTML = "";

      chat.messages.forEach((message, idx) => {
        // Track coordinates for narrator messages in chat history
        if ((message.role === "narrator" || 
             (message.role === "user" && message.content.includes("[NARRATOR:"))) && 
            !message.coords) {
          message.coords = window.currentPlayerCoords || [1, 1];
        }
        displayMessage(message, idx);
      });

      // Show/hide summarize button based on message count
      const summarizeBtn = document.getElementById("summarizeBtn");
      if (summarizeBtn) {
        if (chat.messages.length > 6) {
          summarizeBtn.style.display = "block";
        } else {
          summarizeBtn.style.display = "none";
        }
      }

      chatMessages.scrollTop = chatMessages.scrollHeight;

      document.querySelectorAll("#chatList li").forEach((li) => {
        li.classList.remove("active");
        if (li.dataset.id === chatId) {
          li.classList.add("active");
        }
      });

      const systemPromptTextarea = document.getElementById("systemPrompt");
      if (systemPromptTextarea) {
        systemPromptTextarea.value =
          chat.system_prompt || "Default system prompt here...";
      }
      
      updateLoadChatGenderToggle(chat);

    })
    .catch((error) => {
      console.error("Error loading chat:", error);
      showNotification("Failed to load chat. Is the backend running?", "error");
    })
    .finally(() => {
        // ...
        updateMoodColor(); 
        updateBodyLanguageState();
        // Start polling for mood color updates
        if (moodColorInterval) clearInterval(moodColorInterval);
        moodColorInterval = setInterval(() => {
            updateMoodColor();
            updateBodyLanguageState();
        }, 8000); // Update every 8 seconds
    });
}

// Delete a chat
function deleteChat(chatId) {
  if (!confirm("Are you sure you want to delete this chat?")) {
    return;
  }

  console.log("Deleting chat with ID:", chatId);
  fetch(`${API_BASE_URL}/chats?id=${chatId}`, {
    method: "DELETE",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("Chat deleted successfully:", data);
      if (currentChatId === chatId) {
        startNewChat();
      }
      loadChats();
      showNotification("Chat deleted");
    })
    .catch((error) => {
      console.error("Error deleting chat:", error);
      showNotification("Failed to delete chat. Is the backend running?", "error");
    });
}

function formatAndStyleMessage(text) {
  if (!text) return "";

  function applyMarkdown(chunk) {
    if (!chunk) return "";
    let processedChunk = chunk.replace(/</g, "&lt;").replace(/>/g, "&gt;");

    processedChunk = processedChunk.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    processedChunk = processedChunk.replace(/\*(.*?)\*/g, "<em>$1</em>");
    processedChunk = processedChunk.replace(/`([^`]+)`/g, "<code>$1</code>");
    processedChunk = processedChunk.replace(/\n/g, "<br>");
    return processedChunk;
  }

  let html = "";
  let lastIndex = 0;
  const dialogueRegex = /(["“”])(.*?)(["“”])/g;
  const attributionRegex =
    /^(\s*,\s*|\s+)(\w+\s+(said|whispered|muttered|asked|yelled|shouted|replied|cried|growled|remarked|murmured|gasped|hissed|retorted)[\w\s,.]*?)(?=[.?!]|\n|$)/i;

  let match;
  while ((match = dialogueRegex.exec(text)) !== null) {
    let actionChunk = text.substring(lastIndex, match.index);
    html += `<span class="action-text">${applyMarkdown(actionChunk)}</span>`;

    let dialogueChunk = match[0];
    html += `<span class="dialogue-text">${applyMarkdown(dialogueChunk)}</span>`;
    lastIndex = dialogueRegex.lastIndex;

    const remainingText = text.substring(lastIndex);
    const attributionMatch = remainingText.match(attributionRegex);

    if (attributionMatch) {
      let attributionChunk = attributionMatch[0];
      html += `<span class="attribution-text">${applyMarkdown(
        attributionChunk
      )}</span>`;
      lastIndex += attributionChunk.length;
    }
  }

  if (lastIndex < text.length) {
    let finalActionChunk = text.substring(lastIndex);
    html += `<span class="action-text">${applyMarkdown(finalActionChunk)}</span>`;
  }

  if (html === "") {
    return `<span class="action-text">${applyMarkdown(text)}</span>`;
  }

  return html;
}

// Display and Save an edited message
function displayMessage(message, index) {
  const chatMessages = document.getElementById("chatMessages");

  // Create the main container for the entire row
  const messageRow = document.createElement("div");

  // Create the message bubble element
  const messageElement = document.createElement("div");

  // --- Determine Role and Class ---
  let roleClass = message.role; // Default to 'user', 'system', etc.
  if (message.role === "assistant" && currentCharacterId) {
    roleClass = "character";
  } else if (message.display_as === "narrator" || 
             (message.role === "user" && message.content.includes("[NARRATOR:"))) {
    roleClass = "narrator";
  }

  // Apply classes to the row and the message bubble itself
  messageRow.className = `message-row ${roleClass}`;
  if (roleClass === "narrator") {
    // Narrator gets a special class for full-width styling
    messageElement.className = "narrator-message";
    // Make narrator messages clickable for map flashing
    messageElement.style.cursor = "pointer";
    messageElement.title = "Click to flash location on map";
  } else {
    messageElement.className = `message ${roleClass}`;
  }

  // --- Create the Side Box ---
  const sideBox = document.createElement("div");
  sideBox.className = "side-box";

  // Set the content of the side box based on the role
  if (roleClass === 'character') {
    // For a real implementation, you would fetch the character's name.
    // We can also add an image here later.
    // For example: sideBox.innerHTML = `<img src="${character.avatar_url}" />`;
    sideBox.textContent = "Character"; // Placeholder
  } else if (roleClass === 'user') {
    sideBox.textContent = message.user_name || "User";
  } else if (roleClass === 'narrator') {
    sideBox.textContent = "Narrator";
  }


  // --- Assemble the Message Content ---
  const contentWrapper = document.createElement("div");
  contentWrapper.className = "message-content";

  if (["assistant", "character", "narrator", "system"].includes(message.role)) {
    contentWrapper.innerHTML = message.content;
  } else {
    contentWrapper.innerHTML = formatAndStyleMessage(message.content);
  }
  
  // Add click handler for narrator messages to flash map location
  if (roleClass === "narrator") {
    const coords = message.coords || extractCoordsFromNarratorMessage(message);
    if (coords) {
      messageElement.addEventListener("click", () => {
        flashNodeOnMap(coords[0], coords[1]);
      });
    }
  }
  
  messageElement.appendChild(contentWrapper);

  // --- Assemble the final row ---
  // The order of appending determines the visual order (CSS can reverse it for user)
  messageRow.appendChild(sideBox);
  messageRow.appendChild(messageElement);


  // --- Add Timestamp and Edit Button (if not narrator) ---
  if (roleClass !== 'narrator') {
    const editBtn = document.createElement("button");
    editBtn.className = "small-btn edit-btn";
    editBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="vertical-align:middle;"><path d="M14.69 2.86l2.45 2.45c.39.39.39 1.02 0 1.41l-9.19 9.19-3.25.81.81-3.25 9.19-9.19a1 1 0 0 1 1.41 0z" fill="#888"/></svg>`;
    editBtn.addEventListener("click", () => {
        // (Your existing edit logic here)
    });
    contentWrapper.appendChild(editBtn);

    const timestampElement = document.createElement("span");
    timestampElement.className = "message-meta";
    timestampElement.textContent = formatTimestamp(message.timestamp);
    messageElement.appendChild(timestampElement);
  }

  // Append the fully assembled row to the chat window
  chatMessages.appendChild(messageRow);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Save an edited message to the backend
function saveEditedMessage(messageIndex, newContent) {
  fetch(`${API_BASE_URL}/chat/${currentChatId}/edit-message`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_index: messageIndex,
      new_content: newContent,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadChat(currentChatId); // Reload chat to reflect changes
        showNotification("Message updated!", "success");
      } else {
        showNotification("Failed to update message.", "error");
      }
    })
    .catch((error) => {
      showNotification("Error updating message.", "error");
      console.error(error);
    });
}

// Send a message to the backend
function sendMessage() {
  console.log("=== sendMessage called ===");

  const userInput = document.getElementById("userInput");
  const userNameInput = document.getElementById("userNameInput");
  let message = userInput.value.trim();
  let userName = userNameInput ? userNameInput.value.trim() : "User";

  if (pendingDiceResult !== null && pendingDiceSides !== null) {
    message += ` [OOC: I rolled a ${pendingDiceResult} on a d${pendingDiceSides}]`;
    pendingDiceResult = null;
    pendingDiceSides = null;
  }
  
  // Always stop the timer when a manual message is sent
  console.log("🛑 Stopping timer due to manual message");
  stopContinueTimer();

  if (!message) {
    console.log("❌ Message is empty, aborting");
    return;
  }
  if (isLoading) {
    console.log("❌ Already loading, aborting");
    return;
  }
  
  console.log("📝 Sending message:", message);
  userInput.value = ""; // Clear input
  
  const chatMessages = document.getElementById("chatMessages");
  const userMsgIndex = chatMessages.children.length;
  displayMessage({
    role: "user",
    user_name: userName,
    content: message,
    timestamp: Math.floor(Date.now() / 1000),
  }, userMsgIndex);

  isLoading = true;
  const sendBtn = document.getElementById("sendBtn");
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerHTML = 'Sending <span class="spinner"></span>';
  }

  fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: message,
      chat_id: currentChatId,
      character_id: currentCharacterId,
      user_name: userName, // <-- send user name
    }),
    credentials: 'include',
  })
    .then((response) => {
      console.log("📥 Send message response status:", response.status);
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("✅ Message response received:", data);

      if (!currentChatId) {
        currentChatId = data.chat_id;
        console.log("🆔 Set new chat ID:", currentChatId);
        loadChats();
      }

      const assistantMsgIndex = chatMessages.children.length;
      displayMessage({
        role: "assistant",
        content: data.response,
        timestamp: Math.floor(Date.now() / 1000),
      }, assistantMsgIndex);

      // Then show narrator message if it exists
      let narratorWasDisplayed = false;
      if (data.narrator_message) {
        const narratorMsgIndex = chatMessages.children.length;
        displayMessage({
          role: "narrator",
          content: data.narrator_message,
          timestamp: Math.floor(Date.now() / 1000),
          coords: data.narrator_coords || data.current_coords  // Add coordinates for map flashing
        }, narratorMsgIndex);
        narratorWasDisplayed = true;
      }

      if (data.look_result) {
        displayMessage({
          role: "system",
          content: data.look_result,
          timestamp: Math.floor(Date.now() / 1000)
        }, chatMessages.children.length);
      }

      if (data.current_coords && Array.isArray(data.current_coords)) {
        updatePlayerDot(data.current_coords[0], data.current_coords[1]);
      }

      if (data && data.visited_nodes) {
        updateFogOfWar(data.visited_nodes);
        window.currentVisitedNodes = data.visited_nodes;
        // updateFogOfWarZoom(data.visited_nodes);
      }
      
      // --- AUTO-CONTINUE LOGIC ---
      // Auto-continue when LLM moves or uses @LOOK (narrator message enhances but isn't required)
      if (data.llm_moved || data.llm_used_look) {
        console.log(`Auto-continue triggered: llm_moved=${data.llm_moved}, llm_used_look=${data.llm_used_look}, narratorWasDisplayed=${narratorWasDisplayed}`);
        // Wait a moment for UI update, then auto-continue
        setTimeout(() => {
          fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: "[OOC: Continue.]", // or "" if you want a blank message
              chat_id: currentChatId,
              character_id: currentCharacterId,
              user_name: userName,
            }),
            credentials: 'include',
          })
          .then(response => response.json())
          .then(autoData => {
            // Display the LLM's auto-response
            const autoMsgIndex = chatMessages.children.length;
            displayMessage({
              role: "assistant",
              content: autoData.response,
              timestamp: Math.floor(Date.now() / 1000),
            }, autoMsgIndex);

            if (autoData.narrator_message) {
              const autoNarratorMsgIndex = chatMessages.children.length;
              displayMessage({
                role: "narrator",
                content: autoData.narrator_message,
                timestamp: Math.floor(Date.now() / 1000),
                coords: autoData.narrator_coords || autoData.current_coords  // Add coordinates for map flashing
              }, autoNarratorMsgIndex);
            }

            if (autoData.current_coords && Array.isArray(autoData.current_coords)) {
              updatePlayerDot(autoData.current_coords[0], autoData.current_coords[1]);
            }
          });
        }, 1200); // 1.2s delay for smoother UX
      }
    })
    .catch((error) => {
      console.error("❌ Error sending message:", error);
      showNotification("Failed to send message. Is the backend running?", "error");
    })
    .finally(() => {
      // --- START OF CORRECTION ---
      // This block now controls the entire post-request state.
      console.log("🏁 Send message request finished");

      // 1. Set loading to false FIRST.
      isLoading = false; 
      console.log("✅ isLoading set to false");
      
      // 2. Reset the button.
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
      }

      // 3. Scroll the chat.
      const chatMessages = document.getElementById("chatMessages");
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
      
      // 4. NOW, check if we should start the timer.
      console.log("🔍 Checking if should start auto-continue timer:");
      console.log("  - isAutoContinueEnabled:", isAutoContinueEnabled);
      if (isAutoContinueEnabled) {
        console.log("🔄 Starting auto-continue timer after request finished");
        startContinueTimer();
      } else {
        console.log("⏹️ Auto-continue disabled, not starting timer");
      }

      // 5. Update the mood color immediately.
      updateMoodColor(); // Add this for an immediate update
      updateBodyLanguageState(); 
        
        if (isAutoContinueEnabled) {
            startContinueTimer();
        }
    });
}

// Add a manual trigger function for testing
function manualTriggerAutoContinue() {
  console.log("🧪 Manual trigger requested");
  triggerAutoContinue();
}



/* Gender Toggle Functions */

// document.addEventListener("DOMContentLoaded", function() {
//   const genderToggle = document.getElementById("bodyGenderToggle");
//   const bodyIconImg = document.getElementById("bodyIconImg");
//   const moodOverlay = document.getElementById("moodOverlay");
//   const preferred = localStorage.getItem("preferredBodyGender");

//   if (genderToggle) {
//     // Restore toggle state from localStorage (default to female if not set)
//     genderToggle.checked = preferred === "f";

//     // Always update the image to match the toggle state
//     if (bodyIconImg) {
//       if (genderToggle.checked) {
//         bodyIconImg.src = "img/body_icon_f.png";
//         if (moodOverlay) {
//           moodOverlay.style.webkitMaskImage = `url('img/body_icon_f.png')`;
//           moodOverlay.style.maskImage = `url('img/body_icon_f.png')`;
//         }
//       } else {
//         bodyIconImg.src = "img/body_icon_m.png";
//         if (moodOverlay) {
//           moodOverlay.style.webkitMaskImage = `url('img/body_icon_m.png')`;
//           moodOverlay.style.maskImage = `url('img/body_icon_m.png')`;
//         }
//       }
//     }
//   }
// }); 


// Function to update body image and mood overlay based on toggle state
function updateBodyImageAndMood(isFemale) {
  const bodyIconImg = document.getElementById("bodyIconImg");
  const moodOverlay = document.getElementById("moodOverlay");
  
  if (bodyIconImg) {
    if (isFemale) {
      bodyIconImg.src = "img/body_icon_f.png";
      if (moodOverlay) {
        moodOverlay.style.webkitMaskImage = `url('img/body_icon_f.png')`;
        moodOverlay.style.maskImage = `url('img/body_icon_f.png')`;
      }
    } else {
      bodyIconImg.src = "img/body_icon_m.png";
      if (moodOverlay) {
        moodOverlay.style.webkitMaskImage = `url('img/body_icon_m.png')`;
        moodOverlay.style.maskImage = `url('img/body_icon_m.png')`;
      }
    }
  }
}

// Function to get the appropriate gender preference for current context
function getCurrentGenderPreference() {
  if (window.currentCharacterId) {
    // Check for character-specific preference first
    const charPref = localStorage.getItem("bodyGender_" + window.currentCharacterId);
    if (charPref !== null) {
      return charPref === "f";
    }
    // If no character-specific preference, fall back to global
    const globalPref = localStorage.getItem("preferredBodyGender");
    return globalPref === "f";
  }
  
  // No character, use global preference
  const globalPref = localStorage.getItem("preferredBodyGender");
  return globalPref === "f"; // Default to female if no preference set
}

// Function to set gender preference for current context
function setCurrentGenderPreference(isFemale) {
  const genderValue = isFemale ? "f" : "m";
  
  if (window.currentCharacterId) {
    // Always save character-specific preference when in a character chat
    localStorage.setItem("bodyGender_" + window.currentCharacterId, genderValue);
    console.log(`Saved gender preference for character ${window.currentCharacterId}: ${genderValue}`);
  } else {
    // Save global preference when not in a character chat
    localStorage.setItem("preferredBodyGender", genderValue);
    console.log(`Saved global gender preference: ${genderValue}`);
  }
}

document.getElementById("bodyGenderToggle").addEventListener("change", function() {
  const isFemale = this.checked;
  
  // Save the preference
  setCurrentGenderPreference(isFemale);
  
  // Update the body image and mood overlay
  updateBodyImageAndMood(isFemale);
});

// Updated DOMContentLoaded event listener
document.addEventListener("DOMContentLoaded", function() {
  const genderToggle = document.getElementById("bodyGenderToggle");
  
  if (genderToggle) {
    // Get the current preference
    const isFemale = getCurrentGenderPreference();
    
    // Set toggle state without triggering change event
    genderToggle.checked = isFemale;
    
    // Update the body image and mood overlay
    updateBodyImageAndMood(isFemale);
  }
});

// This should replace the existing gender toggle code in your loadChat function:
function updateLoadChatGenderToggle(chat) {
  const genderToggle = document.getElementById("bodyGenderToggle");
  
  if (genderToggle) {
    // Make sure currentCharacterId is set before getting preference
    console.log(`Loading chat with character ID: ${chat.character_id}`);
    
    // Get preference for this specific chat
    const isFemale = getCurrentGenderPreference();
    console.log(`Gender preference for this chat: ${isFemale ? 'female' : 'male'}`);
    
    // Set toggle state without triggering change event
    genderToggle.checked = isFemale;
    
    // Update the body image and mood overlay
    updateBodyImageAndMood(isFemale);
  }
}

function debugGenderPreferences() {
  console.log("=== Gender Preferences Debug ===");
  console.log("Current character ID:", window.currentCharacterId);
  console.log("Global preference:", localStorage.getItem("preferredBodyGender"));
  
  // Show all character-specific preferences
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith("bodyGender_")) {
      console.log(`${key}: ${localStorage.getItem(key)}`);
    }
  }
  console.log("=== End Debug ===");
}



// Display a message in the chat
/* function displayMessage(message) {
  console.log("Displaying message:", message);
  const chatMessages = document.getElementById("chatMessages");
  const messageElement = document.createElement("div");

  let messageClass = message.role;
  if (message.role === "assistant" && currentCharacterId) {
    messageClass = "character";
  }

  messageElement.className = `message ${messageClass}`;

  const contentWrapper = document.createElement("div");
  contentWrapper.className = "message-content";
  contentWrapper.innerHTML = formatAndStyleMessage(message.content);
  messageElement.appendChild(contentWrapper);

  const timestampElement = document.createElement("span");
  timestampElement.className = "message-meta";
  timestampElement.textContent = formatTimestamp(message.timestamp);
  messageElement.appendChild(timestampElement);

  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
} */

// Update the active mode display

// Extract coordinates from narrator messages stored in chat history
function extractCoordsFromNarratorMessage(message) {
  // For existing narrator messages, we'll use the current player coordinates
  // In the future, we could store coordinates in the message when saving
  if (message.role === "narrator" || 
      (message.role === "user" && message.content.includes("[NARRATOR:"))) {
    return window.currentPlayerCoords || [1, 1];
  }
  return null;
}

// Flash a specific node on the map with yellow glow
function flashNodeOnMap(x, y) {
  console.log(`Flashing node at coordinates: [${x}, ${y}]`);
  
  // Flash on both mini-map and zoom map
  flashNodeOnMiniMap(x, y);
  
  // If zoom map is visible, flash there too
  const zoomOverlay = document.getElementById('world-map-zoom-overlay');
  if (zoomOverlay && zoomOverlay.style.display !== 'none') {
    flashNodeOnZoomMap(x, y);
  }
}

function flashNodeOnMiniMap(x, y) {
  const mapPanel = document.getElementById('world-map-panel');
  const mapWidth = mapPanel.offsetWidth;
  const mapHeight = mapPanel.offsetHeight;
  
  // Convert grid coordinates to pixel position
  const px = (x / 99) * mapWidth;
  const py = (y / 99) * mapHeight;
  
  // Create flash element
  const flashElement = document.createElement('div');
  flashElement.style.position = 'absolute';
  flashElement.style.left = `${px - 10}px`;
  flashElement.style.top = `${py - 10}px`;
  flashElement.style.width = '20px';
  flashElement.style.height = '20px';
  flashElement.style.borderRadius = '50%';
  flashElement.style.backgroundColor = 'rgba(255, 255, 0, 0.8)';
  flashElement.style.boxShadow = '0 0 20px rgba(255, 255, 0, 0.9)';
  flashElement.style.pointerEvents = 'none';
  flashElement.style.zIndex = '1000';
  flashElement.style.animation = 'nodeFlash 3s ease-in-out';
  
  mapPanel.appendChild(flashElement);
  
  // Remove after animation
  setTimeout(() => {
    if (flashElement.parentNode) {
      flashElement.parentNode.removeChild(flashElement);
    }
  }, 3000);
}

function flashNodeOnZoomMap(x, y) {
  const zoomInner = document.getElementById('world-map-zoom-inner');
  const mapWidth = zoomInner.offsetWidth;
  const mapHeight = zoomInner.offsetHeight;
  
  // Convert grid coordinates to pixel position
  const px = (x / 99) * mapWidth;
  const py = (y / 99) * mapHeight;
  
  // Create flash element
  const flashElement = document.createElement('div');
  flashElement.style.position = 'absolute';
  flashElement.style.left = `${px - 15}px`;
  flashElement.style.top = `${py - 15}px`;
  flashElement.style.width = '30px';
  flashElement.style.height = '30px';
  flashElement.style.borderRadius = '50%';
  flashElement.style.backgroundColor = 'rgba(255, 255, 0, 0.8)';
  flashElement.style.boxShadow = '0 0 30px rgba(255, 255, 0, 0.9)';
  flashElement.style.pointerEvents = 'none';
  flashElement.style.zIndex = '1000';
  flashElement.style.animation = 'nodeFlash 3s ease-in-out';
  
  zoomInner.appendChild(flashElement);
  
  // Remove after animation
  setTimeout(() => {
    if (flashElement.parentNode) {
      flashElement.parentNode.removeChild(flashElement);
    }
  }, 3000);
}

// World Map update
function updatePlayerDot(x, y) {
  window.currentPlayerCoords = [x, y];
  // x, y are in 0-99 grid coordinates
  const mapPanel = document.getElementById('world-map-panel');
  const dot = document.getElementById('player-dot');
  const mapWidth = mapPanel.offsetWidth;
  const mapHeight = mapPanel.offsetHeight;

  // Convert grid (0-99) to pixel position
  const px = (x / 99) * mapWidth;
  const py = (y / 99) * mapHeight;

  dot.style.left = `${px}px`;
  dot.style.top = `${py}px`;

  const zoomOverlay = document.getElementById('world-map-zoom-overlay');
  if (zoomOverlay && zoomOverlay.style.display !== 'none') {
    updatePlayerDotZoom(x, y);
  }
}

let worldMapZoomTimeout = null;

document.getElementById('world-map-panel').addEventListener('mouseenter', function() {
  // Set a delay (e.g., 600ms) before showing the zoom overlay
  worldMapZoomTimeout = setTimeout(showWorldMapZoom, 1000); // Increase delay as desired
});

document.getElementById('world-map-panel').addEventListener('mouseleave', function() {
  // Cancel the zoom if the mouse leaves before the delay
  clearTimeout(worldMapZoomTimeout);
});

// Keep click-to-zoom instant
document.getElementById('world-map-panel').addEventListener('click', showWorldMapZoom);

// document.getElementById('world-map-panel').addEventListener('mouseenter', showWorldMapZoom);
document.getElementById('world-map-panel').addEventListener('click', showWorldMapZoom);

function updatePlayerDotZoom(x, y) {
  const zoomInner = document.getElementById('world-map-zoom-inner');
  const dot = document.getElementById('player-dot-zoom');
  const mapWidth = zoomInner.offsetWidth;
  const mapHeight = zoomInner.offsetHeight;

  // 1. Define the icon's size in pixels for consistency.
  const iconSize = 10; // You can adjust this value.
  // dot.style.width = `${iconSize}px`;
  // dot.style.height = `${iconSize}px`;

  // 2. Calculate the base coordinates.
  let px = (x / 99) * mapWidth;
  let py = (y / 99) * mapHeight;
  // const offsetX = 0;
  // const offsetY = 0;

  // 3. Adjust coordinates to place the icon's anchor point correctly.
  //    This replaces the CSS transform. To place the bottom-center of the icon
  //    on the coordinate (like a map pin), use this:
  // px -= (iconSize); // 
  // py -= iconSize;       // Place bottom edge on the point
  // px = Math.max(0, Math.min(px, mapWidth - iconSize));   // Keep within bounds  -10
  // py = Math.max(0, Math.min(py, mapHeight - iconSize));  // Keep within bounds  -20


  px = px;
  py = py;

  // 4. Set the final position.
  dot.style.left = `${px - 17}px`;
  dot.style.top = `${py - 28}px`;
}

function showWorldMapZoom() {
  document.getElementById('world-map-zoom-overlay').style.display = 'flex';

  // Use a setTimeout to allow the browser to render the map first.
  // This ensures that offsetWidth and offsetHeight will return the correct dimensions.
  setTimeout(() => {
    if (window.currentPlayerCoords) {
      updatePlayerDotZoom(
        window.currentPlayerCoords[0],
        window.currentPlayerCoords[1]
      );
    }
    // Use currentPlayerCoords if set, otherwise default to [1,1]
    const coords = (window.currentPlayerCoords && window.currentPlayerCoords.length === 2)
      ? window.currentPlayerCoords
      : [0, 1];
    updatePlayerDotZoom(coords[0], coords[1]);
  }, 0); // A delay of 0 is enough to push this to the next browser task.
}

function updateFogOfWar(visitedNodes) {
  // Update sidebar mini-map fog
  const fogCanvasMini = document.getElementById('world-map-fog');
  if (fogCanvasMini) {
    const ctxMini = fogCanvasMini.getContext('2d');
    const widthMini = fogCanvasMini.width;
    const heightMini = fogCanvasMini.height;
    ctxMini.clearRect(0, 0, widthMini, heightMini);
    ctxMini.fillStyle = 'rgba(0,0,0,0.98)';
    ctxMini.fillRect(0, 0, widthMini, heightMini);
    visitedNodes.forEach(([x, y]) => {
      const px = (x / 99) * widthMini;
      const py = (y / 99) * heightMini;
      ctxMini.save();
      ctxMini.globalCompositeOperation = 'destination-out';
      ctxMini.beginPath();
      ctxMini.arc(px, py, 8, 0, 2 * Math.PI); // Smaller radius for mini-map
      ctxMini.fill();
      ctxMini.restore();
    });
  }

  // Update zoomed map fog
  const fogCanvasZoom = document.getElementById('world-map-zoom-fog');
  if (fogCanvasZoom) {
    const ctxZoom = fogCanvasZoom.getContext('2d');
    const widthZoom = fogCanvasZoom.width;
    const heightZoom = fogCanvasZoom.height;
    ctxZoom.clearRect(0, 0, widthZoom, heightZoom);
    ctxZoom.fillStyle = 'rgba(0,0,0,1)';
    ctxZoom.fillRect(0, 0, widthZoom, heightZoom);
    visitedNodes.forEach(([x, y]) => {
      const px = (x / 99) * widthZoom;
      const py = (y / 99) * heightZoom;
      ctxZoom.save();
      ctxZoom.globalCompositeOperation = 'destination-out';
      ctxZoom.beginPath();
      ctxZoom.arc(px, py, 16, 0, 2 * Math.PI); // Larger radius for zoom
      ctxZoom.fill();
      ctxZoom.restore();
    });
  }
}

// Hide overlay on click or mouseleave
document.getElementById('world-map-zoom-inner').addEventListener('mouseleave', function(e){
  document.getElementById('world-map-zoom-overlay').style.display = 'none';
});

 document.getElementById('world-map-zoom-overlay').addEventListener('click', function(e){
   if(e.target === this) this.style.display = 'none';
 });

document.getElementById('playerIconSelect').addEventListener('change', function() {
  const iconUrl = this.value;
  document.querySelectorAll('#player-dot img, #player-dot-zoom img').forEach(img => {
    img.src = iconUrl;
  });
});

document.addEventListener('DOMContentLoaded', function() {
  updateFogOfWar([]);
});
