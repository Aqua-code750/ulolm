import os
import sqlite3
import hashlib
import json
import ast
from pathlib import Path
from typing import Dict, List, Any

class ProjectMemory:
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.ulolm_dir = self.workspace / ".ulolm"
        self.db_path = self.ulolm_dir / "index.db"
        self.state_path = self.ulolm_dir / "project_state.json"
        
    def initialize(self):
        """Initializes the memory folders and SQLite index database."""
        self.ulolm_dir.mkdir(parents=True, exist_ok=True)
        
        # Create SQLite database schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                filepath TEXT PRIMARY KEY,
                last_modified REAL,
                sha256 TEXT,
                content_summary TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT,
                symbol_name TEXT,
                symbol_type TEXT,
                start_line INTEGER,
                end_line INTEGER,
                docstring TEXT,
                FOREIGN KEY(filepath) REFERENCES files(filepath) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize default project state if missing
        if not self.state_path.exists():
            default_state = {
                "project_name": self.workspace.name,
                "version": "0.1.0",
                "tech_stack": {
                    "language": "Unknown",
                    "version": "",
                    "libraries": []
                },
                "architecture": {
                    "pattern": "Undetermined",
                    "entrypoint": "",
                    "key_components": []
                },
                "rules_and_conventions": [],
                "roadmap": {
                    "completed": [],
                    "in_progress": [],
                    "todo": []
                }
            }
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(default_state, f, indent=4)

    def scan_and_sync(self) -> List[str]:
        """Scans workspace directory, compares hashes, and updates SQLite index."""
        if not self.db_path.exists():
            self.initialize()
            
        modified_files = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fetch existing indexed files
        cursor.execute("SELECT filepath, sha256 FROM files")
        indexed_files = dict(cursor.fetchall())
        
        current_files = set()
        
        # Walk directory
        for root, dirs, files in os.walk(self.workspace):
            # Exclude folders
            if ".ulolm" in root or ".git" in root or "__pycache__" in root or "node_modules" in root:
                continue
                
            for filename in files:
                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(self.workspace))
                current_files.add(rel_path)
                
                # Check modification stats
                try:
                    mtime = file_path.stat().st_mtime
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                except Exception:
                    continue
                
                # Verify if file needs parsing/updating
                if rel_path not in indexed_files or indexed_files[rel_path] != file_hash:
                    modified_files.append(rel_path)
                    
                    # Update file table
                    cursor.execute("""
                        INSERT OR REPLACE INTO files (filepath, last_modified, sha256, content_summary)
                        VALUES (?, ?, ?, ?)
                    """, (rel_path, mtime, file_hash, f"File updated: {rel_path}"))
                    
                    # Clear previous symbols for this file
                    cursor.execute("DELETE FROM symbols WHERE filepath = ?", (rel_path,))
                    
                    # Parse symbols if python file
                    if filename.endswith(".py"):
                        self._parse_python_symbols(cursor, file_path, rel_path)
                        
        # Delete files that no longer exist
        for rel_path in indexed_files:
            if rel_path not in current_files:
                cursor.execute("DELETE FROM files WHERE filepath = ?", (rel_path,))
                cursor.execute("DELETE FROM symbols WHERE filepath = ?", (rel_path,))
                modified_files.append(rel_path)
                
        conn.commit()
        conn.close()
        return modified_files

    def _parse_python_symbols(self, cursor: sqlite3.Cursor, full_path: Path, rel_path: str):
        """Extracts class and function definitions from python files using AST parser."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(full_path))
                
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node) or ""
                    cursor.execute("""
                        INSERT INTO symbols (filepath, symbol_name, symbol_type, start_line, end_line, docstring)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (rel_path, node.name, "function", node.lineno, node.end_lineno, doc))
                elif isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node) or ""
                    cursor.execute("""
                        INSERT INTO symbols (filepath, symbol_name, symbol_type, start_line, end_line, docstring)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (rel_path, node.name, "class", node.lineno, node.end_lineno, doc))
        except Exception:
            # Skip AST parsing if file contains syntax errors
            pass

    def get_project_state(self) -> Dict[str, Any]:
        """Loads and returns the project state metadata."""
        if not self.state_path.exists():
            self.initialize()
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def get_project_context(self) -> str:
        """Constructs a detailed text summary of the codebase for prompt injection."""
        state = self.get_project_state()
        
        # Load files and symbols list from SQLite
        if not self.db_path.exists():
            return "No project files indexed yet."
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT filepath FROM files")
        files = [r[0] for r in cursor.fetchall()]
        
        cursor.execute("SELECT filepath, symbol_name, symbol_type, docstring FROM symbols")
        symbols = cursor.fetchall()
        conn.close()
        
        context = []
        context.append("=== UloLM PROJECT MEMORY ===")
        context.append(f"Project Name: {state.get('project_name', 'Unnamed')}")
        context.append(f"Target Stack: {json.dumps(state.get('tech_stack', {}))}")
        context.append(f"Architecture Pattern: {state.get('architecture', {}).get('pattern', 'Unknown')}")
        
        context.append("\nIndexed Files:")
        for f in files:
            context.append(f" - {f}")
            
        if symbols:
            context.append("\nKey Symbols Extracted:")
            for filepath, sym_name, sym_type, doc in symbols:
                doc_snippet = f" // {doc.splitlines()[0]}" if doc else ""
                context.append(f" - [{sym_type.upper()}] {sym_name} in {filepath}{doc_snippet}")
                
        context.append("\nRoadmap:")
        roadmap = state.get("roadmap", {})
        context.append(f" - Completed: {', '.join(roadmap.get('completed', [])) or 'None'}")
        context.append(f" - In Progress: {', '.join(roadmap.get('in_progress', [])) or 'None'}")
        context.append(f" - Todo: {', '.join(roadmap.get('todo', [])) or 'None'}")
        context.append("============================")
        
        return "\n".join(context)
