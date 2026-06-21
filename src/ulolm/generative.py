import os
import sys
import json
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

AVAILABLE_MODELS = {
    "ulollama": {"file": "ulollama.pt", "ram": "512 MB", "name": "UloLlama (Custom Tiny GPT)"}
}

DEFAULT_MODEL_KEY = "ulollama"

# ─────────────────────────────────────────────────────────────
# Tiny GPT Model Architecture (Decoder-Only Transformer)
# ─────────────────────────────────────────────────────────────

class Head(nn.Module):
    """ One head of self-attention """
    def __init__(self, head_size, n_embd, block_size, dropout=0.1):
        super().__init__()
        self.key = nn.Linear(n_embd, head_size, bias=False)
        self.query = nn.Linear(n_embd, head_size, bias=False)
        self.value = nn.Linear(n_embd, head_size, bias=False)
        self.register_buffer('tril', torch.tril(torch.ones(block_size, block_size)))
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        B, T, C = x.shape
        k = self.key(x)   # (B, T, head_size)
        q = self.query(x) # (B, T, head_size)
        # Compute attention scores
        wei = q @ k.transpose(-2, -1) * (C**-0.5) # (B, T, head_size) @ (B, head_size, T) -> (B, T, T)
        wei = wei.masked_fill(self.tril[:T, :T] == 0, float('-inf')) # (B, T, T)
        wei = F.softmax(wei, dim=-1) # (B, T, T)
        wei = self.dropout(wei)
        # Perform weighted aggregation of values
        v = self.value(x) # (B, T, head_size)
        out = wei @ v # (B, T, T) @ (B, T, head_size) -> (B, T, head_size)
        return out

class MultiHeadAttention(nn.Module):
    """ Multiple heads of self-attention in parallel """
    def __init__(self, num_heads, head_size, n_embd, block_size, dropout=0.1):
        super().__init__()
        self.heads = nn.ModuleList([Head(head_size, n_embd, block_size, dropout) for _ in range(num_heads)])
        self.proj = nn.Linear(n_embd, n_embd)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        out = torch.cat([h(x) for h in self.heads], dim=-1)
        out = self.dropout(self.proj(out))
        return out

class FeedForward(nn.Module):
    """ Simple linear layer followed by ReLU non-linearity """
    def __init__(self, n_embd, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),
            nn.ReLU(),
            nn.Linear(4 * n_embd, n_embd),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.net(x)

class Block(nn.Module):
    """ Transformer block: communication followed by computation """
    def __init__(self, n_embd, n_head, block_size, dropout=0.1):
        super().__init__()
        head_size = n_embd // n_head
        self.sa = MultiHeadAttention(n_head, head_size, n_embd, block_size, dropout)
        self.ffwd = FeedForward(n_embd, dropout)
        self.ln1 = nn.LayerNorm(n_embd)
        self.ln2 = nn.LayerNorm(n_embd)

    def forward(self, x):
        x = x + self.sa(self.ln1(x))
        x = x + self.ffwd(self.ln2(x))
        return x

