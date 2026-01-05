from typing import List, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingRecallManager:
    def __init__(self):
        pass
    
    def weather_type_match_recall(self, text: str, weather_type: List[str]) -> float:
        """
        把模板库弄成一个json 然后我们这里直接做label匹配(基于天气类型) 返回得分最高的1-2个模板
        """
        raise NotImplementedError
    
    def embedding_recall(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        基于embedding召回
        """
        raise NotImplementedError
    
    def bm25_recall(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        基于bm25算法召回
        """
        raise NotImplementedError
    
    def embedding_bm25_recall(self, history_text: str, forecast_text: str) -> str:
        """
        embedding + bm25 召回 做后处理排序
        """
        raise NotImplementedError