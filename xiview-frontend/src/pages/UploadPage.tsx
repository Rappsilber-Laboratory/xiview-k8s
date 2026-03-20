import { useState } from 'react';
import { Upload, File, AlertCircle } from 'lucide-react';

export default function UploadPage() {
  const [files, setFiles] = useState<globalThis.File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const response = await fetch('/pride/ws/archive/crosslinking/v3/upload_local', {
        method: 'POST',
        headers: {
          'X-API-Key': 'your_api_key'
        },
        body: formData
      });

      if (response.ok) {
        setIsComplete(true);
        setFiles([]); // Clear after upload
      } else {
        console.error('Upload failed:', await response.text());
      }
    } catch (e) {
      console.error('Upload Error:', e);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Submit Datasets</h2>
        <p>Upload mzIdentML and peak list components for parsing</p>
      </div>

      <div className="glass-panel upload-container">
        
        {/* Dropzone area */}
        <div className="upload-dropzone">
          <Upload className="upload-icon" />
          <h3 style={{ marginBottom: '0.5rem' }}>Select or drop files here</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Supports .mzid, .mzML, .mgf, .csv, and .fasta
          </p>
          <input 
            type="file" 
            id="file-upload" 
            multiple 
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                setFiles(Array.from(e.target.files));
                setIsComplete(false); // Reset completion status for new file
              }
            }}
          />
          <button 
            className="upload-btn"
            onClick={() => document.getElementById('file-upload')?.click()}
            style={{ background: 'rgba(99, 102, 241, 0.2)', color: 'var(--accent-color)', border: '1px solid var(--accent-color)' }}
          >
            Browse Files
          </button>
        </div>

        {/* Selected files feedback */}
        <div className="file-list">
          {files.map((file, idx) => (
             <div className="file-item" key={idx}>
               <div className="file-info">
                 <File className="file-icon" />
                 <div className="file-details">
                   <h4>File {idx + 1}</h4>
                   <p>{file.name}</p>
                 </div>
               </div>
               <span className="status-badge success">Ready</span>
             </div>
          ))}
          
          {files.length === 0 && !isComplete && (
            <div className="file-item">
              <div className="file-info">
                <File className="file-icon" />
                <div className="file-details">
                  <h4>Identification File</h4>
                  <p>No file selected — Select mzIdentML and peaklists.</p>
                </div>
              </div>
            </div>
          )}

          {isComplete && (
            <div className="file-item" style={{ background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.2)'}}>
              <div className="file-info">
                <File className="file-icon" color="var(--success-color)" />
                <div className="file-details">
                  <h4 style={{ color: 'var(--success-color)' }}>Parsing Submitted Successfully</h4>
                  <p>Check the "My Data" tab to view your parsed dataset once the server finishes indexing.</p>
                </div>
              </div>
            </div>
          )}

        </div>

        <button 
          className="upload-btn" 
          disabled={files.length === 0 || isUploading} 
          onClick={handleUpload}
          style={{ alignSelf: 'flex-end', opacity: (files.length === 0 || isUploading) ? 0.6 : 1 }}
        >
          {isUploading ? 'Parsing...' : 'Begin Parsing'} <Upload size={18} />
        </button>

      </div>

      {/* Info Sections */}
      <div className="glass-panel info-section" style={{ marginTop: '2rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={20} color="var(--accent-color)" />
          How to submit a crosslinking dataset
        </h3>
        <p>
          Uploading peptide identifications as <strong>mzIdentML</strong> is the recommended way to use xiVIEW. The submitted mzIdentML must validate against the official schema and properly attach sequence data for target proteins.
        </p>
        <ul className="info-list" style={{ marginTop: '1rem' }}>
          <li>Every <code>&lt;DBSequence&gt;</code> element that describes a target protein must include the sequence explicitly.</li>
          <li>If the accession attributes are valid UniProtKB accessions, visual annotations will be dynamically fetched.</li>
          <li>There is a <strong>10GB</strong> data size and transmission limit.</li>
        </ul>
      </div>
    </div>
  );
}
