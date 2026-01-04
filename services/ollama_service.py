"""
Ollama Service - Manages connection to local Ollama instance
"""
import requests
from typing import List, Dict, Optional, Generator
import config


class OllamaService:
    """Service for interacting with Ollama API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
    
    def check_connection(self) -> Dict:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return {"connected": True, "message": "Ollama is running"}
            else:
                return {"connected": False, "message": f"Ollama returned status {response.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"connected": False, "message": "Cannot connect to Ollama. Make sure it's running."}
        except requests.exceptions.Timeout:
            return {"connected": False, "message": "Connection to Ollama timed out"}
        except Exception as e:
            return {"connected": False, "message": str(e)}
    
    def get_available_models(self) -> List[Dict]:
        """Fetch all installed Ollama models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return [{
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "size_formatted": self._format_size(model.get("size", 0)),
                    "modified_at": model.get("modified_at", ""),
                    "digest": model.get("digest", "")[:12] if model.get("digest") else "",
                    "details": model.get("details", {})
                } for model in models]
            return []
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get detailed information about a specific model"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting model info: {e}")
            return None
    
    def generate(self, prompt: str, model: str = None, 
                 system_prompt: str = None,
                 temperature: float = 0.7,
                 context_length: int = 4096,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 stream: bool = False) -> str:
        """Generate a response using the specified model"""
        model = model or config.DEFAULT_MODEL
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_ctx": context_length,
                "top_p": top_p,
                "top_k": top_k
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Longer timeout for generation
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                return f"Error: Ollama returned status {response.status_code}"
        except requests.exceptions.Timeout:
            return "Error: Generation timed out. Try a shorter prompt or faster model."
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_stream(self, prompt: str, model: str = None,
                        system_prompt: str = None,
                        temperature: float = 0.7,
                        context_length: int = 4096,
                        top_p: float = 0.9,
                        top_k: int = 40) -> Generator[str, None, None]:
        """Generate a streaming response"""
        model = model or config.DEFAULT_MODEL
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": context_length,
                "top_p": top_p,
                "top_k": top_k
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=120
            )
            
            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def pull_model(self, model_name: str) -> Generator[Dict, None, None]:
        """Download a new model from Ollama registry"""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=3600  # 1 hour timeout for large models
            )
            
            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    yield data
        except Exception as e:
            yield {"error": str(e)}
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error deleting model: {e}")
            return False
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"


# Singleton instance
ollama_service = OllamaService()
