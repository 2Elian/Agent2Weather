import os
import json
import docx
from enum import Enum
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import re
from pathlib import Path
import asyncio
from datetime import datetime

# 清除代理设置
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

class WeatherType(Enum):
    # 降水类
    LIGHT_RAIN = "小雨"
    MODERATE_RAIN = "中雨"
    HEAVY_RAIN = "大雨"
    STORM_RAIN = "暴雨"
    HEAVY_STORM_RAIN = "大暴雨"
    EXTREME_STORM_RAIN = "特大暴雨"
    FREEZING_RAIN = "冻雨"
    SNOW = "雪"
    SLEET = "雨夹雪"
    HAIL = "冰雹"
    
    # 温度类
    EXTREME_HEAT = "极端高温"
    HIGH_TEMP = "高温"
    LOW_TEMP = "低温"
    SEVERE_COLD = "严寒"
    FROST = "霜冻"
    
    # 风类
    BREEZE = "微风"
    MODERATE_WIND = "和风"
    FRESH_WIND = "清风"
    STRONG_WIND = "强风"
    GALE = "大风"
    SEVERE_GALE = "烈风"
    STORM = "狂风"
    HURRICANE = "飓风"
    
    # 能见度类
    HAZE = "轻雾"
    MIST = "雾"
    DENSE_FOG = "浓雾"
    HEAVY_FOG = "大雾"
    DENSE_SMOG = "浓雾霾"
    
    # 湿度类
    HUMID = "潮湿"
    DRY = "干燥"
    
    # 组合/特殊类
    SUNNY_COLD = "晴冷"
    WARM_HUMID = "闷热"
    WINDY_RAIN = "风雨"
    THUNDERSTORM = "雷暴"
    SANDSTORM = "沙尘暴"
    TYPHOON = "台风"
    GENERAL = "一般天气"

class WeatherTextClassifier:
    def __init__(self):
        """初始化大模型分类器"""
        print("正在初始化大模型连接...")
        try:
            self.llm = ChatOpenAI(
                model="qwen30b",
                api_key="NuistMathAutoModelForCausalLM",
                base_url="http://172.16.107.15:23333/v1",
                temperature=0.2,
                timeout=120.0,
                max_retries=1
            )
            print("✓ 大模型连接成功")
        except Exception as e:
            print(f"✗ 大模型连接失败: {e}")
            raise
        
        # 预定义类别列表
        self.valid_categories = [member.value for member in WeatherType]
        
        # 构建prompt
        self.prompt_template, self.categories_text = self._build_prompt_template()
    
    def _build_prompt_template(self) -> str:
        """构建分类prompt"""
        categories_text = "\n".join([f"- {cat}" for cat in self.valid_categories])
        
        return """
# 角色与任务
你是一名资深气象分析专家，负责对输入的气象文本进行精准分类。你的核心任务是根据给定的文本内容，将其归类到预定义的天气类别中。

## 天气分类标准（严格遵循）
{categories_text}

## 分析流程
1. **文本理解**：仔细阅读输入文本，提取所有气象相关描述（降水、温度、风力、能见度、湿度等）
2. **特征匹配**：将文本中的气象特征与预定义类别进行精确匹配
3. **类别判断**：确定最符合文本描述的天气类别
4. **验证检查**：
   - 确保类别与文本描述一致
   - 避免过度解读或遗漏明显特征
   - 如文本描述模糊，选择最可能类别

## 输出格式（必须严格遵守）：
{{
  "weather_categories": ["天气类型1", "天气类型2", "天气类型3"]
}}

## 重要提醒
- 输出必须是合法的JSON格式
- weather_categories数组元素必须是上述分类标准中的中文名称
- 如无匹配，返回 ["一般天气"]

# 输入文本：
{input_text}
""" , categories_text
    
    async def classify_text(self, text: str) -> List[str]:
        """使用大模型对文本进行分类"""
        try:
            # 构建prompt
            prompt = self.prompt_template.format(categories_text=self.categories_text, input_text=text)
            
            # 调用大模型
            print(f"正在调用大模型分类...")
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # 提取JSON响应
            result = self._extract_json(response.content)
            print(f"大模型返回: {result}")
            
            # 验证类别
            if "weather_categories" in result:
                categories = self._validate_categories(result["weather_categories"])
                return categories
            else:
                raise
                
        except Exception as e:
            print(f"大模型分类失败: {e}")
            raise
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """从大模型响应中提取JSON"""
        try:
            # 清理响应
            text = response.strip()
            
            # 查找JSON部分
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                return json.loads(json_str)
            else:
                # 如果没有找到JSON对象，尝试查找数组
                start = text.find('[')
                end = text.rfind(']')
                if start != -1 and end != -1:
                    json_str = text[start:end+1]
                    categories = json.loads(json_str)
                    return {"weather_categories": categories}
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {response}")
        
        # 如果解析失败，返回默认
        return {"weather_categories": ["一般天气"]}
    
    def _validate_categories(self, categories: List[str]) -> List[str]:
        """验证并清理类别"""
        valid_cats = []
        for cat in categories:
            clean_cat = cat.strip().strip('"').strip("'")
            if clean_cat in self.valid_categories:
                valid_cats.append(clean_cat)
        
        # 去重
        unique_cats = []
        seen = set()
        for cat in valid_cats:
            if cat not in seen:
                seen.add(cat)
                unique_cats.append(cat)
        
        # 如果没有有效类别，返回默认
        if not unique_cats:
            unique_cats = ["一般天气"]
        
        # 限制最多3个
        return unique_cats[:3]

