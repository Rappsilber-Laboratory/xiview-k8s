import { Eye, Trash2, Database, Download } from 'lucide-react';

export default function HistoryPage() {
  const mockDatasets = [
    {
      id: 'PXD038060',
      name: 'PolII_XiVersion1.6.742_PSM',
      date: '2023-11-04 14:32',
      status: 'success',
      size: '2.4 GB',
      spectra: '42,109'
    },
    {
      id: 'PXD000001',
      name: 'HSA-Active_Trial',
      date: '2023-12-10 09:15',
      status: 'processing',
      size: '800 MB',
      spectra: 'n/a'
    },
    {
      id: 'JPST001914',
      name: 'Rappsilber_CLMS_Data',
      date: '2024-01-22 18:01',
      status: 'failed',
      size: 'Unknown',
      spectra: '0'
    }
  ];

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>My Data</h2>
        <p>Review and query stored crosslinking projects</p>
      </div>

      <div className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem', alignItems: 'center' }}>
          <h3>Recently Uploaded Datasets</h3>
          <button className="upload-btn" style={{ margin: 0, padding: '0.5rem 1rem' }}>
            <Database size={16} /> Sync API
          </button>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project ID</th>
                <th>Dataset Name</th>
                <th>Upload Date</th>
                <th>Size</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {mockDatasets.map((ds) => (
                <tr key={ds.id}>
                  <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{ds.id}</td>
                  <td>{ds.name}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{ds.date}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{ds.size}</td>
                  <td>
                    <span className={`status-badge ${ds.status}`}>
                      {ds.status === 'success' && 'Ready / xiVIEW'}
                      {ds.status === 'processing' && 'Parsing..'}
                      {ds.status === 'failed' && 'Validation Error'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button className="action-btn view" title="View in xiVIEW" disabled={ds.status !== 'success'}>
                        <Eye size={18} />
                      </button>
                      <button className="action-btn view" title="Download">
                        <Download size={18} />
                      </button>
                      <button className="action-btn delete" title="Delete Dataset">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
