import React, { useState } from 'react';
import { Form, Select, DatePicker, Button, Card, message } from 'antd';
import { fetchStations } from '../api/request';

const { Option } = Select;
const { RangePicker } = DatePicker;

const TaskForm = ({ onFinish, loading }) => {
  const [form] = Form.useForm();
  const [stationOptions, setStationOptions] = useState([]);
  const [fetchingStations, setFetchingStations] = useState(false);

  const handleSubmit = (values) => {
    const formattedValues = {
      ...values,
      start_date: values.date_range[0].format('YYYY-MM-DD'),
      end_date: values.date_range[1].format('YYYY-MM-DD'),
      date_range: undefined, // Remove the range object
    };
    onFinish(formattedValues);
  };

  const handleDateChange = async (dates) => {
    if (!dates || dates.length !== 2) {
      setStationOptions([]);
      return;
    }
    
    const startDate = dates[0].format('YYYY-MM-DD');
    const endDate = dates[1].format('YYYY-MM-DD');
    
    setFetchingStations(true);
    setStationOptions([]); // Clear previous options
    
    try {
        const response = await fetchStations(startDate, endDate);
        if (response.status === 'success') {
             const stations = response.data.stations || [];
             setStationOptions(stations);
             if (stations.length === 0) {
                 message.warning("该时间段内未找到历史可用站点");
             } else {
                 message.success(`已加载 ${stations.length} 个可用站点`);
             }
        } else {
             message.error("获取站点列表失败");
        }
    } catch (error) {
        console.error(error);
        message.error("获取站点列表出错，请检查后端服务");
    } finally {
        setFetchingStations(false);
    }
  };

  return (
    <Card title="任务配置" className="task-form-card">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          task_type: "气象呈阅件",
        }}
      >
        <Form.Item
          name="task_type"
          label="任务类型"
          rules={[{ required: true, message: '请选择任务类型' }]}
        >
          <Select disabled>
            <Option value="气象呈阅件">气象呈阅件</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="date_range"
          label="日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
        >
          <RangePicker style={{ width: '100%' }} onChange={handleDateChange} />
        </Form.Item>

        <Form.Item
          name="station_names"
          label="自动站名称"
          rules={[{ required: true, message: '请选择自动站' }]}
        >
          <Select 
            mode="multiple" 
            placeholder={fetchingStations ? "正在加载站点..." : "请先选择日期范围"} 
            loading={fetchingStations}
            allowClear
          >
            {stationOptions.map(station => (
              <Option key={station} value={station}>{station}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            生成报告
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default TaskForm;