def read_docx_files(directory_path: str) -> Dict[str, str]:
    """读取docx文件，一个文件为一条数据"""
    directory = Path(directory_path)
    if not directory.exists():
        raise ValueError(f"目录不存在: {directory_path}")
    
    file_contents = {}
    
    # 遍历所有docx文件
    for file_path in directory.glob("*.docx"):
        try:
            print(f"正在读取文件: {file_path.name}")
            
            # 读取整个文件内容（不分割段落）
            doc = docx.Document(file_path)
            full_text = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:  # 只保留非空段落
                    full_text.append(text)
            
            # 合并为一条数据
            file_contents[file_path.name] = "\n".join(full_text)
            print(f"✓ 读取成功，文本长度: {len(file_contents[file_path.name])} 字符")
            
        except Exception as e:
            print(f"✗ 读取文件 {file_path.name} 失败: {e}")
    
    return file_contents

async def main():
    classifier = WeatherTextClassifier()
    input_dir = r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\pre_work\label_build\docx"
    output_file = r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\data\sm\weather_classification_results.json"
    all_file_contents = read_docx_files(input_dir)

    all_results = []
    processed_count = 0
    error_count = 0
    
    for filename, full_text in all_file_contents.items():
        try:
            categories = await classifier.classify_text(full_text)
            result_entry = {
                "file_name": filename,
                "text_content": full_text,
                "weather_categories": categories,
                "processed_time": datetime.now().isoformat(),
                "text_length": len(full_text)
            }
            
            all_results.append(result_entry)
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            error_entry = {
                "file_name": filename,
                "text_content": full_text[:500] + "..." if len(full_text) > 500 else full_text,
                "weather_categories": ["一般天气"],
                "error": str(e),
                "processed_time": datetime.now().isoformat()
            }
            all_results.append(error_entry)
    category_stats = {}
    for result in all_results:
        for category in result.get("weather_categories", []):
            category_stats[category] = category_stats.get(category, 0) + 1
    output_data = {
        "metadata": {
            "total_files": len(all_results),
            "successful": processed_count,
            "errors": error_count,
            "processing_date": datetime.now().isoformat(),
            "category_statistics": category_stats
        },
        "results": all_results
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    simple_output = []
    for result in all_results:
        simple_output.append({
            "category": result["weather_categories"][0] if result["weather_categories"] else "一般天气",
            "context": result["text_content"]
        })
    
    simple_output_file = output_file.replace(".json", "_simple.json")
    with open(simple_output_file, 'w', encoding='utf-8') as f:
        json.dump(simple_output, f, ensure_ascii=False, indent=2)
if __name__ == "__main__":
    asyncio.run(main())