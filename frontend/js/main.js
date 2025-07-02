// Global variables
let currentChatId = null;
let currentCharacterId = null;
let isLoading = false;
const API_BASE_URL = "http://localhost:5000/api";

// --- START: New Auto-Continue Globals ---
let autoContinueTimerId = null;
let isAutoContinueEnabled = false;
const AUTO_CONTINUE_DELAY = 40000; // 40 seconds
// --- END: New Auto-Continue Globals ---
let pendingDiceResult = null;
let pendingDiceSides = null;
let moodColorInterval = null;
let isReadingBodyLanguage = false;

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM fully loaded");

  // Initialize the app
  try {
    console.log("Loading chats...");
    loadChats();
    console.log("Loading characters...");
    loadCharacters();
    console.log("Loading settings...");
    loadSettings();

    // Initialize summarize button (hidden by default)
    const summarizeBtn = document.getElementById("summarizeBtn");
    if (summarizeBtn) {
      summarizeBtn.style.display = "none";
    }

    // Event listeners for buttons
    console.log("Setting up event listeners...");

    const newChatBtn = document.getElementById("newChatBtn");
    if (newChatBtn) {
      newChatBtn.addEventListener("click", () => {
        console.log("New Chat button clicked");
        startNewChat();
      });
    } else {
      console.error("New Chat button not found");
    }

    const settingsBtn = document.getElementById("settingsBtn");
    if (settingsBtn) {
      settingsBtn.addEventListener("click", () => {
        console.log("Settings button clicked");
        openSettingsModal();
      });
    } else {
      console.error("Settings button not found");
    }

    const sendBtn = document.getElementById("sendBtn");
    if (sendBtn) {
      sendBtn.addEventListener("click", () => {
        console.log("Send button clicked");
        sendMessage();
      });
    } else {
      console.error("Send button not found");
    }

    const userInput = document.getElementById("userInput");
    if (userInput) {
      userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          console.log("Enter key pressed in input");
          e.preventDefault();
          sendMessage();
        }
      });
    } else {
      console.error("User input not found");
    }

    const newCharacterBtn = document.getElementById("newCharacterBtn");
    if (newCharacterBtn) {
      newCharacterBtn.addEventListener("click", () => {
        console.log("New Character button clicked");
        openCharacterModal();
      });
    } else {
      console.error("New Character button not found");
    }

    // Modal close buttons
    document.querySelectorAll(".close").forEach((closeBtn) => {
      closeBtn.addEventListener("click", () => {
        console.log("Modal close button clicked");
        document.getElementById("settingsModal").style.display = "none";
        document.getElementById("characterModal").style.display = "none";
      });
    });

    // Form submissions
    const settingsForm = document.getElementById("settingsForm");
    if (settingsForm) {
      settingsForm.addEventListener("submit", (e) => {
        console.log("Settings form submitted");
        e.preventDefault();
        saveSettings(e);
      });
    } else {
      console.error("Settings form not found");
    }

    const characterForm = document.getElementById("characterForm");
    if (characterForm) {
      characterForm.addEventListener("submit", (e) => {
        console.log("Character form submitted");
        e.preventDefault();
        saveCharacter(e);
      });
    } else {
      console.error("Character form not found");
    }

    // Temperature slider
    const temperatureSlider = document.getElementById("temperature");
    const temperatureValue = document.getElementById("temperatureValue");
    if (temperatureSlider && temperatureValue) {
      temperatureSlider.addEventListener("input", () => {
        temperatureValue.textContent = temperatureSlider.value;
      });
    }

    // LLM provider change
    const llmProvider = document.getElementById("llmProvider");
    if (llmProvider) {
      llmProvider.addEventListener("change", toggleProviderSettings);
    }

    console.log("Initialization complete");

    // Dice roll buttons
    const diceButtons = {
      roll6Btn: 6,
      roll20Btn: 20,
      roll2Btn: 2,
      roll10Btn: 10
    };
    const diceResult = document.getElementById("diceResult");
    const copyDiceBtn = document.getElementById("copyDiceBtn");
    const pasteDiceBtn = document.getElementById("pasteDiceBtn");

    // Add event listeners for each dice button
    Object.entries(diceButtons).forEach(([buttonId, sides]) => {
      const button = document.getElementById(buttonId);
      if (button) {
        button.addEventListener("click", () => {
          const result = rollDice(sides);
          diceResult.textContent = `Result: ${result}`;
        });
      }
    });

    // Copy dice result to clipboard
    if (copyDiceBtn) {
      copyDiceBtn.addEventListener("click", () => {
        const resultText = diceResult.textContent.replace("Result: ", "");
        if (resultText !== "-") {
          navigator.clipboard
            .writeText(resultText)
            .then(() => {
              showNotification("Dice result copied to clipboard!", "success");
            })
            .catch((err) => {
              console.error("Failed to copy dice result:", err);
              showNotification("Failed to copy dice result.", "error");
            });
        } else {
          showNotification("No dice result to copy.", "error");
        }
      });
    }

   Object.entries(diceButtons).forEach(([buttonId, sides]) => {
    const button = document.getElementById(buttonId);
    if (button) {
      button.addEventListener("click", () => {
        const result = rollDice(sides);
        pendingDiceResult = result; // Store for next message
        pendingDiceSides = sides;
        // Show unobtrusive notification (handled below)
        showDicePendingTooltip(button, sides);
      });
    }

    const bodyText = document.getElementById("bodyLanguageText");
    const bodyLanguageOverlay = document.getElementById("bodyLanguageOverlay");
    if (bodyLanguageOverlay) {
        bodyLanguageOverlay.addEventListener("click", () => {
            // 1. Check the flag. If an action is already in progress, do nothing.
            if (isReadingBodyLanguage) {
                console.log("Read body language action already in progress. Ignoring click.");
                return;
            }
            if (!currentChatId) return;

            // 2. Set the flag to true to block other clicks.
            isReadingBodyLanguage = true;
            console.log("Flag set to true. Starting read-body-language request.");

            // Call the backend endpoint
            fetch(`${API_BASE_URL}/chat/${currentChatId}/read-body-language`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('API call to trigger body language event failed.');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    console.log("Backend confirmed trait/prompt changes. Hiding overlay.");
                    bodyLanguageOverlay.classList.remove('visible');
                    // showNotification("You try to read their expression...", "info"); // Debug ONLY
                }
            })
            .catch(error => {
                console.error("Error during read-body-language event:", error);
                showNotification("Could not perform the action.", "error");
            })
            .finally(() => {
                // 3. IMPORTANT: Reset the flag to false after the API call is complete.
                isReadingBodyLanguage = false;
                console.log("Flag reset to false. Ready for next action.");
            });
        });
    }

  });

  

