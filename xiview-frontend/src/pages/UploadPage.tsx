import { useState } from 'react';
import { Upload, FileText, File, AlertCircle } from 'lucide-react';

export default function UploadPage() {
  const [file, setFile] = useState<globalThis.File | null>(null);

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
                setFile(e.target.files[0]);
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
          <div className="file-item">
            <div className="file-info">
              <File className="file-icon" />
              <div className="file-details">
                <h4>Identification File</h4>
                <p>{file ? file.name : 'No file selected — Select a mzIdentML or CSV.'}</p>
              </div>
            </div>
            {file && <span className="status-badge success">Ready</span>}
          </div>
          <div className="file-item">
            <div className="file-info">
              <FileText className="file-icon" />
              <div className="file-details">
                <h4>Peak List File(s)</h4>
                <p>No peak list selected — spectra will refer to database records.</p>
              </div>
            </div>
          </div>
        </div>

        <button className="upload-btn" disabled={!file} style={{ alignSelf: 'flex-end' }}>
          Begin Parsing <Upload size={18} />
        </button>

      </div>

      {/* Info Sections */}
      <div className="glass-panel info-section">
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
