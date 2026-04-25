import { FileText } from 'lucide-react'
import './SourceBadge.css'

export default function SourceBadge({ source, page }) {
  return (
    <span className="source-badge">
      <FileText size={11} />
      <span className="source-badge-name">{source}</span>
      {page != null && <span className="source-badge-page">p.{page}</span>}
    </span>
  )
}
