# 前端开发指南 - 气象服务材料写作系统 (Weather-Agent-YiChun)

本文档旨在指导前端开发人员基于 `a2w` 后端 API 构建气象呈阅件生成页面。

## 1. 技术栈要求
- **框架**: React
- **UI 组件库**: 推荐 Ant Design (Antd) 或类似的现代化组件库
- **PDF 生成**: `react-pdf` / `jspdf` + `html2canvas` / `print-js` (前端生成预览)
- **HTTP 客户端**: Axios

---

## 2. API 接口文档

### 2.1 生成气象呈阅件
执行完整的工作流，生成包含实况、预报、建议、摘要等全套内容的报告。

- **URL**: `/smw/WeatherReport` (具体前缀请参考后端配置，默认为 `/api/v1` 或直接根路径，需确认 `global_config.py`)
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (Request Body)

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `task_type` | string | 是 | 任务类型 | `"气象呈阅件"` |
| `start_date` | string | 是 | 开始日期 (YYYY-MM-DD) | `"2025-06-08"` |
| `end_date` | string | 是 | 结束日期 (YYYY-MM-DD) | `"2025-06-12"` |
| `station_names` | array | 是 | 自动站名称列表 | `["赤岸观下气象观测站", "丰城秀市座山"]` |

**注意**: `station_names` 前端需做限制，当前仅支持从 `["赤岸观下气象观测站", "丰城秀市座山", "其他"]` 中进行多选。

#### 响应结构 (Response Body)

```json
{
  "status": "success", // 或 "failed"
  "data": {
    "history": "文本内容...",       // 前期天气实况
    "forecast": "文本内容...",      // 具体天气预报
    "suggestion": "文本内容...",    // 关注与建议
    "summary": "文本内容...",       // 摘要
    "final_brief": "文本内容..."    // 简短标题/概况
  },
  "error": null, // 失败时为错误信息字符串
  "metadata": {
    "duration": "150.23s", // 总耗时
    "all_state": {
       // 包含详细的执行状态、中间数据、思考过程等
       "init_weather_data": [...], // 天气分类结果
       "history": {
           "think_response": "AI思考过程...",
           "response": "...",
           "sql_data": [...] // 执行的SQL及结果
       },
       "forecast": { ... }
       // ... 其他步骤状态
    }
  }
}
```

---

## 3. 页面功能需求

### 3.1 任务配置区域 (Input Form)
页面顶部或左侧应放置配置表单，包含以下控件：
1.  **任务类型**: 下拉选择或固定显示，默认为 "气象呈阅件"。
2.  **日期范围**: 日期范围选择器 (RangePicker)，选择 `start_date` 和 `end_date`。
3.  **自动站名称**: 多选下拉框 (Select with multiple mode)。
    *   **选项**: `赤岸观下气象观测站`, `丰城秀市座山`, `其他`。
4.  **提交按钮**: 点击后调用 API，按钮需进入 Loading 状态，因为生成过程可能较长（预计 1-3 分钟）。

### 3.2 结果展示区域 (Result Display)
API 返回成功后，在页面主体区域展示生成结果。

#### A. 核心文本展示
将 `data` 字段中的各部分内容分块展示，支持简单的文本编辑（可选）：
*   **标题**: `final_brief`
*   **摘要**: `summary`
*   **实况**: `history`
*   **预报**: `forecast`
*   **建议**: `suggestion`

#### B. Metadata 可视化 (重要)
由于 `metadata` 包含大量技术细节（AI 思考过程、SQL 数据），需设计美观的交互来展示，避免页面杂乱。建议采用 **“抽屉 (Drawer)”** 或 **“折叠面板 (Collapse)”** 的形式。

*   **整体色调**: 白色/极简风格。
*   **耗时**: 醒目展示 `metadata.duration`。
*   **AI 思考过程 (`think_response`)**:
    *   通常包含 AI 的推理逻辑，文本较长。
    *   建议使用 Markdown 渲染组件展示。
    *   提供“查看思考过程”的按钮，点击展开。
*   **SQL 数据 (`sql_data`)**:
    *   以表格形式展示查询到的气象数据。
    *   支持横向滚动，因为字段可能较多。
