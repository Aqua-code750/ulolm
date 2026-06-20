import os
import random
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class NativeGenerativeLLM(nn.Module if HAS_TORCH else object):
    """
    A 100% Native, from-scratch Generative Neural Network.
    Uses a Character-Level LSTM to generate text autoregressively.
    Zero external pre-trained weights. Zero API wrappers.
    """
    def __init__(self, vocab_size, hidden_size=128, num_layers=2):
        if HAS_TORCH:
            super().__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.embedding = nn.Embedding(vocab_size, hidden_size)
            self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, vocab_size)
        
    def forward(self, x, hidden=None):
        out = self.embedding(x)
        out, hidden = self.lstm(out, hidden)
        out = self.fc(out)
        return out, hidden

class GenerativeEngine:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.model_path = Path(workspace_path) / ".ulolm" / "native_llm.pt"
        self.vocab_path = Path(workspace_path) / ".ulolm" / "vocab.txt"
        self.chars = []
        self.char_to_int = {}
        self.int_to_char = {}
        self.vocab_size = 0
        self.model = None
        
        if HAS_TORCH:
            self._load_or_init()

    def _load_or_init(self):
        if self.vocab_path.exists():
            with open(self.vocab_path, "r", encoding="utf-8") as f:
                self.chars = list(f.read())
            self.char_to_int = {c: i for i, c in enumerate(self.chars)}
            self.int_to_char = {i: c for i, c in enumerate(self.chars)}
            self.vocab_size = len(self.chars)
            
            if self.vocab_size > 0:
                self.model = NativeGenerativeLLM(self.vocab_size)
                if self.model_path.exists():
                    self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
        
    def _create_vocab(self, text: str):
        self.chars = sorted(list(set(text)))
        self.char_to_int = {c: i for i, c in enumerate(self.chars)}
        self.int_to_char = {i: c for i, c in enumerate(self.chars)}
        self.vocab_size = len(self.chars)
        
        self.vocab_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vocab_path, "w", encoding="utf-8") as f:
            f.write("".join(self.chars))
            
        self.model = NativeGenerativeLLM(self.vocab_size)

    def train_on_workspace(self, epochs: int = 3, max_chars: int = 100000):
        """Trains the generative model locally using project files."""
        if not HAS_TORCH:
            return False, "PyTorch is not installed. Cannot train generative AI."
            
        text_data = ""
        # Read text files from workspace to learn
        for root, dirs, files in os.walk(self.workspace_path):
            if ".git" in root or ".ulolm" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(('.py', '.md', '.txt', '.js', '.html', '.css')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            text_data += f.read() + "\n\n"
                    except Exception:
                        pass
        
        if not text_data:
            text_data = "Hello world! This is a default training string because no files were found."
            
        # Limit size for speed
        text_data = text_data[:max_chars]
        
        # Build vocabulary
        self._create_vocab(text_data)
        
        # Prepare training data
        seq_length = 50
        dataX = []
        dataY = []
        for i in range(0, len(text_data) - seq_length, 5):
            seq_in = text_data[i:i + seq_length]
            seq_out = text_data[i + 1:i + seq_length + 1]
            dataX.append([self.char_to_int[char] for char in seq_in])
            dataY.append([self.char_to_int[char] for char in seq_out])
            
        n_patterns = len(dataX)
        if n_patterns == 0:
            return False, "Not enough text data to train."
            
        X = torch.tensor(dataX, dtype=torch.long)
        y = torch.tensor(dataY, dtype=torch.long)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.005)
        
        self.model.train()
        batch_size = 128
        
        # Simple training loop
        for epoch in range(epochs):
            for i in range(0, n_patterns, batch_size):
                batch_X = X[i:i+batch_size]
                batch_y = y[i:i+batch_size]
                
                optimizer.zero_grad()
                output, _ = self.model(batch_X)
                
                # Reshape for CrossEntropyLoss
                loss = criterion(output.view(-1, self.vocab_size), batch_y.view(-1))
                loss.backward()
                optimizer.step()
                
        # Save model
        torch.save(self.model.state_dict(), self.model_path)
        return True, f"Successfully trained native generative model on {len(text_data)} characters."

    def generate(self, prompt: str, length: int = 200, temperature: float = 0.8) -> str:
        """Autoregressively generates text character-by-character natively."""
        if not HAS_TORCH or self.model is None or self.vocab_size == 0:
            return (
                "Native Generative Model is uninitialized! "
                "Please run `/train_gen` first to train your AI on this workspace."
            )
            
        self.model.eval()
        
        # Filter prompt to known chars
        prompt = "".join([c for c in prompt if c in self.char_to_int])
        if not prompt:
            prompt = random.choice(self.chars)
            
        input_seq = [self.char_to_int[c] for c in prompt]
        hidden = None
        generated_text = prompt
        
        with torch.no_grad():
            for _ in range(length):
                x = torch.tensor([input_seq], dtype=torch.long)
                out, hidden = self.model(x, hidden)
                
                # Get logits for the last character
                logits = out[0, -1, :] / temperature
                probs = torch.softmax(logits, dim=0)
                
                # Sample the next character
                next_char_idx = torch.multinomial(probs, 1).item()
                next_char = self.int_to_char[next_char_idx]
                
                generated_text += next_char
                input_seq.append(next_char_idx)
                
                # Keep sliding window
                if len(input_seq) > 50:
                    input_seq = input_seq[1:]
                    
        return generated_text
