import os
import sys
from pathlib import Path

try:
    from gpt4all import GPT4All
    HAS_GPT4ALL = True
except ImportError:
    HAS_GPT4ALL = False

class GenerativeEngine:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        # We store models locally in the workspace .ulolm directory so it's portable
        self.model_dir = Path(workspace_path) / ".ulolm"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = "Phi-3-mini-4k-instruct-q4.gguf"
        self.model_path = self.model_dir / self.model_name
        self.model = None

    def _load_model(self, allow_download=False):
        if not HAS_GPT4ALL:
            return False, "gpt4all module is not installed."
        
        # Check if model exists
        if not self.model_path.exists() and not allow_download:
            return False, f"Model file {self.model_name} not found in {self.model_dir}. Please run `/train_gen` first to download the weights."

        try:
            # Load or download the model
            self.model = GPT4All(
                model_name=self.model_name,
                model_path=str(self.model_dir),
                allow_download=allow_download
            )
            return True, "Model loaded successfully."
        except Exception as e:
            return False, f"Failed to load GPT4All model: {e}"

    def train_on_workspace(self, epochs: int = 0, max_tokens: int = 0):
        """
        Since we upgraded to a pre-trained GPT4All model (Phi-3),
        'training' now downloads and caches the state-of-the-art model natively.
        """
        success, msg = self._load_model(allow_download=True)
        if success:
            return True, f"Successfully initialized and verified local native model: {self.model_name}"
        else:
            return False, msg

    def generate(self, prompt: str, length: int = 500, temperature: float = 0.3, system_context: str = "") -> str:
        """Generates text natively using the GPT4All model with optional system context."""
        if not HAS_GPT4ALL:
            return (
                "GPT4All is not installed! "
                "Please ensure the dependencies are installed."
            )
            
        if self.model is None:
            success, msg = self._load_model(allow_download=False)
            if not success:
                return (
                    "Native Generative Model weights not found! "
                    "Please run `/train_gen` first to download and initialize the AI."
                )

        # Generate response using the local model
        try:
            # Build system prompt — use expert context if provided, otherwise default
            if system_context:
                system_prompt = system_context
            else:
                system_prompt = "You are UloLM, a highly capable native AI running entirely locally. Be extremely helpful and concise."
            
            # Use the chat session to keep the formatting appropriate for the model
            with self.model.chat_session(system_prompt=system_prompt):
                response = self.model.generate(
                    prompt,
                    max_tokens=length,
                    temp=temperature
                )
            return response.strip()
        except Exception as e:
            return f"Error during native generation: {e}"