*   **天气分析 (`init_weather_data`)**:
    *   展示每个站点的天气标签（如“低温”、“霜冻”）。
    *   使用 Tag 组件展示 `weather_types`。
    *   展示预警信息 (`alert`)，根据级别显示不同颜色（蓝/黄/橙/红）。

---

## 4. PDF 报告生成规范

前端需基于生成的内容渲染一个符合公文规范的预览页面，并支持导出为 PDF。

### 4.1 排版顺序与样式
文档需严格按照以下顺序排列：

1.  **任务类型 (大红头)**
    *   **内容**: 对应表单中的 `task_type` (如 "气象呈阅件")。
    *   **样式**: 
        *   字体: 方正小标宋简体 (或类似的衬线体)。
        *   字号: 一号或二号 (极大)。
        *   颜色: 红色 (#FF0000)。
        *   对齐: 居中。
        *   下划线: 红色横线贯通版面 (可选，视具体公文规范定)。

2.  **简短标题 (小红头)**
    *   **内容**: 对应 `data.final_brief`。
    *   **样式**:
        *   字体: 黑体或楷体。
        *   字号: 三号。
        *   颜色: 红色 (#FF0000)。
        *   对齐: 居中。
        *   间距: 与大红头保持一定距离。

3.  **正文内容** (黑色字体，仿宋或楷体，三号字)
    *   **摘要 (`summary`)**: 通常作为开篇段落。
    *   **前期天气实况 (`history`)**: 一级标题加粗，内容换行。
    *   **具体天气预报 (`forecast`)**: 一级标题加粗，内容换行。
    *   **关注与建议 (`suggestion`)**: 一级标题加粗，内容换行。

### 4.2 渲染建议
*   创建一个专门的不可见 `div` 或独立的预览路由用于 PDF 渲染。
*   使用 CSS `@media print` 控制打印样式，隐藏页面上的按钮、表单等无关元素。
*   **PDF 导出**: 调用浏览器打印功能 (`window.print()`) 并选择“另存为 PDF”，或使用 `html2canvas` + `jspdf` 截图生成。

---

## 5. Mock 数据示例

```json
{
    "status": "success",
    "data": {
        "history": "12月以来，全市平均降雨量8.3毫米...",
        "forecast": "预计未来一周我市将出现连续阴雨天气...",
        "suggestion": "1. 防范低温对农业的影响...\n2. 注意交通安全...",
        "summary": "本周我市前晴后雨，气温先升后降...",
        "final_brief": "未来一周多阴雨天气 需防范强对流"
    },
    "error": null,
    "metadata": {
        "duration": "150.23s",
        "all_state": {
            "task_type": "气象呈阅件",
            "start_date": "2025-06-08",
            "end_date": "2025-06-12",
            "station_names": ["赤岸观下气象观测站", "丰城秀市座山"],
            "init_weather_data": [
                {
                    "station_name": "赤岸观下气象观测站",
                    "weather_types": ["低温", "霜冻", "轻雾"],
                    "primary_type": "低温",
                    "reason": "低温: 0.0℃；霜冻: 最低温0.0℃",
                    "severity": "轻度天气",
                    "alert": "蓝色预警：请注意天气变化",
                    "metrics_summary": {
                        "avg_temp": 0.0,
                        "precip": 0.0,
                        "max_wind_speed": 0.0,
                        "min_visibility": 10000.0
                    }
                }
            ],
            "history": {
                "status": "success",
                "response": "12月以来，全市平均降雨量8.3毫米...",
                "think_response": "首先查询历史降水数据...然后对比常年同期...",
                "recall_template": "模版内容..."
            },
            "forecast": {
                "status": "success",
                "recall_template": "模版内容...",
                "sql_data": [
                    {
                        "站名": "丰城市",
                        "日期": "2025-06-08",
                        "时段": "上午",
                        "平均温度": 27.9,
                        "平均气压": 993.9,
                        "平均相对湿度": 94,
                        "总降水量": 11999988.0,
                        "平均风速": 0.6
                    }
                ],
                "response": "预计未来一周..."
            }
        }
    }
}
```