/* Object.entries(diceButtons).forEach(([buttonId, sides]) => {
  const button = document.getElementById(buttonId);
  if (button) {
    button.addEventListener("click", () => {
      const result = rollDice(sides);
      diceResult.textContent = `Result: ${result}`;
      pendingDiceResult = result; // Store for next message
      pendingDiceSides = sides;
      // showNotification(`You rolled a d${sides}: ${result}. It will be appended to your next message.`, "success");
    });
  }
}); */



    // Load plots into the dropdown
    fetch(`${API_BASE_URL}/plots`)
      .then((response) => response.json())
      .then((data) => {
        const plotSelector = document.getElementById("plotSelector");
        if (plotSelector && data.plots) {
          Object.entries(data.plots).forEach(([key, plot]) => {
            const option = document.createElement("option");
            option.value = key;
            option.textContent = plot.name;
            option.dataset.description = plot.description;
            plotSelector.appendChild(option);
          });
        }
      })
      .catch((error) => {
        console.error("Error loading plots:", error);
        showNotification("Failed to load plots. Is the backend running?", "error");
      });

    // Handle plot selection
    const selectPlotBtn = document.getElementById("selectPlotBtn");
    if (selectPlotBtn) {
      selectPlotBtn.addEventListener("click", () => {
        const plotSelector = document.getElementById("plotSelector");
        const selectedOption = plotSelector.options[plotSelector.selectedIndex];
        const systemPromptTextarea = document.getElementById("systemPrompt");

        if (selectedOption && selectedOption.value) {
          const plotName = selectedOption.textContent;
          const plotDescription = selectedOption.dataset.description;

          // Append the plot name and description to the current system prompt
          const currentPrompt = systemPromptTextarea.value.trim();
          const updatedPrompt = `${currentPrompt}\n\nPlot Selected: ${plotName}. ${plotDescription}`;
          systemPromptTextarea.value = updatedPrompt;

          // Trigger the update automatically
          updateSystemPrompt();
        } else {
          showNotification("Please select a plot.", "error");
        }
      });
    }

    // --- START: New Auto-Continue Listeners ---
    const autoContinueToggle = document.getElementById("autoContinueToggle");

    if (autoContinueToggle) {
      // Ensure the toggle is unchecked on load
      autoContinueToggle.checked = false;
      isAutoContinueEnabled = false;

      autoContinueToggle.addEventListener("change", (e) => {
        isAutoContinueEnabled = e.target.checked;
        console.log(`Auto-continue enabled: ${isAutoContinueEnabled}`);
        if (!isAutoContinueEnabled) {
          stopContinueTimer(); // Stop timer if toggled off
        }
      });
    }

    if (userInput) {
      userInput.addEventListener("input", () => {
        // Stop the timer as soon as the user starts typing
        if (autoContinueTimerId) {
          stopContinueTimer();
        }
      });
    }
    // --- END: New Auto-Continue Listeners ---

    // Handle system prompt updates
    const updateSystemPromptBtn = document.getElementById(
      "updateSystemPromptBtn"
    );
    if (updateSystemPromptBtn) {
      updateSystemPromptBtn.addEventListener("click", updateSystemPrompt);
    }
  } catch (error) {
    console.error("Error during initialization:", error);
  }
});

