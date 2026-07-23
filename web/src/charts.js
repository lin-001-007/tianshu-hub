/** Canvas 动态图表绘制 */

export function pctOf(value, unit) {
  if (unit === '%') return Math.min(100, value)
  if (unit === 'MB/s') return Math.min(100, value * 15)
  if (unit === 'GB') return Math.min(100, value * 5)
  if (unit === 'MHz') return Math.min(100, value / 30)
  if (unit === '°C') return Math.min(100, value)
  return Math.min(100, value / 3)
}

export function colorOf(pct) {
  if (pct > 85) return '#ff5050'
  if (pct > 60) return '#ffaa00'
  return '#00e5ff'
}

export function drawDonutChart(ctx, W, H, slices, t = 0, centerLabel = '资源') {
  ctx.clearRect(0, 0, W, H)
  const cx = W / 2, cy = H / 2
  const r = Math.min(W, H) / 2 - 6
  const inner = r * 0.58
  let start = -Math.PI / 2
  const total = slices.reduce((s, x) => s + x.value, 0) || 1

  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.arc(cx, cy, inner, Math.PI * 2, 0, true)
  ctx.fillStyle = 'rgba(255,255,255,0.04)'
  ctx.fill()

  slices.forEach((sl, i) => {
    const sweep = (sl.value / total) * Math.PI * 2
    const wobble = Math.sin(t * 0.002 + i) * 0.015
    ctx.beginPath()
    ctx.arc(cx, cy, r, start + wobble, start + sweep - wobble)
    ctx.arc(cx, cy, inner, start + sweep - wobble, start + wobble, true)
    ctx.closePath()
    ctx.fillStyle = sl.color
    ctx.globalAlpha = 0.85
    ctx.fill()
    ctx.globalAlpha = 1
    start += sweep
  })

  ctx.fillStyle = 'rgba(200,230,255,0.7)'
  ctx.font = '9px monospace'
  ctx.textAlign = 'center'
  ctx.fillText(centerLabel, cx, cy + 3)
}

export function drawBarChart(ctx, W, H, bars, t = 0, alertPulse = 0) {
  ctx.clearRect(0, 0, W, H)
  const n = bars.length
  const gap = 8
  const bw = (W - gap * (n + 1)) / n
  bars.forEach((b, i) => {
    const x = gap + i * (bw + gap)
    const pct = Math.min(100, b.val)
    const pulse = alertPulse > 0 ? (Math.sin(t * 0.012 + i * 0.8) * 0.5 + 0.5) * alertPulse * 0.15 : 0
    const h = ((pct / 100) * (H - 24)) * (0.92 + Math.sin(t * 0.003 + i) * 0.04 + pulse)
    const y = H - 16 - h
    ctx.fillStyle = 'rgba(255,255,255,0.06)'
    ctx.fillRect(x, 14, bw, H - 24)
    const grad = ctx.createLinearGradient(x, y + h, x, y)
    grad.addColorStop(0, b.color)
    grad.addColorStop(1, 'rgba(0,229,255,0.15)')
    ctx.fillStyle = grad
    ctx.shadowColor = alertPulse > 0 && pulse > 0.05 ? '#ff4444' : b.color
    ctx.shadowBlur = 8 + pulse * 12
    ctx.fillRect(x, y, bw, h)
    ctx.shadowBlur = 0
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(String(Math.round(pct)), x + bw / 2, y - 3)
    ctx.fillStyle = 'rgba(0,229,255,0.55)'
    ctx.font = '8px sans-serif'
    ctx.fillText(b.label, x + bw / 2, H - 4)
  })
}

export function drawSparkline(ctx, W, H, data, color) {
  ctx.clearRect(0, 0, W, H)
  if (!data.length) return
  ctx.strokeStyle = color
  ctx.lineWidth = 1.5
  ctx.shadowColor = color
  ctx.shadowBlur = 6
  ctx.beginPath()
  data.forEach((v, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * W
    const y = H - 2 - (v / 100) * (H - 4)
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.stroke()
  ctx.shadowBlur = 0
  const lx = W, ly = H - 2 - (data[data.length - 1] / 100) * (H - 4)
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(lx, ly, 2.5, 0, Math.PI * 2)
  ctx.fill()
}

export function drawMultiLine(ctx, W, H, series) {
  ctx.clearRect(0, 0, W, H)
  series.forEach((s, si) => {
    if (!s.data.length) return
    const max = s.max ?? 100
    ctx.strokeStyle = s.color
    ctx.lineWidth = si === 0 ? 2 : 1.5
    ctx.shadowColor = s.color
    ctx.shadowBlur = 6
    ctx.beginPath()
    s.data.forEach((v, i) => {
      const x = (i / Math.max(s.data.length - 1, 1)) * W
      const y = H - 8 - (v / max) * (H - 16)
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
    })
    ctx.stroke()
    ctx.shadowBlur = 0
  })
}
