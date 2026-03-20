import { useState } from 'react';
import { UploadCloud, Database } from 'lucide-react';
import UploadPage from './pages/UploadPage';
import HistoryPage from './pages/HistoryPage';

function App() {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div className="layout">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>xiVIEW</h1>
        </div>
        <nav className="nav-menu">
          <div 
            className={`nav-link ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <UploadCloud size={20} />
            <span>Upload Data</span>
          </div>
          <div 
            className={`nav-link ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <Database size={20} />
            <span>My Data</span>
          </div>
        </nav>
        
        <div className="sidebar-footer">
          <img src="https://www.xiview.org/images/logos/rappsilber-lab-small.png" alt="Rappsilber Lab" />
          <img src="https://www.xiview.org/images/logos/wellcome-trust-small.png" alt="Wellcome Trust" />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'upload' && <UploadPage />}
        {activeTab === 'history' && <HistoryPage />}
      </main>
    </div>
  );
}

export default App;
