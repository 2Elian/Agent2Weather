import React, { forwardRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './PdfReport.css';

const PdfReport = forwardRef(({ data, taskType }, ref) => {
  if (!data) return null;

  const { final_brief, summary, history, forecast, suggestion } = data;

  // Helper to remove duplicate headers if they exist in markdown content
  const cleanContent = (content, headerPrefix) => {
    if (!content) return "";
    const regex = new RegExp(`^#*\\s*${headerPrefix}.*`, 'm');
    return content.replace(regex, '').trim();
  };

  return (
    <div ref={ref} className="pdf-report-container">
      {/* 大红头 */}
      <div className="pdf-header-large">
        {taskType || "气象呈阅件"}
      </div>
      
      {/* 红线 */}
      <div className="pdf-red-line"></div>

      {/* 小红头 (简短标题) */}
      <div className="pdf-header-small">
        {final_brief}
      </div>

      <div className="pdf-content">
        {/* 摘要 */}
        <div className="pdf-section">
            <div className="pdf-text markdown-body">
                <ReactMarkdown>{summary}</ReactMarkdown>
            </div>
        </div>

        {/* 前期天气实况 */}
        <div className="pdf-section">
          <div className="pdf-section-title">一、前期天气实况</div>
          <div className="pdf-text-block markdown-body">
            <ReactMarkdown>{cleanContent(history, "一、")}</ReactMarkdown>
          </div>
        </div>

        {/* 具体天气预报 */}
        <div className="pdf-section">
          <div className="pdf-section-title">二、具体天气预报</div>
          <div className="pdf-text-block markdown-body">
            <ReactMarkdown>{cleanContent(forecast, "二、")}</ReactMarkdown>
          </div>
        </div>

        {/* 关注与建议 */}
        <div className="pdf-section">
          <div className="pdf-section-title">三、关注与建议</div>
          <div className="pdf-text-block markdown-body">
            <ReactMarkdown>{cleanContent(suggestion, "三、")}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
});

export default PdfReport;
