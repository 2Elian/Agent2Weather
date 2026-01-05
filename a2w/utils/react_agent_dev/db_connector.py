#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Connector Module
SQL Server数据库连接器
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from logging import Logger


def setup_logger(name: str) -> Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


class SQLServerConnector:
    """SQL Server数据库连接器"""
    
    def __init__(self, host: str, port: str, database: str, username: str, password: str):
        """
        初始化SQL Server连接器
        
        Args:
            host: 数据库主机地址
            port: 数据库端口
            database: 数据库名称
            username: 用户名
            password: 密码
        """
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
        """建立数据库连接池"""
        try:
            import aioodbc
            self.pool = await aioodbc.create_pool(dsn=self.connection_string, autocommit=True)
            self.logger.info("SQL Server connection pool has been established.")
        except Exception as e:
            self.logger.error(f"SQL Server connect failed: {e}")
            raise
    
    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("SQL Server connection pool is closed.")
    
    async def execute_query(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            
        Returns:
            查询结果列表，每个元素是一个字典
        """
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


# 示例使用
if __name__ == "__main__":
    # 创建数据库连接器实例
    db_connector = SQLServerConnector(
        host="localhost",
        port="1433",
        database="weather_db",
        username="sa",
        password="your_password"
    )
    
    # 注意：实际使用时需要在异步环境中运行
    print("数据库连接器已创建")