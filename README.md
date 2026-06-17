# UloLM - Universal Local & Cloud AI Platform

UloLM is a next-generation local and cloud-based AI environment combining the ease-of-use of a standard chatbot interface, the power of multi-agent workspace routing, and the local execution capabilities of an operating system sandbox.

---

## 📖 Architectural Specifications

All requested architectural blueprints, design sheets, roadmaps, and security policies are stored in the `/docs/` folder:

1. **[System Architecture](file:///docs/system_architecture.md)**: Details runtime layers, components, folder structure, technology stack, and component lifecycle diagrams.
2. **[Project Memory System](file:///docs/memory_system.md)**: Outlines workspace index database schemas (SQLite), AST symbol parsers, architectural metadata templates (`project_state.json`), and context prompt injection routines.
3. **[Model Family & Architecture](file:///docs/model_architecture.md)**: Defines parameters, network design features (Grouped-Query Attention, SwiGLU FFN), context lengths, local model hardware targets (Nano, Mini, Base), and speculative decoding settings.
4. **[Agent routing framework](file:///docs/agent_framework.md)**: Explains the internal expert router protocol, specialist profiles (Coding, Research, Math, Writing, GameDev, Design), and message packets.
5. **[CLI, Security, and Cloud Deployments](file:///docs/cli_and_operation.md)**: Maps terminal loop interactions, sandboxed tool call gatekeepers, cross-platform requirements, and cloud scaling/GPU Triton load balancers.
6. **[Roadmap and Risk Mitigation](file:///docs/roadmap_and_risks.md)**: Maps the 5-phase engineering path, performance risks, hallucinations, and compiler self-correction systems.

---

## 🚀 Interactive CLI Prototype

We have built a fully functional CLI prototype demonstrating the terminal experience, the project memory database, agent expert-routing, and safe workspace code-generation capabilities.

## Getting Started

### Installation (Pip)
You can install UloLM directly using pip:
```bash
pip install .
```
After installation, you can launch UloLM from anywhere using the `ulolm` command:
```bash
ulolm
```

### Installation (Standalone Executable)
If you prefer not to use Python, you can compile UloLM into a standalone executable.
1. Run the build script:
```powershell
.\build_exe.ps1
```
2. The executable will be created at `dist/ulolm.exe`. You can move this anywhere and run it natively on Windows.

### Installation (Source)
1. Clone the repository
2. Install the lightweight requirements:
```bash
pip install -r requirements.txt
```
3. Run the CLI:
```bash
python main.py
```
Launch the interactive terminal interface from the project root:

```bash
python src/ulolm/cli.py
```

Upon launch, UloLM will display the active workspace and models:
```text
┌──────────────────────────────────────────┐
│ UloLM Ready                              │
│ Current Model: UloLMBase (Local)         │
│ Active Workspace: /Users/kavs1/UloLM     │
└──────────────────────────────────────────┘
You:
>
```

---

## 🎯 Example Workflows & Demo Prompt Commands

Since the prototype contains a **Mock Mode** by default, you can trigger its core agent capabilities immediately without configuring API keys:

### 1. Create a Game Project
Type: `create a pygame shooter game` or `initialize a 2D platformer game`.
* **Action**: The **Expert Router** routes the request to `GameDevelopment` and `Coding` experts.
* **Security Gatekeeper**: Prompts approval for files.
* **Workspace Executor**: Creates a fully working Pygame sprite game inside the workspace (`src/main.py`), a `requirements.txt`, and a `.ulolm/project_state.json` locking in project rules.

### 2. Verify Project State Memory
Type `/info` inside the CLI loop.
* **Action**: Prints the live database memory status. You will see the newly created files, their hashes, active development state, and classes/methods extracted directly by the AST scanner.

### 3. Check AST Code Parsing
Modify `src/main.py` or write any Python file, e.g., create a class or method. Run any prompt.
* **Action**: UloLM automatically scans the workspace directory, notices the code changes, extracts the class/function names, and updates the local SQLite index. Run `/info` to verify.

---

## 🛠 Advanced Config: Local Ollama & Cloud OpenAI Backends

To connect UloLM to real local models (Ollama) or cloud models (OpenAI), configure the backend within the CLI session:

* **Ollama (Local Inference)**:
  1. Start Ollama on your machine. Ensure you have downloaded the base model (e.g. `ollama pull llama3`).
  2. Inside the UloLM CLI, type: `/config backend ollama`.
  3. UloLM will now query your local Ollama instance for all prompts!

* **OpenAI (Cloud Inference)**:
  1. Set your OpenAI key environment variable: `export OPENAI_API_KEY="your-api-key"` (or set it in your Windows Environment Variables).
  2. Inside the UloLM CLI, type: `/config backend openai`.
  3. UloLM will now query GPT-4o-mini, injecting your local project memory context.
