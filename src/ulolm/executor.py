import os
from pathlib import Path
from typing import Dict, Any

class WorkspaceExecutor:
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()

    def is_safe_path(self, target_path: str) -> bool:
        """Enforces filesystem sandboxing by blocking path traversal attempts."""
        try:
            target = (self.workspace / target_path).resolve()
            # The resolved path must start with the workspace root directory
            return target.parts[:len(self.workspace.parts)] == self.workspace.parts
        except Exception:
            return False

    def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Executes tool requests (e.g. write_file) safely."""
        name = tool_call.get("name")
        params = tool_call.get("parameters", {})
        
        if name == "write_file":
            path = params.get("path")
            content = params.get("content", "")
            
            if not path:
                return {"status": "error", "message": "Missing 'path' parameter."}
                
            if not self.is_safe_path(path):
                return {
                    "status": "error", 
                    "message": f"Security Exception: Path traversal blocked. '{path}' is outside workspace."
                }
                
            try:
                full_path = (self.workspace / path).resolve()
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                return {
                    "status": "success", 
                    "filepath": path, 
                    "bytes_written": len(content.encode('utf-8'))
                }
            except Exception as e:
                return {"status": "error", "message": f"Failed to write file: {str(e)}"}
                
        return {"status": "error", "message": f"Unknown tool execution: {name}"}
