import { useState, useEffect } from 'react';
import { UploadCloud, Database } from 'lucide-react';
import UploadPage from './pages/UploadPage';
import HistoryPage from './pages/HistoryPage';
import NetworkPage from './pages/NetworkPage';

function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    if (hash.startsWith('network')) return hash;
    return hash === 'history' ? 'history' : 'upload';
  });

  useEffect(() => {
    window.location.hash = activeTab;
  }, [activeTab]);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash === 'history' || hash === 'upload' || hash.startsWith('network')) {
        setActiveTab(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

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
      <main className="main-content" style={activeTab.startsWith('network') ? { padding: 0, display: 'flex', flexDirection: 'column' } : {}}>
        {activeTab === 'upload' && <UploadPage />}
        {activeTab === 'history' && <HistoryPage />}
        {activeTab.startsWith('network') && <NetworkPage />}
      </main>
    </div>
  );
}

export default App;
