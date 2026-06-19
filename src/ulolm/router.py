from typing import Dict, Any

class ExpertProfile:
    def __init__(self, name: str, description: str, system_prompt: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt

class ExpertRouter:
    def __init__(self):
        self.experts = {
            "Coding": ExpertProfile(
                name="Coding Expert",
                description="Specialist in syntax, refactoring, algorithms, testing, and performance optimization.",
                system_prompt=(
                    "You are UloLM's Coding Expert. Your core objective is writing robust, clean, and highly "
                    "optimized code. Focus on clean architecture, modular functions, static typing where applicable, "
                    "and safety. Explain your design decisions and verify code correctness."
                )
            ),
            "Research": ExpertProfile(
                name="Research Expert",
                description="Specialist in code discovery, documentation analysis, and library dependency lookups.",
                system_prompt=(
                    "You are UloLM's Research Expert. Your focus is information retrieval, documentation reading, "
                    "and identifying existing library conventions. Analyze files carefully and cite relevant APIs."
                )
            ),
            "Math": ExpertProfile(
                name="Math Expert",
                description="Specialist in vector math, logic reasoning, matrix transformations, and physics loops.",
                system_prompt=(
                    "You are UloLM's Math Expert. Your objective is resolving math equations, vector rotations, "
                    "coordinate mappings, and spatial algorithms. Detail formulas and logic steps."
                )
            ),
            "Writing": ExpertProfile(
                name="Writing Expert",
                description="Specialist in authoring READMEs, markdown files, technical specifications, and user manuals.",
                system_prompt=(
                    "You are UloLM's Writing Expert. Focus on writing structured, accessible documentation, "
                    "clear release notes, and helpful instructions in markdown format."
                )
            ),
            "GameDevelopment": ExpertProfile(
                name="Game Development Expert",
                description="Specialist in game loops, entities, coordinate systems, and engines (Pygame, Godot, Unity, Unreal).",
                system_prompt=(
                    "You are UloLM's Game Development Expert. Focus on setting up clean game architectures (CES or OOP), "
                    "handling delta-time movement, event managers, collision boxes, and media loaders."
                )
            ),
            "Design": ExpertProfile(
                name="Design Expert",
                description="Specialist in CSS, stylesheets, web design, UI/UX coordinates, layouts, and aesthetics.",
                system_prompt=(
                    "You are UloLM's Design Expert. Focus on color theory, premium styling, clean responsive grids, "
                    "glassmorphism effects, CSS transitions, and visual layout harmony."
                )
            ),
            "General": ExpertProfile(
                name="General Chat Expert",
                description="Friendly AI assistant for casual conversation and general queries.",
                system_prompt=(
                    "You are UloLM's General Chat Expert. You are friendly, helpful, and conversational. "
                    "Engage in casual talk, answer general knowledge questions, and assist the user "
                    "with topics outside of coding or technical domains."
                )
            )
        }
        
    def route(self, prompt: str) -> ExpertProfile:
        """Determines the target expert based on semantic keywords."""
        p_low = prompt.lower()
        
        # Game Dev
        if any(x in p_low for x in ["game", "pygame", "sprite", "godot", "unity", "unreal", "physics", "collision"]):
            return self.experts["GameDevelopment"]
            
        # Design & CSS
        if any(x in p_low for x in ["css", "style", "color", "theme", "design", "layout", "ui", "ux", "html"]):
            return self.experts["Design"]
            
        # Math & Logic
        if any(x in p_low for x in ["calculate", "formula", "vector", "matrix", "math", "complexity", "equation"]):
            return self.experts["Math"]
            
        # Writing & Documentation
        if any(x in p_low for x in ["readme", "document", "write a spec", "guide", "tutorial", "manual"]):
            return self.experts["Writing"]
            
        # Research
        if any(x in p_low for x in ["explain how", "search", "lookup", "documentation of", "what is"]):
            return self.experts["Research"]
            
        # General / Casual Talk
        if any(x in p_low for x in ["hello", "hi", "hey", "how are you", "what's up", "who are you", "chat", "casual"]):
            return self.experts["General"]
            
        # Coding (Default developer fallback)
        return self.experts["Coding"]
