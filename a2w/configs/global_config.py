import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class GlobalConfig:
    def __init__(self, env_file: Optional[str] = None):
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        return {
            # llm
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "openai_api_base": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            "model_name": os.getenv("MODEL_NAME", "gpt-4"),
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "120")),
            
            # Agent 配置
            "max_consecutive_auto_reply": int(os.getenv("MAX_CONSECUTIVE_AUTO_REPLY", "10")),
            "max_round": int(os.getenv("MAX_ROUND", "20")),
            
            # API 配置
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "300")), 
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("API_PORT", "8001")),
            
            # 调试配置
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "verbose": os.getenv("VERBOSE", "false").lower() == "true",

            # db配置
            
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
    
    def get_llm_config(self) -> Dict[str, Any]:
        api_base = self.get("openai_api_base")   
        config = {
            "config_list": [
                {
                    "model": self.get("model_name"),
                    "api_key": self.get("openai_api_key"),
                    "base_url": api_base,
                    "timeout": self.get("llm_timeout", 300),
                }
            ],
            "timeout": self.get("llm_timeout", 300),
            "cache_seed": None,
        }
        return config
    
    def validate(self) -> bool:
        required_keys = ["openai_api_key", "default_schema_file"]
        
        for key in required_keys:
            if not self.get(key):
                return False
        
        return True
