# UloLM Model Family & Architecture Proposal

This document outlines the design specifications, parameters, hardware targets, and neural architecture details of the **UloLM Model Family** (Nano, Mini, Base, Pro, Ultra).

---

## 1. UloLM Model Family Matrix

All models share a common instruction tokenization schema, system-prompt template, and tool-calling protocol, enabling a unified developer ecosystem.

| Model Size | Parameter Count | Target Hardware | Quantization | RAM/VRAM Target | Context Window | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UloLMNano** | 1.8 Billion | Older laptops, mobile platforms, Raspberry Pi 5 | INT4 (GGUF) | < 1.5 GB | 8,000 tokens | Fast autocomplete, simple command explanations, low-power terminals. |
| **UloLMMini** | 3.8 Billion | Modern thin-and-light laptops, tablets | INT4 / INT8 | < 3.5 GB | 16,000 tokens | Everyday chat, general writing, basic scripting, quick search. |
| **UloLMBase** | 8.2 Billion | Developer workstations, gaming laptops | Q4_K_M / Q8_0 | < 6.5 GB (CPU/GPU) | 32,000 tokens | Multi-file code generation, refactoring, unit tests, agent execution. |
| **UloLMPro** | 16.0 Billion / 32.0 Billion | High-end GPU workstations (e.g., RTX 4080/4090, Mac Studio) | Q8_0 / FP16 | < 24 GB | 64,000 tokens | Complex system designs, long-form logic reasoning, multi-agent games. |
| **UloLMUltra** | 72.0 Billion (MoE 8x22B) | Enterprise cluster, cloud multi-node servers | FP16 / BF16 | 80 GB+ VRAM | 128,000 tokens | Scientific research, full-repo synthesis, massive cloud API platform. |

---

## 2. Shared Model Architecture

To guarantee easy cross-model compatibility and simple transfer-learning, UloLM models utilize a **Decoder-Only Transformer** model architecture based on the following advancements:

```text
       +------------------------------------+
       |            Input Tokens            |
       +------------------------------------+
                         |
                         v
       +------------------------------------+
       |       Rotary Embeddings (RoPE)     |
       +------------------------------------+
                         |
                         v
       +------------------------------------+
       |     Grouped-Query Attention (GQA)  | <--- KV Cache Optimization
       +------------------------------------+
                         |
                         v
       +------------------------------------+
       |    SwiGLU Activation Function      |
       +------------------------------------+
                         |
                         v
       +------------------------------------+
       |    RMSNorm (Root Mean Square Norm) |
       +------------------------------------+
                         |
                         v
       +------------------------------------+
       |        Output / Softmax            |
       +------------------------------------+
```

### 2.1 Key Architectural Elements:

* **Grouped-Query Attention (GQA)**: Instead of Multi-Head Attention (MHA), UloLM models employ GQA (e.g., 8 Query heads per Key/Value head). This reduces memory consumption during KV caching, enabling large context windows on low-memory systems (like laptops running `UloLMBase`).
* **Rotary Position Embedding (RoPE)**: Supports sequence length scaling up to 128k tokens without training on long contexts from scratch, using Yarn or dynamic NTK-aware scaling factors.
* **SwiGLU Feed-Forward Network (FFN)**: Replaces traditional GELU/ReLU activations with Swish-Gated Linear Units, demonstrating better convergence and training stability for coding benchmarks.
* **RMSNorm (Root Mean Square Normalization)**: Applied before the attention block (Pre-LN) and after, speeding up training times and ensuring stable inference under extreme parameter quantization.

---

## 3. Tool-Calling & Function Activation Design

For agent workflows, UloLM models are fine-tuned with specific token formats for structured JSON tool-calling:

### Token Protocol:
* `<tool_call>`: Marks the start of a tool request.
* `</tool_call>`: Marks the end of a tool request.
* `<tool_response>`: Feeds the result of tool execution back into the model context.

### Code Sample of Target Fine-Tuning Format:
```text
<|im_start|>user
Write a file named 'main.py' containing a hello world in Python.<|im_end|>
<|im_start|>assistant
<tool_call>{"name": "write_file", "parameters": {"path": "main.py", "content": "print('Hello, World!')"}}</tool_call><|im_end|>
<|im_start|>tool
<tool_response>{"status": "success", "bytes_written": 23}</tool_response><|im_end|>
<|im_start|>assistant
I have successfully created the file 'main.py' for you.<|im_end|>
```

---

## 4. Hardware Quantization Strategies

To run efficiently on local machines, weights are compressed using advanced quantization methods:

1. **GGUF (GPT-Generated Unified Format)**: Highly optimized for local execution using CPU SIMD instructions (AVX-512, AMX) and Apple Silicon Metal Performance Shaders (MPS). Used by default for `UloLMNano`, `UloLMMini`, and `UloLMBase`.
2. **GPTQ / AWQ (Activation-aware Weight Quantization)**: Native 4-bit CUDA kernels. Used when executing UloLM on local machines equipped with dedicated NVIDIA GPUs.
3. **Speculative Decoding**:
   * To speed up inference times on user workstations, UloLM supports *Speculative Decoding*.
   * The system runs the 1.8B **UloLMNano** model as a draft model, generating candidate tokens at high speed (> 120 tokens/sec), which are validated in parallel by the 8.2B **UloLMBase** model on a single GPU forward pass. This increases the effective generation speed of `UloLMBase` by 2x to 3x.