// Window events
window.addEventListener("click", (event) => {
  if (event.target === document.getElementById("settingsModal")) {
    document.getElementById("settingsModal").style.display = "none";
  }
  if (event.target === document.getElementById("characterModal")) {
    document.getElementById("characterModal").style.display = "none";
  }
});


// --- HELPER FUNCTION FOR UPDATING SYSTEM PROMPT ---
function updateSystemPrompt() {
  const systemPromptTextarea = document.getElementById("systemPrompt");
  const updatedPrompt = systemPromptTextarea.value.trim();

  if (updatedPrompt) {
    if (currentChatId) {
      // Send the updated prompt to the backend for the current chat
      fetch(`${API_BASE_URL}/chat/${currentChatId}/system-prompt`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_prompt: updatedPrompt }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showNotification(data.error, "error");
          } else {
            showNotification("System prompt updated successfully!", "success");
            console.log(
              "Updated system prompt for chat:",
              currentChatId,
              updatedPrompt
            );
          }
        })
        .catch((error) => {
          console.error("Error updating system prompt:", error);
          showNotification("Failed to update the system prompt.", "error");
        });
    } else {
      showNotification("No chat selected. Cannot update system prompt.", "error");
    }
  } else {
    showNotification("System prompt cannot be empty.", "error");
  }
}


// --- START: Dice Functions ---

function showDicePendingTooltip(button, sides) {
  // Remove any existing tooltip
  let existing = document.getElementById("diceTooltip");
  if (existing) existing.remove();

  // Create tooltip
  const tooltip = document.createElement("div");
  tooltip.id = "diceTooltip";
  tooltip.className = "dice-tooltip";
  tooltip.textContent = `A d${sides} roll will be added to your next message.`;

  // Position tooltip above the button
  const rect = button.getBoundingClientRect();
  tooltip.style.position = "absolute";
  tooltip.style.left = `${rect.left + window.scrollX}px`;
  tooltip.style.top = `${rect.top + window.scrollY - 30}px`;
  tooltip.style.zIndex = 1000;

  document.body.appendChild(tooltip);

  // Remove tooltip after 2 seconds
  setTimeout(() => {
    tooltip.remove();
  }, 2000);
}


// --- START: Mood Color Functions ---

