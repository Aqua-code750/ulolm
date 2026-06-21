import os
import json
from pathlib import Path

class Config:
    def __init__(self):
        self.active_model = "ulollama"
        self.backend = "native"  # Options: native, ollama, openai, gemini, combined
        self.ollama_url = "http://localhost:11434"
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_base_url = "https://api.openai.com/v1"
        self.openai_model = "gpt-4o-mini"
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = "gemini-1.5-flash"
        self.workspace_path = os.getcwd()
        
    def load(self, config_path: Path = None):
        """Loads configuration from a local JSON file if it exists."""
        if config_path is None:
            # Check current workspace first, then home directory
            local_config = Path(os.getcwd()) / ".ulolm" / "config.json"
            global_config = Path.home() / ".ulolm" / "config.toml" # Or json
            
            # Prefer local config over global
            if local_config.exists():
                config_path = local_config
            elif (Path.home() / ".ulolm.config.json").exists():
                config_path = Path.home() / ".ulolm.config.json"

        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_model = data.get("active_model", self.active_model)
                    self.backend = data.get("backend", self.backend)
                    self.ollama_url = data.get("ollama_url", self.ollama_url)
                    self.openai_api_key = data.get("openai_api_key", self.openai_api_key)
                    self.openai_base_url = data.get("openai_base_url", self.openai_base_url)
                    self.openai_model = data.get("openai_model", self.openai_model)
                    self.gemini_api_key = data.get("gemini_api_key", self.gemini_api_key)
                    self.gemini_model = data.get("gemini_model", self.gemini_model)
            except Exception:
                # Silently fallback to defaults on corrupt config
                pass
        
        # Override with environment variables if present
        # Parse local .env file natively if it exists
        env_file = Path(os.getcwd()) / ".env"
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, val = line.split('=', 1)
                            os.environ[key.strip()] = val.strip()
            except Exception:
                pass

        self.backend = os.environ.get("ULOLM_BACKEND", self.backend)
        self.active_model = os.environ.get("ULOLM_MODEL", self.active_model)
        self.ollama_url = os.environ.get("OLLAMA_URL", self.ollama_url)
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", self.openai_api_key)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", self.gemini_api_key)

    def save(self, config_path: Path):
        """Saves current configuration to a file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "active_model": self.active_model,
            "backend": self.backend,
            "ollama_url": self.ollama_url,
            "openai_api_key": self.openai_api_key,
            "openai_base_url": self.openai_base_url,
            "openai_model": self.openai_model,
            "gemini_api_key": self.gemini_api_key,
            "gemini_model": self.gemini_model
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def __repr__(self):
        return (f"<Config model={self.active_model} backend={self.backend} "
                f"workspace={self.workspace_path}>")
