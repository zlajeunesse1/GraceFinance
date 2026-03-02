/**
 * Confetti — Lightweight CSS-only confetti burst.
 *
 * Fires on check-in completion. Extra intense on milestone streaks.
 * Pure CSS animations — no libraries, no canvas, no performance hit.
 *
 * Place at: src/components/Confetti.jsx
 */

import { useState, useEffect } from "react"

var COLORS = ["#22D3A7", "#BC8CFF", "#58A6FF", "#D29922", "#F85149", "#3FB950"]

export default function Confetti({ active, intense }) {
  var particleState = useState([])
  var particles = particleState[0]
  var setParticles = particleState[1]

  useEffect(function () {
    if (!active) {
      setParticles([])
      return
    }

    var count = intense ? 40 : 20
    var newParticles = []
    for (var i = 0; i < count; i++) {
      newParticles.push({
        id: i,
        x: 40 + Math.random() * 20,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        delay: Math.random() * 0.5,
        duration: 1.2 + Math.random() * 0.8,
        angle: -60 + Math.random() * 120,
        distance: 60 + Math.random() * 140,
        size: 4 + Math.random() * 4,
        rotation: Math.random() * 360,
      })
    }
    setParticles(newParticles)

    var timer = setTimeout(function () {
      setParticles([])
    }, 2500)

    return function () { clearTimeout(timer) }
  }, [active, intense])

  if (particles.length === 0) return null

  var keyframes = ""
  particles.forEach(function (p) {
    var endX = Math.cos(p.angle * Math.PI / 180) * p.distance
    var endY = -Math.abs(Math.sin(p.angle * Math.PI / 180) * p.distance)
    keyframes += "@keyframes confetti-" + p.id + " {"
    keyframes += "0% { opacity: 1; transform: translate(0, 0) rotate(0deg) scale(1); }"
    keyframes += "60% { opacity: 1; }"
    keyframes += "100% { opacity: 0; transform: translate(" + endX + "px, " + (endY + 80) + "px) rotate(" + p.rotation + "deg) scale(0.3); }"
    keyframes += "} "
  })

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      pointerEvents: "none", zIndex: 9999, overflow: "hidden",
    }}>
      <style>{keyframes}</style>
      {particles.map(function (p) {
        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: p.x + "%",
              top: "50%",
              width: p.size,
              height: p.size * 0.6,
              background: p.color,
              borderRadius: 1,
              animation: "confetti-" + p.id + " " + p.duration + "s ease-out " + p.delay + "s both",
            }}
          />
        )
      })}
    </div>
  )
}
