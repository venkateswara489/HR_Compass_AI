import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles } from 'lucide-react'
import './ChatInput.css'

const SUGGESTIONS = [
  'What is the sick leave policy?',
  'How many annual leave days do I get?',
  'What is the code of conduct for remote work?',
  'How do I apply for parental leave?',
  'What are the performance review criteria?',
]

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const textareaRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    const q = value.trim()
    if (!q || disabled) return
    onSend(q)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleChange = (e) => {
    setValue(e.target.value)
    // Auto-grow textarea
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  const handleSuggestion = (s) => {
    setValue(s)
    textareaRef.current?.focus()
  }

  return (
    <div className="chat-input-wrapper">
      {/* Suggestions */}
      <AnimatePresence>
        {!value && !disabled && (
          <motion.div
            className="suggestions-row"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.2 }}
          >
            <Sparkles size={12} style={{ color: 'var(--clr-violet)', flexShrink: 0 }} />
            <div className="suggestions-chips">
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => handleSuggestion(s)}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.96 }}
                  id={`suggestion-${i}`}
                >
                  {s}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input form */}
      <form onSubmit={handleSubmit} className={`chat-input-form glass-2 ${focused ? 'focused' : ''}`}>
        <textarea
          ref={textareaRef}
          id="chat-query-input"
          className="chat-textarea"
          placeholder="Ask about any HR policy… (Enter to send, Shift+Enter for new line)"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          rows={1}
          aria-label="Chat query input"
        />
        <motion.button
          type="submit"
          className={`send-btn ${value.trim() && !disabled ? 'send-btn--active' : ''}`}
          disabled={!value.trim() || disabled}
          whileHover={value.trim() && !disabled ? { scale: 1.08 } : {}}
          whileTap={value.trim() && !disabled ? { scale: 0.92 } : {}}
          id="send-message-btn"
        >
          <Send size={17} strokeWidth={2.2} />
        </motion.button>
      </form>
      <p className="chat-input-hint">AI-grounded answers — no hallucination. Powered by FAISS + BM25 hybrid retrieval.</p>
    </div>
  )
}
