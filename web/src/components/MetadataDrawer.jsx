import React from 'react';
import { Drawer, Descriptions, Table, Tag, Collapse, Typography, Card, Space } from 'antd';
import ReactMarkdown from 'react-markdown';

const { Panel } = Collapse;
const { Title, Text, Paragraph } = Typography;

const StageDetail = ({ data, stageName, hasSqlData = false }) => {
  if (!data) return <Text type="secondary">暂无数据</Text>;

  const { recall_template, response, think_response, sql_data } = data;

  const sqlColumns = [
    { title: '站名', dataIndex: '站名', key: '站名' },
    { title: '日期', dataIndex: '日期', key: '日期' },
    { title: '时段', dataIndex: '时段', key: '时段' },
    { title: '平均温度', dataIndex: '平均温度', key: '平均温度' },
    { title: '降水量', dataIndex: '总降水量', key: '总降水量' },
    { title: '风速', dataIndex: '平均风速', key: '平均风速' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {recall_template && (
        <Card size="small" title="Prompt 模板 (Recall Template)" type="inner">
           <Paragraph style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
             {recall_template}
           </Paragraph>
        </Card>
      )}

      {hasSqlData && sql_data && (
         <Card size="small" title="数据库查询结果 (SQL Data)" type="inner">
            <Table 
              dataSource={Array.isArray(sql_data) ? sql_data : []} 
              columns={sqlColumns} 
              scroll={{ x: 800 }} 
              pagination={false}
              size="small"
              rowKey={(record) => `${record.站名}-${record.日期}-${record.时段}-${Math.random()}`}
            />
         </Card>
      )}

      {think_response && (
        <Card size="small" title="思考过程 (Think Response)" type="inner" style={{ background: '#fffbe6', borderColor: '#ffe58f' }}>
           <div className="markdown-content">
             <ReactMarkdown>{think_response}</ReactMarkdown>
           </div>
        </Card>
      )}

      {response && (
        <Card size="small" title="生成结果 (Response)" type="inner">
           <div className="markdown-content">
             <ReactMarkdown>{response}</ReactMarkdown>
           </div>
        </Card>
      )}
    </div>
  );
};

const MetadataDrawer = ({ visible, onClose, metadata }) => {
  if (!metadata) return null;

  const { duration, all_state } = metadata;
  const { init_weather_data, history, forecast, suggestion, summary } = all_state || {};

  return (
    <Drawer
      title="执行详情 (Metadata)"
      placement="right"
      width={900}
      onClose={onClose}
      open={visible}
    >
      <Descriptions title="基本信息" bordered column={1}>
        <Descriptions.Item label="总耗时">{duration}</Descriptions.Item>
        <Descriptions.Item label="任务类型">{all_state?.task_type}</Descriptions.Item>
        <Descriptions.Item label="时间范围">{all_state?.start_date} ~ {all_state?.end_date}</Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 24 }}>
        <Title level={5}>天气分析结果 (Init Data)</Title>
        {init_weather_data?.map((station, index) => (
          <Descriptions key={index} bordered size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="站点" span={3}>{station.station_name}</Descriptions.Item>
            <Descriptions.Item label="天气类型" span={3}>
              {station.weather_types?.map(type => (
                <Tag color="blue" key={type}>{type}</Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="预警信息" span={3}>
              <Text type={station.alert?.includes('红') ? 'danger' : 'warning'}>{station.alert}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="判定原因" span={3}>{station.reason}</Descriptions.Item>
          </Descriptions>
        ))}
      </div>

      <div style={{ marginTop: 24 }}>
        <Title level={5}>详细执行链路</Title>
        <Collapse defaultActiveKey={['history', 'forecast']}>
          <Panel header="1. 前期天气实况 (History)" key="history">
            <StageDetail data={history} stageName="History" />
          </Panel>
          <Panel header="2. 具体天气预报 (Forecast)" key="forecast">
             <StageDetail data={forecast} stageName="Forecast" hasSqlData={true} />
          </Panel>
          <Panel header="3. 关注与建议 (Suggestion)" key="suggestion">
             <StageDetail data={suggestion} stageName="Suggestion" />
          </Panel>
          <Panel header="4. 摘要生成 (Summary)" key="summary">
             <StageDetail data={summary} stageName="Summary" />
          </Panel>
        </Collapse>
      </div>
    </Drawer>
  );
};

export default MetadataDrawer;
