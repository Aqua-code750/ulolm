import json
import re
import random as _random
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List
from .heuristic import HeuristicEngine

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
            return self._query_native(prompt, system_context)

    def _query_ollama(self, prompt: str, system_context: str) -> ModelResponse:
        url = f"{self.config.ollama_url}/api/chat"
        model_name = "codellama" if self.config.active_model == "UloLMBase" else "phi3"
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

    def _parse_response(self, text: str) -> ModelResponse:
        import re
        import json
        tools = []
        json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "name" in item:
                            tools.append(item)
                elif isinstance(data, dict) and "name" in data:
                    tools.append(data)
                elif isinstance(data, dict) and "tools_to_call" in data:
                    tools.extend(data["tools_to_call"])
            except Exception:
                pass
        return ModelResponse(text, tools)

    def _pc(self, system_context: str) -> dict:
        """Parse context from system_context string."""
        ctx = {"project_name":"","tech_stack":"","files":[],"symbols":[],"roadmap_completed":[],"rp":[],"rt":[],"has":False}
        if not system_context:
            return ctx
        in_files = in_symbols = False
        for line in system_context.splitlines():
            s = line.strip()
            if s.startswith("Project Name:"):
                ctx["project_name"] = s.split(":", 1)[1].strip()
                if ctx["project_name"] and ctx["project_name"] != "Unnamed":
                    ctx["has"] = True
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
                if v and v != "None": ctx["rp"] = [x.strip() for x in v.split(",")]
            elif s.startswith("- Todo:"):
                v = s.split(":", 1)[1].strip()
                if v and v != "None": ctx["rt"] = [x.strip() for x in v.split(",")]
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

    def _query_native(self, prompt: str, system_context: str) -> ModelResponse:
        from .memory import ProjectMemory
        
        # Initialize the heuristic engine
        engine = HeuristicEngine()
        
        # 1. Identify Intent
        intent = engine.identify_intent(prompt)
        
        # 2. Extract context using TF-IDF mathematical scoring
        memory = ProjectMemory(self.config.workspace_path)
        context_str = memory.search_context(prompt, engine)
        
        # 2.5 Dynamic Cloud Retrieval
        if intent == "KNOWLEDGE_QUERY" or intent == "GENERAL_CHAT":
            # Extract the core topic to search
            import re
            topic = prompt
            topic_match = re.search(r'(?:who is|what is|tell me about|when did|how did|history of|explain the concept of)\s+(.*)', prompt.lower())
            if topic_match:
                topic = topic_match.group(1).strip('? ')
            else:
                topic = " ".join(engine.tokenize(prompt))
                
            if topic:
                wiki_data = self._search_wikipedia(topic)
                if wiki_data:
                    context_str = wiki_data + "\n\n" + context_str
                    intent = "KNOWLEDGE_QUERY" # Upgrade intent if we found data
        
        # 3. Synthesize the final heuristic response
        response_text = engine.synthesize_response(intent, prompt, context_str)
        
        return ModelResponse(response_text, [])
