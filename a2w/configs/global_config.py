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
            
            # API服务配置
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("API_PORT", "8001")),
            "api_prefix": os.getenv("API_PREFIX", ""),
            
            # 调试配置
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "verbose": os.getenv("VERBOSE", "false").lower() == "true",

            # db配置
            "db_host": os.getenv("DATABASE_HOST", "127.0.0.1"),
            "db_port": int(os.getenv("DATABASE_PORT", "1433")),
            "db_name": os.getenv("DATABASE_NAME", "A2W_YiChun"),
            "db_username": os.getenv("DATABASE_USERNAME", "sa"),
            "db_password": os.getenv("DATABASE_PASSWORD", "YourStrong!Passw0rd"),
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
                }
            ],
            "cache_seed": None,
        }
        return config
    
    def validate(self) -> bool:
        required_keys = ["openai_api_key", "default_schema_file"]
        
        for key in required_keys:
            if not self.get(key):
                return False
        
        return True
