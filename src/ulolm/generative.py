import os
import sys
from pathlib import Path

try:
    from gpt4all import GPT4All
    HAS_GPT4ALL = True
except ImportError:
    HAS_GPT4ALL = False

# All available models from the GPT4All catalog
AVAILABLE_MODELS = {
    # ── Lightweight (2-4 GB RAM) ──
    "llama-3.2-1b":     {"file": "Llama-3.2-1B-Instruct-Q4_0.gguf",       "ram": "2 GB",  "name": "Llama 3.2 1B Instruct"},
    "llama-3.2-3b":     {"file": "Llama-3.2-3B-Instruct-Q4_0.gguf",       "ram": "4 GB",  "name": "Llama 3.2 3B Instruct"},
    "phi-3-mini":       {"file": "Phi-3-mini-4k-instruct.Q4_0.gguf",      "ram": "4 GB",  "name": "Phi-3 Mini Instruct"},
    "deepseek-r1-1.5b": {"file": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_0.gguf","ram": "3 GB", "name": "DeepSeek R1 1.5B"},
    "mini-orca":        {"file": "orca-mini-3b-gguf2-q4_0.gguf",          "ram": "4 GB",  "name": "Mini Orca 3B"},
    "qwen2-1.5b":       {"file": "qwen2-1_5b-instruct-q4_0.gguf",         "ram": "3 GB",  "name": "Qwen2 1.5B Instruct"},
    # ── Medium (8 GB RAM) ──
    "llama-3-8b":       {"file": "Meta-Llama-3-8B-Instruct.Q4_0.gguf",    "ram": "8 GB",  "name": "Llama 3 8B Instruct"},
    "llama-3.1-8b":     {"file": "Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf","ram": "8 GB","name": "Llama 3.1 8B 128k"},
    "deepseek-r1-7b":   {"file": "DeepSeek-R1-Distill-Qwen-7B-Q4_0.gguf", "ram": "8 GB", "name": "DeepSeek R1 7B"},
    "deepseek-r1-8b":   {"file": "DeepSeek-R1-Distill-Llama-8B-Q4_0.gguf","ram": "8 GB",  "name": "DeepSeek R1 8B"},
    "mistral-7b":       {"file": "mistral-7b-instruct-v0.1.Q4_0.gguf",    "ram": "8 GB",  "name": "Mistral 7B Instruct"},
    "mistral-openorca":  {"file": "mistral-7b-openorca.gguf2.Q4_0.gguf",  "ram": "8 GB",  "name": "Mistral OpenOrca"},
    "hermes-2-mistral":  {"file": "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf","ram": "8 GB", "name": "Nous Hermes 2 Mistral"},
    "ghost-7b":          {"file": "ghost-7b-v0.9.1-Q4_0.gguf",            "ram": "8 GB",  "name": "Ghost 7B"},
    "orca-2-7b":         {"file": "orca-2-7b.Q4_0.gguf",                  "ram": "8 GB",  "name": "Orca 2 Medium"},
    "reasoner-v1":       {"file": "qwen2.5-coder-7b-instruct-q4_0.gguf",  "ram": "8 GB",  "name": "Qwen 2.5 Coder 7B"},
    # ── Heavy (16 GB RAM) ──
    "deepseek-r1-14b":  {"file": "DeepSeek-R1-Distill-Qwen-14B-Q4_0.gguf","ram": "16 GB", "name": "DeepSeek R1 14B"},
    "orca-2-13b":       {"file": "orca-2-13b.Q4_0.gguf",                  "ram": "16 GB", "name": "Orca 2 Full"},
    "wizard-13b":       {"file": "wizardlm-13b-v1.2.Q4_0.gguf",           "ram": "16 GB", "name": "Wizard v1.2"},
    "hermes-13b":       {"file": "nous-hermes-llama2-13b.Q4_0.gguf",      "ram": "16 GB", "name": "Hermes 13B"},
    # ── Code-Specific ──
    "starcoder":        {"file": "starcoder-newbpe-q4_0.gguf",            "ram": "4 GB",  "name": "StarCoder"},
    "replit":           {"file": "replit-code-v1_5-3b-newbpe-q4_0.gguf",  "ram": "4 GB",  "name": "Replit Code 3B"},
    "rift-coder":       {"file": "rift-coder-v0-7b-q4_0.gguf",            "ram": "8 GB",  "name": "Rift Coder 7B"},
}

DEFAULT_MODEL_KEY = "llama-3.2-3b"


class GenerativeEngine:
    def __init__(self, workspace_path: str, model_key: str = None):
        self.workspace_path = workspace_path
        self.model_dir = Path(workspace_path) / ".ulolm"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_key = model_key or self._load_selected_model() or DEFAULT_MODEL_KEY
        self.model = None

    def _load_selected_model(self) -> str:
        """Read the user's selected model from .ulolm/native_model.txt"""
        model_file = self.model_dir / "native_model.txt"
        if model_file.exists():
            key = model_file.read_text(encoding="utf-8").strip()
            if key in AVAILABLE_MODELS:
                return key
        return ""

    def _save_selected_model(self, key: str):
        """Persist the user's model choice."""
        model_file = self.model_dir / "native_model.txt"
        model_file.write_text(key, encoding="utf-8")

    @property
    def model_info(self) -> dict:
        return AVAILABLE_MODELS.get(self.model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])

    @property
    def model_filename(self) -> str:
        return self.model_info["file"]

    def set_model(self, key: str) -> tuple:
        """Switch the active native model."""
        if key not in AVAILABLE_MODELS:
            return False, f"Unknown model '{key}'. Run /models to see available options."
        self.model_key = key
        self.model = None  # Force reload on next generate
        self._save_selected_model(key)
        info = AVAILABLE_MODELS[key]
        return True, f"Switched native model to {info['name']} ({info['ram']} RAM required)"

    def _load_model(self, allow_download=False):
        if not HAS_GPT4ALL:
            return False, "gpt4all module is not installed."

        model_path = self.model_dir / self.model_filename
        if not model_path.exists() and not allow_download:
            return False, f"Model {self.model_filename} not found. Run `/train_gen` to download it."

        try:
            self.model = GPT4All(
                model_name=self.model_filename,
                model_path=str(self.model_dir),
                allow_download=allow_download
            )
            return True, "Model loaded successfully."
        except Exception as e:
            return False, f"Failed to load model: {e}"

    def _fetch_download_url(self) -> tuple:
        """Fetch the download URL and filesize for the current model from models3.json."""
        import urllib.request
        import json
        
        filename = self.model_filename
        try:
            req = urllib.request.Request(
                "https://gpt4all.io/models/models3.json",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                for model in data:
                    if model.get("filename") == filename:
                        url = model.get("url")
                        size = int(model.get("filesize", 0)) if model.get("filesize") else None
                        return url, size
        except Exception:
            pass
            
        # Fallback URL if models3.json lookup fails
        fallback_url = f"https://gpt4all.io/models/gguf/{filename}"
        return fallback_url, None

    def download_model_file(self, progress_callback=None) -> tuple:
        """Downloads the current model file with resume support and retries."""
        import urllib.request
        import time
        
        dest_path = self.model_dir / self.model_filename
        if dest_path.exists():
            return True, "Model file already exists."
            
        url, expected_size = self._fetch_download_url()
        temp_path = dest_path.with_suffix(".part")
        
        retries = 5
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        
        for attempt in range(retries):
            try:
                downloaded = 0
                if temp_path.exists():
                    downloaded = temp_path.stat().st_size
                    if expected_size and downloaded >= expected_size:
                        try:
                            temp_path.rename(dest_path)
                            return True, "Model downloaded successfully."
                        except Exception:
                            pass
                    headers["Range"] = f"bytes={downloaded}-"
                
                req = urllib.request.Request(url, headers=headers)
                
                try:
                    response = urllib.request.urlopen(req, timeout=20)
                    status_code = response.getcode()
                except urllib.error.HTTPError as e:
                    if e.code == 416:  # Range not satisfiable (might be fully downloaded)
                        try:
                            temp_path.rename(dest_path)
                            return True, "Model downloaded successfully."
                        except Exception:
                            pass
                        return True, "Model downloaded successfully."
                    raise e
                
                # Check if resuming
                is_resume = (status_code == 206)
                if not is_resume:
                    downloaded = 0
                    write_mode = "wb"
                else:
                    write_mode = "ab"
                    
                total_size = expected_size
                content_len = response.headers.get("Content-Length")
                if content_len:
                    if is_resume:
                        total_size = downloaded + int(content_len)
                    else:
                        total_size = int(content_len)
                
                chunk_size = 1024 * 1024  # 1MB chunks
                
                # Create directory if not exists
                self.model_dir.mkdir(parents=True, exist_ok=True)
                
                with open(temp_path, write_mode) as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            try:
                                progress_callback(downloaded, total_size)
                            except Exception:
                                pass
                            
                # Rename to final file
                if temp_path.exists():
                    temp_path.rename(dest_path)
                return True, "Model downloaded successfully."
                
            except (ConnectionResetError, ConnectionAbortedError, urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt == retries - 1:
                    return False, f"Failed after {retries} attempts. Last error: {e}"
                time.sleep(2 ** attempt)  # Backoff: 1s, 2s, 4s, 8s...
                
        return False, "Failed to download model due to connection issues."

    def train_on_workspace(self, progress_callback=None):
        """Downloads the selected native model and loads it."""
        success, msg = self.download_model_file(progress_callback=progress_callback)
        if not success:
            return False, msg
            
        success, msg = self._load_model(allow_download=False)
        if success:
            self._save_selected_model(self.model_key)
            info = self.model_info
            return True, f"Successfully initialized {info['name']} ({info['ram']} RAM) — model cached locally."
        else:
            return False, msg

    def generate(self, prompt: str, length: int = 500, temperature: float = 0.3, system_context: str = "") -> str:
        """Generates text natively using the GPT4All model with optional system context."""
        if not HAS_GPT4ALL:
            return "GPT4All is not installed! Please ensure the dependencies are installed."

        if self.model is None:
            success, msg = self._load_model(allow_download=False)
            if not success:
                return "Native model not found! Please run `/train_gen` first to download it."

        try:
            if system_context:
                system_prompt = system_context
            else:
                system_prompt = "You are UloLM, a highly capable native AI running entirely locally. Be extremely helpful and concise."

            with self.model.chat_session(system_prompt=system_prompt):
                response = self.model.generate(
                    prompt,
                    max_tokens=length,
                    temp=temperature
                )
            return response.strip()
        except Exception as e:
            return f"Error during native generation: {e}"
