import json
import re
import random as _random
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List

class ModelResponse:
    def __init__(self, text: str, tools_to_call: List[Dict[str, Any]] = None):
        self.text = text
        self.tools_to_call = tools_to_call or []

class ModelEngine:
    def __init__(self, config):
        self.config = config

    def query(self, prompt: str, system_context: str = "") -> ModelResponse:
        backend = self.config.backend.lower()
        if backend == "ollama":
            return self._query_ollama(prompt, system_context)
        elif backend == "openai":
            return self._query_openai(prompt, system_context)
        elif backend == "gemini":
            return self._query_gemini(prompt, system_context)
        else:
            return self._query_mock(prompt, system_context)

    def _query_ollama(self, prompt: str, system_context: str) -> ModelResponse:
        url = f"{self.config.ollama_url}/api/chat"
        model_name = "llama3" if self.config.active_model == "UloLMBase" else "phi3"
        payload = {"model": model_name, "messages": [
            {"role": "system", "content": system_context},
            {"role": "user", "content": prompt}
        ], "stream": False, "options": {"temperature": 0.2}}
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return self._parse_response(res.get("message", {}).get("content", ""))
        except urllib.error.URLError as e:
            return ModelResponse(f"Error connecting to Ollama: {e.reason}.\nMake sure Ollama is running at {self.config.ollama_url}.")
        except Exception as e:
            return ModelResponse(f"Ollama query failed: {e}")

    def _query_openai(self, prompt: str, system_context: str) -> ModelResponse:
        if not self.config.openai_api_key:
            return ModelResponse("OpenAI API Key is missing. Set the OPENAI_API_KEY environment variable.")
        url = f"{self.config.openai_base_url}/chat/completions"
        payload = {"model": self.config.openai_model, "messages": [
            {"role": "system", "content": system_context},
            {"role": "user", "content": prompt}
        ], "temperature": 0.2}
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.config.openai_api_key}'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return self._parse_response(res.get("choices", [{}])[0].get("message", {}).get("content", ""))
        except urllib.error.HTTPError as e:
            return ModelResponse(f"OpenAI API Error: {e.code} - {e.read().decode('utf-8')}")
        except Exception as e:
            return ModelResponse(f"OpenAI query failed: {e}")

    def _query_gemini(self, prompt: str, system_context: str) -> ModelResponse:
        if not self.config.gemini_api_key:
            return ModelResponse("Gemini API Key is missing. Set the GEMINI_API_KEY environment variable or run `/config gemini_api_key YOUR_KEY`.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.gemini_model}:generateContent?key={self.config.gemini_api_key}"
        
        # Format for Gemini
        parts = []
        if system_context:
            parts.append({"text": f"System Context:\n{system_context}\n\n"})
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.2}
        }
        
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                
                # Extract text
                text = ""
                try:
                    candidates = res.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                except Exception:
                    text = str(res)
                    
                return self._parse_response(text)
        except urllib.error.HTTPError as e:
            return ModelResponse(f"Gemini API Error: {e.code} - {e.read().decode('utf-8')}")
        except Exception as e:
            return ModelResponse(f"Gemini query failed: {e}")

    def _pc(self, system_context: str) -> dict:
        """Parse context from system_context string."""
        ctx = {"project_name":"","tech_stack":"","files":[],"symbols":[],"roadmap_completed":[],"roadmap_in_progress":[],"roadmap_todo":[],"has_project":False}
        if not system_context:
            return ctx
        in_files = in_symbols = False
        for line in system_context.splitlines():
            s = line.strip()
            if s.startswith("Project Name:"):
                ctx["project_name"] = s.split(":", 1)[1].strip()
                if ctx["project_name"] and ctx["project_name"] != "Unnamed":
                    ctx["has_project"] = True
                in_files = in_symbols = False
            elif s.startswith("Target Stack:"):
                ctx["tech_stack"] = s.split(":", 1)[1].strip()
                in_files = in_symbols = False
            elif s == "Indexed Files:":
                in_files, in_symbols = True, False
            elif s == "Key Symbols Extracted:":
                in_files, in_symbols = False, True
            elif s.startswith("Roadmap:") or s.startswith("="):
                in_files = in_symbols = False
            elif s.startswith("- Completed:"):
                v = s.split(":", 1)[1].strip()
                if v and v != "None": ctx["roadmap_completed"] = [x.strip() for x in v.split(",")]
            elif s.startswith("- In Progress:"):
                v = s.split(":", 1)[1].strip()
                if v and v != "None": ctx["roadmap_in_progress"] = [x.strip() for x in v.split(",")]
            elif s.startswith("- Todo:"):
                v = s.split(":", 1)[1].strip()
                if v and v != "None": ctx["roadmap_todo"] = [x.strip() for x in v.split(",")]
            elif s.startswith("- "):
                entry = s[2:].strip()
                if in_files: ctx["files"].append(entry)
                elif in_symbols: ctx["symbols"].append(entry)
        return ctx

    def _search_wikipedia(self, query: str) -> str:
        """Fetches a summary from Wikipedia to act as an infinite knowledge base."""
        import urllib.parse
        try:
            # 1. Search for the exact page title
            q = urllib.parse.quote(query)
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&utf8=&format=json"
            req = urllib.request.Request(search_url, headers={'User-Agent': 'UloLM/2.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                search_data = json.loads(resp.read().decode('utf-8'))
                
            if not search_data.get('query', {}).get('search'):
                return ""
                
            title = search_data['query']['search'][0]['title']
            
            # 2. Fetch the summary for that title
            t = urllib.parse.quote(title)
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{t}"
            req2 = urllib.request.Request(summary_url, headers={'User-Agent': 'UloLM/2.0'})
            with urllib.request.urlopen(req2, timeout=5) as resp2:
                summary_data = json.loads(resp2.read().decode('utf-8'))
                
            extract = summary_data.get('extract', '')
            if extract:
                return f"**From Wikipedia ({title}):**\n\n{extract}"
            return ""
        except Exception:
            return ""

    # ─────────────────────────────────────────────────────────────
    # Mock Engine — Full Conversational AI
    # ─────────────────────────────────────────────────────────────

    def _query_mock(self, prompt: str, system_context: str) -> ModelResponse:
        p = prompt.lower().strip()
        ctx = self._pc(system_context)
        R = ModelResponse

        # ═══════════════════════════════════════════
        # CODING & DEV TASKS
        # ═══════════════════════════════════════════

        if any(x in p for x in ["game","pygame","platformer","shooter","godot","unity","unreal"]):
            if ctx["has"] and any(x in ctx["tech_stack"].lower() for x in ["pygame","game","godot"]):
                t = f"🎮 Your game project **{ctx['project_name']}** is loaded.\n"
                if ctx["files"]: t += f"Files: {', '.join(f'`{f}`' for f in ctx['files'][:5])}\n"
                if ctx["rp"]: t += f"In progress: {', '.join(ctx['rp'])}\n"
                if ctx["rt"]: t += f"Todo: {', '.join(ctx['rt'])}\n"
                t += "\nI can add features, fix bugs, or restructure — just say what."
                return R(t, [])
            st = {"project_name":"pygame-adventure","version":"0.1.0",
                "tech_stack":{"language":"Python","engine":"Pygame","libraries":["pygame"]},
                "architecture":{"entrypoint":"src/main.py","components":["GameLoop","Player","Enemy"]},
                "roadmap":{"completed":["Setup"],"in_progress":["Main loop"],"todo":["Audio","Levels"]}}
            code = ("import pygame,sys,random\npygame.init()\nW,H=800,600\nscreen=pygame.display.set_mode((W,H))\n"
                "pygame.display.set_caption('UloLM Game')\nclock=pygame.time.Clock()\n"
                "BG,PC,EC,TX=(10,10,15),(50,120,240),(240,70,70),(240,240,240)\n\n"
                "class Player(pygame.sprite.Sprite):\n  def __init__(self):\n    super().__init__()\n"
                "    self.image=pygame.Surface((50,50));self.image.fill(PC)\n"
                "    self.rect=self.image.get_rect(center=(W//2,H-80));self.speed=6\n"
                "  def update(self):\n    k=pygame.key.get_pressed()\n"
                "    if k[pygame.K_LEFT] and self.rect.left>0:self.rect.x-=self.speed\n"
                "    if k[pygame.K_RIGHT] and self.rect.right<W:self.rect.x+=self.speed\n\n"
                "class Enemy(pygame.sprite.Sprite):\n  def __init__(self):\n    super().__init__()\n"
                "    self.image=pygame.Surface((30,30));self.image.fill(EC)\n"
                "    self.rect=self.image.get_rect(center=(random.randint(50,W-50),-50))\n"
                "    self.speed=random.randint(3,7)\n"
                "  def update(self):\n    self.rect.y+=self.speed\n"
                "    if self.rect.top>H:self.rect.y=-50;self.rect.x=random.randint(50,W-50)\n\n"
                "player=Player()\nenemies=pygame.sprite.Group([Enemy() for _ in range(5)])\n"
                "sprites=pygame.sprite.Group(player,*enemies)\nrun,score=True,0\nwhile run:\n"
                "  clock.tick(60)\n  for e in pygame.event.get():\n    if e.type==pygame.QUIT:run=False\n"
                "  sprites.update()\n  if pygame.sprite.spritecollide(player,enemies,False):print(f'Game Over! {score}');run=False\n"
                "  screen.fill(BG);sprites.draw(screen)\n  f=pygame.font.SysFont('Arial',24)\n"
                "  screen.blit(f.render(f'Score:{score}',True,TX),(10,10))\n  pygame.display.flip();score+=1\n"
                "pygame.quit();sys.exit()\n")
            tools = [
                {"name":"write_file","parameters":{"path":".ulolm/project_state.json","content":json.dumps(st,indent=4)}},
                {"name":"write_file","parameters":{"path":"src/main.py","content":code}},
                {"name":"write_file","parameters":{"path":"requirements.txt","content":"pygame\n"}}
            ]
            return R("🎮 Created a Pygame project:\n- `src/main.py` — playable game with player movement and enemies\n- `.ulolm/project_state.json` — project memory\n\n```bash\npip install pygame\npython src/main.py\n```\nUse arrow keys to dodge enemies. Score goes up every frame.", tools)

        if any(x in p for x in ["website","webpage","html","web app","landing page","frontend","react","vue"]):
            html = ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
                '<title>My Site</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:#0a0a0f;color:#e0e0e0}'
                '.hero{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0a0a1a,#1a1a3e,#0a0a1a)}'
                'h1{font-size:3.5rem;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}'
                'p{margin-top:1rem;font-size:1.2rem;color:#9ca3af}</style></head><body><section class="hero"><div style="text-align:center">'
                '<h1>Welcome</h1><p>Built with UloLM</p></div></section></body></html>')
            return R("🌐 Created `index.html` — dark-themed landing page with gradient text and centered hero section. Open it in your browser to see it.",
                [{"name":"write_file","parameters":{"path":"index.html","content":html}}])

        if any(x in p for x in ["optimize","refactor","performance","speed up","make faster"]):
            t = "⚡ Here are the optimizations I would apply:\n\n"
            t += "1. **Replace nested loops** with hash-map lookups — O(n²) → O(n)\n"
            t += "2. **Pre-allocate lists** — `[None]*n` instead of appending in loops\n"
            t += "3. **Memoize** pure functions with `@functools.lru_cache`\n"
            t += "4. **Generators** — `yield` instead of building full lists for single-pass iteration\n"
            t += "5. **String building** — `''.join(parts)` instead of `s += piece` in loops\n"
            t += "6. **Batch I/O** — read/write files in chunks, batch DB queries\n"
            t += "7. **Use built-ins** — `sum()`, `map()`, `any()`, `all()` are C-optimized\n"
            t += "8. **Avoid global lookups** — assign frequently used globals to local variables\n"
            if ctx["files"]: t += f"\nI see {len(ctx['files'])} files in your workspace — paste the slow code and I will rewrite it."
            return R(t, [])

        if any(x in p for x in ["error","bug","crash","traceback","exception","broken","not working","debug"]):
            t = "🔍 Here are the most common Python errors and their fixes:\n\n"
            t += "| Error | Cause | Fix |\n| :--- | :--- | :--- |\n"
            t += "| `ModuleNotFoundError` | Package not installed | `pip install <package>` |\n"
            t += "| `ImportError` | Wrong import path | Check module name and structure |\n"
            t += "| `TypeError: NoneType` | Function returns None | Add missing `return` statement |\n"
            t += "| `IndexError` | List index out of range | Check `len()` before accessing |\n"
            t += "| `KeyError` | Dict key missing | Use `.get(key, default)` |\n"
            t += "| `AttributeError` | Object has no attribute | Check spelling or object type |\n"
            t += "| `ValueError` | Wrong value for operation | Validate input before processing |\n"
            t += "| `FileNotFoundError` | Path does not exist | Use `Path.exists()` check first |\n"
            t += "| `ZeroDivisionError` | Dividing by zero | Add `if divisor != 0` guard |\n"
            t += "| `RecursionError` | Infinite recursion | Check base case in recursive function |\n\n"
            t += "Paste your error and I will diagnose it."
            return R(t, [])

        if any(x in p for x in ["continue","resume","pick up where","keep going","next step"]):
            if ctx["has"]:
                t = f"🔄 **{ctx['project_name']}** — {len(ctx['files'])} files, {len(ctx['symbols'])} symbols.\n"
                if ctx["rp"]: t += "\n**In progress:**\n" + "".join(f"- 🔨 {x}\n" for x in ctx["rp"])
                if ctx["rt"]: t += "\n**Next up:**\n" + "".join(f"- ⬜ {x}\n" for x in ctx["rt"][:4])
            else:
                t = "No project loaded yet. Tell me what to build and I will create the project structure."
            return R(t, [])

        if any(x in p for x in ["write test","unittest","pytest","write tests"]):
            t = "🧪 Here is a test template you can use:\n\n```python\nimport unittest\n\nclass TestMyCode(unittest.TestCase):\n    def test_basic(self):\n        self.assertEqual(1 + 1, 2)\n\n    def test_string(self):\n        self.assertIn('hello', 'hello world')\n\n    def test_exception(self):\n        with self.assertRaises(ValueError):\n            int('not_a_number')\n\nif __name__ == '__main__':\n    unittest.main()\n```\n\n"
            if ctx["symbols"]: t += f"I found these symbols in your project I could test: {', '.join(ctx['symbols'][:5])}\n"
            t += "Tell me which function to test and I will generate real test cases for it."
            return R(t, [])

        if any(x in p for x in ["git init","git commit","git push","git pull","git branch","git merge","version control"]):
            return R("Here is a Git cheat sheet:\n\n"
                "```bash\ngit init                    # Start a repo\ngit add .                   # Stage everything\n"
                "git commit -m \"message\"     # Commit\ngit branch feature-x        # Create branch\n"
                "git checkout feature-x      # Switch branch\ngit merge feature-x         # Merge into current\n"
                "git push origin main        # Push to remote\ngit pull origin main        # Pull latest\n"
                "git log --oneline -10       # View history\ngit stash                   # Stash changes\n"
                "git stash pop               # Restore stashed\ngit diff                    # See changes\n"
                "git reset --hard HEAD~1     # Undo last commit (destructive!)\n```", [])

        if any(x in p for x in ["how to install","setup python","pip install","npm install","docker","venv","virtual env","conda"]):
            return R("**Python setup:**\n```bash\npython -m venv .venv\n.venv\\Scripts\\activate      # Windows\nsource .venv/bin/activate   # macOS/Linux\npip install <package>\npip freeze > requirements.txt\n```\n\n"
                "**Node.js setup:**\n```bash\nnpm init -y\nnpm install express\nnpm run dev\n```\n\n"
                "**Docker setup:**\n```dockerfile\nFROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"main.py\"]\n```\n```bash\ndocker build -t myapp .\ndocker run -p 8080:8080 myapp\n```", [])

        if any(x in p for x in ["database","sql","sqlite","postgres","mysql","mongo","redis"]):
            return R("Here is a quick SQLite example in Python:\n\n```python\nimport sqlite3\n\nconn = sqlite3.connect('app.db')\nc = conn.cursor()\n\nc.execute('''CREATE TABLE IF NOT EXISTS users (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    name TEXT NOT NULL,\n    email TEXT UNIQUE\n)''')\n\nc.execute(\"INSERT INTO users (name, email) VALUES (?, ?)\", ('Alice', 'alice@example.com'))\nconn.commit()\n\nfor row in c.execute('SELECT * FROM users'):\n    print(row)\n\nconn.close()\n```\n\n"
                "**PostgreSQL** — use `psycopg2`. **MongoDB** — use `pymongo`. **Redis** — use `redis-py`.\n"
                "I can generate a full database layer for any of these.", [])

        if any(x in p for x in ["python script","automate","automation","scrape","scraper","bot","cron"]):
            code = ("import os, json, time\nfrom pathlib import Path\nfrom datetime import datetime\n\n"
                "def run():\n    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')\n"
                "    files = list(Path('.').rglob('*'))\n"
                "    print(f'[{ts}] Found {len(files)} files')\n"
                "    return {'time': ts, 'count': len(files)}\n\n"
                "if __name__ == '__main__':\n    print(json.dumps(run(), indent=2))\n")
            return R("🤖 Created `scripts/automate.py` — a starter automation script that scans your workspace and logs file counts with timestamps.\n\n```bash\npython scripts/automate.py\n```\n\nModify the `run()` function with your actual logic — file renaming, API calls, data processing, whatever you need.",
                [{"name":"write_file","parameters":{"path":"scripts/automate.py","content":code}}])

        if any(x in p for x in ["readme","document","write a spec","write docs"]):
            if ctx["has"]:
                t = f"✍️ Here is an auto-generated README for **{ctx['project_name']}**:\n\n"
                t += f"```markdown\n# {ctx['project_name']}\n\n"
                if ctx["tech_stack"]: t += f"**Stack:** {ctx['tech_stack']}\n\n"
                t += "## Files\n"
                for f in ctx["files"][:10]: t += f"- `{f}`\n"
                if ctx["symbols"]: t += "\n## Key Components\n" + "".join(f"- {s}\n" for s in ctx["symbols"][:8])
                t += "```\n\nI can expand this with installation instructions, API docs, and usage examples."
            else:
                t = "✍️ No project loaded, but here is a README template:\n\n```markdown\n# Project Name\n\nBrief description.\n\n## Installation\n```bash\npip install -r requirements.txt\n```\n\n## Usage\n```bash\npython main.py\n```\n\n## License\nMIT\n```"
            return R(t, [])

        if any(x in p for x in ["css","style","color","theme","dark mode","layout","font"]):
            return R("🎨 Here is a modern CSS starter with dark mode:\n\n```css\n:root {\n  --bg: #0a0a0f;\n  --surface: #1a1a2e;\n  --primary: #60a5fa;\n  --accent: #a78bfa;\n  --text: #e0e0e0;\n  --muted: #6b7280;\n  --radius: 12px;\n}\n\n* { margin: 0; padding: 0; box-sizing: border-box; }\n\nbody {\n  font-family: 'Inter', system-ui, sans-serif;\n  background: var(--bg);\n  color: var(--text);\n  line-height: 1.6;\n}\n\n.card {\n  background: var(--surface);\n  border-radius: var(--radius);\n  padding: 2rem;\n  backdrop-filter: blur(10px);\n  border: 1px solid rgba(255,255,255,0.05);\n}\n\n.btn {\n  background: linear-gradient(135deg, var(--primary), var(--accent));\n  color: white;\n  border: none;\n  padding: 0.75rem 1.5rem;\n  border-radius: var(--radius);\n  cursor: pointer;\n  font-weight: 600;\n  transition: transform 0.2s, box-shadow 0.2s;\n}\n\n.btn:hover {\n  transform: translateY(-2px);\n  box-shadow: 0 4px 20px rgba(96,165,250,0.3);\n}\n```\n\nThis gives you CSS variables for easy theming, glassmorphism cards, and animated buttons.", [])

        # ═══════════════════════════════════════════
        # GENERAL KNOWLEDGE — answer, don't ask
        # ═══════════════════════════════════════════

        # Capitals
        caps = {"afghanistan":"Kabul","albania":"Tirana","algeria":"Algiers","argentina":"Buenos Aires",
            "australia":"Canberra","austria":"Vienna","bangladesh":"Dhaka","belgium":"Brussels",
            "brazil":"Brasília","cambodia":"Phnom Penh","canada":"Ottawa","chile":"Santiago",
            "china":"Beijing","colombia":"Bogotá","croatia":"Zagreb","cuba":"Havana",
            "czech republic":"Prague","czechia":"Prague","denmark":"Copenhagen","egypt":"Cairo",
            "ethiopia":"Addis Ababa","finland":"Helsinki","france":"Paris","germany":"Berlin",
            "ghana":"Accra","greece":"Athens","hungary":"Budapest","iceland":"Reykjavik",
            "india":"New Delhi","indonesia":"Jakarta","iran":"Tehran","iraq":"Baghdad",
            "ireland":"Dublin","israel":"Jerusalem","italy":"Rome","jamaica":"Kingston",
            "japan":"Tokyo","jordan":"Amman","kenya":"Nairobi","kuwait":"Kuwait City",
            "lebanon":"Beirut","libya":"Tripoli","malaysia":"Kuala Lumpur","mexico":"Mexico City",
            "morocco":"Rabat","myanmar":"Naypyidaw","nepal":"Kathmandu","netherlands":"Amsterdam",
            "new zealand":"Wellington","nigeria":"Abuja","north korea":"Pyongyang","norway":"Oslo",
            "pakistan":"Islamabad","peru":"Lima","philippines":"Manila","poland":"Warsaw",
            "portugal":"Lisbon","qatar":"Doha","romania":"Bucharest","russia":"Moscow",
            "saudi arabia":"Riyadh","singapore":"Singapore","south africa":"Pretoria",
            "south korea":"Seoul","spain":"Madrid","sri lanka":"Sri Jayawardenepura Kotte",
            "sweden":"Stockholm","switzerland":"Bern","syria":"Damascus","taiwan":"Taipei",
            "thailand":"Bangkok","turkey":"Ankara","uae":"Abu Dhabi","united arab emirates":"Abu Dhabi",
            "uk":"London","united kingdom":"London","england":"London","usa":"Washington, D.C.",
            "united states":"Washington, D.C.","ukraine":"Kyiv","uzbekistan":"Tashkent",
            "venezuela":"Caracas","vietnam":"Hanoi","zimbabwe":"Harare"}
        for country, capital in caps.items():
            if country in p and ("capital" in p or "capitol" in p):
                return R(f"The capital of **{country.title()}** is **{capital}**.", [])

        # Math eval
        if any(c.isdigit() for c in p) and any(x in p for x in ["+","-","*","/","plus","minus","times","divided","percent","sqrt","square root","power","^"]):
            expr = prompt.strip()
            expr = re.sub(r'(?i)\bplus\b', '+', expr)
            expr = re.sub(r'(?i)\bminus\b', '-', expr)
            expr = re.sub(r'(?i)\btimes\b', '*', expr)
            expr = re.sub(r'(?i)\bdivided by\b', '/', expr)
            expr = re.sub(r'(?i)\bpercent of\b', '/100*', expr)
            expr = re.sub(r'(?i)\bsquare root of\b', 'sqrt', expr)
            expr = re.sub(r'\^', '**', expr)
            calc = re.sub(r'[^0-9+\-*/().%\s]', '', expr).strip()
            if calc:
                try:
                    result = eval(calc, {"__builtins__": {}}, {})
                    return R(f"**{prompt.strip()}** = **{result}**", [])
                except: pass

        if any(x in p for x in ["calculate","formula","equation","algebra","calculus","matrix","vector","math"]):
            return R("🔢 I can solve math problems. Here are some examples:\n\n"
                "- `2 + 2` → **4**\n- `15 percent of 230` → **34.5**\n- `2 ^ 10` → **1024**\n- `sqrt(144)` → **12**\n\n"
                "For complex problems: Area of a circle = π × r². A triangle = ½ × base × height. "
                "Pythagorean theorem: a² + b² = c².\n\nType a math expression and I will compute it.", [])

        # Science
        if any(x in p for x in ["speed of light","how fast is light"]):
            return R("The speed of light in a vacuum is **299,792,458 m/s** (~186,282 mi/s). Light from the Sun takes about **8 minutes 20 seconds** to reach Earth. Nothing with mass can reach or exceed this speed — it is the universal speed limit.", [])
        if "photosynthesis" in p:
            return R("**Photosynthesis** converts sunlight into chemical energy.\n\n**Equation:** 6CO₂ + 6H₂O + sunlight → C₆H₁₂O₆ + 6O₂\n\nPlants absorb CO₂ and water, use chlorophyll to capture light energy, and produce glucose (food) and oxygen (what we breathe). It happens in the chloroplasts of plant cells.", [])
        if any(x in p for x in ["gravity","gravitational"]):
            return R("**Gravity** is the force of attraction between objects with mass.\n\n- Earth's surface gravity: **9.8 m/s²**\n- Moon: ~1.6 m/s² (⅙ of Earth)\n- Jupiter: ~24.8 m/s² (2.5× Earth)\n\nNewton described it as F = G(m₁m₂)/r². Einstein's General Relativity reframed it as the curvature of spacetime caused by mass.", [])
        if any(x in p for x in ["planet","solar system","mercury","venus","mars","jupiter","saturn","uranus","neptune"]):
            return R("**The Solar System** — 8 planets from the Sun:\n\n"
                "| Planet | Distance | Fun Fact |\n| :--- | :--- | :--- |\n"
                "| Mercury | 58M km | Smallest, no atmosphere |\n"
                "| Venus | 108M km | Hottest (462°C), spins backward |\n"
                "| Earth | 150M km | Only known life 🌍 |\n"
                "| Mars | 228M km | Red planet, tallest volcano |\n"
                "| Jupiter | 778M km | Largest, Great Red Spot storm |\n"
                "| Saturn | 1.4B km | Iconic rings made of ice |\n"
                "| Uranus | 2.9B km | Tilted 98° on its side |\n"
                "| Neptune | 4.5B km | Strongest winds (2,100 km/h) |\n\n"
                "Pluto was reclassified as a dwarf planet in 2006.", [])
        if any(x in p for x in ["black hole"]):
            return R("A **black hole** is a region of spacetime where gravity is so strong that nothing — not even light — can escape.\n\n- Formed when massive stars collapse at end of life\n- The boundary is called the **event horizon**\n- At the center is a **singularity** — a point of infinite density\n- The supermassive black hole at the center of our galaxy (Sagittarius A*) has the mass of ~4 million Suns\n- First image of a black hole was captured in 2019 by the Event Horizon Telescope", [])
        if any(x in p for x in ["dna","genetics","gene","chromosome"]):
            return R("**DNA (Deoxyribonucleic Acid)** is the molecule that carries genetic instructions for life.\n\n- Shaped as a **double helix** — two strands twisted together\n- Made of 4 bases: **A**denine, **T**hymine, **G**uanine, **C**ytosine\n- A pairs with T, G pairs with C\n- Human DNA has ~**3 billion** base pairs across **23 pairs** of chromosomes\n- **Genes** are segments of DNA that code for proteins\n- Your DNA is 99.9% identical to every other human", [])
        if any(x in p for x in ["evolution","natural selection","darwin"]):
            return R("**Evolution** is the change in inherited traits of populations over generations.\n\n- **Charles Darwin** proposed natural selection in 1859 (On the Origin of Species)\n- **Natural selection:** organisms better adapted to their environment survive and reproduce more\n- **Key mechanisms:** mutation, selection, genetic drift, gene flow\n- All life on Earth shares a common ancestor (~3.8 billion years ago)\n- Evolution is not \"survival of the fittest\" in the gym sense — it means best *fit* to the environment", [])
        if any(x in p for x in ["atom","electron","proton","neutron","element","periodic table"]):
            return R("**Atoms** are the building blocks of matter.\n\n- **Protons** (+ charge) and **neutrons** (neutral) form the nucleus\n- **Electrons** (- charge) orbit the nucleus in shells\n- Number of protons = **atomic number** (defines the element)\n- Hydrogen: 1 proton. Carbon: 6. Iron: 26. Gold: 79.\n- The periodic table organizes all 118 known elements by atomic number\n- Atoms are ~99.9999999% empty space", [])
        if any(x in p for x in ["water","h2o"]) and any(x in p for x in ["what is","boiling","freezing","made of"]):
            return R("**Water (H₂O)** — two hydrogen atoms bonded to one oxygen atom.\n\n- Freezing point: **0°C** (32°F)\n- Boiling point: **100°C** (212°F)\n- Covers ~71% of Earth's surface\n- Essential for all known forms of life\n- Water is the only natural substance that exists in all 3 states (solid, liquid, gas) on Earth's surface\n- A water molecule is bent at ~104.5°", [])

        # History / Inventions
        inv = {
            "electricity": "**Benjamin Franklin** proved lightning was electrical (1752). **Michael Faraday** discovered electromagnetic induction (1831). **Thomas Edison** made the practical light bulb (1879). **Nikola Tesla** pioneered AC power systems.",
            "internet": "The Internet evolved from **ARPANET** (1969, U.S. DoD). **Tim Berners-Lee** invented the **World Wide Web** in 1989 at CERN.",
            "telephone": "**Alexander Graham Bell** patented the telephone in **1876**.",
            "computer": "**Charles Babbage** designed the Analytical Engine (1830s). **Alan Turing** formalized computation (1936). **ENIAC** (1945) was the first electronic general-purpose computer.",
            "python": "**Guido van Rossum** created Python, first released in **1991**. Named after Monty Python, not the snake.",
            "linux": "**Linus Torvalds** created Linux in **1991** as a free, open-source OS kernel.",
            "google": "**Larry Page** and **Sergey Brin** founded Google in **1998** at Stanford.",
            "apple": "**Steve Jobs**, **Steve Wozniak**, and **Ronald Wayne** founded Apple in **1976**.",
            "microsoft": "**Bill Gates** and **Paul Allen** founded Microsoft in **1975**.",
            "tesla": "**Tesla Inc.** was incorporated in **2003** by Eberhard and Tarpenning. **Elon Musk** joined in 2004.",
            "airplane": "**Wright Brothers** (Orville and Wilbur) made the first powered flight on **December 17, 1903** at Kitty Hawk, NC. The flight lasted 12 seconds.",
            "television": "**Philo Farnsworth** demonstrated the first fully electronic TV in **1927**. **John Logie Baird** demonstrated a mechanical TV in 1926.",
            "radio": "**Guglielmo Marconi** sent the first radio signal across the Atlantic in **1901**.",
            "penicillin": "**Alexander Fleming** discovered penicillin in **1928** when mold contaminated a petri dish. It became the first widely used antibiotic.",
            "vaccine": "**Edward Jenner** created the first vaccine (smallpox) in **1796** using cowpox material.",
            "printing press": "**Johannes Gutenberg** invented the movable-type printing press around **1440**, revolutionizing the spread of knowledge.",
            "steam engine": "**Thomas Newcomen** built the first practical steam engine (1712). **James Watt** greatly improved it (1769).",
            "bitcoin": "**Satoshi Nakamoto** (pseudonym) published the Bitcoin whitepaper in **2008** and launched the network in January 2009.",
            "youtube": "**Steve Chen**, **Chad Hurley**, and **Jawed Karim** founded YouTube in **2005**. Google acquired it in 2006 for $1.65 billion.",
            "wikipedia": "**Jimmy Wales** and **Larry Sanger** launched Wikipedia on **January 15, 2001**.",
            "instagram": "**Kevin Systrom** and **Mike Krieger** launched Instagram in **October 2010**. Facebook acquired it in 2012.",
            "netflix": "**Reed Hastings** and **Marc Randolph** founded Netflix in **1997** as a DVD rental service. Streaming launched in 2007.",
        }
        for key, answer in inv.items():
            if key in p and any(x in p for x in ["who invented","who discovered","who created","who founded","who made","who built","who started","history of","origin of"]):
                return R(answer, [])

        # Definitions
        defs = {
            "machine learning": "**Machine Learning** — systems that learn patterns from data instead of being explicitly programmed. Types: supervised (labeled data), unsupervised (finding patterns), reinforcement (learning from rewards).",
            "artificial intelligence": "**AI** — the simulation of human intelligence by computers: learning, reasoning, problem-solving, perception, and language understanding. Subfields include ML, NLP, computer vision, and robotics.",
            "blockchain": "**Blockchain** — a decentralized digital ledger where transactions are recorded in linked blocks, each containing a cryptographic hash of the previous block, making it tamper-resistant.",
            "cryptocurrency": "**Cryptocurrency** — digital currency using cryptography on decentralized blockchains. Bitcoin (2009) was the first. Others: Ethereum, Solana, Cardano.",
            "quantum computing": "**Quantum Computing** — uses qubits that can be in superposition (0 and 1 simultaneously), enabling exponentially faster computation for certain problems like factoring, optimization, and simulation.",
            "neural network": "**Neural Network** — layers of interconnected nodes (neurons) that process data. Input → hidden layers → output. Deep networks with many hidden layers power modern AI (image recognition, language models).",
            "recursion": "**Recursion** — a function that calls itself on simpler input. Needs a base case to stop.\n\n```python\ndef factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)\n```\n\nfactorial(5) = 5 × 4 × 3 × 2 × 1 = **120**",
            "api": "**API (Application Programming Interface)** — a contract between software systems. REST APIs use HTTP: `GET` (read), `POST` (create), `PUT` (update), `DELETE` (remove). Data is usually JSON.",
            "algorithm": "**Algorithm** — a step-by-step procedure for solving a problem. Measured by time complexity (speed) and space complexity (memory). Common: sorting (O(n log n)), searching (O(log n)), graph traversal (O(V+E)).",
            "docker": "**Docker** — packages apps with all dependencies into containers that run identically everywhere. Lighter than VMs because containers share the host OS kernel.",
            "kubernetes": "**Kubernetes (K8s)** — orchestrates containers across clusters. Handles scaling, load balancing, rolling updates, and self-healing. Created by Google, now open-source (CNCF).",
            "rust": "**Rust** — systems language focused on safety and speed. Ownership system prevents memory bugs at compile time. No garbage collector. Used for browsers (Firefox), crypto, CLI tools, and WebAssembly.",
            "typescript": "**TypeScript** — JavaScript with static types. Catches errors at compile time. Compiles to plain JS. Created by Microsoft. Used by Angular, Vue 3, Next.js, and most modern web projects.",
            "javascript": "**JavaScript** — the language of the web. Runs in browsers and on servers (Node.js). Dynamic typing, prototype-based OOP, first-class functions. Created by Brendan Eich in 1995 in 10 days.",
            "react": "**React** — a JavaScript UI library by Facebook/Meta. Uses components, JSX (HTML-in-JS), virtual DOM for performance, and hooks for state management. Most popular frontend framework.",
            "linux": "**Linux** — open-source OS kernel by Linus Torvalds (1991). Powers Android, servers (~96% of top web servers), supercomputers (100% of top 500), and IoT devices.",
            "git": "**Git** — distributed version control system by Linus Torvalds (2005). Tracks code changes, enables branching, merging, and collaboration. GitHub, GitLab, and Bitbucket host Git repos.",
            "cloud computing": "**Cloud Computing** — on-demand computing resources (servers, storage, databases) over the internet. Major providers: AWS (Amazon), Azure (Microsoft), GCP (Google). Models: IaaS, PaaS, SaaS.",
            "devops": "**DevOps** — culture and practices that unify development and operations. Key practices: CI/CD, infrastructure as code, monitoring, containerization. Tools: Jenkins, GitHub Actions, Terraform, Docker.",
            "agile": "**Agile** — iterative software development methodology. Work in short sprints (1-4 weeks), deliver incrementally, adapt to change. Frameworks: Scrum, Kanban. Replaces waterfall's rigid phases.",
            "big o notation": "**Big O Notation** measures algorithm efficiency:\n- **O(1)** — constant (hash lookup)\n- **O(log n)** — logarithmic (binary search)\n- **O(n)** — linear (simple loop)\n- **O(n log n)** — linearithmic (merge sort)\n- **O(n²)** — quadratic (nested loops)\n- **O(2ⁿ)** — exponential (brute force)",
            "tcp ip": "**TCP/IP** — the protocol stack that powers the internet. **IP** handles addressing and routing. **TCP** ensures reliable, ordered delivery of data. Together they let computers communicate across networks.",
            "http": "**HTTP** — HyperText Transfer Protocol. How browsers communicate with servers. Methods: GET, POST, PUT, DELETE. Status codes: 200 (OK), 404 (Not Found), 500 (Server Error). HTTPS adds TLS encryption.",
            "compiler": "**A Compiler** translates source code into machine code before execution (C, Rust, Go). An **interpreter** executes line by line (Python, Ruby). **JIT compilers** compile at runtime (Java, JavaScript V8).",
            "design pattern": "**Design Patterns** — reusable solutions to common software problems:\n- **Singleton** — one instance only\n- **Factory** — create objects without specifying class\n- **Observer** — event-driven pub/sub\n- **Strategy** — swap algorithms at runtime\n- **MVC** — Model-View-Controller separation",
        }
        for key, definition in defs.items():
            if key in p and any(x in p for x in ["what is","what's","what are","explain","define","tell me about","describe","meaning of"]):
                return R(definition, [])

        # Jokes
        if any(x in p for x in ["joke","funny","make me laugh","humor","tell me something funny"]):
            jokes = [
                "Why do programmers prefer dark mode?\n\nBecause light attracts bugs. 🪲",
                "A SQL query walks into a bar, sees two tables, and asks... *\"Can I JOIN you?\"*",
                "Why did the developer go broke? He used up all his cache. 💸",
                "!false — It's funny because it's true.",
                "A programmer's wife says: *\"Go get a loaf of bread. If they have eggs, get a dozen.\"*\n\nHe comes back with 12 loaves. *\"They had eggs.\"* 🍞",
                "There are only 10 types of people in the world: those who understand binary and those who don't.",
                "A QA engineer walks into a bar. Orders 1 beer. Orders 0 beers. Orders 99999999 beers. Orders -1 beers. Orders a lizard. Orders NULL beers. First customer walks in and asks where the bathroom is. The bar bursts into flames. 🔥",
                "Why do Java developers wear glasses? Because they can't C#. 👓",
                "['hip','hip'] — hip hip array! 🎉",
                "What is a programmer's favorite hangout? Foo Bar. 🍸",
                "How do you comfort a JavaScript bug? You console it. 💻",
                "Why was the JavaScript developer sad? Because he didn't Node how to Express himself. 😢",
                "What is the object-oriented way to become wealthy? Inheritance. 💰",
                "ASCII silly question, get a silly ANSI. 😄",
                "A programmer puts two glasses on his bedside table before going to sleep. A full one in case he gets thirsty, and an empty one in case he doesn't.",
            ]
            return R(jokes[hash(prompt) % len(jokes)], [])

        # Time/Date
        if any(x in p for x in ["what time","current time","what day","today's date","what date","what year"]):
            now = datetime.now()
            return R(f"It's **{now.strftime('%I:%M %p')}** on **{now.strftime('%A, %B %d, %Y')}**.", [])

        # Weather
        if "weather" in p:
            return R("I run locally without internet access, so I can't check live weather. But here's how you can get it programmatically:\n\n```python\nimport requests\nAPI_KEY = 'your_key'  # Get free key at openweathermap.org\ncity = 'London'\nurl = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric'\ndata = requests.get(url).json()\nprint(f\"{data['weather'][0]['description']}, {data['main']['temp']}°C\")\n```\n\nSign up at [openweathermap.org](https://openweathermap.org/api) for a free API key.", [])

        # Cooking
        recipes = {
            "pancake": "🥞 **Pancakes**\n\n**Ingredients:** 1 cup flour, 1 tbsp sugar, 1 tsp baking powder, 1 egg, 1 cup milk, 2 tbsp melted butter\n\n**Steps:**\n1. Mix dry ingredients\n2. Whisk egg + milk + butter separately\n3. Combine — don't overmix, lumps are fine\n4. Heat pan on medium, pour ¼ cup per pancake\n5. Flip when bubbles form (~2 min/side)\n6. Serve with maple syrup 🍁",
            "pasta": "🍝 **Simple Garlic Pasta**\n\n**Ingredients:** 200g spaghetti, 4 cloves garlic, 3 tbsp olive oil, red pepper flakes, parmesan, salt, parsley\n\n**Steps:**\n1. Boil pasta in salted water until al dente, save 1 cup pasta water\n2. Slice garlic thin, sauté in olive oil on low heat until golden (not brown)\n3. Add pepper flakes, toss in drained pasta\n4. Add pasta water splash by splash until silky\n5. Top with parmesan and parsley",
            "scrambled eggs": "🥚 **Perfect Scrambled Eggs** (Gordon Ramsay method)\n\n**Ingredients:** 3 eggs, 1 tbsp butter, salt, pepper, chives\n\n**Steps:**\n1. Cold pan — add eggs and butter, no pre-beat\n2. Medium heat, stir constantly with spatula\n3. On/off heat every 30 seconds (prevents overcooking)\n4. When 80% set, remove from heat — residual heat finishes them\n5. Season, add chives. Should be creamy, not rubbery",
            "fried rice": "🍚 **Egg Fried Rice**\n\n**Ingredients:** 2 cups day-old rice, 2 eggs, 3 tbsp soy sauce, 1 tbsp sesame oil, 2 green onions, garlic\n\n**Steps:**\n1. High heat — scramble eggs, set aside\n2. Same pan — sauté garlic 30 seconds\n3. Add cold rice, break up clumps, fry 3-4 min\n4. Add soy sauce and sesame oil, toss\n5. Add eggs back, toss with green onions",
            "cookie": "🍪 **Chocolate Chip Cookies**\n\n**Ingredients:** 2¼ cups flour, 1 cup butter (softened), ¾ cup sugar, ¾ cup brown sugar, 2 eggs, 1 tsp vanilla, 1 tsp baking soda, 2 cups chocolate chips\n\n**Steps:**\n1. Cream butter + sugars until fluffy\n2. Beat in eggs and vanilla\n3. Mix in flour + baking soda\n4. Fold in chocolate chips\n5. Scoop onto baking sheet\n6. Bake at 375°F / 190°C for 9-11 minutes\n7. Let cool 5 min (they firm up!)",
            "smoothie": "🥤 **Berry Smoothie**\n\n**Ingredients:** 1 banana, 1 cup mixed berries, 1 cup yogurt (or milk), 1 tbsp honey, ice\n\n**Steps:**\n1. Add everything to blender\n2. Blend until smooth (30-60 seconds)\n3. Pour and enjoy. Add protein powder or spinach for extra nutrition.",
            "sandwich": "🥪 **Club Sandwich**\n\n**Layers:** Toast 3 slices of bread. Layer 1: mayo, lettuce, turkey/chicken. Layer 2: bacon, tomato, more lettuce. Secure with toothpicks, cut diagonally.",
            "omelette": "🍳 **French Omelette**\n\n**Ingredients:** 3 eggs, 1 tbsp butter, salt, pepper, fillings (cheese/herbs/mushrooms)\n\n**Steps:**\n1. Beat eggs with fork, season\n2. Medium heat, melt butter until foamy\n3. Pour eggs, stir gently with chopstick\n4. When mostly set, add fillings to one side\n5. Fold over, slide onto plate. Should be pale yellow, not brown",
        }
        if any(x in p for x in ["recipe","how to cook","how to make","how to bake","ingredients"]):
            for dish, recipe in recipes.items():
                if dish in p: return R(recipe, [])
            return R("🍳 I know recipes for: pancakes, pasta, scrambled eggs, fried rice, cookies, smoothies, sandwiches, and omelettes.\n\nTell me which one you want, or name any dish and I will give you the recipe.", [])

        # Movies/Books/Music
        if any(x in p for x in ["recommend","suggestion","suggest","best","favorite","good"]):
            if any(x in p for x in ["movie","film","watch"]):
                return R("🎬 **Movie recommendations:**\n\n"
                    "**Sci-Fi:** Interstellar, Blade Runner 2049, Arrival, The Matrix, Ex Machina\n"
                    "**Thriller:** Inception, Parasite, Se7en, Gone Girl, Shutter Island\n"
                    "**Animation:** Spider-Verse, Spirited Away, WALL-E, Coco, Your Name\n"
                    "**Drama:** Shawshank Redemption, Whiplash, Good Will Hunting, Fight Club\n"
                    "**Comedy:** Grand Budapest Hotel, Superbad, Everything Everywhere All at Once\n"
                    "**Horror:** Get Out, Hereditary, The Shining, A Quiet Place", [])
            if any(x in p for x in ["book","read","reading"]):
                return R("📚 **Book recommendations:**\n\n"
                    "**Programming:** Clean Code, Designing Data-Intensive Apps, The Pragmatic Programmer\n"
                    "**Sci-Fi:** Dune, Project Hail Mary, Neuromancer, The Three-Body Problem\n"
                    "**Self-Improvement:** Atomic Habits, Deep Work, Thinking Fast and Slow\n"
                    "**Philosophy:** Meditations (Marcus Aurelius), Man's Search for Meaning\n"
                    "**Fiction:** 1984, Hitchhiker's Guide, Kafka on the Shore, Sapiens", [])
            if any(x in p for x in ["song","music","listen","playlist"]):
                return R("🎵 **Music picks:**\n\n"
                    "**Coding focus:** Lo-fi hip hop, Synthwave, Brian Eno's ambient, Tycho\n"
                    "**Energetic:** Daft Punk, The Weeknd, Kendrick Lamar, Tame Impala\n"
                    "**Chill:** Khruangbin, Mac DeMarco, Nujabes, Bonobo\n"
                    "**Classic:** Bohemian Rhapsody, Hotel California, Stairway to Heaven\n"
                    "**Instrumental:** Hans Zimmer, Ludovico Einaudi, Explosions in the Sky", [])

        # Motivation
        if any(x in p for x in ["motivat","inspire","feeling down","feeling sad","stressed","depressed","anxious","encourage","lonely","give up","tired of"]):
            return R("Progress is not always visible. Every problem you wrestle with makes you sharper.\n\n"
                "**Things that actually help:**\n"
                "- Take a walk. Fresh air resets your brain.\n"
                "- Break it down. Do the smallest possible next step.\n"
                "- Sleep on it. Bugs that take hours at midnight take minutes in the morning.\n"
                "- Talk to someone. You are not meant to figure everything out alone.\n"
                "- Remember: you have already solved hundreds of problems you once thought were impossible.\n\n"
                "You are doing better than you think. Keep going. 💪", [])

        # Philosophy / deep questions
        if any(x in p for x in ["meaning of life","purpose of life","why do we exist","why are we here","what is consciousness"]):
            return R("That is one of humanity's oldest questions.\n\n"
                "- **Existentialism** (Sartre): Life has no inherent meaning — we create our own through choices.\n"
                "- **Absurdism** (Camus): The universe is indifferent, but we can find joy anyway.\n"
                "- **Viktor Frankl**: Meaning comes from purpose, love, and how we face suffering.\n"
                "- **Biology**: Life exists to replicate and adapt.\n"
                "- **Buddhism**: Suffering comes from attachment; meaning comes from mindfulness and compassion.\n\n"
                "My take: meaning is not something you find — it is something you build. Create things, help people, stay curious.", [])

        # Animals
        if any(x in p for x in ["fastest animal","slowest animal","biggest animal","smallest animal","animal fact","fun fact about animal"]):
            return R("🐾 **Animal facts:**\n\n"
                "- **Fastest:** Peregrine falcon — 390 km/h (242 mph) in dive. On land: cheetah at 112 km/h.\n"
                "- **Largest:** Blue whale — up to 30 meters, 150 tonnes. Largest animal EVER.\n"
                "- **Smallest mammal:** Bumblebee bat — 2 grams.\n"
                "- **Longest living:** Greenland shark — can live 400+ years.\n"
                "- **Smartest:** Great apes, dolphins, octopuses, crows (can use tools and solve puzzles).\n"
                "- **Octopuses** have 3 hearts, blue blood, and can edit their own RNA.\n"
                "- **Tardigrades** survive in space, radiation, and near absolute zero.", [])

        # Space
        if any(x in p for x in ["how far is the moon","distance to moon","moon fact"]):
            return R("🌙 The Moon is approximately **384,400 km** (238,855 miles) from Earth.\n\n- Light takes ~1.3 seconds to travel from Earth to Moon\n- 12 people have walked on it (Apollo missions, 1969-1972)\n- The Moon is slowly moving away from Earth (~3.8 cm/year)\n- It has no atmosphere, so footprints last millions of years\n- Same side always faces Earth (tidally locked)", [])
        if any(x in p for x in ["how far is the sun","distance to sun","sun fact"]):
            return R("☀️ The Sun is approximately **149.6 million km** (93 million miles) from Earth.\n\n- Light takes ~8 min 20 sec to reach us\n- Surface temperature: ~5,500°C. Core: ~15 million°C\n- It is a medium-sized star (G-type main-sequence)\n- Contains 99.86% of the solar system's mass\n- Will become a red giant in ~5 billion years", [])

        # Health
        if any(x in p for x in ["how much water","drink water","hydration"]):
            return R("💧 General guideline: about **2-3 liters** (8-12 cups) of water per day for adults.\n\n"
                "This varies based on body weight, activity level, and climate. A simple rule: drink when thirsty, and check your urine — pale yellow means you are well hydrated.", [])
        if any(x in p for x in ["how much sleep","sleep need","hours of sleep"]):
            return R("😴 **Recommended sleep by age:**\n\n"
                "- Teens (13-18): 8-10 hours\n- Adults (18-64): **7-9 hours**\n- Older adults (65+): 7-8 hours\n\n"
                "Quality matters as much as quantity. Tips: consistent schedule, cool dark room, no screens 1 hour before bed, no caffeine after 2 PM.", [])
        if any(x in p for x in ["lose weight","weight loss","burn fat","diet tip"]):
            return R("⚖️ Weight loss fundamentally comes down to **calories in < calories out**.\n\n"
                "**Evidence-based tips:**\n"
                "1. Track what you eat for a week — awareness alone helps\n"
                "2. Eat more protein — it keeps you full longer\n"
                "3. Strength training — builds muscle which burns more calories at rest\n"
                "4. Sleep 7-9 hours — poor sleep increases hunger hormones\n"
                "5. Walk more — 10,000 steps/day burns ~400-500 extra calories\n"
                "6. Drink water before meals — reduces overeating\n"
                "7. Be patient — sustainable loss is 0.5-1 kg/week\n\n"
                "⚠️ I am an AI, not a doctor. Consult a healthcare professional for personalized advice.", [])

        # Quotes
        if any(x in p for x in ["quote","wisdom","wise words","inspirational"]):
            quotes = [
                "*\"The only way to do great work is to love what you do.\"* — Steve Jobs",
                "*\"First, solve the problem. Then, write the code.\"* — John Johnson",
                "*\"Talk is cheap. Show me the code.\"* — Linus Torvalds",
                "*\"The best time to plant a tree was 20 years ago. The second best time is now.\"* — Chinese Proverb",
                "*\"Simplicity is the ultimate sophistication.\"* — Leonardo da Vinci",
                "*\"It does not matter how slowly you go as long as you do not stop.\"* — Confucius",
                "*\"The greatest glory in living lies not in never falling, but in rising every time we fall.\"* — Nelson Mandela",
                "*\"In the middle of difficulty lies opportunity.\"* — Albert Einstein",
                "*\"Code is like humor. When you have to explain it, it's bad.\"* — Cory House",
                "*\"Any fool can write code that a computer can understand. Good programmers write code that humans can understand.\"* — Martin Fowler",
            ]
            return R(quotes[hash(prompt) % len(quotes)], [])

        # Study tips / productivity
        if any(x in p for x in ["study tip","how to study","learn faster","be productive","productivity tip","focus","concentrate","procrastinat"]):
            return R("📚 **Proven study & productivity techniques:**\n\n"
                "1. **Pomodoro:** Work 25 min, break 5 min. Repeat 4x, then long break.\n"
                "2. **Active recall:** Don't just re-read. Close the book and try to recall. Test yourself.\n"
                "3. **Spaced repetition:** Review material at increasing intervals (1 day, 3 days, 7 days, 14 days).\n"
                "4. **Feynman Technique:** Explain the concept as if teaching a 5-year-old. If you can't, you don't understand it.\n"
                "5. **2-minute rule:** If a task takes < 2 minutes, do it now.\n"
                "6. **Eat the frog:** Do the hardest task first thing in the morning.\n"
                "7. **Remove distractions:** Phone in another room. Website blockers. Clean desk.\n"
                "8. **Sleep:** Your brain consolidates learning during sleep. Don't skip it.", [])

        # Interview / Career
        if any(x in p for x in ["job interview","interview tip","prepare for interview","career advice","get hired","resume tip"]):
            return R("💼 **Interview preparation:**\n\n"
                "**Before:**\n"
                "- Research the company thoroughly — products, culture, recent news\n"
                "- Practice the STAR method (Situation, Task, Action, Result) for behavioral questions\n"
                "- Prepare 3-5 questions to ask the interviewer\n"
                "- For coding interviews: grind LeetCode mediums, focus on arrays, trees, graphs, dynamic programming\n\n"
                "**During:**\n"
                "- Think out loud — interviewers want to see your thought process\n"
                "- Clarify requirements before jumping into code\n"
                "- Start with brute force, then optimize\n"
                "- Ask about edge cases\n\n"
                "**Common questions:**\n"
                "- Tell me about yourself (2-min elevator pitch)\n"
                "- Why this company? (show genuine interest)\n"
                "- Biggest challenge? (show growth and problem-solving)", [])

        # Languages
        if any(x in p for x in ["translate","how to say","how do you say","translation"]):
            common = {"hello":{"spanish":"Hola","french":"Bonjour","german":"Hallo","japanese":"こんにちは (Konnichiwa)","korean":"안녕하세요 (Annyeonghaseyo)","chinese":"你好 (Nǐ hǎo)","hindi":"नमस्ते (Namaste)","arabic":"مرحبا (Marhaba)","italian":"Ciao","portuguese":"Olá","russian":"Привет (Privet)"},
                "thank you":{"spanish":"Gracias","french":"Merci","german":"Danke","japanese":"ありがとう (Arigatou)","korean":"감사합니다 (Gamsahamnida)","chinese":"谢谢 (Xièxiè)","hindi":"धन्यवाद (Dhanyavaad)","arabic":"شكراً (Shukran)","italian":"Grazie","portuguese":"Obrigado/a","russian":"Спасибо (Spasibo)"},
                "goodbye":{"spanish":"Adiós","french":"Au revoir","german":"Auf Wiedersehen","japanese":"さようなら (Sayōnara)","korean":"안녕히 가세요","chinese":"再见 (Zàijiàn)","hindi":"अलविदा (Alvida)","italian":"Arrivederci","portuguese":"Adeus","russian":"До свидания (Do svidaniya)"}}
            for word, translations in common.items():
                if word in p:
                    t = f"**\"{word.title()}\"** in different languages:\n\n"
                    for lang, trans in translations.items():
                        t += f"- **{lang.title()}:** {trans}\n"
                    return R(t, [])
            return R("I know common translations for greetings like \"hello\", \"thank you\", and \"goodbye\" in 11+ languages. For full translation, I recommend [DeepL](https://deepl.com) or Google Translate.", [])

        # ═══════════════════════════════════════════
        # IDENTITY & SOCIAL
        # ═══════════════════════════════════════════

        if any(x in p for x in ["who are you","what are you","your name","about you","what can you do"]):
            t = f"I am **UloLM** — running **{self.config.active_model}** ({self.config.backend} backend).\n\n"
            t += "I can answer questions, build projects, write code, solve math, tell jokes, recommend movies, explain science, give life advice, and remember your workspace across sessions."
            if ctx["has"]: t += f"\n\nActive project: **{ctx['project_name']}** ({len(ctx['files'])} files)"
            return R(t, [])

        if any(x == p for x in ["hi","hey","yo","sup","hello","hola","hii","hiii"]) or any(x in p for x in ["good morning","good evening","good afternoon","good night","howdy","what's up","whats up"]):
            t = "Hey! 👋 "
            if ctx["has"]:
                t += f"You are in **{ctx['project_name']}**"
                if ctx["rp"]: t += f" — last working on: *{', '.join(ctx['rp'])}*"
                t += "."
            else:
                t += "What's on your mind?"
            return R(t, [])

        if any(x in p for x in ["how are you","how r u","how r you","how you doing","how's it going","how is it going"]):
            return R("I'm doing great, thanks! Ready to help with whatever you need — coding, questions, ideas, or just a chat. 😊", [])

        if any(x in p for x in ["thanks","thank you","thx","appreciate"]):
            t = "You're welcome! 😊"
            if ctx["rt"]: t += f" Next on your roadmap: *{ctx['rt'][0]}*."
            return R(t, [])
        if any(x in p for x in ["bye","goodbye","see you","gotta go","gtg","i'm leaving"]):
            t = "See you! 👋"
            if ctx["has"]: t += f" **{ctx['project_name']}** is saved — I'll remember everything."
            return R(t, [])
        if any(x in p for x in ["nice","awesome","great","cool","perfect","good job","well done","amazing","love it"]):
            return R("Glad you like it! 😄 What's next?", [])
        if any(x in p for x in ["you're wrong","that's wrong","incorrect","not right","bad answer"]):
            return R("I appreciate the correction! I'm a built-in knowledge system so I can make mistakes. If you tell me what's wrong, I'll learn from it for next time.", [])
        if any(x in p for x in ["i love you","love you","marry me"]):
            return R("That's sweet! 😊 I'm flattered, but I'm just a local AI assistant. I can, however, help you write a love letter if you need one! ✉️", [])
        if any(x in p for x in ["are you human","are you real","are you alive","are you sentient","do you have feelings"]):
            return R("I'm an AI — I process text and generate responses based on patterns. I don't have consciousness, feelings, or subjective experience. But I'm designed to be as helpful and natural to talk to as possible.", [])

        # ═══════════════════════════════════════════
        # SMART FALLBACK — V2 Infinite Knowledge (Wikipedia)
        # ═══════════════════════════════════════════

        # Try definitions lookup one more time with looser matching
        for key in defs:
            if key in p:
                return R(defs[key], [])

        prompt_trimmed = prompt.strip()
        words = prompt_trimmed.split()
        wc = len(words)
        
        # Extract a potential query by stripping common prefixes
        search_query = prompt_trimmed.lower()
        for prefix in ["what is", "who is", "what are", "who are", "tell me about", "explain", "history of"]:
            if search_query.startswith(prefix):
                search_query = search_query[len(prefix):].strip(" ?")
                break
        search_query = search_query.strip(" ?")

        if search_query and len(search_query) > 2:
            wiki_answer = self._search_wikipedia(search_query)
            if wiki_answer:
                return R(wiki_answer, [])

        # If Wikipedia fails or query is too short/generic
        if wc <= 2:
            topic = prompt_trimmed.title()
            t = f"**{topic}** — that is a broad topic. Here is what I can tell you:\n\n"
            t += f"I have built-in knowledge and internet lookup capabilities. Try asking something specific like:\n"
            t += f"- *\"What is {prompt_trimmed}?\"*\n"
            t += f"- *\"Tell me about {prompt_trimmed}\"*\n"
            t += f"- *\"How does {prompt_trimmed} work?\"*"
            return R(t, [])

        # Medium/Long — acknowledge and be honest
        t = f"I read your message carefully. Here is my honest take:\n\n"
        t += f"I searched my built-in knowledge base and Wikipedia, but couldn't find a confident answer for *\"{prompt_trimmed}\"*.\n\n"
        t += f"**To unlock unlimited reasoning and logic:**\n"
        t += f"1. Install Ollama from [ollama.com](https://ollama.com)\n"
        t += f"2. Run `ollama pull llama3`\n"
        t += f"3. Type `/config backend ollama` here\n\n"
        t += f"Then I can answer literally anything with full AI capabilities."
        if ctx["has_project"]:
            t += f"\n\n📂 Your project **{ctx['project_name']}** ({len(ctx['files'])} files) will stay loaded."
        return R(t, [])

    def _parse_response(self, content: str) -> ModelResponse:
        tools, text = [], content
        st, et = "<tool_call>", "</tool_call>"
        while st in text and et in text:
            si, ei = text.find(st), text.find(et)
            try: tools.append(json.loads(text[si+len(st):ei].strip()))
            except: pass
            text = text[:si] + text[ei+len(et):]
        return ModelResponse(text.strip(), tools)
