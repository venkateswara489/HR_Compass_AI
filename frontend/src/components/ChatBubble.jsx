import { motion } from 'framer-motion'
import { ThumbsUp, ThumbsDown, Bot, User } from 'lucide-react'
import SourceBadge from './SourceBadge'
import ConfidenceBar from './ConfidenceBar'
import './ChatBubble.css'

const bubbleVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: {
    opacity: 1, y: 0, scale: 1,
    transition: { type: 'spring', stiffness: 260, damping: 22 },
  },
}

export function TypingIndicator() {
  return (
    <motion.div
      className="bubble-row bubble-row--bot"
      variants={bubbleVariants}
      initial="hidden"
      animate="visible"
    >
      <div className="bubble-avatar bubble-avatar--bot">
        <Bot size={15} />
      </div>
      <div className="bubble bubble--bot typing-bubble">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </motion.div>
  )
}

export default function ChatBubble({ message, index, onFeedback }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      className={`bubble-row ${isUser ? 'bubble-row--user' : 'bubble-row--bot'}`}
      variants={bubbleVariants}
      initial="hidden"
      animate="visible"
      id={`msg-${index}`}
    >
      {!isUser && (
        <div className="bubble-avatar bubble-avatar--bot">
          <Bot size={15} />
        </div>
      )}

      <div className={`bubble-content ${isUser ? '' : 'bubble-content--bot'}`}>
        <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--bot'}`}>
          <p className="bubble-text">{message.content}</p>
        </div>

        {/* Bot-only extras */}
        {!isUser && (
          <>
            {/* Source badges */}
            {message.sources?.length > 0 && (
              <div className="bubble-sources">
                {message.sources.map((src, i) => (
                  <SourceBadge key={i} source={src.source} page={src.page} />
                ))}
              </div>
            )}

            {/* Confidence bar */}
            {message.confidence != null && (
              <ConfidenceBar value={message.confidence} />
            )}

            {/* Feedback */}
            <div className="bubble-feedback">
              <motion.button
                className={`feedback-btn ${message.feedback === true ? 'feedback-btn--active-pos' : ''}`}
                onClick={() => onFeedback(index, true)}
                whileHover={{ scale: 1.15 }}
                whileTap={{ scale: 0.9 }}
                title="Helpful"
                id={`feedback-like-${index}`}
              >
                <ThumbsUp size={13} />
              </motion.button>
              <motion.button
                className={`feedback-btn ${message.feedback === false ? 'feedback-btn--active-neg' : ''}`}
                onClick={() => onFeedback(index, false)}
                whileHover={{ scale: 1.15 }}
                whileTap={{ scale: 0.9 }}
                title="Not helpful"
                id={`feedback-dislike-${index}`}
              >
                <ThumbsDown size={13} />
              </motion.button>
            </div>
          </>
        )}
      </div>

      {isUser && (
        <div className="bubble-avatar bubble-avatar--user">
          <User size={15} />
        </div>
      )}
    </motion.div>
  )
}
