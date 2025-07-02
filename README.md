# 🎭 Moodweaver
### *AI Characters with Real Emotions & Dynamic Stories*

<div align="center">

![Moodweaver Banner](https://github.com/user-attachments/assets/65eb2f28-ade4-45ce-b722-a91fc53b5d6a)

*Transform your AI conversations into immersive role-playing experiences*

[🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [🎮 Demo](#-demo) • [📖 Documentation](#-documentation)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/liamlb)

</div>

---

## 🌟 What Makes Moodweaver Special?

Moodweaver brings AI characters to life with dynamically scripted emotions, evolving personalities, and immersive storytelling.

### 🧠 **The Personality Orrery**
Our emotion engine gives AI characters persistent, evolving emotional states:
- **Dynamic Traits**: Trust, paranoia, humor, aggression - all shift based on your interactions
- **Sentiment Analysis**: Characters genuinely react to praise, criticism, flirtation, and hostility  
- **Cathartic Events**: Witness dramatic personality shifts like "Overflowing Joy" or "Paranoid Breakdown"
- **Environmental Awareness**: Characters' surroundings have some effect on their personality
- **Anti-Repetition System**: Characters become bored by repetitive comments, encouraging creative interactions

### 🎯 **Intelligent Task System**
Characters aren't just reactive - they have **agency and goals**:
- AI-driven story controller creates compelling narrative arcs
- Task-based personality guidance keeps characters motivated
- Rich narrative framework with core tensions and hooks
- Progress tracking and priority management for character objectives

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎨 Visual Mood & Body Language System

**See your character's emotions in real-time through color-coded vibes!**

## How it works:
**🌈 Mood Colors = Instant Emotional Intel**
- Character silhouette changes color based on feelings
- Red = angry/aggressive | Blue = sad | Yellow = funny/open/happy
- Colors blend for complex emotions (purple = sad + angry)

**🫥 Mystery Mode**
- Sometimes the mood gets hidden behind an overlay
- Happens at set conversation points
- Character becomes emotionally "unreadable"

**👀 Read the Person & Consequences**
- Click the hidden mood = maybe you're noticed staring
- If character notices, they can react immediately
- Their trust drops, tension rises

## The Magic:
Powered by `PersonalityOrrery` engine for authentic emotional responses that actually matter to gameplay.

### 🗺️ **Interactive World System**
- **Exploration Commands**: The character can LOOK at the available directions around them. And can MOVE in any available direction. 
    - User uses different commands "@LOOK: (direction)" and "I go (direction)"
- **Persistent World Changes**: Actions permanently affect locations. Revisit areas to see lasting effects of previous interactions
    - In area: "*Asuka takes the bottle off the shelf, guzzles it, and slams it on the bar.*" 
    - Returning to area later: "*An empty bottle sits on the bar.*"
- **Dynamic Environment**: Areas blend with neighboring locations for immersive descriptions

### 🎲 **RPG Tools**
- Built-in dice roller (d6, d10, d20, d2)
- Predefined plot structures ("Stranger-to-Besties", "Odd Couple")
- Character creation & management
- Auto-continue AI conversation responses
- Interactive maps with blended area descriptions

</td>
<td width="50%">

### 🔌 **Multi-LLM Support**
- **OpenAI** (GPT-4.1) - Recommended
- **Anthropic** (Claude-3.5-Sonnet) - Recommended
- **Ollama** (Local models)
- *Coming Soon: Google Gemini, OpenRouter*

### 💾 **Smart Memory & Chat Management**
- Long-term conversation context with intelligent summarization
- Persistent character states across sessions
- Chat history management with load/delete functionality
- Message editing capabilities
- Formatted display with novel-like styling

### ⚙️ **Advanced Configuration**
- Dual LLM setup (main + support for sentiment analysis)
- Customizable API endpoints and temperature settings
- Character mood indicators with male/female silhouettes
- Triggerable events through UI interactions

</td>
</tr>
</table>

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/moodweaver.git
cd moodweaver

# Install dependencies
pip install -r requirements.txt

# Run Start file
click Windows bat or Mac/Linux Start sh in main folder

# Settings
Setup your LLM provider in settings interface
```

### 🔑 **API Keys Required**
- OpenAI API key for GPT models
- Anthropic API key for Claude models
- Or run locally with Ollama (no API key needed)

### 🤖 **Recommended Models**
- **OpenAI**: `gpt-4.1` (best performance)
- **Anthropic**: `claude-3-5-sonnet` (excellent reasoning)
- **Local**: Any Ollama-compatible model

---

## 🎮 Demo

```
👤 User: "You seem tense today..."

🤖 AI: *shifts uncomfortably, avoiding eye contact* 
    "Tense? I'm not— Look, just because I haven't been 
    sleeping doesn't mean anything's wrong."
    
    [Paranoia: ↑ | Trust: ↓ | Mood: Defensive]

👤 User: "@LOOK: north"

🤖 AI: *glances toward the northern path*
    "There's a winding trail leading up into the hills. 
    I can hear water flowing from somewhere beyond the trees..."
    
    [Curiosity: ↑ | Mood: Intrigued]

👤 User: "I go north"

🤖 AI: *follows reluctantly, footsteps crunching on fallen leaves*
    "This place feels... different. Like someone was here recently."
    
    [Paranoia: ↑ | Environmental Tension: ↑]
```
![MWpic2](https://github.com/user-attachments/assets/00a389ab-de0d-4642-94e4-73ed3e6ef008)

---

## 🌟 Key Gameplay Features

### 🎭 **Character Agency**
- AI characters have their own goals and motivations
- Task-driven behavior creates dynamic storytelling
- Characters can initiate actions and drive the narrative forward

### 🗺️ **World Exploration**
- Use `@LOOK: <direction>` to scout ahead
- Move with `I go <direction>` to explore
- Every action leaves permanent marks on the world
- Environmental storytelling through area descriptions

### 🎲 **Chance & Choice**
- Built-in dice rolling for skill checks and random events
- Multiple plot frameworks to guide your story
- Auto-continue feature keeps the action flowing

---

## 🫥 Todo

- Modular character import/export
- Custom trait/emotion saved configurations
- Premade characters with custom traits/emotions
- Google Gemini and OpenRouter support
- UI improvements and themes
- Light/Dark mode toggle
- Enhanced world map visualization

---

## 🛠️ Technology Stack

<div align="center">

| Frontend | Backend | AI Integration |
|----------|---------|----------------|
| JavaScript | Python | OpenAI API |
| HTML/CSS | Flask | Anthropic API |
| Dynamic UI | PersonalityOrrery | Ollama Support |

</div>

---

## 📖 Documentation

- [🏗️ **Setup Guide**](docs/setup.md) - Get started in minutes
- [🎭 **Character Creation**](docs/characters.md) - Design compelling AI personas  
- [🧠 **Personality System**](docs/personality.md) - Deep dive into the Orrery
- [🗺️ **World System**](docs/world.md) - Interactive environments and exploration
- [⚙️ **Configuration**](docs/config.md) - Customize your experience
- [🔧 **API Reference**](docs/api.md) - Developer documentation

---

## 🤝 Contributing

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

### 🌟 **Star this repo if you love interactive AI storytelling!** 🌟

*Made with ❤️ for the AI RPG community*

</div>
