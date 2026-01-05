from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, List, Dict, Tuple, Set
from enum import Enum
import datetime
from a2w.utils.logger import setup_logger

logger = setup_logger(name="WeatherClassifier")
class WeatherSeverity(Enum):
    """天气严重程度等级"""
    EXTREME = "极端天气"      # 红色预警
    SEVERE = "严重天气"       # 橙色预警  
    MODERATE = "中等天气"     # 黄色预警
    MILD = "轻度天气"         # 蓝色预警
    GENERAL = "一般天气"      # 无预警

@dataclass
class WeatherMetrics:
    """天气指标数据类"""
    avg_temp: float            # 日平均温度 (°C)
    min_temp: float            # 最低温度 (°C)
    max_temp: float            # 最高温度 (°C)
    precip: float              # 累计降水量 (mm)
    max_wind_speed: float      # 最大风速 (m/s)
    min_visibility: float      # 最小能见度 (m)
    humidity: Optional[float] = None  # 相对湿度 (%)
    pressure: Optional[float] = None  # 气压 (hPa)
    cloud_cover: Optional[float] = None  # 云量 (0-1)
    sunshine_hours: Optional[float] = None  # 日照时数 (h)
    
    # 衍生指标
    @property
    def temperature_range(self) -> float:
        """日温差"""
        return self.max_temp - self.min_temp
    
    @property
    def is_freezing(self) -> bool:
        """是否冰冻(这里需要依据具体情况而定->最低温低于0°C)"""
        return self.min_temp < 0
    
    @property
    def is_high_humidity(self) -> bool:
        """是否高湿"""
        return self.humidity is not None and self.humidity >= 80
    
    @property
    def is_low_humidity(self) -> bool:
        """是否低湿"""
        return self.humidity is not None and self.humidity <= 30


class WeatherType(Enum):
    """完整的天气类型枚举"""
    # 降水类
    LIGHT_RAIN = "小雨"               # 0.1-9.9mm
    MODERATE_RAIN = "中雨"            # 10.0-24.9mm
    HEAVY_RAIN = "大雨"               # 25.0-49.9mm
    STORM_RAIN = "暴雨"               # 50.0-99.9mm
    HEAVY_STORM_RAIN = "大暴雨"       # 100.0-249.9mm
    EXTREME_STORM_RAIN = "特大暴雨"   # ≥250.0mm
    FREEZING_RAIN = "冻雨"           # 冻雨
    SNOW = "雪"                      # 降雪
    SLEET = "雨夹雪"                 # 雨夹雪
    HAIL = "冰雹"                    # 冰雹
    
    # 温度类
    EXTREME_HEAT = "极端高温"         # ≥40°C
    HIGH_TEMP = "高温"               # 35-39.9°C
    LOW_TEMP = "低温"                # ≤0°C
    SEVERE_COLD = "严寒"             # ≤-10°C
    FROST = "霜冻"                   # 霜冻
    
    # 风类
    BREEZE = "微风"                  # 3.4-5.4 m/s
    MODERATE_WIND = "和风"           # 5.5-7.9 m/s
    FRESH_WIND = "清风"             # 8.0-10.7 m/s
    STRONG_WIND = "强风"            # 10.8-13.8 m/s
    GALE = "大风"                   # 13.9-17.1 m/s
    SEVERE_GALE = "烈风"            # 17.2-20.7 m/s
    STORM = "狂风"                  # 20.8-24.4 m/s
    HURRICANE = "飓风"              # ≥24.5 m/s
    
    # 能见度类
    HAZE = "轻雾"                   # 1000-10000m
    MIST = "雾"                     # 500-1000m
    DENSE_FOG = "浓雾"              # 200-500m
    HEAVY_FOG = "大雾"              # 50-200m
    DENSE_SMOG = "浓雾霾"           # <50m
    
    # 湿度类
    HUMID = "潮湿"                  # ≥80%
    DRY = "干燥"                    # ≤30%
    
    # 组合/特殊类
    SUNNY_COLD = "晴冷"             # 晴天低温
    WARM_HUMID = "闷热"             # 高温高湿
    WINDY_RAIN = "风雨"             # 大风降雨
    THUNDERSTORM = "雷暴"           # 雷暴天气
    SANDSTORM = "沙尘暴"           # 沙尘天气
    TYPHOON = "台风"               # 台风天气
    GENERAL = "一般天气"            # 无明显特征


