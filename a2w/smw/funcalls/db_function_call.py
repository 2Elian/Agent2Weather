import asyncio
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timedelta
from langchain_core.tools import tool

from a2w.api.middleware.db.sql_connector import SQLServerConnector
from a2w.smw.funcalls import register_tool

_SQLServerExe: SQLServerConnector = None
def set_sqlserver_exe(db_instance: SQLServerConnector):
    global _SQLServerExe
    _SQLServerExe = db_instance
    
async def _async_execute_query(sql: str) -> Dict[str, Any]:
    if _SQLServerExe is None:
        raise ValueError("SQLServerExe 未初始化")
    try:
        data = await _SQLServerExe.execute_query(sql)
        return {
            "status": "success",
            "message": "查询执行成功",
            "data": data,
            "row_count": len(data) if data else 0,
            "query_time": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def get_table_name_by_date(date_str: str) -> str:
    try:
        year = date_str[:4]
        return f"automatic_station_his_day_data_{year}"
    except:
        return "automatic_station_his_day_data_2024"

def get_table_names_by_date_range(start_date: str, end_date: str) -> List[str]:
    try:
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        table_names = []
        for year in range(start_year, end_year + 1):
            table_names.append(f"automatic_station_his_day_data_{year}")
        
        return table_names
    except:
        return ["automatic_station_his_day_data_2024"]

def get_table_names_for_year_range(start_year: int, end_year: int) -> List[str]:
    table_names = []
    for year in range(start_year, end_year + 1):
        table_names.append(f"automatic_station_his_day_data_{year}")
    return table_names

def build_city_conditions(cities: List[str]) -> str:
    if not cities:
        return "1=1"
    
    conditions = []
    for city in cities:
        conditions.append(f"(city LIKE '%{city}%' OR cnty LIKE '%{city}%')")
    
    return f"({' OR '.join(conditions)})"

def build_date_condition(start_date: str, end_date: str) -> str:
    return f"observation_time BETWEEN '{start_date}' AND '{end_date}'"

def build_union_sql_for_tables(tables: List[str], select_sql: str, where_conditions: str) -> str:
    union_parts = []
    for table in tables:
        union_parts.append(f"SELECT {select_sql} FROM {table} WHERE {where_conditions}")
    
    return "\nUNION ALL\n".join(union_parts)

async def execute_cross_year_query(start_date: str, end_date: str, cities: List[str], 
                                  select_fields: str, group_by: str = "", 
                                  order_by: str = "", limit: str = "") -> Dict[str, Any]:
    """
    执行跨年份查询
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        cities: 城市列表
        select_fields: SELECT字段
        group_by: GROUP BY子句
        order_by: ORDER BY子句
        limit: LIMIT子句
    """
    table_names = get_table_names_by_date_range(start_date, end_date)
    city_condition = build_city_conditions(cities)
    date_condition = build_date_condition(start_date, end_date)
    where_condition = f"{date_condition} AND {city_condition}"
    if len(table_names) == 1:
        sql = f"""
        SELECT {select_fields}
        FROM {table_names[0]}
        WHERE {where_condition}
        """
        if group_by:
            sql += f" GROUP BY {group_by}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        
        return await _async_execute_query(sql)
    union_parts = []
    for table in table_names:
        union_sql = f"SELECT {select_fields} FROM {table} WHERE {where_condition}"
        union_parts.append(union_sql)
    
    union_query = "\nUNION ALL\n".join(union_parts)
    if group_by:
        sql = f"""
        SELECT {select_fields.replace('*', f"{group_by}, COUNT(*) as count")}
        FROM (
            {union_query}
        ) AS combined_data
        GROUP BY {group_by}
        """
    else:
        sql = f"SELECT * FROM ({union_query}) AS combined_data"
    
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {limit}"
    
    return await _async_execute_query(sql)

@register_tool
@tool
async def query_precipitation_data(start_date: str, end_date: str, cities: List[str] = [], 
                                  aggregation: str = "average") -> Dict[str, Any]:
    """
    查询指定日期范围的降水数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        aggregation: 聚合方式: daily/total/average/max

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    if aggregation == "daily":
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as daily_precipitation,
            MAX(pre_max_1h) as max_hourly_precipitation,
            pre_max_1h_otime as max_precipitation_time
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY observation_time, city, cnty, pre_max_1h_otime
        ORDER BY observation_time, city
        """
    
    elif aggregation == "total":
        sql = f"""
        SELECT 
            city,
            cnty,
            SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as total_precipitation,
            COUNT(DISTINCT observation_time) as rainy_days,
            MAX(pre_max_1h) as max_hourly_precipitation
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY city, cnty
        ORDER BY total_precipitation DESC
        """
    
    elif aggregation == "max":
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            station_name,
            pre_max_1h as max_hourly_precipitation,
            pre_time_2020 + pre_time_0808 as daily_precipitation,
            pre_max_1h_otime as occurrence_time
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        ORDER BY pre_max_1h DESC
        LIMIT 10
        """
    
    else:  # average
        city_group = "city, cnty" if cities else "1"
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            AVG(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as avg_precipitation,
            AVG(pre_max_1h) as avg_max_hourly_precipitation,
            COUNT(DISTINCT observation_time) as observation_days
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY {city_group}
        """
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_temperature_data(start_date: str, end_date: str, cities: List[str] = [], 
                                aggregation: str = "average") -> Dict[str, Any]:
    """
    查询指定日期范围的温度数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        aggregation: 聚合方式: daily/average/max/min/range

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    
    if aggregation == "daily":
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            AVG(tem_avg) as avg_temperature,
            MAX(tem_max) as max_temperature,
            MIN(tem_min) as min_temperature,
            MAX(tem_max) - MIN(tem_min) as daily_range
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY observation_time, city, cnty
        ORDER BY observation_time
        """
    
    elif aggregation == "max":
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            station_name,
            tem_max as max_temperature,
            tem_max_otime as occurrence_time,
            tem_avg as avg_temperature_on_day
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND tem_max IS NOT NULL
        ORDER BY tem_max DESC
        LIMIT 10
        """
    
    elif aggregation == "min":
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            station_name,
            tem_min as min_temperature,
            tem_min_otime as occurrence_time,
            tem_avg as avg_temperature_on_day
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND tem_min IS NOT NULL
        ORDER BY tem_min ASC
        LIMIT 10
        """
    
    elif aggregation == "range":
        city_group = "city, cnty" if cities else "1"
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            AVG(tem_max - tem_min) as avg_daily_range,
            MAX(tem_max - tem_min) as max_daily_range,
            MIN(tem_max - tem_min) as min_daily_range
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY {city_group}
        """
    
    else:  # average
        city_group = "city, cnty" if cities else "1"
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            AVG(tem_avg) as period_avg_temperature,
            AVG(tem_max) as period_avg_max_temperature,
            AVG(tem_min) as period_avg_min_temperature,
            MAX(tem_max) as period_max_temperature,
            MIN(tem_min) as period_min_temperature,
            MAX(tem_max) - MIN(tem_min) as period_temperature_range,
            COUNT(DISTINCT observation_time) as observation_days
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY {city_group}
        """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_wind_data(start_date: str, end_date: str, cities: List[str] = [], 
                         include_direction: bool = True, include_extremes: bool = False) -> Dict[str, Any]:
    """
    查询指定日期范围的风速风向数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        include_direction: 是否包含风向信息
        include_extremes: 是否包含极值风速

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    
    if include_extremes:
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            station_name,
            win_s_max as max_wind_speed,
            win_s_inst_max as extreme_wind_speed,
            win_d_s_max as max_wind_direction,
            win_d_inst_max as extreme_wind_direction,
            win_s_max_otime as max_speed_time,
            win_s_inst_max_otime as extreme_speed_time
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND win_s_max IS NOT NULL
        ORDER BY win_s_max DESC
        LIMIT 10
        """
    
    elif include_direction:
        city_group = "city, cnty" if cities else "1"
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            win_d_avg_2mi_c as wind_direction_category,
            COUNT(*) as occurrence_count,
            AVG(win_s_2mi_avg) as avg_wind_speed,
            AVG(win_s_max) as avg_max_wind_speed
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND win_d_avg_2mi_c IS NOT NULL
        GROUP BY {city_group}, win_d_avg_2mi_c
        ORDER BY {city_group}, occurrence_count DESC
        """
    
    else:
        city_group = "city, cnty" if cities else "1"
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            AVG(win_s_2mi_avg) as avg_2min_wind_speed,
            AVG(win_s_10mi_avg) as avg_10min_wind_speed,
            COUNT(*) as observation_count
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND win_s_2mi_avg IS NOT NULL
        GROUP BY {city_group}
        """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_humidity_data(start_date: str, end_date: str, cities: List[str] = [], 
                             include_min_humidity: bool = True) -> Dict[str, Any]:
    """
    查询指定日期范围的湿度数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        include_min_humidity: 是否包含最小湿度

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    city_group = "city, cnty" if cities else "1"
    
    min_humidity_fields = ""
    min_humidity_where = ""
    
    if include_min_humidity:
        min_humidity_fields = ", MIN(rhu_min) as period_min_humidity, AVG(rhu_min) as avg_min_humidity"
        min_humidity_where = " AND rhu_min IS NOT NULL"
    
    sql = f"""
    SELECT 
        {'city, cnty,' if cities else ''}
        AVG(rhu_avg) as avg_humidity,
        COUNT(DISTINCT observation_time) as observation_days
        {min_humidity_fields}
    FROM {table_name}
    WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
      AND {city_condition}
      AND rhu_avg IS NOT NULL {min_humidity_where}
    GROUP BY {city_group}
    """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_pressure_data(start_date: str, end_date: str, cities: List[str] = [], 
                             include_sea_level: bool = True, include_extremes: bool = False) -> Dict[str, Any]:
    """
    查询指定日期范围的气压数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        include_sea_level: 是否包含海平面气压
        include_extremes: 是否包含气压极值

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    
    if include_extremes:
        sql = f"""
        SELECT 
            observation_time as date,
            city,
            cnty,
            station_name,
            prs_max as max_pressure,
            prs_min as min_pressure,
            prs_max_otime as max_pressure_time,
            prs_min_otime as min_pressure_time,
            prs_sea_avg as sea_level_pressure
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND prs_max IS NOT NULL AND prs_min IS NOT NULL
        ORDER BY (prs_max - prs_min) DESC
        LIMIT 10
        """
    
    else:
        city_group = "city, cnty" if cities else "1"
        sea_level_field = ", AVG(prs_sea_avg) as avg_sea_level_pressure" if include_sea_level else ""
        
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            AVG(prs_avg) as avg_pressure,
            AVG(prs_max) as avg_max_pressure,
            AVG(prs_min) as avg_min_pressure
            {sea_level_field}
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
          AND prs_avg IS NOT NULL
        GROUP BY {city_group}
        """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_visibility_data(start_date: str, end_date: str, cities: List[str] = [], 
                               include_min_visibility: bool = True) -> Dict[str, Any]:
    """
    查询指定日期范围的能见度数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        include_min_visibility: 是否包含最小能见度

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    city_group = "city, cnty" if cities else "1"
    
    min_visibility_fields = ", MIN(vis_min) as min_visibility, AVG(vis_min) as avg_min_visibility" if include_min_visibility else ""
    
    sql = f"""
    SELECT 
        {'city, cnty,' if cities else ''}
        AVG(COALESCE(vis_min, 0)) as avg_visibility
        {min_visibility_fields}
    FROM {table_name}
    WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
      AND {city_condition}
    GROUP BY {city_group}
    """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_comprehensive_weather(start_date: str, end_date: str, cities: List[str] = [], 
                                     include_metrics: List[str] = None) -> Dict[str, Any]:
    """
    综合查询指定日期范围的多种天气指标数据

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        include_metrics: 包含的指标列表，可选：temperature, precipitation, wind, humidity, pressure, visibility

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    if include_metrics is None:
        include_metrics = ["temperature", "precipitation", "wind", "humidity"]
    
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    city_group = "city, cnty" if cities else "1"

    fields = []
    
    if "temperature" in include_metrics:
        fields.extend([
            "AVG(tem_avg) as avg_temperature",
            "MAX(tem_max) as max_temperature",
            "MIN(tem_min) as min_temperature"
        ])
    
    if "precipitation" in include_metrics:
        fields.extend([
            "SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as total_precipitation",
            "MAX(pre_max_1h) as max_hourly_precipitation"
        ])
    
    if "wind" in include_metrics:
        fields.extend([
            "AVG(win_s_2mi_avg) as avg_wind_speed",
            "MAX(win_s_max) as max_wind_speed"
        ])
    
    if "humidity" in include_metrics:
        fields.extend([
            "AVG(rhu_avg) as avg_humidity",
            "MIN(rhu_min) as min_humidity"
        ])
    
    if "pressure" in include_metrics:
        fields.extend([
            "AVG(prs_avg) as avg_pressure",
            "AVG(prs_sea_avg) as avg_sea_level_pressure"
        ])
    
    if "visibility" in include_metrics:
        fields.extend([
            "AVG(COALESCE(vis_min, 0)) as avg_visibility"
        ])
    
    fields_str = ",\n            ".join(fields) if fields else "1 as placeholder"
    
    sql = f"""
    SELECT 
        {'city, cnty,' if cities else ''}
        {fields_str},
        COUNT(DISTINCT observation_time) as observation_days
    FROM {table_name}
    WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
      AND {city_condition}
    GROUP BY {city_group}
    """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_weather_days_statistics(start_date: str, end_date: str, cities: List[str] = [], 
                                       weather_types: List[str] = None) -> Dict[str, Any]:
    """
    查询各种天气类型的日数统计

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        weather_types: 天气类型列表，可选：rainy, sunny, windy, foggy, cold, hot

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    table_name = get_table_name_by_date(start_date)
    city_condition = build_city_conditions(cities)
    city_group = "city, cnty" if cities else "1"
    
    # 构建天气类型条件
    weather_conditions = []
    if weather_types:
        if "rainy" in weather_types:
            weather_conditions.append("(pre_time_2020 > 0 OR pre_time_0808 > 0)")
        if "sunny" in weather_types:
            weather_conditions.append("(clo_cov_avg < 30)")  # 假设云量小于30为晴天
        if "windy" in weather_types:
            weather_conditions.append("(win_s_max > 10.8)")  # 风速大于10.8m/s（6级风）
        if "foggy" in weather_types:
            weather_conditions.append("(vis_min < 1000)")  # 能见度小于1km
        if "cold" in weather_types:
            weather_conditions.append("(tem_avg < 10)")  # 平均气温低于10度
        if "hot" in weather_types:
            weather_conditions.append("(tem_avg > 28)")  # 平均气温高于28度

    if not weather_conditions:
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            COUNT(DISTINCT observation_time) as total_days,
            SUM(CASE WHEN pre_time_2020 > 0 OR pre_time_0808 > 0 THEN 1 ELSE 0 END) as rainy_days,
            SUM(CASE WHEN tem_avg < 10 THEN 1 ELSE 0 END) as cold_days,
            SUM(CASE WHEN tem_avg > 28 THEN 1 ELSE 0 END) as hot_days,
            SUM(CASE WHEN win_s_max > 10.8 THEN 1 ELSE 0 END) as windy_days,
            SUM(CASE WHEN vis_min < 1000 THEN 1 ELSE 0 END) as foggy_days
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY {city_group}
        """
    else:
        conditions = []
        for i, condition in enumerate(weather_conditions):
            conditions.append(f"""
            SUM(CASE WHEN {condition} THEN 1 ELSE 0 END) as weather_type_{i+1}_days
            """)
        
        conditions_str = ",\n            ".join(conditions)
        
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            COUNT(DISTINCT observation_time) as total_days,
            {conditions_str}
        FROM {table_name}
        WHERE observation_time BETWEEN '{start_date}' AND '{end_date}'
          AND {city_condition}
        GROUP BY {city_group}
        """
    
    result = await _async_execute_query(sql)
    return result

@register_tool
@tool
async def query_comparison_data(start_date: str, end_date: str, cities: List[str] = [], 
                               compare_period: str = "climatology", climatology_years: int = 30) -> Dict[str, Any]:
    """
    查询数据对比（与气候值或其他时期对比）

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        compare_period: 对比时期：climatology（气候值）、last_year（去年同期）、same_period_last_year（历史同期）
        climatology_years: 气候基准年数（仅当compare_period=climatology时有效），默认30年

    Returns:
        dict: 查询结果，包含以下字段
            - status: success 或 error
            - message: 信息描述
            - data: 查询结果列表
            - row_count: 数据行数
            - query_time: 查询执行时间
    """
    city_condition = build_city_conditions(cities)
    city_group = "city, cnty" if cities else "1"
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if compare_period == "last_year":
            last_year_start = (start_dt - timedelta(days=365)).strftime("%Y-%m-%d")
            last_year_end = (end_dt - timedelta(days=365)).strftime("%Y-%m-%d")
            current_tables = get_table_names_by_date_range(start_date, end_date)
            last_year_tables = get_table_names_by_date_range(last_year_start, last_year_end)

            current_select_fields = f"""
                {'city, cnty,' if cities else ''}
                AVG(tem_avg) as current_avg_temperature,
                SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as current_total_precipitation,
                AVG(rhu_avg) as current_avg_humidity,
                COUNT(DISTINCT observation_time) as current_days
            """
            last_year_select_fields = f"""
                {'city, cnty,' if cities else ''}
                AVG(tem_avg) as last_year_avg_temperature,
                SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as last_year_total_precipitation,
                AVG(rhu_avg) as last_year_avg_humidity,
                COUNT(DISTINCT observation_time) as last_year_days
            """

            sql = f"""
            WITH current_data AS (
                SELECT {current_select_fields}
                FROM (
                    {build_union_sql_for_tables(current_tables, current_select_fields, 
                                               f"{build_date_condition(start_date, end_date)} AND {city_condition}")}
                ) AS t
                GROUP BY {city_group}
            ),
            last_year_data AS (
                SELECT {last_year_select_fields}
                FROM (
                    {build_union_sql_for_tables(last_year_tables, last_year_select_fields,
                                               f"{build_date_condition(last_year_start, last_year_end)} AND {city_condition}")}
                ) AS t
                GROUP BY {city_group}
            )
            SELECT 
                COALESCE(c.city, ly.city) as city,
                COALESCE(c.cnty, ly.cnty) as cnty,
                c.current_avg_temperature,
                ly.last_year_avg_temperature,
                c.current_avg_temperature - ly.last_year_avg_temperature as temp_difference,
                c.current_total_precipitation,
                ly.last_year_total_precipitation,
                c.current_total_precipitation - ly.last_year_total_precipitation as precip_difference,
                CASE 
                    WHEN ly.last_year_total_precipitation > 0 
                    THEN ROUND((c.current_total_precipitation - ly.last_year_total_precipitation) * 100.0 / ly.last_year_total_precipitation, 1)
                    ELSE NULL
                END as precip_change_percent,
                c.current_avg_humidity,
                ly.last_year_avg_humidity,
                c.current_avg_humidity - ly.last_year_avg_humidity as humidity_difference,
                c.current_days,
                ly.last_year_days
            FROM current_data c
            FULL OUTER JOIN last_year_data ly 
                ON {'c.city = ly.city AND c.cnty = ly.cnty' if cities else '1=1'}
            ORDER BY COALESCE(c.city, ly.city), COALESCE(c.cnty, ly.cnty)
            """
            
        elif compare_period == "same_period_last_year":
            # TODO 这里需要按日对比，比较复杂，先简化处理为去年同期
            return await query_comparison_data(start_date, end_date, cities, "last_year")
            
        elif compare_period == "climatology":
            # 与气候值对比（多年平均值）
            # 计算气候基准期：前N年同期
            climatology_start_year = start_dt.year - climatology_years
            climatology_end_year = start_dt.year - 1
            climatology_tables = get_table_names_for_year_range(climatology_start_year, climatology_end_year)

            climatology_select_fields = f"""
                {'city, cnty,' if cities else ''}
                AVG(tem_avg) as climatology_avg_temperature,
                AVG(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as climatology_avg_precipitation,
                AVG(rhu_avg) as climatology_avg_humidity,
                COUNT(*) as climatology_years_count
            """

            current_tables = get_table_names_by_date_range(start_date, end_date)
            current_select_fields = f"""
                {'city, cnty,' if cities else ''}
                AVG(tem_avg) as current_avg_temperature,
                SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as current_total_precipitation,
                AVG(rhu_avg) as current_avg_humidity,
                COUNT(DISTINCT observation_time) as current_days
            """

            climatology_base_query = f"""
            SELECT 
                {'city, cnty,' if cities else ''}
                year,
                AVG(tem_avg) as year_avg_temperature,
                AVG(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as year_avg_precipitation,
                AVG(rhu_avg) as year_avg_humidity
            FROM (
                {build_union_sql_for_tables(climatology_tables, 
                                           f"{'city, cnty,' if cities else ''} year, tem_avg, pre_time_2020, pre_time_0808, rhu_avg",
                                           f"MONTH(observation_time) = {start_dt.month} AND DAY(observation_time) BETWEEN {start_dt.day} AND {end_dt.day} AND {city_condition}")}
            ) AS t
            GROUP BY {'city, cnty,' if cities else ''} year
            """

            sql = f"""
            WITH climatology_base AS (
                {climatology_base_query}
            ),
            climatology_summary AS (
                SELECT 
                    {'city, cnty,' if cities else ''}
                    AVG(year_avg_temperature) as climatology_avg_temperature,
                    AVG(year_avg_precipitation) * {((end_dt - start_dt).days + 1)} as climatology_avg_total_precipitation,
                    AVG(year_avg_humidity) as climatology_avg_humidity,
                    COUNT(DISTINCT year) as climatology_years_count
                FROM climatology_base
                GROUP BY {city_group}
            ),
            current_data AS (
                SELECT {current_select_fields}
                FROM (
                    {build_union_sql_for_tables(current_tables, current_select_fields,
                                               f"{build_date_condition(start_date, end_date)} AND {city_condition}")}
                ) AS t
                GROUP BY {city_group}
            )
            SELECT 
                COALESCE(c.city, cl.city) as city,
                COALESCE(c.cnty, cl.cnty) as cnty,
                c.current_avg_temperature,
                cl.climatology_avg_temperature,
                c.current_avg_temperature - cl.climatology_avg_temperature as temp_anomaly,
                c.current_total_precipitation,
                cl.climatology_avg_total_precipitation,
                c.current_total_precipitation - cl.climatology_avg_total_precipitation as precip_anomaly,
                CASE 
                    WHEN cl.climatology_avg_total_precipitation > 0 
                    THEN ROUND((c.current_total_precipitation - cl.climatology_avg_total_precipitation) * 100.0 / cl.climatology_avg_total_precipitation, 1)
                    ELSE NULL
                END as precip_anomaly_percent,
                c.current_avg_humidity,
                cl.climatology_avg_humidity,
                c.current_avg_humidity - cl.climatology_avg_humidity as humidity_anomaly,
                c.current_days,
                cl.climatology_years_count
            FROM current_data c
            FULL OUTER JOIN climatology_summary cl 
                ON {'c.city = cl.city AND c.cnty = cl.cnty' if cities else '1=1'}
            ORDER BY COALESCE(c.city, cl.city), COALESCE(c.cnty, cl.cnty)
            """
            
        else:
            return await query_comprehensive_weather(start_date, end_date, cities)
        
        result = await _async_execute_query(sql)
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"对比查询失败: {str(e)}",
            "data": None,
            "row_count": 0,
            "query_time": datetime.now().isoformat()
        }

