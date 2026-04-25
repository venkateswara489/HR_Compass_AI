import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import AdminPage from './pages/AdminPage'
import { useState } from 'react'

export default function App() {
  const [role, setRole] = useState('Employee')

  return (
    <BrowserRouter>
      {/* Ambient background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <Routes>
        <Route path="/" element={<ChatPage role={role} setRole={setRole} />} />
        <Route path="/admin" element={<AdminPage role={role} setRole={setRole} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
