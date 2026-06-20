# UloLM - Universal Local & Cloud AI Platform 🚀

UloLM is a next-generation local and cloud-based AI environment combining the ease-of-use of a standard chatbot interface, the power of multi-agent workspace routing, and the local execution capabilities of an operating system sandbox. 

Recently updated to feature a completely custom, lightweight **PyTorch Neural Engine**, UloLM is designed to be blazingly fast and run natively entirely on your local hardware.

---

## ⚡ Installation (The Fast Way)

UloLM is officially distributed via **Scoop**, meaning you can install the complete PyTorch-powered executable in a single command on any Windows machine:

```powershell
scoop install https://raw.githubusercontent.com/Aqua-code750/Extras/add-ulolm/bucket/ulolm.json
```

Once installed, simply type `ulolm` in your terminal from absolutely anywhere to launch the AI workspace.

## 📦 Installation (Python / Source)

If you prefer building from source or running it as a Python module:

1. Clone the repository
2. Install the lightweight requirements:
```bash
pip install -r requirements.txt
```
3. Run the CLI natively:
```bash
python main.py
```

## 🧠 PyTorch Heuristic Engine

Our expert router utilizes a highly optimized `EmbeddingBag` MLP built entirely on CPU-optimized PyTorch. It dynamically routes your requests to the correct expert system (Game Dev, Mathematics, Python Coding, etc.) in milliseconds, completely offline.

---

## 🏗️ Architectural Specifications

All requested architectural blueprints, design sheets, roadmaps, and security policies are stored in the `/docs/` folder:

1. **[System Architecture](docs/system_architecture.md)**: Details runtime layers, components, folder structure, technology stack, and component lifecycle diagrams.
2. **[Project Memory System](docs/memory_system.md)**: Outlines workspace index database schemas (SQLite), AST symbol parsers, architectural metadata templates (`project_state.json`), and context prompt injection routines.
3. **[Model Family & Architecture](docs/model_architecture.md)**: Defines parameters, network design features (Grouped-Query Attention, SwiGLU FFN), context lengths, local model hardware targets (Nano, Mini, Base), and speculative decoding settings.

## 🎮 Example Workflows

Since the prototype contains a **Mock Mode** by default, you can trigger its core agent capabilities immediately without configuring API keys:

### 1. Create a Game Project
Type: `create a pygame shooter game` or `initialize a 2D platformer game`.
* **Action**: The **Expert Router** routes the request to `GameDevelopment` and `Coding` experts.
* **Security Gatekeeper**: Prompts approval for files.
* **Workspace Executor**: Creates a fully working Pygame sprite game inside the workspace (`src/main.py`), a `requirements.txt`, and a `.ulolm/project_state.json` locking in project rules.

---

> **Support Open Source!**
> If you like lightweight local AI tools, consider leaving a ⭐ on the repository!