async function updateMoodColor() {
  if (!currentChatId) {
    // Hide the overlay if no chat is active
    const moodOverlay = document.getElementById("moodOverlay");
    if(moodOverlay) moodOverlay.style.backgroundColor = "transparent";
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/chat/${currentChatId}/mood-color`);
    if (!response.ok) {
        throw new Error(`Mood color API error: ${response.status}`);
    }
    const color = await response.json();
    
    const moodOverlay = document.getElementById("moodOverlay");
    if (moodOverlay) {
      moodOverlay.style.backgroundColor = `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a})`;
    }
  } catch (error) {
    console.error("Failed to fetch mood color:", error);
  }
}

 // Fetches and updates the character's body language visibility state.

async function updateBodyLanguageState() {
  const bodyOverlay = document.getElementById("bodyLanguageOverlay");
  const bodyText = document.getElementById("bodyLanguageText");

  if (!currentChatId || !bodyOverlay || !bodyText) {
    if (bodyOverlay) bodyOverlay.classList.remove("visible");
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/chat/${currentChatId}/body-language-state`);
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    
    const state = await response.json();
    
    if (!state.is_readable) {
      bodyOverlay.classList.add("visible");
      bodyText.textContent = `Take the chance to read ${state.character_name}'s body language?`;
    } else {
      bodyOverlay.classList.remove("visible");
    }
  } catch (error) {
    console.error("Failed to fetch body language state:", error);
    bodyOverlay.classList.remove("visible");
  }
}


// --- START: Auto-Continue Functions (Debug Version) ---
function startContinueTimer() {
  console.log("=== startContinueTimer called ===");
  console.log("isAutoContinueEnabled:", isAutoContinueEnabled);
  console.log("isLoading:", isLoading);
  console.log("currentChatId:", currentChatId);
  
  // Don't start timer if auto-continue is disabled, already loading, or no current chat
  if (!isAutoContinueEnabled) {
    console.log("❌ Auto-continue is disabled, not starting timer");
    return;
  }
  
  if (isLoading) {
    console.log("❌ Currently loading, not starting timer");
    return;
  }
  
  if (!currentChatId) {
    console.log("❌ No current chat ID, not starting timer");
    return;
  }

  const autoContinueBtn = document.getElementById("autoContinueBtn");
  if (!autoContinueBtn) {
    console.error("❌ Auto-continue button not found in DOM");
    return;
  }

  // Stop any existing timer first
  if (autoContinueTimerId) {
    console.log("🔄 Clearing existing timer");
    clearTimeout(autoContinueTimerId);
    autoContinueTimerId = null;
  }

  console.log(`✅ Starting auto-continue timer for ${AUTO_CONTINUE_DELAY}ms`);
  autoContinueBtn.style.display = "block";
  autoContinueBtn.classList.add("is-counting-down");

  // Set a timeout to trigger the continuation
  autoContinueTimerId = setTimeout(() => {
    console.log("⏰ Auto-continue timer finished! Triggering continuation...");
    triggerAutoContinue();
  }, AUTO_CONTINUE_DELAY);
  
  console.log("Timer ID set to:", autoContinueTimerId);
}

function stopContinueTimer() {
  console.log("=== stopContinueTimer called ===");
  
  const autoContinueBtn = document.getElementById("autoContinueBtn");
  if (autoContinueTimerId) {
    console.log("🛑 Stopping auto-continue timer, ID:", autoContinueTimerId);
    clearTimeout(autoContinueTimerId);
    autoContinueTimerId = null;
  } else {
    console.log("ℹ️ No timer to stop");
  }
  
  if (autoContinueBtn) {
    autoContinueBtn.classList.remove("is-counting-down");
    autoContinueBtn.style.display = "none";
    console.log("🎨 Updated button styling");
  }
}

