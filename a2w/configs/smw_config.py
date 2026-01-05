import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class SmwConfig:
    def __init__(self, env_file: Optional[str] = None):
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        return {
            # smw weather classily result json
            "smw_weather_classify_path": os.getenv("SMW_WEATHER_CLASSIFY_PATH", ""),
            # basecase data save path
            "badcase_data_path": os.getenv("BADCASE_DATA_PATH", ""),
            
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def __repr__(self):
        return f"SmwConfig({self._config})"

    def __str__(self):
        return f"SmwConfig: {self._config}"