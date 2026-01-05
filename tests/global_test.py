import random
from datetime import datetime
import calendar

start_year = 1949
end_year = 2023

stations = [
    "万载杨源村","宜丰谭山院前","靖安中源","高安上湖","樟树张家山","袁州慈化",
    "宜丰花桥","万载县西坑村气象观测站","宜丰谭山院前","铜鼓大漕","万载白良","奉新赤田",
    "万载洞口村","上高","万载红旗村","高安新街","袁州金瑞庙前","高安汪家圩",
    "樟树吴城","樟树洞塘","靖安仁首","高安华林","樟树洋湖","高安八景",
    "袁州飞剑潭","奉新赤岸","铜鼓新开","万载白良","铜鼓英朝","万载沙潭村",
    "樟树义成","上高工业园镜山口","铜鼓正坑","樟树","丰城焦坑曲源","奉新会埠渣村",
    "铜鼓浒村","高安伍桥","高安荷岭","樟树"
]

cntys = [
    "万载县","宜丰县","靖安县","高安市","樟树市","袁州区","宜丰县","万载县","宜丰县","铜鼓县",
    "万载县","奉新县","万载县","上高县","万载县","高安市","袁州区","高安市","樟树市","樟树市",
    "靖安县","高安市","樟树市","高安市","袁州区","奉新县","铜鼓县","万载县","铜鼓县","万载县",
    "樟树市","上高县","铜鼓县","樟树市","丰城市","奉新县","铜鼓县","高安市","高安市","樟树市"
]

fields = {
    "id": "int",
    "station_name": "nvarchar",
    "station_number": "nvarchar",
    "town": "nvarchar",
    "rep_corr_id": "nvarchar",
    "province": "nvarchar",
    "city": "nvarchar",
    "cnty": "nvarchar",
    "observation_time": "datetime",
    "lat": "numeric",
    "lon": "numeric",
    "alti": "numeric",
    "prs_sensor_alti": "numeric",
    "station_levl": "int",
    "admin_code_chn": "nvarchar",
    "year": "int",
    "mon": "int",
    "day": "int",
    "prs_avg": "numeric",
    "prs_max": "numeric",
    "prs_max_otime": "nvarchar",
    "prs_min": "numeric",
    "prs_min_otime": "nvarchar",
    "prs_sea_avg": "numeric",
    "tem_avg": "numeric",
    "tem_max": "numeric",
    "tem_max_otime": "nvarchar",
    "tem_min": "numeric",
    "tem_min_otime": "nvarchar",
    "vap_avg": "numeric",
    "rhu_avg": "numeric",
    "rhu_min": "numeric",
    "rhu_min_otime": "nvarchar",
    "clo_cov_avg": "numeric",
    "clo_cov_low_avg": "numeric",
    "vis_min": "numeric",
    "vis_min_otime": "nvarchar",
    "pre_max_1h": "numeric",
    "pre_max_1h_otime": "nvarchar",
    "input_time": "datetime"
}

def rand_value(field_type):
    if field_type == "int":
        return random.randint(1, 1000)
    elif field_type == "numeric":
        return round(random.uniform(0, 100), 2)
    elif field_type == "nvarchar":
        return "示例"
    elif field_type == "datetime":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        return "示例"

output_file = "insert_station_full.sql"

with open(output_file, "w", encoding="utf-8") as f:
    for year in range(start_year, end_year+1):
        table_name = f"automatic_station_his_day_data_{year}"
        f.write(f"-- 插入 {table_name}\n")
        for i, station in enumerate(stations):
            for month in range(1, 13):  # 遍历每个月
                _, last_day = calendar.monthrange(year, month)  # 获取当月天数
                for day in range(1, last_day+1):
                    values = []
                    for field, ftype in fields.items():
                        if field == "station_name":
                            values.append(f"'{station}'")
                        elif field == "province":
                            values.append("'江西省'")
                        elif field == "city":
                            values.append("'宜春市'")
                        elif field == "cnty":
                            values.append(f"'{cntys[i]}'")
                        elif field == "observation_time":
                            values.append(f"'{year}-{month:02d}-{day:02d} 08:00:00'")
                        elif field == "year":
                            values.append(str(year))
                        elif field == "mon":
                            values.append(str(month))
                        elif field == "day":
                            values.append(str(day))
                        else:
                            val = rand_value(ftype)
                            if ftype in ["int", "numeric"]:
                                values.append(str(val))
                            else:
                                values.append(f"'{val}'")
                    sql = f"INSERT INTO {table_name} ({', '.join(fields.keys())})\nVALUES ({', '.join(values)});\n"
                    f.write(sql)

print(f"完整 SQL 已生成到 {output_file}")
