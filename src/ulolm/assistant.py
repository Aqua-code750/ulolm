from pathlib import Path
from typing import Optional
from ulolm.config import Config
from ulolm.models import ModelEngine, ModelResponse
from ulolm.memory import ProjectMemory
from ulolm.router import ExpertRouter

class UloLMAssistant:
    """
    A full AI Model Assistant ready to be integrated into any Python project.
    Handles workspace memory, context routing, and AI backend interactions.
    """
    
    def __init__(self, workspace_path: str = ".", backend: str = "native", model: str = "UloLMBase"):
        self.workspace = Path(workspace_path).resolve()
        
        # Configure the assistant
        self.config = Config()
        self.config.workspace_path = str(self.workspace)
        self.config.backend = backend
        self.config.active_model = model
        
        # Initialize memory and routing
        self.memory = ProjectMemory(str(self.workspace))
        self.engine = ModelEngine(self.config)
        self.router = ExpertRouter()
        
        # Sync workspace memory on startup
        self.memory.scan_and_sync()

    def chat(self, user_input: str) -> str:
        """
        Send a message to the AI assistant and get a response.
        Automatically handles context injection and expert routing.
        """
        # 1. Route to the correct expert personality
        expert = self.router.route(user_input)
        
        # 2. Get the latest project context from memory
        project_context = self.memory.get_project_context()
        system_context = f"{expert.system_prompt}\n\n{project_context}"
        
        # 3. Query the engine
        response: ModelResponse = self.engine.query(user_input, system_context)
        
        # 4. Return the text response
        return response.text

    def change_backend(self, backend: str, model: str):
        """Switch the AI backend (e.g., from 'mock' to 'ollama' or 'openai')."""
        self.config.backend = backend
        self.config.active_model = model
        self.engine = ModelEngine(self.config)
