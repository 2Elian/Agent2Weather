import React, { forwardRef } from 'react';
import './PdfReport.css';

const PdfReport = forwardRef(({ data, taskType }, ref) => {
  if (!data) return null;

  const { final_brief, summary, history, forecast, suggestion } = data;

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
            <p className="pdf-text">{summary}</p>
        </div>

        {/* 前期天气实况 */}
        <div className="pdf-section">
          <div className="pdf-section-title">一、前期天气实况</div>
          <div className="pdf-text-block">
            {history}
          </div>
        </div>

        {/* 具体天气预报 */}
        <div className="pdf-section">
          <div className="pdf-section-title">二、具体天气预报</div>
          <div className="pdf-text-block">
            {forecast}
          </div>
        </div>

        {/* 关注与建议 */}
        <div className="pdf-section">
          <div className="pdf-section-title">三、关注与建议</div>
          <div className="pdf-text-block">
            {suggestion}
          </div>
        </div>
      </div>
    </div>
  );
});

export default PdfReport;
