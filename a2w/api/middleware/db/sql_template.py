
# 小时表按逐小时数据返回
TABLE_HOUR_HOURLY: str = """
SELECT 
    station_name,
    observation_time,
    temperature AS 气温,
    pressure AS 气压,
    pressure_sea AS 海平面气压,
    relative_humidity AS 相对湿度,
    rainfall AS 降水量,
    wind_speed AS 风速,
    visibility AS 水平能见度
FROM {table_name}
WHERE station_name IN ({placeholders}) 
AND observation_time >= ? 
AND observation_time <= ?
ORDER BY station_name, observation_time
        """
# 小时表按逐小时数据返回 并以cnty进行过滤
TABLE_HOUR_HOURLY_CNTY: str = """
-- 小时表，按县聚合
WITH station_hourly AS (
    SELECT
        station_name,
        cnty,
        observation_time,
        ROUND(temperature, 1) AS 气温,
        ROUND(pressure, 1) AS 气压,
        ROUND(pressure_sea, 1) AS 海平面气压,
        ROUND(relative_humidity, 1) AS 相对湿度,
        ROUND(rainfall, 1) AS 降水量,
        ROUND(wind_speed, 1) AS 风速,
        ROUND(visibility, 1) AS 水平能见度
    FROM {table_name}
    WHERE station_name IN ({placeholders})
        AND observation_time >= ?
        AND observation_time <= ?
)
SELECT
    cnty AS 站名,
    observation_time AS 时间,
    ROUND(AVG(气温), 1) AS 气温,
    ROUND(AVG(气压), 1) AS 气压,
    ROUND(AVG(海平面气压), 1) AS 海平面气压,
    ROUND(AVG(相对湿度), 1) AS 相对湿度,
    ROUND(SUM(降水量), 1) AS 降水量,
    ROUND(AVG(风速), 1) AS 风速,
    ROUND(AVG(水平能见度), 1) AS 水平能见度
FROM station_hourly
GROUP BY cnty, observation_time
ORDER BY cnty, observation_time;
        """

TABLE_HOUR_HALF: str = """
SELECT
    station_name,
    CAST(observation_time AS date) AS 日期,
    CASE WHEN DATEPART(hour, observation_time) < 12 THEN '上午' ELSE '下午' END AS 时段,
    ROUND(AVG(temperature), 1) AS 平均温度,
    ROUND(AVG(pressure), 1) AS 平均气压,
    ROUND(AVG(pressure_sea), 1) AS 平均海平面气压,
    ROUND(AVG(relative_humidity), 1) AS 平均相对湿度,
    ROUND(SUM(rainfall), 1) AS 总降水量,
    ROUND(AVG(wind_speed), 1) AS 平均风速,
    ROUND(AVG(visibility), 1) AS 平均水平能见度
FROM {table_name}
WHERE station_name IN ({placeholders}) 
AND observation_time >= ? 
AND observation_time <= ?
GROUP BY
    station_name,
    CAST(observation_time AS date),
    CASE WHEN DATEPART(hour, observation_time) < 12 THEN '上午' ELSE '下午' END
ORDER BY
    station_name,
    日期,
    时段;
    """

