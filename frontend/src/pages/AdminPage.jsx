import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import AdminPanel from '../components/AdminPanel'
import './AdminPage.css'

export default function AdminPage({ role, setRole }) {
  const navigate = useNavigate()

  return (
    <div className="admin-page" id="admin-page">
      <Sidebar
        role={role}
        setRole={setRole}
        chatCount={0}
        helpfulCount={0}
        onClearChat={() => {}}
      />

      <div className="admin-content">
        {role !== 'HR' ? (
          /* Access denied */
          <motion.div
            className="access-denied"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 240, damping: 22 }}
          >
            <div className="access-denied-icon">
              <AlertTriangle size={32} />
            </div>
            <h2>Access Restricted</h2>
            <p>The Admin Panel is only available to users with the <strong>HR</strong> role.</p>
            <p>Please switch to the HR role in the sidebar to access this section.</p>
            <motion.button
              className="access-denied-btn"
              onClick={() => navigate('/')}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              id="go-to-chat-btn"
            >
              ← Back to Chat
            </motion.button>
          </motion.div>
        ) : (
          <AdminPanel />
        )}
      </div>
    </div>
  )
}
