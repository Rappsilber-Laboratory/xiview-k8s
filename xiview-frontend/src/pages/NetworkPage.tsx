import { ArrowLeft, ExternalLink } from 'lucide-react';

export default function NetworkPage() {
  // Parse project and file from query parameters
  const hash = window.location.hash;
  const queryString = hash.split('?')[1] || '';
  const params = new URLSearchParams(queryString);
  const project = params.get('project') || '';
  const file = params.get('file') || '';

  const iframeSrc = `/network.html?project=${project}&file=${file}`;

  return (
    <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', padding: '1rem', borderBottom: '1px solid var(--panel-border)', background: 'var(--panel-bg)', flexShrink: 0 }}>
        <button 
          onClick={() => window.location.hash = 'history'}
          className="action-btn"
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginRight: '1rem', padding: '0.5rem 1rem', background: '#f1f5f9', color: 'var(--text-primary)', fontWeight: 500 }}
        >
          <ArrowLeft size={18} />
          Back to History
        </button>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '1.2rem', margin: 0, color: 'var(--accent-color)' }}>xiVIEW Network</h2>
          {(file || project) && <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Dataset: {file} (Project: {project})</span>}
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <a
            href={iframeSrc}
            target="_blank"
            rel="noreferrer"
            className="action-btn view"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: '#dbeafe', color: '#2563eb', fontWeight: 500, textDecoration: 'none', borderRadius: '4px' }}
          >
            <ExternalLink size={18} />
            Open in New Tab
          </a>
        </div>
      </div>
      
      <div style={{ flex: 1, position: 'relative', width: '100%' }}>
        <iframe 
          src={iframeSrc} 
          style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
          title={`xiVIEW Network - ${file}`}
        />
      </div>
    </div>
  );
}
