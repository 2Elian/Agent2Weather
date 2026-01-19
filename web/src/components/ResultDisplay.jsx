import React from 'react';
import { Card, Typography, Button, Space, Divider } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const ResultDisplay = ({ data, onOpenMetadata, onExportPdf }) => {
  if (!data) return null;

  const { final_brief, summary, history, forecast, suggestion } = data;

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
        <Paragraph>{summary}</Paragraph>

        <Divider orientation="left">前期天气实况</Divider>
        <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{history}</Paragraph>

        <Divider orientation="left">具体天气预报</Divider>
        <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{forecast}</Paragraph>

        <Divider orientation="left">关注与建议</Divider>
        <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{suggestion}</Paragraph>
      </div>
    </Card>
  );
};

export default ResultDisplay;