TABLE_HOUR_HALF_CNTY: str = """
-- 上午/下午表，按县聚合
WITH station_half AS (
    SELECT
        station_name,
        cnty,
        CAST(observation_time AS date) AS 日期,
        CASE WHEN DATEPART(hour, observation_time) < 12 THEN '上午' ELSE '下午' END AS 时段,
        ROUND(AVG(temperature), 1) AS 平均温度,
        ROUND(AVG(pressure), 1) AS 平均气压,
        ROUND(AVG(pressure_sea), 1) AS 平均海平面气压,
        ROUND(AVG(relative_humidity), 1) AS 平均相对湿度,
        ROUND(SUM(rainfall), 1) AS 总降水量,
        ROUND(AVG(wind_speed), 1) AS 平均风速,
        ROUND(AVG(visibility), 1) AS 平均水平能见度
    FROM {table_name}
    WHERE station_name IN ({placeholders})
        AND observation_time >= ?
        AND observation_time <= ?
    GROUP BY station_name, cnty, CAST(observation_time AS date),
                CASE WHEN DATEPART(hour, observation_time) < 12 THEN '上午' ELSE '下午' END
)
SELECT
    cnty AS 站名,
    日期,
    时段,
    ROUND(AVG(平均温度), 1) AS 平均温度,
    ROUND(AVG(平均气压), 1) AS 平均气压,
    ROUND(AVG(平均海平面气压), 1) AS 平均海平面气压,
    ROUND(AVG(平均相对湿度), 1) AS 平均相对湿度,
    ROUND(SUM(总降水量), 1) AS 总降水量,
    ROUND(AVG(平均风速), 1) AS 平均风速,
    ROUND(AVG(平均水平能见度), 1) AS 平均水平能见度
FROM station_half
GROUP BY cnty, 日期, 时段
ORDER BY cnty, 日期, 时段;
"""

TABLE_HOUR_DAY: str = """
SELECT
    station_name,
    CAST(observation_time AS date) AS 日期,
    ROUND(AVG(temperature), 1) AS 日平均温度,
    ROUND(AVG(pressure), 1) AS 日平均气压,
    ROUND(AVG(pressure_sea), 1) AS 日平均海平面雅琪,
    ROUND(AVG(relative_humidity), 1) AS 日平均相对湿度,
    ROUND(SUM(rainfall), 1) AS 日平均降水量,
    ROUND(AVG(wind_speed), 1) AS 日平均风速,
    ROUND(AVG(visibility), 1) AS 日平均水平能见度
FROM {table_name}
WHERE station_name IN ({placeholders}) 
AND observation_time >= ? 
AND observation_time <= ?
GROUP BY station_name, CAST(observation_time AS date)
ORDER BY station_name, 日期;
"""

TABLE_HOUR_DAY_CNTY: str = """
-- 日表，按县聚合
WITH station_daily AS (
    SELECT
        station_name,
        cnty,
        CAST(observation_time AS date) AS 日期,
        ROUND(AVG(temperature), 1) AS 日平均温度,
        ROUND(AVG(pressure), 1) AS 日平均气压,
        ROUND(AVG(pressure_sea), 1) AS 日平均海平面气压,
        ROUND(AVG(relative_humidity), 1) AS 日平均相对湿度,
        ROUND(SUM(rainfall), 1) AS 日降水量,
        ROUND(AVG(wind_speed), 1) AS 日平均风速,
        ROUND(AVG(visibility), 1) AS 日平均水平能见度
    FROM {table_name}
    WHERE station_name IN ({placeholders})
        AND observation_time >= ?
        AND observation_time <= ?
    GROUP BY station_name, cnty, CAST(observation_time AS date)
)
SELECT
    cnty AS 站名,
    日期,
    ROUND(AVG(日平均温度), 1) AS 日平均温度,
    ROUND(AVG(日平均气压), 1) AS 日平均气压,
    ROUND(AVG(日平均海平面气压), 1) AS 日平均海平面气压,
    ROUND(AVG(日平均相对湿度), 1) AS 日平均相对湿度,
    ROUND(SUM(日降水量), 1) AS 日降水量,
    ROUND(AVG(日平均风速), 1) AS 日平均风速,
    ROUND(AVG(日平均水平能见度), 1) AS 日平均水平能见度
FROM station_daily
GROUP BY cnty, 日期
ORDER BY cnty, 日期;
"""


SQL_TEMPLATE = {
    "hour_table": {
        "hourly": {
            "by_station": TABLE_HOUR_HOURLY,
            "by_county": TABLE_HOUR_HOURLY_CNTY
        },
        "half": {
            "by_station": TABLE_HOUR_HALF,
            "by_county": TABLE_HOUR_HALF_CNTY
        },
        "daily": {
            "by_station": TABLE_HOUR_DAY,
            "by_county": TABLE_HOUR_DAY_CNTY
        }
    }
}