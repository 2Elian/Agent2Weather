import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import aiomysql

from .base_db import DBConnector
from .sql_template import SQL_TEMPLATE
from a2w.utils.logger import setup_logger

class SQLServerConnector(DBConnector):
    def __init__(self, host: str, port: str, database: str, username: str, password: str):
        self.connection_string = (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER={host},{port};"
                f"DATABASE={database};"
                f"UID={username};PWD={password};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
            )
        self.logger = setup_logger(name="SQLServerExecutor")
        self.pool = None
        self.logger.info(f"DB will use SQLServer as Connector: Host:{host} --> Database{database}")
    
    async def connect(self):
        try:
            import aioodbc
            self.pool = await aioodbc.create_pool(dsn=self.connection_string, autocommit=True)
            self.logger.info("SQL Server connection pool has been established.")
        except Exception as e:
            self.logger.error(f"SQL Server connect failed: {e}")
            raise
    
    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("SQL Server connection pool is closed.")
    
    async def execute_query(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql)
                    rows = await cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in rows] if rows else []
        except Exception as e:
            self.logger.error(f"SQL execution failed: {e}")
            return None
    
    async def query_weather_metrics(self, regions: List[str], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        placeholders = ",".join(["?"] * len(regions))
        table_name = f"automatic_station_his_day_data_{start_date[:4]}"  # 使用开始日期年份的日表作为天气类型的固定SQL查询

        sql = f"""
        SELECT 
            station_name,
            AVG(tem_avg) as avg_temp,
            MIN(tem_min) as min_temp,
            MAX(tem_max) as max_temp,
            SUM(rain) as total_precip,
            MAX(win_s_max) as max_wind_speed,
            MIN(vis_min) as min_visibility,
            AVG(rhu_avg) as avg_humidity
        FROM {table_name}
        WHERE station_name IN ({placeholders}) AND observation_time BETWEEN ? AND ?
        GROUP BY station_name
        ORDER BY station_name
        """
        # GROUP BY station_name 分别对每个站点计算聚合函数 --> 如果没有的话 就会按照筛选的列计算avg
        # ORDER BY station_name 按站点名称排序结果集
        start_datetime = f"{start_date} 00:00:00.000" # TODO 根据日表/小时表里面的observation_time的格式而定
        end_datetime = f"{end_date} 23:59:59.999"
        params = regions + [start_datetime, end_datetime]

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, params)
                    rows = await cursor.fetchall()
                    if not rows:
                        return []

                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"查询日表天气指标数据失败: {e}")
            return None
    
    async def query_detailed_weather_from_dayTable(self,  regions: List[str],  start_date: str,  end_date: str, detail_level: str = "standard") -> List[Dict[str, Any]]:
        """
        detail_level: 
            'standard' - 标准
            'detailed' - 详细
            'extreme' - 极端天气相关
        """
        placeholders = ",".join(["?"] * len(regions))
        year = start_date[:4]
        table_name = f"automatic_station_his_day_data_{year}"
        
        start_datetime = f"{start_date} 00:00:00"
        end_datetime = f"{end_date} 23:59:59"
        params = regions + [start_datetime, end_datetime]
        
        if detail_level == "standard":
            sql = f"""
            SELECT 
                station_name,
                DATE(observation_time) as date,
                tem_avg as avg_temp,
                tem_min as min_temp,
                tem_max as max_temp,
                rain as total_precip,
                win_s_max as max_wind_speed,
                win_s_inst_max as max_wind_gust,  -- 极大风速
                vis_min as min_visibility,
                rhu_avg as avg_humidity,
                rhu_min as min_humidity,
                prs_avg as avg_pressure,
                
                -- 天气现象判断
                CASE 
                    WHEN rain >= 10 THEN '有雨'
                    WHEN vis_min < 500 THEN '有雾'
                    WHEN win_s_max >= 10.8 THEN '有大风'
                    WHEN tem_avg < 5 AND rain < 1 THEN '晴冷'
                    WHEN tem_max >= 35 THEN '高温'
                    ELSE '一般'
                END as weather_type,
                
                -- 常见天气现象
                CASE 
                    WHEN fog IS NOT NULL AND fog != '' THEN '雾'
                    WHEN rain > 0 THEN '雨'
                    WHEN snow IS NOT NULL AND snow != '' THEN '雪'
                    WHEN hail IS NOT NULL AND hail != '' THEN '冰雹'
                    WHEN thunder IS NOT NULL AND thunder != '' THEN '雷'
                    ELSE ''
                END as weather_desc
                
            FROM {table_name}
            WHERE station_name IN ({placeholders}) 
            AND observation_time BETWEEN ? AND ?
            ORDER BY station_name, observation_time
            """
            
        elif detail_level == "detailed":
            sql = f"""
            SELECT 
                station_name,
                DATE(observation_time) as date,
                
                -- 温度相关
                tem_avg as avg_temp,
                tem_min as min_temp,
                tem_max as max_temp,
                tem_min_otime as min_temp_time,
                tem_max_otime as max_temp_time,
                
                -- 降水相关
                rain as total_precip,
                pre_max_1h as max_hourly_precip,
                pre_max_1h_otime as max_precip_time,
                pre_time_2008 as precip_20_08,
                pre_time_0820 as precip_08_20,
                pre_time_2020 as precip_20_20,
                pre_time_0808 as precip_08_08,
                
                -- 风速相关
                win_s_max as max_wind_speed,
                win_s_max_otime as max_wind_time,
                win_s_inst_max as max_wind_gust,
                win_s_inst_max_otime as max_gust_time,
                win_s_2mi_avg as avg_wind_2min,
                win_s_10mi_avg as avg_wind_10min,
                win_d_s_max as max_wind_direction,
                
                -- 能见度相关
                vis_min as min_visibility,
                vis_min_otime as min_visibility_time,
                
                -- 湿度相关
                rhu_avg as avg_humidity,
                rhu_min as min_humidity,
                rhu_min_otime as min_humidity_time,
                
                -- 气压相关
                prs_avg as avg_pressure,
                prs_max as max_pressure,
                prs_max_otime as max_pressure_time,
                prs_min as min_pressure,
                prs_min_otime as min_pressure_time,
                prs_sea_avg as avg_sea_pressure,
                
                -- 云量
                clo_cov_avg as avg_cloud_cover,
                clo_cov_low_avg as avg_low_cloud_cover,
                
                -- 地温
                gst_avg as avg_ground_temp,
                gst_max as max_ground_temp,
                gst_min as min_ground_temp,
                
                -- 天气现象汇总
                CASE 
                    WHEN rain > 0 THEN '有降水'
                    ELSE ''
                END as has_precip,
                CASE 
                    WHEN fog IS NOT NULL AND fog != '' THEN '有雾'
                    ELSE ''
                END as has_fog,
                CASE 
                    WHEN snow IS NOT NULL AND snow != '' THEN '有雪'
                    ELSE ''
                END as has_snow,
                CASE 
                    WHEN hail IS NOT NULL AND hail != '' THEN '有冰雹'
                    ELSE ''
                END as has_hail,
                CASE 
                    WHEN thunder IS NOT NULL AND thunder != '' THEN '有雷暴'
                    ELSE ''
                END as has_thunder
                
            FROM {table_name}
            WHERE station_name IN ({placeholders}) 
            AND observation_time BETWEEN ? AND ?
            ORDER BY station_name, observation_time
            """
            
        else:  # detail_level == "extreme"
            sql = f"""
            SELECT 
                station_name,
                DATE(observation_time) as date,
                
                -- 极端温度
                tem_max as max_temp,
                tem_max_otime as max_temp_time,
                tem_min as min_temp,
                tem_min_otime as min_temp_time,
                
                -- 极端降水
                rain as total_precip,
                pre_max_1h as max_hourly_precip,
                pre_max_1h_otime as max_precip_time,
                
                -- 极端风速
                win_s_max as max_wind_speed,
                win_s_max_otime as max_wind_time,
                win_s_inst_max as max_wind_gust,
                win_s_inst_max_otime as max_gust_time,
                
                -- 极端能见度
                vis_min as min_visibility,
                vis_min_otime as min_visibility_time,
                
                -- 极端天气现象标志
                CASE 
                    WHEN rain >= 50 THEN '暴雨'
                    WHEN rain >= 25 THEN '大雨'
                    WHEN rain >= 10 THEN '中雨'
                    WHEN rain > 0 THEN '小雨'
                    ELSE ''
                END as rain_level,
                
                CASE 
                    WHEN win_s_max >= 24.5 THEN '飓风'
                    WHEN win_s_max >= 20.8 THEN '狂风'
                    WHEN win_s_max >= 17.2 THEN '烈风'
                    WHEN win_s_max >= 13.9 THEN '大风'
                    WHEN win_s_max >= 10.8 THEN '强风'
                    ELSE ''
                END as wind_level,
                
                CASE 
                    WHEN vis_min < 50 THEN '浓雾霾'
                    WHEN vis_min < 200 THEN '大雾'
                    WHEN vis_min < 500 THEN '浓雾'
                    WHEN vis_min < 1000 THEN '雾'
                    ELSE ''
                END as visibility_level,
                
                CASE 
                    WHEN tem_max >= 40 THEN '极端高温'
                    WHEN tem_max >= 35 THEN '高温'
                    WHEN tem_min <= -10 THEN '严寒'
                    WHEN tem_min <= 0 THEN '低温'
                    ELSE ''
                END as temp_level,
                
                -- 是否有特殊天气现象
                CASE WHEN fog IS NOT NULL AND fog != '' THEN 1 ELSE 0 END as fog_flag,
                CASE WHEN snow IS NOT NULL AND snow != '' THEN 1 ELSE 0 END as snow_flag,
                CASE WHEN hail IS NOT NULL AND hail != '' THEN 1 ELSE 0 END as hail_flag,
                CASE WHEN thunder IS NOT NULL AND thunder != '' THEN 1 ELSE 0 END as thunder_flag,
                CASE WHEN glaze IS NOT NULL AND glaze != '' THEN 1 ELSE 0 END as glaze_flag
                
            FROM {table_name}
            WHERE station_name IN ({placeholders}) 
            AND observation_time BETWEEN ? AND ?
            ORDER BY station_name, observation_time
            """
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, params)
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        self.logger.warning(f"日表未找到数据: regions={regions}, date={start_date}~{end_date}")
                        return []
                    
                    columns = [col[0] for col in cursor.description]
                    results = []
                    
                    for row in rows:
                        record = {}
                        for col_name, value in zip(columns, row):
                            # 处理特殊值
                            if col_name in ["min_visibility", "vis_min"] and value == 999999:
                                record[col_name] = 10000
                            elif value is None:
                                if any(keyword in col_name for keyword in ["precip", "rain", "prcp"]):
                                    record[col_name] = 0.0
                                elif "temp" in col_name or "tem" in col_name:
                                    record[col_name] = 0.0 if "_time" not in col_name else None
                                elif "wind" in col_name or "win" in col_name:
                                    record[col_name] = 0.0 if "_time" not in col_name else None
                                elif "visibility" in col_name or "vis" in col_name:
                                    record[col_name] = 10000 if "_time" not in col_name else None
                                elif "humidity" in col_name or "rhu" in col_name:
                                    record[col_name] = None
                                elif "time" in col_name or "otime" in col_name:
                                    record[col_name] = None
                                else:
                                    record[col_name] = None
                            elif isinstance(value, Decimal):
                                record[col_name] = float(value)
                            elif isinstance(value, datetime.datetime):
                                record[col_name] = value.strftime("%Y-%m-%d %H:%M:%S")
                            elif isinstance(value, datetime.date):
                                record[col_name] = value.strftime("%Y-%m-%d")
                            else:
                                record[col_name] = value
                        record["data_source"] = "day_table"
                        record["table_name"] = table_name
                        
                        results.append(record)
                    return results
                    
        except Exception as e:
            self.logger.error(f"查询日表数据失败: {e}")
            if "doesn't exist" in str(e) or "no such table" in str(e):
                self.logger.warning(f"表 {table_name} 不存在")
            raise
        
    async def query_detailed_weather_from_hourTable(self, regions: List[str], start_date: str, end_date: str,aggregation: str = "hourly", station_name_to_cnty: bool = False) -> List[Dict[str, Any]]:
        """
        aggregation: 
            'hourly' - 每小时原始数据
            'half' - 上午和下午的数据
            'daily' - 每日聚合数据
        station_name_to_cnty: 是否要将station_name转换成对应的区/县
        """
        placeholders = ",".join(["?"] * len(regions))
        start_datetime = f"{start_date} 00:00:00"
        end_datetime = f"{end_date} 23:59:59"
        params = regions + [start_datetime, end_datetime]
        table_name = f"automatic_station_data"
        key_county = "by_county" if station_name_to_cnty else "by_station"
        sql = SQL_TEMPLATE["hour_table"][aggregation][key_county].format(
            table_name=table_name, placeholders=placeholders
        )

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, params)
                    rows = await cursor.fetchall()
                    if not rows:
                        self.logger.warning(f"未找到数据: regions={regions}, date={start_date}~{end_date}")
                        return []
                    columns = [col[0] for col in cursor.description]
                    results = []
                    for row in rows:
                        record = {}
                        for col_name, value in zip(columns, row):
                            # 特殊值处理
                            if col_name in ["日平均水平能见度", "平均水平能见度"] and value == 999999:
                                record[col_name] = 10000
                            elif value is None:
                                if "降水" in col_name:
                                    record[col_name] = 0.0
                                elif "温度" in col_name:
                                    record[col_name] = 0.0
                                elif "风速" in col_name:
                                    record[col_name] = 0.0
                                elif "能见度" in col_name:
                                    record[col_name] = 10000
                                elif "湿度" in col_name:
                                    record[col_name] = None
                                else:
                                    record[col_name] = None
                            elif isinstance(value, Decimal):
                                record[col_name] = float(value)
                            elif isinstance(value, datetime.datetime):
                                record[col_name] = value.strftime("%Y-%m-%d %H:%M:%S")
                            elif isinstance(value, datetime.date):
                                record[col_name] = value.strftime("%Y-%m-%d")
                            else:
                                record[col_name] = value
                        results.append(record)
                    
                    self.logger.info(f"The query returned {len(results)} records of \"{aggregation}\".")
                    return results
                    
        except Exception as e:
            self.logger.error(f"查询{aggregation}数据失败: {e}")
            if "doesn't exist" in str(e) or "no such table" in str(e):
                self.logger.warning(f"表 {table_name} 不存在，尝试其他表名格式...")
            raise
        
    async def query_cnty_by_regions(self, regions: List[str]) -> List[str]:
        """根据 station_name 查询对应的区县"""
        table_name = f"automatic_station_data"
        placeholders = ",".join(["?"] * len(regions))
        params = regions

        sql = f"""
        SELECT DISTINCT cnty
        FROM {table_name}
        WHERE station_name IN ({placeholders})
        AND cnty IS NOT NULL
        AND cnty <> ''
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, params)
                    rows = await cursor.fetchall()

                    if not rows:
                        raise
                    cnty_list = [row[0] for row in rows if row[0]]
                    return cnty_list

        except Exception as e:
            raise