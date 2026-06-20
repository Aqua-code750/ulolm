import os
import re
import json
import random
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

GRAMMAR_CORPUS = """
Hello! I am UloLM, a purely native PyTorch neural network.
I have analyzed the provided context from your workspace files.
Based on my understanding of your request, here is the generated output.
I am operating completely natively on your local machine.
There are no wrappers, no external APIs, and no downloaded weights.
I am using a custom word-level Long Short-Term Memory neural network.
This ensures that I generate perfectly coherent English sentences with proper grammar.
My vocabulary consists of the words found in this grammar corpus and your workspace files.
I am functioning optimally and my neural weights have been optimized successfully.
How can I assist you with your software development project today?
Let me analyze the local Python and Markdown files to find the answer.
The function returns the expected output based on the provided arguments.
Please ensure that the dependencies are installed correctly in your environment.
I can confirm that the build process completed without any fatal errors.
We should refactor this code block to improve overall performance and readability.
"""

class NativeGenerativeLLM(nn.Module if HAS_TORCH else object):
    """
    A 100% Native, Word-Level Generative Neural Network.
    Zero external pre-trained weights. Zero API wrappers.
    Uses Word-Level tokenization to guarantee zero scrambled letters.
    """
    def __init__(self, vocab_size, hidden_size=256, num_layers=2):
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
        self.model_path = Path(workspace_path) / ".ulolm" / "native_llm_word.pt"
        self.vocab_path = Path(workspace_path) / ".ulolm" / "vocab_word.json"
        self.words = []
        self.word_to_int = {}
        self.int_to_word = {}
        self.vocab_size = 0
        self.model = None
        
        if HAS_TORCH:
            self._load_or_init()

    def _tokenize(self, text: str) -> list:
        # Extract words and punctuation as separate tokens to preserve grammar
        return re.findall(r"[\w']+|[.,!?;]", text)

    def _load_or_init(self):
        if self.vocab_path.exists():
            try:
                with open(self.vocab_path, "r", encoding="utf-8") as f:
                    self.words = json.load(f)
                self.word_to_int = {w: i for i, w in enumerate(self.words)}
                self.int_to_word = {i: w for i, w in enumerate(self.words)}
                self.vocab_size = len(self.words)
                
                if self.vocab_size > 0:
                    self.model = NativeGenerativeLLM(self.vocab_size)
                    if self.model_path.exists():
                        self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
            except Exception:
                pass
        
    def _create_vocab(self, tokens: list):
        # Keep unique tokens sorted
        self.words = sorted(list(set(tokens)))
        # Add an unknown token fallback
        if "<UNK>" not in self.words:
            self.words.insert(0, "<UNK>")
            
        self.word_to_int = {w: i for i, w in enumerate(self.words)}
        self.int_to_word = {i: w for i, w in enumerate(self.words)}
        self.vocab_size = len(self.words)
        
        self.vocab_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vocab_path, "w", encoding="utf-8") as f:
            json.dump(self.words, f)
            
        self.model = NativeGenerativeLLM(self.vocab_size)

    def train_on_workspace(self, epochs: int = 15, max_tokens: int = 20000):
        """Trains the generative model locally using the Grammar Corpus and project files."""
        if not HAS_TORCH:
            return False, "PyTorch is not installed. Cannot train generative AI."
            
        # Start with the foundational grammar corpus!
        text_data = GRAMMAR_CORPUS * 5  # Multiply to heavily bias toward correct grammar
        
        # Read text files from workspace to learn project vocabulary
        for root, dirs, files in os.walk(self.workspace_path):
            if ".git" in root or ".ulolm" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(('.py', '.md', '.txt')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            text_data += f.read()[:5000] + "\n\n" # Take small chunks to avoid diluting grammar
                    except Exception:
                        pass
        
        tokens = self._tokenize(text_data)[:max_tokens]
        
        if not tokens:
            return False, "No data available to train."
            
        self._create_vocab(tokens)
        
        seq_length = 5
        dataX = []
        dataY = []
        for i in range(0, len(tokens) - seq_length, 1):
            seq_in = tokens[i:i + seq_length]
            seq_out = tokens[i + 1:i + seq_length + 1]
            dataX.append([self.word_to_int[w] for w in seq_in])
            dataY.append([self.word_to_int[w] for w in seq_out])
            
        n_patterns = len(dataX)
        if n_patterns == 0:
            return False, "Not enough text data to train."
            
        X = torch.tensor(dataX, dtype=torch.long)
        y = torch.tensor(dataY, dtype=torch.long)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.002)
        
        self.model.train()
        batch_size = 64
        
        # Training loop
        for epoch in range(epochs):
            for i in range(0, n_patterns, batch_size):
                batch_X = X[i:i+batch_size]
                batch_y = y[i:i+batch_size]
                
                optimizer.zero_grad()
                output, _ = self.model(batch_X)
                
                loss = criterion(output.view(-1, self.vocab_size), batch_y.view(-1))
                loss.backward()
                optimizer.step()
                
        torch.save(self.model.state_dict(), self.model_path)
        return True, f"Successfully trained Word-Level model on {len(tokens)} tokens!"

    def generate(self, prompt: str, length: int = 50, temperature: float = 0.2) -> str:
        """Autoregressively generates text word-by-word natively."""
        if not HAS_TORCH or self.model is None or self.vocab_size == 0:
            return (
                "Native Generative Model is uninitialized! "
                "Please run `/train_gen` first to train your AI on this workspace."
            )
            
        self.model.eval()
        
        prompt_tokens = self._tokenize(prompt)
        # Filter to known words, or use a default starter from grammar corpus
        valid_tokens = [w for w in prompt_tokens if w in self.word_to_int]
        if not valid_tokens:
            valid_tokens = ["I", "am", "UloLM"]
            
        input_seq = [self.word_to_int[w] for w in valid_tokens[-5:]]
        hidden = None
        
        generated_tokens = valid_tokens.copy()
        
        with torch.no_grad():
            for _ in range(length):
                x = torch.tensor([input_seq], dtype=torch.long)
                out, hidden = self.model(x, hidden)
                
                # Temperature scaled logits
                logits = out[0, -1, :] / temperature
                probs = torch.softmax(logits, dim=0)
                
                next_word_idx = torch.multinomial(probs, 1).item()
                next_word = self.int_to_word[next_word_idx]
                
                generated_tokens.append(next_word)
                input_seq.append(next_word_idx)
                
                if len(input_seq) > 5:
                    input_seq = input_seq[1:]
                    
                if next_word in [".", "!", "?"] and len(generated_tokens) > length * 0.8:
                    break
                    
        # Reconstruct string with proper spacing
        result = generated_tokens[0]
        for token in generated_tokens[1:]:
            if token in [".", ",", "!", "?", ";"]:
                result += token
            else:
                result += " " + token
                
        return result
