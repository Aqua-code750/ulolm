# UloLM Training Corpus

> This file serves as UloLM's local knowledge base. The BM25 retrieval engine indexes this document and injects relevant chunks into the model's context window at inference time.

---

## System Behavior

### Q: Who are you?
A: I am UloLM, a fully native AI assistant running entirely on your local machine. I use a quantized Phi-3 transformer model loaded directly into memory via GPT4All. No data leaves your computer, and I require no internet connection after initial setup.

### Q: What can you do?
A: I can write code, debug errors, explain concepts, refactor projects, generate documentation, answer general knowledge questions, and execute file operations in your workspace. I route each query through a specialized expert system to provide domain-specific responses.

### Q: How do you work?
A: When you type a query, the Expert Router classifies your intent and selects a domain expert (Coding, Math, Design, etc.). The Workspace Memory system retrieves relevant context from your indexed project files using BM25 scoring. Both the expert's system prompt and the retrieved context are injected into my prompt before I generate a response.

---

## Python Programming

### Q: What is the difference between a list and a tuple?
A: A list is mutable — you can add, remove, and modify elements after creation. A tuple is immutable — once created, its elements cannot be changed. Tuples are slightly faster and use less memory, making them ideal for fixed collections. Use lists when you need to modify the collection, and tuples when the data should remain constant.

### Q: How do decorators work in Python?
A: A decorator is a function that takes another function as an argument and extends its behavior without modifying the original function's source code. Decorators use the `@` syntax:
```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b
```

### Q: What are context managers?
A: Context managers handle resource acquisition and release using the `with` statement. They implement `__enter__` and `__exit__` methods. The most common use is file handling:
```python
with open("data.txt", "r") as f:
    content = f.read()
# File is automatically closed here, even if an exception occurred
```
You can create custom context managers using the `contextlib.contextmanager` decorator or by defining a class with `__enter__` and `__exit__`.

### Q: Explain async/await in Python.
A: Python's `asyncio` module enables concurrent execution using coroutines. `async def` defines a coroutine function, and `await` suspends execution until the awaited coroutine completes. This is ideal for I/O-bound tasks like network requests or file operations:
```python
import asyncio

async def fetch_data(url):
    # Simulate network delay
    await asyncio.sleep(1)
    return {"status": "ok"}

async def main():
    result = await fetch_data("https://example.com")
    print(result)

asyncio.run(main())
```

### Q: What are type hints and why should I use them?
A: Type hints annotate function signatures and variables with expected types. They don't enforce types at runtime but enable static analysis tools like `mypy` to catch bugs before execution:
```python
from typing import List, Optional, Dict

def process_items(items: List[str], limit: Optional[int] = None) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in items[:limit]:
        result[item] = len(item)
    return result
```

### Q: How do I handle errors properly in Python?
A: Use specific exception types rather than bare `except` clauses. Always handle the narrowest exception possible:
```python
try:
    value = int(user_input)
    result = 100 / value
except ValueError:
    print("Input must be a valid integer.")
except ZeroDivisionError:
    print("Cannot divide by zero.")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    print("Cleanup code runs regardless of exceptions.")
```

### Q: What is a dataclass?
A: Dataclasses reduce boilerplate for classes that primarily store data. They auto-generate `__init__`, `__repr__`, `__eq__`, and other methods:
```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class Project:
    name: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        return f"{self.name} v{self.version}"
```

---

## Data Structures and Algorithms

### Q: What is Big O notation?
A: Big O notation describes the upper bound of an algorithm's time or space complexity as input size grows. Common complexities:
- **O(1)**: Constant — hash table lookup
- **O(log n)**: Logarithmic — binary search
- **O(n)**: Linear — single loop through array
- **O(n log n)**: Linearithmic — merge sort, heap sort
- **O(n²)**: Quadratic — nested loops, bubble sort
- **O(2ⁿ)**: Exponential — recursive Fibonacci without memoization

### Q: Explain binary search.
A: Binary search finds an element in a sorted array by repeatedly dividing the search interval in half:
```python
def binary_search(arr: list, target: int) -> int:
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1  # Not found
```
Time complexity: O(log n). Requires the array to be sorted.

### Q: What is dynamic programming?
A: Dynamic programming solves complex problems by breaking them into overlapping subproblems and caching results to avoid redundant computation. Two approaches:
- **Top-down (memoization)**: Recursive with a cache
- **Bottom-up (tabulation)**: Iterative, building solutions from smallest subproblems

```python
# Fibonacci with memoization
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

---

## Web Development

### Q: What is REST?
A: REST (Representational State Transfer) is an architectural style for designing networked applications. Key principles:
- **Stateless**: Each request contains all information needed to process it
- **Resource-based**: URLs identify resources, HTTP methods define actions
- **Uniform interface**: GET (read), POST (create), PUT (update), DELETE (remove)
- **Client-server separation**: Frontend and backend are independent

### Q: What is CORS?
A: CORS (Cross-Origin Resource Sharing) is a security mechanism that restricts how a web page from one origin can request resources from a different origin. The server must include specific headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`) to permit cross-origin requests. Without CORS headers, browsers block the response.

### Q: Explain the difference between SSR and CSR.
A: **Server-Side Rendering (SSR)** generates HTML on the server for each request. The browser receives fully rendered HTML, improving initial load time and SEO. **Client-Side Rendering (CSR)** sends a minimal HTML shell with JavaScript that renders content in the browser. CSR enables rich interactivity but has slower initial loads and poor SEO without additional configuration.