class TinyGPT(nn.Module):
    def __init__(self, vocab_size, n_embd=128, n_head=4, n_layer=3, block_size=64, dropout=0.1):
        super().__init__()
        self.block_size = block_size
        self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
        self.position_embedding_table = nn.Embedding(block_size, n_embd)
        self.blocks = nn.Sequential(*[Block(n_embd, n_head, block_size, dropout) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        tok_emb = self.token_embedding_table(idx) # (B, T, n_embd)
        pos_emb = self.position_embedding_table(torch.arange(T, device=idx.device)) # (T, n_embd)
        x = tok_emb + pos_emb # (B, T, n_embd)
        x = self.blocks(x) # (B, T, n_embd)
        x = self.ln_f(x) # (B, T, n_embd)
        logits = self.lm_head(x) # (B, T, vocab_size)

        if targets is None:
            loss = None
        else:
            B, T, C = logits.shape
            logits = logits.view(B*T, C)
            targets = targets.view(B*T)
            loss = F.cross_entropy(logits, targets)

        return logits, loss

    def generate(self, idx, max_new_tokens, temperature=0.7):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] # (B, C)
            if temperature > 0:
                logits = logits / temperature
                probs = F.softmax(logits, dim=-1)
                idx_next = torch.multinomial(probs, num_samples=1)
            else:
                idx_next = torch.argmax(logits, dim=-1, keepdim=True)
            idx = torch.cat((idx, idx_next), dim=1)
        return idx


# ─────────────────────────────────────────────────────────────
# Generative Engine Controller
# ─────────────────────────────────────────────────────────────

class GenerativeEngine:
    def __init__(self, workspace_path: str, model_key: str = None):
        self.workspace_path = workspace_path
        self.model_dir = Path(workspace_path) / ".ulolm"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_key = model_key or self._load_selected_model() or DEFAULT_MODEL_KEY
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = None

    def _load_selected_model(self) -> str:
        model_file = self.model_dir / "native_model.txt"
        if model_file.exists():
            key = model_file.read_text(encoding="utf-8").strip()
            if key in AVAILABLE_MODELS:
                return key
        return ""

    def _save_selected_model(self, key: str):
        model_file = self.model_dir / "native_model.txt"
        model_file.write_text(key, encoding="utf-8")

    @property
    def model_info(self) -> dict:
        return AVAILABLE_MODELS.get(self.model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])

    @property
    def model_filename(self) -> str:
        return self.model_info["file"]

    def set_model(self, key: str) -> tuple:
        if key not in AVAILABLE_MODELS:
            return False, f"Unknown model '{key}'. Run /models to see available options."
        self.model_key = key
        self.model = None
        self._save_selected_model(key)
        info = AVAILABLE_MODELS[key]
        return True, f"Switched native model to {info['name']}"

    def train_on_workspace(self, progress_callback=None):
        """Trains the custom Tiny GPT from scratch on data.md and files in the workspace."""
        # Find training corpus
        corpus_path = Path(self.workspace_path) / "data.md"
        text = ""
        if corpus_path.exists():
            text = corpus_path.read_text(encoding="utf-8")
        else:
            # Fallback scan of workspace files to gather training data
            for file in Path(self.workspace_path).rglob("*.py"):
                if ".venv" not in str(file) and ".ulolm" not in str(file):
                    try:
                        text += file.read_text(encoding="utf-8") + "\n"
                    except Exception:
                        pass
        
        if not text.strip():
            return False, "No training data found in data.md or workspace!"

        # Character-level tokenization
        chars = sorted(list(set(text)))
        vocab_size = len(chars)
        
        # Save vocabulary mapping
        vocab_data = {"chars": chars}
        vocab_file = self.model_dir / "vocab.json"
        vocab_file.write_text(json.dumps(vocab_data), encoding="utf-8")

        stoi = {ch: i for i, ch in enumerate(chars)}
        data = torch.tensor([stoi[c] for c in text], dtype=torch.long)

        # Split into training and validation sets
        n = int(0.9 * len(data))
        train_data = data[:n]
        val_data = data[n:]

        # Hyperparameters
        batch_size = 32
        block_size = 64
        max_iters = 1000
        eval_interval = 100
        device = self.device

        # Get batch helper
        def get_batch(split):
            d = train_data if split == 'train' else val_data
            if len(d) <= block_size:
                # Pad if data is too small
                ix = torch.zeros((batch_size,), dtype=torch.long)
            else:
                ix = torch.randint(len(d) - block_size, (batch_size,))
            x = torch.stack([d[i:i+block_size] if len(d) > block_size else torch.zeros(block_size, dtype=torch.long) for i in ix])
            y = torch.stack([d[i+1:i+block_size+1] if len(d) > block_size else torch.zeros(block_size, dtype=torch.long) for i in ix])
            x, y = x.to(device), y.to(device)
            return x, y

        @torch.no_grad()
        def estimate_loss(model):
            out = {}
            model.eval()
            for split in ['train', 'val']:
                losses = torch.zeros(10)
                for k in range(10):
                    X, Y = get_batch(split)
                    _, loss = model(X, Y)
                    losses[k] = loss.item()
                out[split] = losses.mean().item()
            model.train()
            return out

        model = TinyGPT(vocab_size=vocab_size, block_size=block_size).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

        print("Beginning Tiny GPT training...")
        for iter in range(max_iters):
            if iter % eval_interval == 0 or iter == max_iters - 1:
                losses = estimate_loss(model)
                if progress_callback:
                    try:
                        progress_callback(iter, max_iters, losses['train'], losses['val'])
                    except Exception:
                        pass

            xb, yb = get_batch('train')
            logits, loss = model(xb, yb)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

        # Save model weights
        model_path = self.model_dir / self.model_filename
        torch.save(model.state_dict(), model_path)
        self.model = model
        
        return True, f"Successfully trained UloLlama custom GPT model over {max_iters} steps!"

    def generate(self, prompt: str, length: int = 200, temperature: float = 0.7, system_context: str = "") -> str:
        """Generates text using the trained custom Tiny GPT model."""
        vocab_file = self.model_dir / "vocab.json"
        model_path = self.model_dir / self.model_filename

        if not vocab_file.exists() or not model_path.exists():
            return "UloLlama model weights or vocab not found! Please run `/train_gen` first to train the model."

        try:
            # Load vocab
            vocab_data = json.loads(vocab_file.read_text(encoding="utf-8"))
            chars = vocab_data["chars"]
            vocab_size = len(chars)
            stoi = {ch: i for i, ch in enumerate(chars)}
            itos = {i: ch for i, ch in enumerate(chars)}
            
            # Load model
            if self.model is None:
                self.model = TinyGPT(vocab_size=vocab_size).to(self.device)
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()

            # Encode prompt
            encoded_prompt = []
            for c in prompt:
                if c in stoi:
                    encoded_prompt.append(stoi[c])
            if not encoded_prompt:
                encoded_prompt = [0]
            
            context_tensor = torch.tensor([encoded_prompt], dtype=torch.long, device=self.device)
            
            # Generate
            with torch.no_grad():
                generated_tokens = self.model.generate(context_tensor, max_new_tokens=length, temperature=temperature)
                
            # Decode response
            generated_list = generated_tokens[0].tolist()
            # Return only the newly generated text part
            new_tokens = generated_list[len(encoded_prompt):]
            response = "".join(itos[t] for t in new_tokens)
            return response.strip()
        except Exception as e:
            return f"Error during custom GPT generation: {e}"
