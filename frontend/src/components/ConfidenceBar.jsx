import { motion } from 'framer-motion'
import './ConfidenceBar.css'

const getLevel = (v) => {
  if (v >= 0.6) return { label: 'High', color: '#4ADE80' }
  if (v >= 0.35) return { label: 'Medium', color: '#FBA94C' }
  return { label: 'Low', color: '#F87171' }
}

export default function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100)
  const { label, color } = getLevel(value)

  return (
    <div className="conf-wrap">
      <div className="conf-header">
        <span className="conf-label">Confidence</span>
        <span className="conf-pct" style={{ color }}>{pct}% · {label}</span>
      </div>
      <div className="conf-track">
        <motion.div
          className="conf-fill"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
        />
      </div>
    </div>
  )
}
