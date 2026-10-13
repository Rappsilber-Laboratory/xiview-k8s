import { useState, useEffect } from 'react';
import { Eye, Trash2, Database, Download, Loader2 } from 'lucide-react';

export default function HistoryPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const res = await fetch('/pride/ws/archive/crosslinking/v3/data/get_datasets');
      const data = await res.json();
      setDatasets(data.map((d: any) => ({
        id: d.project_id,
        name: d.identification_file_name,
        status: 'success',
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
        headers: { 'X-API-Key': (window as any).XIVIEW_CONFIG?.API_KEY || 'your_api_key' } // Dynamic runtime key
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

  const handleDownloadStatic = async (id: string, name: string) => {
    setDownloadingId(id);
    try {
      const res = await fetch(`/pride/ws/archive/crosslinking/v3/export_static_project?project_id=${id}`);
      if (!res.ok) {
        let errMsg = 'Failed to generate static export';
        try {
          const errJson = await res.json();
          errMsg = errJson.detail || errMsg;
        } catch {}
        alert(`Export error: ${errMsg}`);
        return;
      }
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const cleanName = (name || id).replace(/\.[^/.]+$/, "");
      a.download = `${cleanName}_static_xiview.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      a.remove();
    } catch (err: any) {
      console.error(err);
      alert(`Download failed: ${err.message || err}`);
    } finally {
      setDownloadingId(null);
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
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} style={{textAlign: 'center', padding: '2rem'}}>Loading...</td></tr>
              ) : datasets.length === 0 ? (
                <tr><td colSpan={4} style={{textAlign: 'center', padding: '2rem'}}>No datasets found.</td></tr>
              ) : datasets.map((ds, index) => (
                <tr key={`${ds.id}-${index}`}>
                  <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{ds.id}</td>
                  <td>{ds.name}</td>
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
                        href={`#network?project=${ds.id}&file=${encodeURIComponent(ds.name)}`} 
                        className="action-btn view" 
                        title="View in xiVIEW"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}
                      >
                        <Eye size={18} />
                      </a>
                      <button 
                        className="action-btn download" 
                        title="Download Self-Contained Static Package (.zip with layouts)" 
                        disabled={downloadingId === ds.id}
                        onClick={() => handleDownloadStatic(ds.id, ds.name)}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        {downloadingId === ds.id ? <Loader2 size={18} className="animate-spin" /> : <Download size={18} />}
                      </button>
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
