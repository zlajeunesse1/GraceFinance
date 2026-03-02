/**
 * DeltaChips — Visual score change indicators.
 *
 * Shows each dimension's before→after delta as a colored chip.
 * Green for up, amber for down, muted for flat.
 *
 * Props:
 *   deltas: { dimension_name: { before, after, direction } }
 *
 * Place at: src/components/DeltaChips.jsx
 */

var DIMENSION_LABELS = {
  fcs_composite: "FCS Score",
  current_stability: "Stability",
  future_outlook: "Outlook",
  purchasing_power: "Purchasing",
  emergency_readiness: "Emergency",
  income_adequacy: "Income",
}

var DIRECTION_CONFIG = {
  up: { arrow: "\u2191", color: "#3FB950", bg: "rgba(63, 185, 80, 0.12)" },
  down: { arrow: "\u2193", color: "#D29922", bg: "rgba(210, 153, 34, 0.12)" },
  flat: { arrow: "\u2192", color: "rgba(255,255,255,0.4)", bg: "rgba(255,255,255,0.04)" },
}

export default function DeltaChips({ deltas }) {
  if (!deltas) return null

  // Show FCS composite first, then individual dimensions
  var keys = Object.keys(deltas)
  var fcsFirst = keys.filter(function (k) { return k === "fcs_composite" })
  var rest = keys.filter(function (k) { return k !== "fcs_composite" })
  var ordered = fcsFirst.concat(rest)

  return (
    <div style={{
      display: "flex",
      flexWrap: "wrap",
      gap: 6,
    }}>
      {ordered.map(function (dim) {
        var delta = deltas[dim]
        var config = DIRECTION_CONFIG[delta.direction] || DIRECTION_CONFIG.flat
        var diff = delta.after - delta.before
        var diffStr = diff === 0 ? "flat" : (diff > 0 ? "+" : "") + diff.toFixed(2)
        var isFCS = dim === "fcs_composite"

        return (
          <div
            key={dim}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: isFCS ? "6px 12px" : "4px 10px",
              borderRadius: 8,
              background: config.bg,
              border: isFCS ? "1px solid " + config.color + "40" : "1px solid transparent",
              fontSize: isFCS ? 13 : 12,
              fontWeight: isFCS ? 600 : 500,
              color: config.color,
              transition: "all 0.3s ease",
              animation: "chip-in 0.4s ease-out both",
              animationDelay: (ordered.indexOf(dim) * 0.08) + "s",
            }}
          >
            <span>{config.arrow}</span>
            <span>{DIMENSION_LABELS[dim] || dim}</span>
            <span style={{ opacity: 0.7 }}>{diffStr}</span>
          </div>
        )
      })}
      <style>{
        "@keyframes chip-in { from { opacity: 0; transform: translateY(8px) scale(0.9); } to { opacity: 1; transform: translateY(0) scale(1); } }"
      }</style>
    </div>
  )
}
