# UloLM Project Memory System Specification

This document details the architecture and mechanisms used by the **UloLM Project Memory System** to maintain deep, long-term awareness of project states, source files, and development history across sessions.

---

## 1. The Long-Term Memory Challenge

A common failure mode of typical AI chatbots is the loss of project context over time. If a user asks to "continue the game" after several weeks, a generic assistant has no record of the project structure, language, libraries, or architectural decisions.

UloLM solves this by introducing a localized, persistent project memory system stored inside the workspace itself (`.ulolm/`).

```text
Project Workspace (e.g. /my-game/)
  │
  ├── src/                       # Main source code
  │    ├── player.py
  │    └── engine.py
  │
  └── .ulolm/                    # UloLM Local Memory Hub
       ├── project_state.json    # High-level architecture & configuration
       ├── index.db              # Relational DB (files, hashes, AST metadata)
       └── vectors/              # Vector database for semantic code search
```

---

## 2. Memory System Components

### 2.1 The Architectural State (`project_state.json`)

This file is the "brain" of the project workspace. It holds a structured summary of the project. The model reads and updates this file as the codebase grows.

```json
{
  "project_name": "space-invaders-2d",
  "version": "0.2.1",
  "tech_stack": {
    "language": "Python",
    "version": "3.11",
    "engine": "Pygame",
    "libraries": ["pygame-ce==2.5.0", "numpy"]
  },
  "architecture": {
    "pattern": "Component-Entity-System (CES) / MVC Hybrid",
    "entrypoint": "src/main.py",
    "key_components": [
      {
        "name": "GameLoop",
        "file": "src/engine.py",
        "description": "Orchestrates delta-time, event dispatching, and state transitions."
      },
      {
        "name": "PlayerSprite",
        "file": "src/player.py",
        "description": "Represents the player ship, controls, and weapon firing mechanics."
      }
    ]
  },
  "rules_and_conventions": [
    "All game entities must inherit from pygame.sprite.Sprite",
    "Do not import pygame modules directly, use pygame.locals where appropriate",
    "Screen dimensions are locked to 800x600 pixels"
  ],
  "roadmap": {
    "completed": [
      "Initialize pygame window",
      "Implement player movements and keyboard input"
    ],
    "in_progress": [
      "Create alien spawning waves and movement algorithms"
    ],
    "todo": [
      "Add sound effects and music",
      "Create scoring system and high score saving"
    ]
  }
}
```

### 2.2 Relational File & AST Database (`index.db`)

UloLM maintains a SQLite database to track every file in the project. During startup or file modification events, UloLM parses the files to extract Abstract Syntax Tree (AST) summaries.

#### SQLite Schema:

```sql
-- Track all workspace files and their modification state
CREATE TABLE files (
    filepath TEXT PRIMARY KEY,
    last_modified DATETIME,
    sha256 TEXT,
    content_summary TEXT,   -- High level structural description
    tokens INTEGER          -- Estimated token count
);

-- Store classes, methods, and functions for quick symbol routing
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT,
    symbol_name TEXT,
    symbol_type TEXT,       -- 'class', 'function', 'struct', 'interface'
    start_line INTEGER,
    end_line INTEGER,
    docstring TEXT,
    FOREIGN KEY(filepath) REFERENCES files(filepath) ON DELETE CASCADE
);

-- Track imports/exports to map architectural dependencies
CREATE TABLE dependencies (
    source_file TEXT,
    target_symbol TEXT,
    dependency_type TEXT,   -- 'import', 'inherits', 'instantiates'
    FOREIGN KEY(source_file) REFERENCES files(filepath) ON DELETE CASCADE
);
```

### 2.3 Semantic Vector Database (`vectors/`)

For large codebases, UloLM chunks source files into semantic blocks (e.g., function-by-function or class-by-class) and embeds them using a lightweight local embedding model (like `nomic-embed-text` or `bge-small`).
* When the user asks: *"Where is the player's collision handling logic?"*
* UloLM embeds the query, searches the local vector store, and fetches the matching code blocks.
* This allows UloLM to answer precise coding questions without feeding the entire codebase into the model's context window.

---

## 3. The Synchronization & Context Construction Flow

When a user issues a prompt, UloLM goes through a strict synchronization and retrieval cycle:

```text
[User issues command: "Add a shield item to the game"]
                 │
                 ▼
1. Scan Filesystem: Check file modification times and SHA256 hashes against index.db.
                 │
                 ▼
2. If changes found: Re-parse modified files, update SQLite index.db, update Vector DB.
                 │
                 ▼
3. Load Context:
   - Read high-level 'project_state.json' (Architecture, Stack, Conventions).
   - Search SQLite for relevant entrypoints (e.g., symbols matching "item" or "shield").
   - Search Vector DB for semantic matches to the prompt query.
                 │
                 ▼
4. Formulate Prompt: Inject retrieved context into System Prompt.
                 │
                 ▼
5. Feed Model: Execute inference (Local/Cloud).
```

### 3.2 Dynamic Context Prompt Structure

The system prompt constructed for the LLM includes:

```text
# SYSTEM PROMPT
You are UloLM's Coding & GameDev Expert. You have access to the active workspace memory.

# CURRENT PROJECT STATE
{Contents of project_state.json}

# RELEVANT SYMBOLS & FILE TREE
- src/items.py (Classes: ShieldItem, Item)
- src/player.py (Methods: take_damage, activate_shield)

# RELEVANT CODE CHUNKS (Retrieved via Vector DB)
[Code snippet showing src/player.py take_damage() method...]

# USER QUESTION
Add a shield item to the game. Ensure it triggers a sound effect.
```
This ensures the model responds with precise edits that fit perfectly into the existing codebase, respecting the files, coding style, and architecture.