function triggerAutoContinue() {
    console.log("=== triggerAutoContinue called ===");
    
    stopContinueTimer(); // Clean up button state

    if (isLoading) {
        console.log("❌ Already loading, aborting auto-continue");
        return;
    }
    
    if (!currentChatId) {
        console.log("❌ No current chat ID, aborting auto-continue");
        return;
    }

    console.log("🚀 Executing auto-continue API call");

    // Set loading state
    isLoading = true;
    const sendBtn = document.getElementById("sendBtn");
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = 'Auto-continuing <span class="spinner"></span>';
        console.log("🔄 Set send button to loading state");
    }

    const INSTRUCTIONAL_CONTINUE_MESSAGE = "[OOC: Continue.]";

    const requestBody = {
        message: INSTRUCTIONAL_CONTINUE_MESSAGE, // Send the instruction instead of ""
        chat_id: currentChatId,
        character_id: currentCharacterId,
    };
    
    console.log("📤 Sending request:", requestBody);

    fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        credentials: 'include',
    })
    .then((response) => {
        console.log("📥 Auto-continue response status:", response.status);
        console.log("📥 Auto-continue response headers:", response.headers);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then((data) => {
        console.log("✅ Auto-continue response received:", data);
        
        displayMessage({
            role: "assistant",
            content: data.response,
            timestamp: Math.floor(Date.now() / 1000),
        });
        
        console.log("💬 Message displayed");
        
        // Check if we should restart the timer
        const userInputValue = document.getElementById("userInput").value.trim();
        console.log("🔍 Checking restart conditions:");
        console.log("  - isAutoContinueEnabled:", isAutoContinueEnabled);
        console.log("  - userInput is empty:", !userInputValue);
        
        // Only restart timer if still enabled and not interrupted by user input
        if (isAutoContinueEnabled && !userInputValue) {
            console.log("🔄 Restarting timer for next auto-continue");
            startContinueTimer();
        } else {
            console.log("⏹️ Not restarting timer");
        }
    })
    .catch((error) => {
        console.error("❌ Error during auto-continuation:", error);
        showNotification("Failed to auto-continue. Is the backend running?", "error");
    })
    .finally(() => {
      console.log("🏁 Auto-continue request finished");
      // --- START OF CORRECTION ---
      // 1. Set loading to false FIRST.
      isLoading = false;
      console.log("✅ isLoading set to false");

      // 2. Reset the button.
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
        console.log("✅ Reset send button");
      }

      // 3. Scroll the chat.
      const chatMessages = document.getElementById("chatMessages");
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }

      // 4. NOW, check if we should restart the timer.
      const userInputValue = document.getElementById("userInput").value.trim();
      console.log("🔍 Checking restart conditions:");
      console.log("  - isAutoContinueEnabled:", isAutoContinueEnabled);
      console.log("  - userInput is empty:", !userInputValue);

      // Only restart timer if still enabled and not interrupted by user input
      if (isAutoContinueEnabled && !userInputValue) {
        console.log("🔄 Restarting timer for next auto-continue");
        startContinueTimer();
      } else {
        console.log("⏹️ Not restarting timer");
      }
      // --- END OF CORRECTION ---
    });
}
// --- END: Auto-Continue Functions ---



