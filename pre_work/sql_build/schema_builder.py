# 自动化脚本: 读取config.yaml 自动生成schema.json至data/sql/schema/{database_name}.json
import os
import json
import pyodbc
from pathlib import Path
import yaml
from typing import List, Dict, Any, Optional

class DBSchemaGenerator:
    def __init__(self, host: str, port: str, database: str, username: str, password: str, driver: str = "ODBC Driver 18 for SQL Server"):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.conn = None

    def connect(self):
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

        self.conn = pyodbc.connect(conn_str)

    def get_tables(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE='BASE TABLE'
        """)
        return [row.TABLE_NAME for row in cursor.fetchall()]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        return [{"name": row.COLUMN_NAME, "type": row.DATA_TYPE} for row in cursor.fetchall()]

    def get_primary_keys(self, table_name: str) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT k.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS t
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
            ON t.CONSTRAINT_NAME = k.CONSTRAINT_NAME
            WHERE t.TABLE_NAME='{table_name}' AND t.CONSTRAINT_TYPE='PRIMARY KEY'
        """)
        return [row.COLUMN_NAME for row in cursor.fetchall()]

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT
                k.COLUMN_NAME,
                ccu.TABLE_NAME AS REFERENCED_TABLE_NAME,
                ccu.COLUMN_NAME AS REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
                ON k.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
            JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
                ON ccu.CONSTRAINT_NAME = rc.UNIQUE_CONSTRAINT_NAME
            WHERE k.TABLE_NAME='{table_name}'
        """)
        fks = []
        for row in cursor.fetchall():
            fks.append({
                "column": row.COLUMN_NAME,
                "references_table": row.REFERENCED_TABLE_NAME,
                "references_column": row.REFERENCED_COLUMN_NAME
            })
        return fks

    def generate_schema(self, db_id: str) -> Dict[str, Any]:
        if not self.conn:
            self.connect()

        tables = self.get_tables()

        table_names = []
        table_names_original = []

        column_names = [[-1, "*"]]
        column_names_original = [[-1, "*"]]
        column_types = ["text"]

        primary_keys = []
        foreign_keys = []

        table_id_map = {table: idx for idx, table in enumerate(tables)}
        column_id_map = {}  # (table, column) -> global column index

        col_idx = 1  # 0 是 *

        for table in tables:
            table_id = table_id_map[table]
            table_names.append(table)
            table_names_original.append(table)

            columns = self.get_columns(table)
            for col in columns:
                column_names.append([table_id, col["name"]])
                column_names_original.append([table_id, col["name"]])
                column_types.append(self.map_sql_type(col["type"]))

                column_id_map[(table, col["name"])] = col_idx
                col_idx += 1

        # primary keys
        for table in tables:
            for pk in self.get_primary_keys(table):
                pk_col_id = column_id_map.get((table, pk))
                if pk_col_id is not None:
                    primary_keys.append(pk_col_id)

        # foreign keys
        for table in tables:
            fks = self.get_foreign_keys(table)
            for fk in fks:
                src = column_id_map.get((table, fk["column"]))
                tgt = column_id_map.get((fk["references_table"], fk["references_column"]))
                if src is not None and tgt is not None:
                    foreign_keys.append([src, tgt])

        return {
            "db_id": db_id,
            "table_names": table_names,
            "table_names_original": table_names_original,
            "column_names": column_names,
            "column_names_original": column_names_original,
            "column_types": column_types,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }
    
    @staticmethod
    def map_sql_type(sql_type: str) -> str:
        sql_type = sql_type.lower()
        if "char" in sql_type or "text" in sql_type or "nchar" in sql_type or "nvarchar" in sql_type:
            return "text"
        elif "int" in sql_type:
            return "int"
        elif "decimal" in sql_type or "numeric" in sql_type or "float" in sql_type or "real" in sql_type:
            return "real"
        elif "date" in sql_type or "time" in sql_type:
            return "text"
        else:
            return "text"

    def save_schema(self, schema, save_path=None):
        if save_path is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parents[2]
            save_dir = project_root / "data" / "sql"
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / "schema.json"

        if isinstance(schema, dict):
            schema = [schema]

        # 读取已有数据
        if save_path.exists():
            with open(save_path, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        raise ValueError("schema.json 必须是 list 结构")
                except json.JSONDecodeError:
                    existing = []
        else:
            existing = []

        # 建立 db_id -> schema 映射
        existing_map = {item["db_id"]: item for item in existing if "db_id" in item}

        for new_item in schema:
            db_id = new_item["db_id"]
            if db_id in existing_map:
                # 合并表
                old_item = existing_map[db_id]

                # 合并 table_names
                old_tables_set = set(old_item["table_names"])
                for t_name in new_item["table_names"]:
                    if t_name not in old_tables_set:
                        old_item["table_names"].append(t_name)
                        old_item["table_names_original"].append(t_name)

                # 合并 columns
                # 保留现有列，新增列追加
                old_col_set = set((col[0], col[1]) for col in old_item["column_names"])
                col_idx_start = len(old_item["column_names"])
                for idx, col in enumerate(new_item["column_names"]):
                    if tuple(col) not in old_col_set:
                        old_item["column_names"].append(col)
                        old_item["column_names_original"].append(new_item["column_names_original"][idx])
                        old_item["column_types"].append(new_item["column_types"][idx])

                # 合并 primary_keys
                old_pks_set = set(old_item.get("primary_keys", []))
                for pk in new_item.get("primary_keys", []):
                    if pk not in old_pks_set:
                        old_item["primary_keys"].append(pk)

                # 合并 foreign_keys
                old_fks_set = set(tuple(fk) for fk in old_item.get("foreign_keys", []))
                for fk in new_item.get("foreign_keys", []):
                    if tuple(fk) not in old_fks_set:
                        old_item["foreign_keys"].append(fk)

                print(f"[update] db_id '{db_id}' merged with new tables/columns if any")
            else:
                existing.append(new_item)
                print(f"[add] db_id '{db_id}' added")

        # 写回文件
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4, ensure_ascii=False)

        print(f"[ok] schema saved to {save_path}")

            
def load_config_from_yaml(yaml_file: str) -> Dict[str, str]:
    with open(yaml_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

if __name__ == "__main__":
    current_file = Path(__file__).resolve()
    yaml_path = current_file.parent / "config.yaml"
    cfg = load_config_from_yaml(yaml_path)["sqlserver"]

    generator = DBSchemaGenerator(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        username=cfg["user"],
        password=cfg["password"]
    )

    schema = generator.generate_schema(db_id=cfg["database"])
    generator.save_schema(schema)
    print("done:")