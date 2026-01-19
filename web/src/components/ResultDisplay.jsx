import React from 'react';
import { Card, Typography, Button, Space, Divider } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { Title, Paragraph } = Typography;

const ResultDisplay = ({ data, onOpenMetadata, onExportPdf }) => {
  if (!data) return null;

  const { final_brief, summary, history, forecast, suggestion } = data;

  // Helper to remove duplicate headers if they exist in markdown content
  const cleanContent = (content, headerPrefix) => {
    if (!content) return "";
    // Remove lines that start with the header prefix (e.g. "一、", "## 一、")
    // This is a simple heuristic; more robust parsing might be needed if format varies greatly
    const regex = new RegExp(`^#*\\s*${headerPrefix}.*`, 'm');
    return content.replace(regex, '').trim();
  };

  return (
    <Card 
      title="生成结果" 
      className="result-card"
      extra={
        <Space>
          <Button icon={<FileTextOutlined />} onClick={onOpenMetadata}>
            查看详情 (Metadata)
          </Button>
          <Button type="primary" icon={<DownloadOutlined />} onClick={onExportPdf}>
            导出 PDF
          </Button>
        </Space>
      }
    >
      <div className="result-content">
        <Title level={4} style={{ textAlign: 'center', color: '#cf1322' }}>{final_brief}</Title>
        
        <Divider orientation="left">摘要</Divider>
        <div className="markdown-body">
            <ReactMarkdown>{summary}</ReactMarkdown>
        </div>

        <Divider orientation="left">前期天气实况</Divider>
        <div className="markdown-body">
            <ReactMarkdown>{cleanContent(history, "一、")}</ReactMarkdown>
        </div>

        <Divider orientation="left">具体天气预报</Divider>
        <div className="markdown-body">
            <ReactMarkdown>{cleanContent(forecast, "二、")}</ReactMarkdown>
        </div>

        <Divider orientation="left">关注与建议</Divider>
        <div className="markdown-body">
            <ReactMarkdown>{cleanContent(suggestion, "三、")}</ReactMarkdown>
        </div>
      </div>
    </Card>
  );
};

export default ResultDisplay;
