import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Compass, Sparkles } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import ChatBubble, { TypingIndicator } from '../components/ChatBubble'
import ChatInput from '../components/ChatInput'
import { sendChat } from '../services/api'
import './ChatPage.css'

const WELCOME_MSG = {
  role: 'assistant',
  content: "👋 Hi! I'm HRCompassAI — your intelligent HR Policy Assistant.\n\nI can answer any question about your company's policies, including leave entitlements, code of conduct, benefits, performance reviews, and more.\n\nAll my answers are strictly grounded in the uploaded policy documents — no hallucination, ever. Ask me anything!",
  sources: [],
  confidence: null,
  feedback: null,
}

export default function ChatPage({ role, setRole }) {
  const [messages, setMessages] = useState([WELCOME_MSG])
  const [loading, setLoading] = useState(false)
  const [feedbackLog, setFeedbackLog] = useState([])
  const bottomRef = useRef(null)

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages, loading])

  const handleSend = async (query) => {
    const userMsg = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const { data } = await sendChat(query, role)
      const botMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        confidence: data.confidence,
        found: data.found,
        feedback: null,
      }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '⚠️ Could not connect to the server. Please make sure the backend API is running.',
          sources: [],
          confidence: null,
          feedback: null,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = (index, helpful) => {
    setMessages((prev) => {
      const updated = [...prev]
      updated[index] = { ...updated[index], feedback: helpful }
      return updated
    })
    const question = messages[index - 1]?.content || ''
    setFeedbackLog((prev) => [...prev, { question, helpful }])
  }

  const handleClearChat = () => setMessages([WELCOME_MSG])

  const chatCount = messages.filter((m) => m.role === 'user').length
  const helpfulCount = feedbackLog.filter((f) => f.helpful).length

  return (
    <div className="chat-page" id="chat-page">
      <Sidebar
        role={role}
        setRole={setRole}
        chatCount={chatCount}
        helpfulCount={helpfulCount}
        onClearChat={handleClearChat}
      />

      <div className="chat-main">
        {/* Top bar */}
        <header className="chat-topbar">
          <div className="chat-topbar-left">
            <div className="chat-topbar-icon">
              <Compass size={16} />
            </div>
            <div>
              <h2 className="chat-topbar-title">Ask HR Policy</h2>
              <p className="chat-topbar-sub">Grounded answers from your company documents</p>
            </div>
          </div>
          <div className="chat-topbar-right">
            <span className="pulse-dot" />
            <span className="chat-topbar-status">Live · {role} access</span>
          </div>
        </header>

        {/* Messages area */}
        <div className="chat-messages" id="chat-messages-container">
          {/* Empty state hero */}
          {messages.length === 1 && !loading && (
            <motion.div
              className="chat-hero"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="chat-hero-orb">
                <Sparkles size={28} />
              </div>
              <h1 className="chat-hero-title gradient-text">Ask Anything About HR Policy</h1>
              <p className="chat-hero-sub">
                Powered by FAISS + BM25 hybrid retrieval and an LLM.
                Answers are always cited from your real policy documents.
              </p>
            </motion.div>
          )}

          {/* Chat history */}
          <motion.div layout className="chat-history">
            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <ChatBubble
                  key={i}
                  message={msg}
                  index={i}
                  onFeedback={handleFeedback}
                />
              ))}
            </AnimatePresence>

            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </motion.div>
        </div>

        {/* Input area */}
        <ChatInput onSend={handleSend} disabled={loading} />
      </div>
    </div>
  )
}
