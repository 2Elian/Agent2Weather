# 前端 Web 应用开发计划

我将基于您提供的开发指南，使用 React + Vite + Ant Design 构建前端应用。以下是详细的实施计划：

## 1. 项目初始化
- 在当前目录下创建 `web` 文件夹。
- 使用 Vite 初始化 React 项目模板。
- 安装核心依赖：
  - `antd`: UI 组件库
  - `axios`: 处理 API 请求
  - `dayjs`: 日期处理（Antd 默认支持）
  - `react-markdown`: 渲染 AI 思考过程
  - `html2canvas` + `jspdf`: 生成 PDF 报告
  - `@ant-design/icons`: 图标库

## 2. 项目结构设计
```
web/
  src/
    api/
      request.js       # Axios 封装
    components/
      TaskForm.jsx     # 任务配置表单
      ResultDisplay.jsx # 结果展示主区域
      MetadataDrawer.jsx # 详细信息抽屉 (思考过程、SQL数据)
      PdfReport.jsx    # 隐藏的 PDF 打印模板
    App.jsx            # 主应用入口
    App.css            # 全局样式与打印样式
```

## 3. 关键功能实现
- **交互表单**: 实现日期范围选择、多选站点（限制选项为指南中指定的三个）。
- **结果展示**: 分块展示实况、预报、建议等内容，支持查看 Metadata。
- **Metadata 可视化**: 使用抽屉展示 AI 思考过程（Markdown 渲染）和 SQL 数据表格。
- **PDF 生成**:
  - 实现符合公文规范的红头文件排版。
  - 集成 PDF 导出功能，支持一键下载。

## 4. 样式与主题
- 整体采用白色/极简风格。
- 针对 PDF 报告部分编写专门的 CSS，确保打印效果符合公文要求（红头、字体大小等）。

待您确认后，我将立即开始执行创建和代码编写工作。