### Q: What is a WebSocket?
A: WebSocket is a protocol that provides persistent, full-duplex communication over a single TCP connection. Unlike HTTP (request-response), WebSockets allow both the client and server to send messages at any time. Common use cases include real-time chat, live notifications, multiplayer games, and collaborative editing.

---

## Game Development

### Q: What is a game loop?
A: A game loop is the core heartbeat of any game. Each iteration processes input, updates game state (physics, AI, collisions), and renders the frame. A fixed-timestep loop ensures consistent physics:
```python
import time

TICK_RATE = 1.0 / 60.0  # 60 updates per second

previous_time = time.time()
accumulator = 0.0

while running:
    current_time = time.time()
    delta = current_time - previous_time
    previous_time = current_time
    accumulator += delta
    
    while accumulator >= TICK_RATE:
        update_physics(TICK_RATE)
        accumulator -= TICK_RATE
    
    render()
```

### Q: What is ECS architecture?
A: Entity-Component-System (ECS) is a design pattern that favors composition over inheritance:
- **Entity**: A unique identifier (just an ID, no data or behavior)
- **Component**: Pure data attached to an entity (Position, Velocity, Sprite)
- **System**: Logic that operates on entities with specific component combinations

ECS provides excellent cache performance and flexibility for game objects.

---

## DevOps and Infrastructure

### Q: What is Docker?
A: Docker is a platform for building, shipping, and running applications in isolated containers. A container packages your application with all its dependencies, ensuring it runs identically across environments. Key concepts:
- **Image**: A read-only template defining the container's filesystem and configuration
- **Container**: A running instance of an image
- **Dockerfile**: A script that defines how to build an image
- **Docker Compose**: A tool for defining multi-container applications

### Q: What is CI/CD?
A: **Continuous Integration (CI)** automatically builds and tests code on every commit. **Continuous Deployment (CD)** automatically deploys tested code to production. Together, they create a pipeline that catches bugs early and accelerates release cycles. Common tools: GitHub Actions, GitLab CI, Jenkins, CircleCI.

### Q: Explain Git branching strategies.
A: Common strategies:
- **Git Flow**: Feature branches merge into `develop`, which merges into `main` for releases. Best for versioned software.
- **GitHub Flow**: Feature branches merge directly into `main`. Simpler, suited for continuous deployment.
- **Trunk-Based Development**: Everyone commits to `main` with short-lived feature branches (< 1 day). Fastest iteration.

---

## System Design

### Q: What is a load balancer?
A: A load balancer distributes incoming network traffic across multiple servers to ensure no single server is overwhelmed. Types include:
- **Round Robin**: Distributes requests sequentially
- **Least Connections**: Routes to the server with fewest active connections
- **IP Hash**: Routes based on client IP for session affinity
- **Weighted**: Assigns more traffic to more powerful servers

### Q: What is caching?
A: Caching stores frequently accessed data in a faster storage layer to reduce latency and load on the primary data source. Caching layers:
- **Browser cache**: Stores static assets locally
- **CDN**: Geographically distributed cache for static content
- **Application cache**: In-memory stores like Redis or Memcached
- **Database cache**: Query result caching

### Q: What is a message queue?
A: A message queue enables asynchronous communication between services by storing messages in a buffer. The producer sends messages to the queue, and the consumer processes them at its own pace. This decouples services and handles traffic spikes gracefully. Common implementations: RabbitMQ, Apache Kafka, Amazon SQS.

---

## Security

### Q: What is SQL injection?
A: SQL injection occurs when untrusted input is inserted directly into a SQL query, allowing an attacker to manipulate the database. Prevention: always use parameterized queries or prepared statements, never string concatenation.

### Q: What is XSS?
A: Cross-Site Scripting (XSS) injects malicious scripts into web pages viewed by other users. Types:
- **Stored XSS**: Script is saved in the database and served to all users
- **Reflected XSS**: Script is included in the URL and reflected back in the response
- **DOM-based XSS**: Script manipulates the page's DOM directly

Prevention: escape all user input, use Content Security Policy headers, sanitize HTML.

### Q: What is the principle of least privilege?
A: Every user, process, and program should operate with the minimum set of permissions necessary to complete its task. This limits the blast radius if a component is compromised. Apply it to database users, API keys, file system permissions, and cloud IAM roles.

---

## Mathematics

### Q: What is a dot product?
A: The dot product of two vectors produces a scalar measuring their alignment. For vectors A = (a₁, a₂) and B = (b₁, b₂): A · B = a₁b₁ + a₂b₂. The result equals |A||B|cos(θ) where θ is the angle between them. A dot product of 0 means the vectors are perpendicular.

### Q: Explain matrix multiplication.
A: To multiply matrices A (m×n) and B (n×p), each element C[i][j] in the result (m×p) is the dot product of row i of A and column j of B. The inner dimensions must match (n). Matrix multiplication is not commutative: AB ≠ BA in general.

### Q: What is gradient descent?
A: Gradient descent is an optimization algorithm that iteratively adjusts parameters to minimize a loss function. At each step, it computes the gradient (direction of steepest ascent) and moves in the opposite direction, scaled by the learning rate. Variants include stochastic gradient descent (SGD), Adam, and RMSProp.
