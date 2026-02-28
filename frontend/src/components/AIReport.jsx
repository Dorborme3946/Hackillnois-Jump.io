import { useState } from 'react'

/**
 * Renders the markdown-ish coaching report from Claude.
 * Simple formatting: ## headings, **bold**, bullet points.
 */
function formatReport(text) {
  if (!text) return []
  const lines = text.split('\n')
  return lines.map((line, i) => {
    if (line.startsWith('## ')) {
      return <h3 key={i} className="text-sky-400 font-semibold text-base mt-5 mb-2">{line.slice(3)}</h3>
    }
    if (line.startsWith('### ')) {
      return <h4 key={i} className="text-gray-200 font-semibold text-sm mt-4 mb-1">{line.slice(4)}</h4>
    }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = line.slice(2)
      return (
        <li key={i} className="text-gray-300 text-sm ml-4 mb-1 list-disc"
          dangerouslySetInnerHTML={{ __html: boldify(content) }}
        />
      )
    }
    if (line.startsWith('---')) {
      return <hr key={i} className="border-gray-800 my-3" />
    }
    if (line.trim() === '') {
      return <div key={i} className="h-2" />
    }
    return (
      <p key={i} className="text-gray-300 text-sm mb-1"
        dangerouslySetInnerHTML={{ __html: boldify(line) }}
      />
    )
  })
}

function boldify(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
}

export default function AIReport({ report = '' }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-6 text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div>
          <h2 className="text-lg font-semibold text-white">AI Coaching Report</h2>
          <p className="text-xs text-gray-500 mt-0.5">Powered by Claude Sonnet</p>
        </div>
        <span className="text-gray-400 text-xl">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="px-6 pb-6">
          <div className="border-t border-gray-800 pt-4">
            {report ? formatReport(report) : (
              <p className="text-gray-500 text-sm">No report available.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