class WeatherClassifier:
    # 降水阈值 (mm)
    PRECIP_THRESHOLDS = {
        WeatherType.LIGHT_RAIN: (0.1, 9.9),
        WeatherType.MODERATE_RAIN: (10.0, 24.9),
        WeatherType.HEAVY_RAIN: (25.0, 49.9),
        WeatherType.STORM_RAIN: (50.0, 99.9),
        WeatherType.HEAVY_STORM_RAIN: (100.0, 249.9),
        WeatherType.EXTREME_STORM_RAIN: (250.0, float('inf'))
    }
    
    # 温度阈值 (°C)
    TEMP_THRESHOLDS = {
        WeatherType.EXTREME_HEAT: (40.0, float('inf')),
        WeatherType.HIGH_TEMP: (35.0, 39.9),
        WeatherType.LOW_TEMP: (float('-inf'), 0.0),
        WeatherType.SEVERE_COLD: (float('-inf'), -10.0),
        WeatherType.FROST: (float('-inf'), 2.0)  # 霜冻通常在2°C以下
    }
    
    # 风速阈值 (m/s) - 蒲福风级
    WIND_THRESHOLDS = {
        WeatherType.BREEZE: (3.4, 5.4),          # 3-4级
        WeatherType.MODERATE_WIND: (5.5, 7.9),   # 4-5级
        WeatherType.FRESH_WIND: (8.0, 10.7),     # 5-6级
        WeatherType.STRONG_WIND: (10.8, 13.8),   # 6-7级
        WeatherType.GALE: (13.9, 17.1),          # 7-8级
        WeatherType.SEVERE_GALE: (17.2, 20.7),   # 8-9级
        WeatherType.STORM: (20.8, 24.4),         # 9-10级
        WeatherType.HURRICANE: (24.5, float('inf'))  # ≥10级
    }
    
    # 能见度阈值 (m)
    VISIBILITY_THRESHOLDS = {
        WeatherType.HAZE: (1000, 10000),
        WeatherType.MIST: (500, 1000),
        WeatherType.DENSE_FOG: (200, 500),
        WeatherType.HEAVY_FOG: (50, 200),
        WeatherType.DENSE_SMOG: (0, 50)
    }

    @staticmethod
    def safe_create_metrics(data: Dict[str, Any]) -> WeatherMetrics:
        try:
            def to_float(value, default=0.0):
                if value is None:
                    return default
                if isinstance(value, Decimal):
                    return float(value)
                try:
                    return float(value)
                except:
                    return default
            min_visibility = data.get("min_visibility")
            if min_visibility in [999999, None]:
                min_visibility = 10000.0
            else:
                min_visibility = to_float(min_visibility, 10000.0)
            humidity = data.get("avg_humidity")
            if humidity in [999999, None]:
                humidity_value = None
            else:
                humidity_value = to_float(humidity)
            return WeatherMetrics(
                avg_temp=to_float(data.get("avg_temp")),
                min_temp=to_float(data.get("min_temp")),
                max_temp=to_float(data.get("max_temp")),
                precip=to_float(data.get("total_precip")),
                max_wind_speed=to_float(data.get("max_wind_speed")),
                min_visibility=min_visibility,
                humidity=humidity_value
            )
        except Exception as e:
            logger.error(f"创建WeatherMetrics失败: {e}, 数据: {data}")
            return WeatherMetrics(
                avg_temp=0.0,
                min_temp=0.0,
                max_temp=0.0,
                precip=0.0,
                max_wind_speed=0.0,
                min_visibility=10000.0,
                humidity=None
            )
    
    @staticmethod
    def classify_stations(stations_data: List[Dict[str, Any]],  season: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        
        for data in stations_data:
            try:
                station_name = data.get("station_name", "未知站点")
                metrics = WeatherClassifier.safe_create_metrics(data)
                weather_types, reason, severity = WeatherClassifier._classify_single(metrics, season)
                suggestions = WeatherClassifier.get_weather_suggestions(weather_types)
                alert = WeatherClassifier.get_weather_alert(weather_types, severity)
                result = {
                    "station_name": station_name,
                    "weather_types": [wt.value for wt in weather_types],
                    "primary_type": weather_types[0].value if weather_types else "一般天气",
                    "reason": reason,
                    "severity": severity.value,
                    "alert": alert,
                    "suggestions": suggestions,
                    "metrics_summary": {
                        "avg_temp": metrics.avg_temp,
                        "precip": metrics.precip,
                        "max_wind_speed": metrics.max_wind_speed,
                        "min_visibility": metrics.min_visibility
                    }
                }
                results.append(result)
                
            except Exception as e:
                raise
        return results

    @staticmethod
    def _classify_single(metrics: WeatherMetrics, season: Optional[str] = None) -> Tuple[List[WeatherType], str, WeatherSeverity]:
        weather_types = []
        reasons = []
        severity_scores = []
        
        # 按降水分类
        precip_type = WeatherClassifier._classify_precipitation(metrics)
        if precip_type:
            weather_types.append(precip_type)
            reasons.append(f"降水量: {metrics.precip:.1f}mm")
            severity_scores.append(WeatherClassifier._get_precip_severity(precip_type))
        
        # 温度分类
        temp_types = WeatherClassifier._classify_temperature(metrics, season)
        weather_types.extend(temp_types)
        for temp_type in temp_types:
            if temp_type == WeatherType.EXTREME_HEAT:
                reasons.append(f"极端高温: {metrics.max_temp:.1f}℃")
            elif temp_type == WeatherType.HIGH_TEMP:
                reasons.append(f"高温: {metrics.max_temp:.1f}℃")
            elif temp_type == WeatherType.LOW_TEMP:
                reasons.append(f"低温: {metrics.min_temp:.1f}℃")
            elif temp_type == WeatherType.SEVERE_COLD:
                reasons.append(f"严寒: {metrics.min_temp:.1f}℃")
            elif temp_type == WeatherType.FROST:
                reasons.append(f"霜冻: 最低温{metrics.min_temp:.1f}℃")
            severity_scores.append(WeatherClassifier._get_temp_severity(temp_type))
        
        # 风速分类
        wind_type = WeatherClassifier._classify_wind(metrics.max_wind_speed)
        if wind_type and wind_type not in [WeatherType.BREEZE, WeatherType.MODERATE_WIND]:
            weather_types.append(wind_type)
            reasons.append(f"最大风速: {metrics.max_wind_speed:.1f}m/s")
            severity_scores.append(WeatherClassifier._get_wind_severity(wind_type))
        
        # 能见度分类
        visibility_type = WeatherClassifier._classify_visibility(metrics.min_visibility)
        if visibility_type:
            weather_types.append(visibility_type)
            reasons.append(f"最小能见度: {metrics.min_visibility:.0f}m")
            severity_scores.append(WeatherClassifier._get_visibility_severity(visibility_type))
        
        # 湿度分类
        if metrics.is_high_humidity:
            weather_types.append(WeatherType.HUMID)
            reasons.append(f"高湿度: {metrics.humidity:.1f}%")
            severity_scores.append(WeatherSeverity.MILD)
        elif metrics.is_low_humidity:
            weather_types.append(WeatherType.DRY)
            reasons.append(f"低湿度: {metrics.humidity:.1f}%")
            severity_scores.append(WeatherSeverity.MILD)
        
        # 特殊组合天气
        special_types = WeatherClassifier._classify_special_weather(metrics, weather_types)
        weather_types.extend(special_types)
        
        # 如果没有检测到特殊天气，返回一般天气
        if not weather_types:
            weather_types.append(WeatherType.GENERAL)
            reasons.append("未达到特殊天气阈值")
            severity_scores.append(WeatherSeverity.GENERAL)
        
        # 确定最终严重程度
        final_severity = max(severity_scores, key=lambda x: x.value) if severity_scores else WeatherSeverity.GENERAL
        
        # 生成原因描述
        reason_text = "；".join(reasons)
        
        return weather_types, reason_text, final_severity
    
    @staticmethod
    def _classify_precipitation(metrics: WeatherMetrics) -> Optional[WeatherType]:
        if metrics.precip < 0.1:
            return None
        
        for precip_type, (min_val, max_val) in WeatherClassifier.PRECIP_THRESHOLDS.items():
            if min_val <= metrics.precip <= max_val:
                return precip_type
        
        return None
    
    @staticmethod
    def _classify_temperature(metrics: WeatherMetrics, season: Optional[str]) -> List[WeatherType]:
        types = []
        
        # 高温分类
        for temp_type, (min_val, max_val) in WeatherClassifier.TEMP_THRESHOLDS.items():
            if min_val <= metrics.max_temp <= max_val:
                types.append(temp_type)
                break
        
        # 低温/霜冻
        if metrics.min_temp <= 2:
            types.append(WeatherType.FROST)
        
        # 季节调整
        if season == "winter":
            # 冬季低温阈值更严格
            if metrics.max_temp <= 5:
                types.append(WeatherType.LOW_TEMP)
        elif season == "summer":
            # 夏季高温阈值可适当放宽
            if metrics.max_temp >= 33 and WeatherType.HIGH_TEMP not in types:
                types.append(WeatherType.HIGH_TEMP)
        
        return types
    
    @staticmethod
    def _classify_wind(wind_speed: float) -> Optional[WeatherType]:
        """分类风速类型"""
        for wind_type, (min_val, max_val) in WeatherClassifier.WIND_THRESHOLDS.items():
            if min_val <= wind_speed <= max_val:
                return wind_type
        
        return None
    
    @staticmethod
    def _classify_visibility(visibility: float) -> Optional[WeatherType]:
        """分类能见度类型"""
        for vis_type, (min_val, max_val) in WeatherClassifier.VISIBILITY_THRESHOLDS.items():
            if min_val <= visibility <= max_val:
                return vis_type
        
        return None
    
    @staticmethod
    def _classify_special_weather(metrics: WeatherMetrics, existing_types: List[WeatherType]) -> List[WeatherType]:
        """分类特殊组合天气"""
        special_types = []
        
        # 晴冷天气：晴天（低降水）且低温
        if metrics.precip < 1 and metrics.avg_temp < 5:
            special_types.append(WeatherType.SUNNY_COLD)
        
        # 闷热天气：高温高湿
        if metrics.max_temp >= 30 and metrics.is_high_humidity:
            special_types.append(WeatherType.WARM_HUMID)
        
        # 风雨天气：大风+降水
        if (WeatherClassifier._classify_wind(metrics.max_wind_speed) in 
            [WeatherType.STRONG_WIND, WeatherType.GALE, WeatherType.SEVERE_GALE, 
             WeatherType.STORM, WeatherType.HURRICANE] and 
            metrics.precip >= 1):
            special_types.append(WeatherType.WINDY_RAIN)
        
        # 冻雨：温度低于0°C且有降水
        if metrics.is_freezing and metrics.precip > 0:
            special_types.append(WeatherType.FREEZING_RAIN)
        
        return special_types
    
    @staticmethod
    def _get_precip_severity(precip_type: WeatherType) -> WeatherSeverity:
        """获取降水严重程度"""
        severity_map = {
            WeatherType.LIGHT_RAIN: WeatherSeverity.MILD,
            WeatherType.MODERATE_RAIN: WeatherSeverity.MODERATE,
            WeatherType.HEAVY_RAIN: WeatherSeverity.SEVERE,
            WeatherType.STORM_RAIN: WeatherSeverity.SEVERE,
            WeatherType.HEAVY_STORM_RAIN: WeatherSeverity.EXTREME,
            WeatherType.EXTREME_STORM_RAIN: WeatherSeverity.EXTREME,
            WeatherType.FREEZING_RAIN: WeatherSeverity.SEVERE,
            WeatherType.SNOW: WeatherSeverity.MODERATE,
            WeatherType.SLEET: WeatherSeverity.MODERATE,
            WeatherType.HAIL: WeatherSeverity.SEVERE
        }
        return severity_map.get(precip_type, WeatherSeverity.MILD)
    
    @staticmethod
    def _get_temp_severity(temp_type: WeatherType) -> WeatherSeverity:
        """获取温度严重程度"""
        severity_map = {
            WeatherType.EXTREME_HEAT: WeatherSeverity.EXTREME,
            WeatherType.HIGH_TEMP: WeatherSeverity.SEVERE,
            WeatherType.LOW_TEMP: WeatherSeverity.MODERATE,
            WeatherType.SEVERE_COLD: WeatherSeverity.SEVERE,
            WeatherType.FROST: WeatherSeverity.MODERATE
        }
        return severity_map.get(temp_type, WeatherSeverity.MILD)
    
    @staticmethod
    def _get_wind_severity(wind_type: WeatherType) -> WeatherSeverity:
        """获取风速严重程度"""
        severity_map = {
            WeatherType.BREEZE: WeatherSeverity.GENERAL,
            WeatherType.MODERATE_WIND: WeatherSeverity.MILD,
            WeatherType.FRESH_WIND: WeatherSeverity.MILD,
            WeatherType.STRONG_WIND: WeatherSeverity.MODERATE,
            WeatherType.GALE: WeatherSeverity.SEVERE,
            WeatherType.SEVERE_GALE: WeatherSeverity.SEVERE,
            WeatherType.STORM: WeatherSeverity.EXTREME,
            WeatherType.HURRICANE: WeatherSeverity.EXTREME
        }
        return severity_map.get(wind_type, WeatherSeverity.MILD)
    
    @staticmethod
    def _get_visibility_severity(vis_type: WeatherType) -> WeatherSeverity:
        """获取能见度严重程度"""
        severity_map = {
            WeatherType.HAZE: WeatherSeverity.MILD,
            WeatherType.MIST: WeatherSeverity.MODERATE,
            WeatherType.DENSE_FOG: WeatherSeverity.SEVERE,
            WeatherType.HEAVY_FOG: WeatherSeverity.EXTREME,
            WeatherType.DENSE_SMOG: WeatherSeverity.EXTREME
        }
        return severity_map.get(vis_type, WeatherSeverity.MILD)
    
    @staticmethod
    def get_weather_alert(weather_types: List[WeatherType], severity: WeatherSeverity) -> str:
        """生成天气预警信息"""
        if severity == WeatherSeverity.EXTREME:
            return "红色预警：请采取紧急应对措施，避免外出"
        elif severity == WeatherSeverity.SEVERE:
            return "橙色预警：请注意防范，减少户外活动"
        elif severity == WeatherSeverity.MODERATE:
            return "黄色预警：请保持警惕"
        elif severity == WeatherSeverity.MILD:
            return "蓝色预警：请注意天气变化"
        else:
            return "天气正常，无需特别防范"
    
    @staticmethod
    def get_weather_suggestions(weather_types: List[WeatherType]) -> List[str]:
        suggestions = []
        
        for weather_type in weather_types:
            if weather_type == WeatherType.HEAVY_RAIN:
                suggestions.extend([
                    "携带雨具，注意防雨",
                    "避免在低洼地带停留",
                    "注意防范城市内涝"
                ])
            elif weather_type == WeatherType.EXTREME_HEAT:
                suggestions.extend([
                    "避免在高温时段外出",
                    "多喝水，注意防暑降温",
                    "使用防晒用品"
                ])
            elif weather_type == WeatherType.SEVERE_COLD:
                suggestions.extend([
                    "注意保暖，穿戴厚实",
                    "预防感冒和冻伤",
                    "注意取暖安全"
                ])
            elif weather_type == WeatherType.GALE:
                suggestions.extend([
                    "固定好室外物品",
                    "避免在高大建筑下停留",
                    "注意高空坠物"
                ])
            elif weather_type == WeatherType.HEAVY_FOG:
                suggestions.extend([
                    "减速慢行，开启雾灯",
                    "避免高速公路行驶",
                    "呼吸道敏感者佩戴口罩"
                ])
            elif weather_type == WeatherType.SNOW:
                suggestions.extend([
                    "注意道路结冰",
                    "穿戴防滑鞋具",
                    "及时清除积雪"
                ])
        return list(dict.fromkeys(suggestions))
    
    @staticmethod
    def parse_sql_result(sql_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            results = []
            for data in sql_data:
                station_name = data.get("station_name")
                if not station_name:
                    logger.warning(f"跳过无站点名称的数据: {data}")
                    continue
                try:
                    def safe_float(value, default=0.0):
                        if value is None:
                            return default
                        if isinstance(value, Decimal):
                            return float(value)
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                    min_visibility = data.get("min_visibility", 10000)
                    if min_visibility == 999999:
                        min_visibility = 10000
                    metrics = WeatherMetrics(
                        avg_temp=safe_float(data.get("avg_temp")),
                        min_temp=safe_float(data.get("min_temp")),
                        max_temp=safe_float(data.get("max_temp")),
                        precip=safe_float(data.get("total_precip")),
                        max_wind_speed=safe_float(data.get("max_wind_speed")),
                        min_visibility=safe_float(min_visibility),
                        humidity=safe_float(data.get("avg_humidity"), default=None)
                    )
                    results.append({
                        "station_name": station_name,
                        "metrics": metrics
                    })
                    logger.debug(f"成功解析站点 {station_name} 的数据")
                    
                except Exception as e:
                    logger.warning(f"解析站点 {station_name} 数据失败: {e}")
                    continue
                    
            logger.info(f"成功解析 {len(results)}/{len(sql_data)} 个站点的数据")
            return results
            
        except Exception as e:
            logger.error(f"批量解析 SQL 结果失败: {e}")
            return []
        
    @staticmethod
    async def classify_with_llm(metrics: WeatherMetrics, llm, region: str) -> tuple[str, str]:
        """
        # TODO 
        使用 LLM 辅助判断天气类型 --> 预留的接口 应该用不到 --> 判断天气类型这一块还是用气象知识比较好
        """
        raise NotImplementedError
