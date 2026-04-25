import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload, Trash2, RefreshCw, FileText, CheckCircle,
  AlertCircle, Loader, CloudUpload, Database,
} from 'lucide-react'
import {
  getDocuments, uploadDocuments, deleteDocument, rebuildIndex,
} from '../services/api'
import './AdminPanel.css'

function Toast({ toast, onDismiss }) {
  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          className={`toast toast--${toast.type}`}
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 280, damping: 22 }}
        >
          {toast.type === 'success' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
          {toast.message}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default function AdminPanel() {
  const [docs, setDocs] = useState([])
  const [uploading, setUploading] = useState(false)
  const [rebuilding, setRebuilding] = useState(false)
  const [rebuildResult, setRebuildResult] = useState(null)
  const [toast, setToast] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchDocs = useCallback(async () => {
    try {
      const { data } = await getDocuments()
      setDocs(data.documents || [])
    } catch {
      setDocs([])
    }
  }, [])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!acceptedFiles.length) return
    setUploading(true)
    try {
      const { data } = await uploadDocuments(acceptedFiles)
      showToast(`✅ Uploaded ${data.uploaded.length} file(s). Rebuild the index to apply.`)
      await fetchDocs()
    } catch (e) {
      showToast(e?.response?.data?.error || 'Upload failed', 'error')
    } finally {
      setUploading(false)
    }
  }, [fetchDocs])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': [], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [], 'text/plain': [] },
    disabled: uploading,
    multiple: true,
  })

  const handleDelete = async (name) => {
    setDeleting(name)
    try {
      await deleteDocument(name)
      showToast(`🗑️ Deleted "${name}"`)
      await fetchDocs()
      setRebuildResult(null)
    } catch (e) {
      showToast(e?.response?.data?.error || 'Delete failed', 'error')
    } finally {
      setDeleting(null)
    }
  }

  const handleRebuild = async () => {
    setRebuilding(true)
    setRebuildResult(null)
    try {
      const { data } = await rebuildIndex()
      setRebuildResult(data)
      showToast(`✅ Index rebuilt — ${data.chunkCount} chunks, ${data.vectorCount} vectors`)
    } catch (e) {
      showToast(e?.response?.data?.error || 'Rebuild failed', 'error')
    } finally {
      setRebuilding(false)
    }
  }

  return (
    <div className="admin-panel" id="admin-panel">
      <Toast toast={toast} />

      {/* Header */}
      <div className="admin-header">
        <div className="admin-header-icon">
          <Database size={22} />
        </div>
        <div>
          <h2 className="admin-title gradient-text">Admin Panel</h2>
          <p className="admin-subtitle">Manage policy documents and the vector index</p>
        </div>
      </div>

      <div className="admin-grid">
        {/* Upload section */}
        <section className="admin-card glass" id="upload-section">
          <div className="admin-card-header">
            <CloudUpload size={18} style={{ color: 'var(--clr-accent)' }} />
            <h3>Upload Policy Documents</h3>
          </div>

          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'dropzone--active' : ''} ${uploading ? 'dropzone--disabled' : ''}`}
            id="file-dropzone"
          >
            <input {...getInputProps()} id="file-input" />
            {uploading ? (
              <div className="dropzone-inner">
                <Loader size={30} className="spin" />
                <p>Uploading…</p>
              </div>
            ) : isDragActive ? (
              <div className="dropzone-inner">
                <Upload size={30} style={{ color: 'var(--clr-accent)' }} />
                <p>Drop files here!</p>
              </div>
            ) : (
              <div className="dropzone-inner">
                <Upload size={28} />
                <p>Drag & drop <strong>PDF, DOCX, TXT</strong> files</p>
                <span>or click to browse</span>
              </div>
            )}
          </div>
        </section>

        {/* Rebuild section */}
        <section className="admin-card glass" id="rebuild-section">
          <div className="admin-card-header">
            <RefreshCw size={18} style={{ color: 'var(--clr-violet)' }} />
            <h3>Rebuild Vector Index</h3>
          </div>
          <p className="admin-card-desc">
            Run this after uploading or deleting documents.
            Large document sets may take a moment.
          </p>

          <motion.button
            className={`rebuild-btn ${rebuilding ? 'rebuild-btn--loading' : ''}`}
            onClick={handleRebuild}
            disabled={rebuilding || docs.length === 0}
            whileHover={!rebuilding ? { scale: 1.02 } : {}}
            whileTap={!rebuilding ? { scale: 0.97 } : {}}
            id="rebuild-index-btn"
          >
            {rebuilding ? (
              <><Loader size={16} className="spin" /> Building index…</>
            ) : (
              <><RefreshCw size={16} /> Rebuild Index Now</>
            )}
          </motion.button>

          <AnimatePresence>
            {rebuildResult && (
              <motion.div
                className="rebuild-result"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <CheckCircle size={14} style={{ color: 'var(--clr-green)', flexShrink: 0 }} />
                <div>
                  <strong>{rebuildResult.chunkCount}</strong> chunks ·{' '}
                  <strong>{rebuildResult.vectorCount}</strong> vectors indexed
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>

      {/* Document list */}
      <section className="admin-card glass" id="documents-section">
        <div className="admin-card-header">
          <FileText size={18} style={{ color: 'var(--clr-sky)' }} />
          <h3>Policy Documents ({docs.length})</h3>
        </div>

        {docs.length === 0 ? (
          <div className="docs-empty">
            <FileText size={36} style={{ opacity: 0.3 }} />
            <p>No documents uploaded yet.</p>
            <span>Use the uploader above to add policy files.</span>
          </div>
        ) : (
          <ul className="docs-list">
            <AnimatePresence>
              {docs.map((doc) => (
                <motion.li
                  key={doc.name}
                  className="doc-item"
                  layout
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10, height: 0 }}
                  transition={{ duration: 0.2 }}
                  id={`doc-${doc.name.replace(/[^a-z0-9]/gi, '-')}`}
                >
                  <div className="doc-info">
                    <div className="doc-icon">
                      <FileText size={15} />
                    </div>
                    <div>
                      <p className="doc-name">{doc.name}</p>
                      <p className="doc-size">{doc.sizeKB} KB</p>
                    </div>
                  </div>
                  <motion.button
                    className="delete-btn"
                    onClick={() => handleDelete(doc.name)}
                    disabled={deleting === doc.name}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    id={`delete-btn-${doc.name.replace(/[^a-z0-9]/gi, '-')}`}
                  >
                    {deleting === doc.name ? <Loader size={14} className="spin" /> : <Trash2 size={14} />}
                  </motion.button>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </section>
    </div>
  )
}