@register_tool   
@tool
async def query_historical_same_period(start_date: str, end_date: str, cities: List[str] = [], 
                                      years_back: int = 5, metrics: List[str] = None) -> Dict[str, Any]:
    """
    查询历史同期数据对比

    Args:
        start_date: 查询开始日期，格式 YYYY-MM-DD
        end_date: 查询结束日期，格式 YYYY-MM-DD
        cities: 城市列表，为空查询所有城市
        years_back: 回溯年数
        metrics: 指标列表，可选：temperature, precipitation, humidity, wind

    Returns:
        dict: 查询结果，包含每年同期的数据对比
    """
    if metrics is None:
        metrics = ["temperature", "precipitation"]
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        city_condition = build_city_conditions(cities)
        city_group = "city, cnty" if cities else "1"
        
        # 构建每年查询的UNION部分
        union_parts = []
        
        for i in range(years_back + 1):
            year_offset = i
            year_start = (start_dt.replace(year=start_dt.year - year_offset)).strftime("%Y-%m-%d")
            year_end = (end_dt.replace(year=end_dt.year - year_offset)).strftime("%Y-%m-%d")
            
            year_tables = get_table_names_by_date_range(year_start, year_end)
            
            # 构建每年的查询字段
            year_fields = []
            if "temperature" in metrics:
                year_fields.extend([
                    f"AVG(tem_avg) as avg_temp_year_{year_offset}",
                    f"MAX(tem_max) as max_temp_year_{year_offset}",
                    f"MIN(tem_min) as min_temp_year_{year_offset}"
                ])
            if "precipitation" in metrics:
                year_fields.extend([
                    f"SUM(COALESCE(pre_time_2020, 0) + COALESCE(pre_time_0808, 0)) as total_precip_year_{year_offset}",
                    f"MAX(pre_max_1h) as max_hourly_precip_year_{year_offset}"
                ])
            if "humidity" in metrics:
                year_fields.extend([
                    f"AVG(rhu_avg) as avg_humidity_year_{year_offset}",
                    f"MIN(rhu_min) as min_humidity_year_{year_offset}"
                ])
            if "wind" in metrics:
                year_fields.extend([
                    f"AVG(win_s_2mi_avg) as avg_wind_speed_year_{year_offset}",
                    f"MAX(win_s_max) as max_wind_speed_year_{year_offset}"
                ])
            
            fields_str = ", ".join(year_fields)
            
            # 构建每年的查询
            year_query = f"""
            SELECT 
                {'city, cnty,' if cities else ''}
                {start_dt.year - year_offset} as year,
                {fields_str},
                COUNT(DISTINCT observation_time) as observation_days
            FROM (
                {build_union_sql_for_tables(year_tables, 
                                           f"{'city, cnty,' if cities else ''} tem_avg, tem_max, tem_min, pre_time_2020, pre_time_0808, pre_max_1h, rhu_avg, rhu_min, win_s_2mi_avg, win_s_max",
                                           f"{build_date_condition(year_start, year_end)} AND {city_condition}")}
            ) AS t
            GROUP BY {city_group}
            """
            
            union_parts.append(year_query)
        
        # 合并所有年份的查询
        union_query = "\nUNION ALL\n".join(union_parts)
        
        # 按城市/地区分组，获取每年的数据
        sql = f"""
        SELECT 
            {'city, cnty,' if cities else ''}
            year,
            {', '.join([f'avg_temp_year_{i}' for i in range(years_back + 1)]) if 'temperature' in metrics else ''}
            {', ' if 'temperature' in metrics and 'precipitation' in metrics else ''}
            {', '.join([f'total_precip_year_{i}' for i in range(years_back + 1)]) if 'precipitation' in metrics else ''}
            {', ' if ('temperature' in metrics or 'precipitation' in metrics) and 'humidity' in metrics else ''}
            {', '.join([f'avg_humidity_year_{i}' for i in range(years_back + 1)]) if 'humidity' in metrics else ''}
            {', ' if ('temperature' in metrics or 'precipitation' in metrics or 'humidity' in metrics) and 'wind' in metrics else ''}
            {', '.join([f'avg_wind_speed_year_{i}' for i in range(years_back + 1)]) if 'wind' in metrics else ''}
        FROM (
            {union_query}
        ) AS all_years
        ORDER BY {'city, cnty,' if cities else ''} year
        """
        
        result = await _async_execute_query(sql)
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"历史同期查询失败: {str(e)}",
            "data": None,
            "row_count": 0,
            "query_time": datetime.now().isoformat()
        }

