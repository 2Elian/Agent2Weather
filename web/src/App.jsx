import React, { useState, useRef } from 'react';
import { Layout, message, Spin, Typography } from 'antd';
import html2pdf from 'html2pdf.js';
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

  const handleExportPdf = () => {
    if (!pdfRef.current) return;
    
    const element = pdfRef.current;
    // 临时显示元素以便 html2pdf 捕获
    // 我们使用 cloneNode 来避免影响原始 DOM，但 html2pdf 需要元素在文档流中可见
    // 由于我们在 App 中已经将其渲染在一个不可见的 fixed 容器中，我们只需要确保该容器在截图时内容正确
    // html2pdf.js 能够处理这种离屏渲染，只要样式正确。
    
    // 关键配置
    const opt = {
      margin:       10, // mm
      filename:     `${taskType}_${new Date().toISOString().split('T')[0]}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true, logging: false },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] } // 智能分页
    };

    message.loading('正在生成 PDF...', 1);
    
    // 我们不需要手动显示/隐藏，因为该元素已经在页面上（虽然位置偏离）。
    // 但为了确保万无一失，我们可以临时将其移入可视区域（使用 absolute + z-index 覆盖），生成后再移回去
    // 或者直接对那个 off-screen 元素操作。html2canvas 对 off-screen 支持较好。
    
    // 使用 worker API 进行生成
    html2pdf().set(opt).from(element).save().then(() => {
        message.success('PDF 导出成功');
    }).catch(err => {
        console.error(err);
        message.error('PDF 生成失败');
    });
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
      <div style={{ position: 'fixed', top: '-10000px', left: '-10000px', width: '210mm', background: 'white', zIndex: -1 }}>
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
