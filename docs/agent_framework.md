# UloLM Agent Framework & Expert Routing Specification

This document details the **UloLM Agent Framework**, outlining the internal expert routing protocols, specialist agent configurations, and communication flow.

---

## 1. Internal Expert-Routing Design

Rather than using one large model with a generic system prompt, UloLM routes tasks to specialized **Expert Agent Profiles**. This mimics a team of developers, researchers, and designers collaborating on a codebase.

The user interacts with a single chat interface, while UloLM acts as a **Coordinator (Router)** that identifies the task type and delegates it.

```text
               +-----------------------------+
               |  User Prompt: "Make a game" |
               +-----------------------------+
                              |
                              v
               +-----------------------------+
               |      Coordinator Router     |
               +-----------------------------+
                              |
                              +-----------------------+
                              | (Determines Expert)   |
                              v                       v
               +-----------------------------+ +--------------+
               |    GameDev Expert Profile   | | Design Exp   | ...
               +-----------------------------+ +--------------+
                              |                       |
                              +-----------+-----------+
                                          | (Actions / Code)
                                          v
                              +-----------------------------+
                              |      Workspace Executor     |
                              +-----------------------------+
```

---

## 2. Expert Profiles & Systems Prompts

Each expert agent has a tailored system prompt and a specific set of active tool permissions.

### 2.1 The Coordinator (Router)
* **Goal**: Analyze the user prompt, read project state metadata, and select the optimal target expert.
* **Selection Logic**: Runs a rapid token classification (using `UloLMNano` or local heuristics) to map user input to one of the target experts.
* **Routing Output**:
  ```json
  {
    "expert": "GameDevelopment",
    "rationale": "User is asking for game assets and game loop implementation in Pygame.",
    "subtasks": [
      {"agent": "Coding", "task": "Write the Sprite classes for player/aliens"},
      {"agent": "Design", "task": "Define the color scheme and screen UI coordinates"}
    ]
  }
  ```

### 2.2 The Coding Expert
* **System Persona**: High-performance, senior compiler and systems engineer.
* **Active Tools**: File read/write, terminal execution, compiler/linter hook, git.
* **Scope**: Code refactoring, syntax compliance, writing unit tests, structural changes, and optimization across the 11 supported languages.

### 2.3 The Research Expert
* **System Persona**: Meticulous documentation analyst and information retriever.
* **Active Tools**: Grep search, semantic vector search, file reader, web search.
* **Scope**: Parsing dependencies, reading standard library documents, indexing local files, resolving bugs by comparing local structures to public API documentation.

### 2.4 The Math & Logic Expert
* **System Persona**: Algorithm researcher and logical reasoning expert.
* **Active Tools**: Python sandbox (for executing calculations), logic solver.
* **Scope**: Complex coordinate calculations (e.g., Godot vector math), physics equations, data structures, profiling performance bottlenecks.

### 2.5 The Game Development Expert
* **System Persona**: Veteran game designer and technical director.
* **Active Tools**: File layout writer, asset generator adapter.
* **Scope**: Structuring game loops, coordinate spaces, entity management, state machines, sound triggers, and integrations for Godot (GDScript/C#), Unity (C#), Unreal (C++), Pygame, and Web-GL/Canvas games.

### 2.6 The Design Expert
* **System Persona**: Professional UI/UX designer and web stylesheet engineer.
* **Active Tools**: CSS generator, HTML mockup tool, image generation executor.
* **Scope**: Visual styling, responsive web structures, CSS animations, asset generation prompting, layout structuring.

---

## 3. Communication Protocol (Internal Message Bus)

When multiple experts need to coordinate (e.g., Code Gen Expert needs Design Expert's color definitions), they communicate via a structured JSON-based message bus.

### Message Payload Example:
```json
{
  "message_id": "msg-8829104",
  "parent_id": null,
  "timestamp": "2026-06-17T19:28:00Z",
  "sender": "GameDevelopment",
  "recipient": "Design",
  "status": "pending",
  "content": {
    "request": "Define a color palette and UI layout specifications for a retro retro-space-shooter game. The target screen resolution is 800x600.",
    "response_format": {
      "bg_color": "hex",
      "player_color": "hex",
      "hud_fonts": "string"
    }
  }
}
```

### Synthesis Phase:
After the experts respond, the **Coordinator** aggregates the file writes, test commands, and explanations into a unified response for the user, rendering a smooth progress bar showing:
1. `[Expert Router] Routed to Game Development & Coding experts.`
2. `[Design Expert] Formulating color palette... Done.`
3. `[Coding Expert] Generating sprite classes... Done.`
4. `[Compiler Verification] Running syntax check... All checks passed.`
5. `[Output] Project files generated successfully.`
