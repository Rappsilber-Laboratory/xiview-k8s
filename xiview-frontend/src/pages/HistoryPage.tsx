import { useState, useEffect } from 'react';
import { Eye, Trash2, Database } from 'lucide-react';

export default function HistoryPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const res = await fetch('/pride/ws/archive/crosslinking/v3/data/get_datasets');
      const data = await res.json();
      setDatasets(data.map((d: any) => ({
        id: d.project_id,
        name: d.identification_file_name,
        date: d.upload_date || 'Unknown', 
        status: 'success',
        size: d.size_matches || 'N/A',
      })));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (!confirm(`Are you sure you want to permanently delete project ${id}?`)) return;
    try {
      const res = await fetch(`/pride/ws/archive/crosslinking/v3/delete/${id}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': 'your_api_key' } // Matches k8s-xiview-upload-api settings
      });
      if (res.ok) {
        fetchDatasets();
      } else {
        alert("Failed to delete the dataset backend registry. Server returned error.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>My Data</h2>
        <p>Review and query stored crosslinking projects</p>
      </div>

      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem', alignItems: 'center' }}>
          <h3>Recently Uploaded Datasets</h3>
          <button className="upload-btn" onClick={fetchDatasets} style={{ margin: 0, padding: '0.5rem 1rem' }}>
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
              {loading ? (
                <tr><td colSpan={6} style={{textAlign: 'center', padding: '2rem'}}>Loading...</td></tr>
              ) : datasets.length === 0 ? (
                <tr><td colSpan={6} style={{textAlign: 'center', padding: '2rem'}}>No datasets found.</td></tr>
              ) : datasets.map((ds, index) => (
                <tr key={`${ds.id}-${index}`}>
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
                      <a 
                        href={`/network.html?project=${ds.id}&file=${ds.name}`} 
                        className="action-btn view" 
                        title="View in xiVIEW"
                        target="_blank"
                        rel="noreferrer"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}
                      >
                        <Eye size={18} />
                      </a>
                      <button className="action-btn delete" title="Delete Dataset" onClick={(e) => handleDelete(ds.id, e)}>
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