// Utility functions
function formatTimestamp(timestamp) {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function showNotification(message, type = "info") {
  // Simple notification - could be enhanced with a proper notification system
  // Simple notification - could be enhanced with a proper notification system
  let alertType = type === 'info' ? 'Info' : type.charAt(0).toUpperCase() + type.slice(1);
  console.log(`Notification (${type}): ${message}`);
  // This will still use a standard alert, but the log will be more descriptive.
  // For a real app, you would build a custom notification element here.
  alert(`${alertType}: ${message}`);
}

function toggleProviderSettings() {
  console.log("Toggling provider settings");
  const provider = document.getElementById("llmProvider").value;

  document.getElementById("ollamaSettings").style.display =
    provider === "ollama" ? "block" : "none";
  document.getElementById("openaiSettings").style.display =
    provider === "openai" ? "block" : "none";
  document.getElementById("anthropicSettings").style.display =
    provider === "anthropic" ? "block" : "none";
  document.getElementById("geminiSettings").style.display =
    provider === "gemini" ? "block" : "none";
  document.getElementById("perplexitySettings").style.display =
    provider === "perplexity" ? "block" : "none";
}

// Settings functions
function openSettingsModal() {
  console.log("Opening settings modal");
  document.getElementById("settingsModal").style.display = "block";
}

function loadSettings() {
  console.log("Fetching settings from API:", `${API_BASE_URL}/settings`);
  fetch(`${API_BASE_URL}/settings`)
    .then((response) => response.json())
    .then((settings) => {
      console.log("Settings loaded:", settings);
      const provider = settings.llm_provider || "ollama";
      
      document.getElementById("llmProvider").value = provider;
      document.getElementById("ollamaUrl").value = settings.ollama_url || "http://localhost:11434";
      document.getElementById("temperature").value = settings.temperature || 0.7;
      document.getElementById("temperatureValue").textContent = settings.temperature || 0.7;

      // FIX: Load API keys using the correct object keys
      document.getElementById("openaiKey").value = settings.api_keys?.openai || "";
      document.getElementById("anthropicKey").value = settings.api_keys?.anthropic || "";
      document.getElementById("geminiKey").value = settings.api_keys?.gemini_key || ""; // Corrected from 'gemini' to 'gemini_key'
      document.getElementById("perplexityKey").value = settings.api_keys?.perplexity || "";

      // FIX: Only populate the model input for the currently active provider
      if (provider === "ollama") {
        document.getElementById("ollamaModel").value = settings.default_model || "llama3";
      } else if (provider === "openai") {
        document.getElementById("openaiModel").value = settings.default_model || "gpt-4.1";
      } else if (provider === "anthropic") {
        document.getElementById("anthropicModel").value = settings.default_model || "claude-3-5-haiku-latest";
      } else if (provider === "gemini") {
        document.getElementById("geminiModel").value = settings.default_model || "gemini-2.5-flash";
      } else if (provider === "perplexity") {
        document.getElementById("perplexityModel").value = settings.default_model || "sonar";
      }
      
      // Load support LLM settings
      if (settings.support_llm) {
        document.getElementById("supportLlmProvider").value = settings.support_llm.provider || provider;
        document.getElementById("supportLlmModel").value = settings.support_llm.model || settings.default_model || "";
      } else {
        // Default to main provider settings if no support LLM configured
        document.getElementById("supportLlmProvider").value = provider;
        document.getElementById("supportLlmModel").value = settings.default_model || "";
      }
      
      // This will now correctly show the Gemini settings panel
      toggleProviderSettings();
    })
    .catch((error) => {
      console.error("Error loading settings:", error);
      showNotification("Failed to load settings. Is the backend running?", "error");
    });
}

function saveSettings(e) {
  if (e) e.preventDefault();

  const provider = document.getElementById("llmProvider").value;
  let model = "";
  if (provider === "ollama") {
    model = document.getElementById("ollamaModel").value;
  } else if (provider === "openai") {
    model = document.getElementById("openaiModel").value;
  } else if (provider === "anthropic") {
    model = document.getElementById("anthropicModel").value;
  } else if (provider === "gemini") {
    model = document.getElementById("geminiModel").value;
  } else if (provider === "perplexity") {
    model = document.getElementById("perplexityModel").value;
  }

  // Always duplicate main provider/model into support fields
  document.getElementById("supportLlmProvider").value = provider;
  document.getElementById("supportLlmModel").value = model;

  // First fetch current settings to preserve support_llm.api_keys
  fetch(`${API_BASE_URL}/settings`)
    .then((response) => response.json())
    .then((currentSettings) => {
      const settings = {
        llm_provider: provider,
        ollama_url: document.getElementById("ollamaUrl").value,
        temperature: parseFloat(document.getElementById("temperature").value),
        api_keys: {
          openai: document.getElementById("openaiKey").value,
          anthropic: document.getElementById("anthropicKey").value,
          perplexity: document.getElementById("perplexityKey").value,
          gemini_key: document.getElementById("geminiKey").value,
        },
        support_llm: {
          provider: provider,
          model: model,
          // Preserve existing support_llm api_keys if they exist
          api_keys: currentSettings.support_llm?.api_keys || {
            openai: "",
            anthropic: "",
            perplexity: "",
            gemini_key: ""
          }
        },
        default_model: model
      };

      return fetch(`${API_BASE_URL}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
    })
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("settingsModal").style.display = "none";
      showNotification("Settings saved successfully");
    })
    .catch((error) => {
      showNotification("Failed to save settings. Is the backend running?", "error");
    });
}

// Utility function to roll a die
function rollDice(sides) {
  return Math.floor(Math.random() * sides) + 1;
}