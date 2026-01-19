import React, { useState, useRef } from 'react';
import { Layout, message, Spin, Typography } from 'antd';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { CloudOutlined } from '@ant-design/icons';
import TaskForm from './components/TaskForm';
import ResultDisplay from './components/ResultDisplay';
import MetadataDrawer from './components/MetadataDrawer';
import PdfReport from './components/PdfReport';
import { generateWeatherReport } from './api/request';
import './App.css';

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

function App() {
  const [loading, setLoading] = useState(false);
  const [resultData, setResultData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [taskType, setTaskType] = useState("气象呈阅件");
  
  const pdfRef = useRef(null);

  const handleTaskSubmit = async (values) => {
    setLoading(true);
    setResultData(null);
    setMetadata(null);
    setTaskType(values.task_type);

    try {
      const response = await generateWeatherReport(values);
      if (response.status === 'success') {
        setResultData(response.data);
        setMetadata(response.metadata);
        message.success(`生成成功！耗时: ${response.metadata.duration}`);
      } else {
        message.error(`生成失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败，请检查网络或后端服务');
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!pdfRef.current) return;
    
    const hideLoading = message.loading('正在生成 PDF...', 0);
    try {
      const element = pdfRef.current;
      element.style.display = 'block';
      
      const canvas = await html2canvas(element, {
        scale: 2, 
        useCORS: true,
        logging: false,
      });
      
      element.style.display = 'none';

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      
      const imgProps = pdf.getImageProperties(imgData);
      const imgHeight = (imgProps.height * pdfWidth) / imgProps.width;
      
      let position = 0;
      pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, imgHeight);
      
      pdf.save(`${taskType}_${new Date().toISOString().split('T')[0]}.pdf`);
      message.success('PDF 导出成功');
    } catch (error) {
      console.error(error);
      message.error('PDF 生成失败');
    } finally {
      hideLoading();
    }
  };

  return (
    <Layout className="layout">
      <Header className="app-header">
        <div className="logo">
          <CloudOutlined style={{ marginRight: '10px', fontSize: '24px' }} />
          <span>A2W: Agent to Weather</span>
        </div>
      </Header>
      <Content className="app-content">
        <div className="content-container">
          <div className="section-title">
            <Title level={2} style={{ margin: 0 }}>智慧气象服务</Title>
            <span className="subtitle">基于Agent-to-Agent的自动化气象服务材料写作助手</span>
          </div>
          
          <div className="main-grid">
             <div className="task-section">
                <TaskForm onFinish={handleTaskSubmit} loading={loading} />
             </div>
             
             <div className="result-section">
                {resultData ? (
                  <ResultDisplay 
                    data={resultData} 
                    onOpenMetadata={() => setDrawerVisible(true)}
                    onExportPdf={handleExportPdf}
                  />
                ) : (
                  <div className="placeholder-box">
                    <CloudOutlined style={{ fontSize: '64px', color: '#d9d9d9', marginBottom: '20px' }} />
                    <div style={{ color: '#999', fontSize: '16px' }}>
                      请在左侧配置任务参数并点击生成报告
                    </div>
                  </div>
                )}
             </div>
          </div>
        </div>
      </Content>
      <Footer style={{ textAlign: 'center', background: 'transparent' }}>
        Agent2Weather | ©2025 | 南京信息工程大学 | 张建伟教授团队
      </Footer>

      <MetadataDrawer 
        visible={drawerVisible} 
        onClose={() => setDrawerVisible(false)} 
        metadata={metadata} 
      />

      {/* Fullscreen Loading Overlay */}
      <Spin spinning={loading} tip="正在生成分析报告，请稍候..." fullscreen size="large" />

      {/* Hidden PDF Render Container - Fixed Width for A4 */}
      <div style={{ position: 'fixed', top: '-10000px', left: '-10000px', width: '794px', background: 'white', zIndex: -1 }}>
         <PdfReport 
            ref={pdfRef} 
            data={resultData} 
            taskType={taskType} 
         />
      </div>
    </Layout>
  );
}

export default App;
