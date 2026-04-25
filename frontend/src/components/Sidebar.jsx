import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageCircle, Settings, ChevronDown, ChevronUp,
  BarChart3, FileText, Compass, Cpu, Shield, Users, Zap,
} from 'lucide-react'
import { getIndexStatus } from '../services/api'
import './Sidebar.css'

const ROLE_META = {
  Employee: { icon: <Users size={14} />, color: '#60A5FA', label: 'Employee' },
  Manager:  { icon: <Shield size={14} />, color: '#A78BFA', label: 'Manager' },
  HR:       { icon: <Zap size={14} />, color: '#4ADE80', label: 'HR Admin' },
}

export default function Sidebar({ role, setRole, chatCount, helpfulCount, onClearChat }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [indexStatus, setIndexStatus] = useState(null)
  const [rolesOpen, setRolesOpen] = useState(true)
  const [statsOpen, setStatsOpen] = useState(true)

  useEffect(() => {
    getIndexStatus()
      .then((r) => setIndexStatus(r.data))
      .catch(() => setIndexStatus(null))
  }, [])

  const navItems = [
    { icon: <MessageCircle size={18} />, label: 'Ask HR', path: '/' },
    ...(role === 'HR'
      ? [{ icon: <Settings size={18} />, label: 'Admin Panel', path: '/admin' }]
      : []),
  ]

  return (
    <aside className="sidebar glass">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Compass size={22} strokeWidth={2.2} />
        </div>
        <div>
          <h1 className="sidebar-logo-title gradient-text">HRCompassAI</h1>
          <p className="sidebar-logo-sub">Policy-Grounded Assistant</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <motion.button
            key={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.97 }}
            id={`nav-${item.label.replace(/\s+/g, '-').toLowerCase()}`}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            {item.label}
          </motion.button>
        ))}
      </nav>

      <div className="sidebar-divider" />

      {/* Role Selector */}
      <div className="sidebar-section">
        <button
          className="sidebar-section-header"
          onClick={() => setRolesOpen(!rolesOpen)}
          id="role-section-toggle"
        >
          <span>👤 Your Role</span>
          {rolesOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        <AnimatePresence>
          {rolesOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="role-grid">
                {Object.entries(ROLE_META).map(([key, meta]) => (
                  <motion.button
                    key={key}
                    className={`role-chip ${role === key ? 'selected' : ''}`}
                    style={{ '--role-color': meta.color }}
                    onClick={() => setRole(key)}
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    id={`role-btn-${key.toLowerCase()}`}
                  >
                    {meta.icon}
                    {meta.label}
                  </motion.button>
                ))}
              </div>
              <p className="role-hint">
                {role === 'HR'
                  ? '🔓 Full access — all policy categories'
                  : `Access: General, Leave${role === 'Manager' ? ', Performance, Disciplinary' : ', Benefits, Code of Conduct'}`}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="sidebar-divider" />

      {/* Index Status */}
      <div className="sidebar-section">
        <div className="index-status-row">
          <Cpu size={14} />
          <span className="index-status-label">Vector Index</span>
          <span
            className={`pill ${indexStatus?.indexed ? 'pill-green' : 'pill-amber'}`}
          >
            {indexStatus?.indexed ? 'Ready' : 'Not built'}
          </span>
        </div>
        {indexStatus?.indexed && (
          <div className="index-meta">
            <div className="index-meta-item">
              <span className="index-meta-value">{indexStatus.vectorCount}</span>
              <span className="index-meta-key">Vectors</span>
            </div>
            <div className="index-meta-divider" />
            <div className="index-meta-item">
              <span className="index-meta-value">{indexStatus.documentCount}</span>
              <span className="index-meta-key">Documents</span>
            </div>
          </div>
        )}
      </div>

      <div className="sidebar-divider" />

      {/* Session Stats */}
      <div className="sidebar-section">
        <button
          className="sidebar-section-header"
          onClick={() => setStatsOpen(!statsOpen)}
          id="stats-section-toggle"
        >
          <span><BarChart3 size={13} style={{ display: 'inline', marginRight: 4 }} />Session Stats</span>
          {statsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        <AnimatePresence>
          {statsOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-value">{chatCount}</span>
                  <span className="stat-label">Questions</span>
                </div>
                <div className="stat-card">
                  <span className="stat-value" style={{ color: 'var(--clr-green)' }}>{helpfulCount}</span>
                  <span className="stat-label">Helpful</span>
                </div>
              </div>
              {chatCount > 0 && (
                <motion.button
                  className="clear-chat-btn"
                  onClick={onClearChat}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  id="clear-chat-btn"
                >
                  🗑️ Clear Chat History
                </motion.button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <FileText size={12} />
        <span>Answers grounded in your policy docs</span>
      </div>
    </aside>
  )
}
