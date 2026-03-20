import { useState } from 'react';
import { LayoutDashboard, UploadCloud, LogOut, Database, PlayCircle } from 'lucide-react';
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
            className={`nav-link ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
          >
            <LayoutDashboard size={20} />
            <span>Home</span>
          </div>
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
          <div className="nav-link">
            <PlayCircle size={20} />
            <span>Demo</span>
          </div>
          <div className="nav-link" style={{ marginTop: 'auto' }}>
            <LogOut size={20} />
            <span>Sign Out</span>
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
        {activeTab === 'home' && (
          <div className="animate-in">
            <div className="page-header">
              <h2>Welcome to xiVIEW</h2>
              <p>Advanced visual analysis of cross-linked mass spectrometry data</p>
            </div>
            <div className="glass-panel">
              <p style={{ color: 'var(--text-secondary)' }}>
                Please navigate to the <strong>Upload</strong> section to parse new mzIdentML files, or view your existing parsed datasets in <strong>My Data</strong>. 
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
