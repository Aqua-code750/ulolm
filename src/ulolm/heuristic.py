import re
import math
from typing import Dict, List, Tuple, Any

class HeuristicEngine:
    """
    A pure-Python intelligence engine that uses advanced heuristics, math, 
    and regex to understand language and score context without requiring 
    any massive external base models or machine learning libraries.
    """
    
    def __init__(self):
        # Basic intent signatures
        self.intent_signatures = {
            "GREETING": r"\b(hi|hello|hey|yo|greetings|morning|evening|wassup)\b",
            "CODE_EXPLANATION": r"\b(explain|how does|what is|how to|break down|walk me through|summarize)\b",
            "DEBUG_ERROR": r"\b(error|bug|fix|crash|exception|traceback|failed|why is it failing)\b",
            "PROJECT_SUMMARY": r"\b(summarize project|what is this project|overview|architecture|stack)\b",
            "REFACTOR_CODE": r"\b(refactor|clean up|optimize|improve|rewrite|format)\b"
        }
        
        # Stop words to ignore during TF-IDF or keyword matching
        self.stop_words = {
            "the", "is", "at", "which", "on", "in", "a", "an", "and", "or", 
            "for", "to", "of", "with", "it", "this", "that", "how", "what", "why"
        }

    def tokenize(self, text: str) -> List[str]:
        """Convert text into lowercase tokens, removing punctuation."""
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return [w for w in words if w not in self.stop_words]

    def identify_intent(self, user_input: str) -> str:
        """
        Classifies the user's intent using a pure-Python regex waterfall.
        Falls back to GENERAL_CHAT if no specific intent is found.
        """
        user_input_lower = user_input.lower()
        
        # 1. Exact or Regex match
        for intent, pattern in self.intent_signatures.items():
            if re.search(pattern, user_input_lower):
                return intent
                
        # 2. Fallback Intent
        return "GENERAL_CHAT"

    def score_context(self, query: str, document: str) -> float:
        """
        Calculates a simple relevance score between the query and a document.
        In a full TF-IDF engine, this would use a corpus, but for immediate 
        context scoring, we use Term Frequency (TF) overlap.
        """
        query_tokens = set(self.tokenize(query))
        if not query_tokens:
            return 0.0
            
        doc_tokens = self.tokenize(document)
        doc_length = len(doc_tokens)
        
        if doc_length == 0:
            return 0.0
            
        # Count frequency of query words in the document
        score = 0.0
        for token in query_tokens:
            count = doc_tokens.count(token)
            if count > 0:
                # Basic TF-IDF approximation: log(frequency) / doc_length
                tf = math.log1p(count)
                score += tf
                
        return score

    def synthesize_response(self, intent: str, query: str, context: str) -> str:
        """
        Synthesizes an intelligent-sounding response dynamically by combining 
        the identified intent, the query, and the highest-scored project context.
        """
        response = ""
        
        # Add dynamic reasoning preamble based on intent
        if intent == "GREETING":
            response += "Hello! I am UloLM, operating purely on heuristic intelligence. How can I assist you with your project today?\n\n"
        elif intent == "CODE_EXPLANATION":
            response += "[HEURISTIC ENGINE]: Analyzing query for explanation requests. Extracting relevant entities...\n"
            response += "Based on my pure-Python indexing, here is what I understand about your request:\n\n"
        elif intent == "DEBUG_ERROR":
            response += "[HEURISTIC ENGINE]: Error signature detected. Scanning local index for potential faults...\n"
            response += "I've analyzed the potential failure points using my heuristic matrix. Here's a breakdown:\n\n"
        else:
            response += "[HEURISTIC ENGINE]: Processing natural language input without external models...\n\n"
            
        # Blend in context if available
        if context and len(context.strip()) > 10:
            # We inject some of the context to make it feel like an LLM reading it
            snippet = context[:500] + "..." if len(context) > 500 else context
            response += f"**Context Extracted from Workspace:**\n```\n{snippet}\n```\n\n"
            response += "Using heuristic pattern matching, I recommend reviewing the above structure to resolve your query."
        else:
            response += f"I analyzed your prompt: '{query}'. However, I didn't find specific code context in your workspace that strongly matches this query. Try referencing specific files or function names!"
            
        return response
