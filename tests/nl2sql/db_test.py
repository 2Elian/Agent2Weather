from typing import List, Optional, Dict, Any
from a2w.api.middleware.db.sql_connector import SQLServerConnector
from a2w.smw.managers.weather_classifier import WeatherClassifier
import asyncio

class TestDB:
    def __init__(self, db: SQLServerConnector):
        self.db = db

    @classmethod
    async def create(cls, host: str, port: str, database: str, username: str, password: str) -> "TestDB":
        db = SQLServerConnector(host, port, database, username, password)
        await db.connect()
        return cls(db)

    async def close(self):
        await self.db.close()
    
    async def query_weather_metrics_test(self, regions: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        # done
        """
        Example Return Data:
            [{'station_name': '高安相城', 'avg_temp': Decimal('7.893750'), 'min_temp': Decimal('-3.5'), 'max_temp': Decimal('23.0'), 'total_precip': None, 'max_wind_speed': Decimal('6.2'), 'min_visibility': 999999, 'avg_humidity': Decimal('61.012500')}, {'station_name': '袁州金瑞庙前', 'avg_temp': Decimal('8.615625'), 'min_temp': Decimal('-2.9'), 'max_temp': Decimal('23.5'), 'total_precip': None, 'max_wind_speed': Decimal('1.8'), 'min_visibility': 999999, 'avg_humidity': Decimal('60.350000')}]
        """
        return await self.db.query_weather_metrics(regions, start_date, end_date)
    
    async def weather_type_judge_node(self, regions: List[str], start_date: str, end_date: str) -> Any:
        # done
        """
        Example Return Data:
            [{'station_name': '高安相城', 'weather_types': ['低温', '霜冻', '轻雾', '晴冷'], 'primary_type': '低温', 'reason': '低温: 0.0℃；霜冻: 最低温0.0℃；最小能见度: 10000m', 'severity': '轻度天气', 'alert': '蓝色
            预警：请注意天气变化', 'suggestions': [], 'metrics_summary': {'avg_temp': 0.0, 'precip': 0.0, 'max_wind_speed': 0.0, 'min_visibility': 10000.0}}, {'station_name': '袁州金瑞庙前', 'weather_types': ['低温', 
            '霜冻', '轻雾', '晴冷'], 'primary_type': '低温', 'reason': '低温: 0.0℃；霜冻: 最低温0.0℃；最小能见度: 10000m', 'severity': '轻度天气', 'alert': '蓝色预警：请注意天气变化', 'suggestions': [], 'metrics_summary': {'avg_temp': 0.0, 'precip': 0.0, 'max_wind_speed': 0.0, 'min_visibility': 10000.0}}]
        """
        metrics_data = await self.db.query_weather_metrics(
            regions=regions,
            start_date=start_date,
            end_date=end_date
        )
        metrics = WeatherClassifier.parse_sql_result(metrics_data)
        analyst_result = WeatherClassifier.classify_stations(metrics)
        return analyst_result
    
    async def query_detailed_weather_from_hourTable(self, regions: List[str], start_date: str, end_date: str) -> Any:
        # done
        """
        Example Return Data:
            too many
            all 6 SQL logics have passed.
        """
        metrics_data = await self.db.query_detailed_weather_from_hourTable(
            regions=regions,
            start_date=start_date,
            end_date=end_date,
            aggregation="half",
            station_name_to_cnty=True
        )
        return metrics_data
        
    

async def main():
    test_db = await TestDB.create(
        host="172.16.107.15",
        port="1433",
        database="A2W_YiChun",
        username="sa",
        password="YourStrong!Passw0rd"
    )

    try:
        result = await test_db.query_detailed_weather_from_hourTable(
            regions=["袁州金瑞庙前", "袁州辽市"],
            start_date="2025-06-10",
            end_date="2025-06-28",
        )
        print(result)
    finally:
        await test_db.close() 

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())