/** 三段式横向反应堆全息线框 — 与遥测数据联动 */

const CYAN = '#00e5ff'
const PURPLE = '#9d4edd'
const ORANGE = '#ff6b35'

function lerp(a, b, t) {
  return a + (b - a) * Math.min(1, Math.max(0, t))
}

function drawWireRing(ctx, cx, cy, rx, ry, rot, color, lw, alpha = 1) {
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16)
    const g = parseInt(color.slice(3, 5), 16)
    const b = parseInt(color.slice(5, 7), 16)
    ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`
  } else {
    ctx.strokeStyle = color
  }
  ctx.lineWidth = lw
  ctx.beginPath()
  ctx.ellipse(cx, cy, rx, ry, rot, 0, Math.PI * 2)
  ctx.stroke()
}

function drawWireTorus(ctx, cx, cy, rx, ry, rot, color, lw, segments = 24) {
  ctx.strokeStyle = color
  ctx.lineWidth = lw
  for (let s = 0; s < segments; s++) {
    const a = (s / segments) * Math.PI * 2 + rot
    const px = cx + Math.cos(a) * rx
    const py = cy + Math.sin(a) * ry * 0.35
    ctx.beginPath()
    ctx.ellipse(px, py, rx * 0.15, ry * 0.55, rot + a * 0.3, 0, Math.PI * 2)
    ctx.stroke()
  }
}

function drawRingParticles(ctx, cx, cy, rx, ry, rot, count, speed, t, color, size) {
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + rot + t * speed * 0.001
    const px = cx + Math.cos(a) * rx
    const py = cy + Math.sin(a) * ry
    ctx.fillStyle = color
    ctx.globalAlpha = 0.5 + Math.sin(t * 0.004 + i) * 0.3
    ctx.beginPath()
    ctx.arc(px, py, size, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function drawShieldSection(ctx, cx, cy, scale, rot, intensity) {
  const rings = 5
  for (let i = 0; i < rings; i++) {
    const rx = (35 + i * 14) * scale
    const ry = (8 + i * 2.5) * scale
    const a = 0.32 + (rings - i) * 0.1
    drawWireRing(ctx, cx, cy, rx, ry, rot * (i % 2 ? 1 : -0.7), CYAN, (i === 0 ? 1.8 : 1.2) * scale, a)
    if (i % 2 === 0) {
      drawWireTorus(ctx, cx, cy, rx * 0.85, ry * 1.2, rot * 0.5 + i * 0.2, `rgba(0,229,255,${a * 0.7})`, 0.8 * scale, 12 + i * 2)
    }
  }
  drawRingParticles(ctx, cx, cy, 55 * scale, 14 * scale, rot, 28 + intensity * 0.2, 1.2, Date.now(), CYAN, 1.2 * scale)

  // 纵向支撑线
  ctx.strokeStyle = 'rgba(0,229,255,0.15)'
  ctx.lineWidth = 0.8 * scale
  ctx.setLineDash([4 * scale, 6 * scale])
  for (let i = -2; i <= 2; i++) {
    ctx.beginPath()
    ctx.moveTo(cx - 60 * scale, cy + i * 18 * scale)
    ctx.lineTo(cx - 20 * scale, cy + i * 10 * scale)
    ctx.stroke()
  }
  ctx.setLineDash([])
}

function drawTurbineSection(ctx, cx, cy, scale, rot, intensity) {
  const rings = 5
  for (let i = 0; i < rings; i++) {
    const rx = (32 + i * 13) * scale
    const ry = (7 + i * 2.2) * scale
    const a = 0.28 + (rings - i) * 0.09
    const col = i >= 3 ? PURPLE : CYAN
    drawWireRing(ctx, cx, cy, rx, ry, rot * (i % 2 ? -1 : 0.8), col, (i === rings - 1 ? 1.6 : 1.1) * scale, a)
  }
  // 涡轮辐条
  const spokes = 8
  ctx.strokeStyle = 'rgba(157,78,221,0.35)'
  ctx.lineWidth = 1 * scale
  for (let i = 0; i < spokes; i++) {
    const a = (i / spokes) * Math.PI * 2 + rot * 2
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx + Math.cos(a) * 58 * scale, cy + Math.sin(a) * 16 * scale)
    ctx.stroke()
  }
  drawRingParticles(ctx, cx, cy, 52 * scale, 13 * scale, rot * 1.5, 24 + intensity * 0.15, 1.5, Date.now(), PURPLE, 1 * scale)
}

function drawCoreSection(ctx, cx, cy, scale, t, cpuPct, coreTemp) {
  const breathe = 0.5 + Math.sin(t * 0.0025) * 0.5
  const tempNorm = Math.min(1, Math.max(0, (coreTemp - 35) / 65))
  const bright = Math.min(1, (cpuPct / 100) * 0.7 + tempNorm * 0.35 + breathe * 0.15)
  const coreR = (22 + breathe * 4) * scale

  // 外层光晕
  const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 3.5)
  glow.addColorStop(0, `rgba(255,107,53,${0.35 * bright})`)
  glow.addColorStop(0.4, `rgba(255,80,30,${0.12 * bright})`)
  glow.addColorStop(1, 'rgba(255,107,53,0)')
  ctx.fillStyle = glow
  ctx.beginPath()
  ctx.arc(cx, cy, coreR * 3.5, 0, Math.PI * 2)
  ctx.fill()

  // 粒子云
  const pCount = Math.floor(60 + cpuPct * 0.8)
  const pSpeed = 0.002 + cpuPct * 0.00004
  for (let i = 0; i < pCount; i++) {
    const seed = i * 1.618
    const a = seed * 2.4 + t * pSpeed * (1 + (i % 5) * 0.2)
    const dist = (0.15 + (Math.sin(seed * 3.1 + t * 0.001) * 0.5 + 0.5) * 0.85) * coreR * 2.2
    const px = cx + Math.cos(a) * dist
    const py = cy + Math.sin(a) * dist * 0.65
    const alpha = 0.3 + bright * 0.6
    ctx.fillStyle = i % 3 === 0 ? `rgba(255,200,100,${alpha})` : `rgba(255,107,53,${alpha * 0.85})`
    ctx.beginPath()
    ctx.arc(px, py, (0.8 + (i % 3) * 0.4) * scale, 0, Math.PI * 2)
    ctx.fill()
  }

  // 线框球体经纬线
  ctx.strokeStyle = `rgba(255,107,53,${0.4 + bright * 0.4})`
  ctx.lineWidth = 1.2 * scale
  const latLines = 6
  for (let i = 0; i < latLines; i++) {
    const lat = ((i / (latLines - 1)) - 0.5) * Math.PI * 0.9
    const ry = Math.cos(lat) * coreR
    const y = cy + Math.sin(lat) * coreR * 0.5
    ctx.beginPath()
    ctx.ellipse(cx, y, coreR, ry, 0, 0, Math.PI * 2)
    ctx.stroke()
  }
  const lonLines = 8
  for (let i = 0; i < lonLines; i++) {
    const a = (i / lonLines) * Math.PI + t * 0.0008
    ctx.beginPath()
    ctx.ellipse(cx, cy, Math.abs(Math.cos(a)) * coreR, coreR, a, 0, Math.PI * 2)
    ctx.stroke()
  }

  // 实心核心
  const coreGrad = ctx.createRadialGradient(cx - coreR * 0.3, cy - coreR * 0.3, 0, cx, cy, coreR)
  coreGrad.addColorStop(0, `rgba(255,220,150,${0.9 * bright})`)
  coreGrad.addColorStop(0.5, `rgba(255,107,53,${0.75 * bright})`)
  coreGrad.addColorStop(1, `rgba(180,40,10,${0.5 * bright})`)
  ctx.fillStyle = coreGrad
  ctx.shadowColor = ORANGE
  ctx.shadowBlur = 25 * scale * bright
  ctx.beginPath()
  ctx.arc(cx, cy, coreR * 0.55, 0, Math.PI * 2)
  ctx.fill()
  ctx.shadowBlur = 0
}

function drawEnergyChannel(ctx, x1, y1, x2, y2, flow, t, color) {
  const speed = 0.003 + flow * 0.008
  const particles = Math.min(20, Math.floor(4 + flow * 3))
  ctx.strokeStyle = color.startsWith('#') ? `${color}33` : color
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16)
    const g = parseInt(color.slice(3, 5), 16)
    const b = parseInt(color.slice(5, 7), 16)
    ctx.strokeStyle = `rgba(${r},${g},${b},0.2)`
  }
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(x1, y1)
  ctx.lineTo(x2, y2)
  ctx.stroke()

  for (let i = 0; i < particles; i++) {
    const prog = ((i / particles) + (t * speed)) % 1
    const px = lerp(x1, x2, prog)
    const py = lerp(y1, y2, prog) + Math.sin(prog * Math.PI * 4 + t * 0.005) * 3
    const alpha = Math.sin(prog * Math.PI) * (0.4 + Math.min(1, flow / 10) * 0.5)
    if (color.startsWith('#')) {
      const r = parseInt(color.slice(1, 3), 16)
      const g = parseInt(color.slice(3, 5), 16)
      const b = parseInt(color.slice(5, 7), 16)
      ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`
    } else ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(px, py, 1.5 + flow * 0.15, 0, Math.PI * 2)
    ctx.fill()
  }
}

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} W
 * @param {number} H
 * @param {number} t - animation timestamp
 * @param {object} p - linkage params
 */
export function drawReactor(ctx, W, H, t, p) {
  const {
    cpuPct = 0,
    threads = 0,
    coreTemp = 52,
    diskIO = 0,
    netFlow = 0,
    radiation = 50,
    alert = 0,
  } = p

  ctx.clearRect(0, 0, W, H)

  const cx = W * 0.5
  const cy = H * 0.55
  const scale = Math.min(W, H) / 480

  // 辐射光晕 — 范围与颜色随 radiation 变化
  const mix = radiation / 100
  const haloR = (90 + radiation * 1.4) * scale
  const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloR)
  const [hr, hg, hb] = [lerp(0, 255, mix * 0.85), lerp(229, 107, mix * 0.85), lerp(255, 53, mix * 0.85)]
  haloGrad.addColorStop(0, `rgba(${hr},${hg},${hb},${0.1 + mix * 0.14})`)
  haloGrad.addColorStop(0.6, `rgba(0,229,255,${0.05 + mix * 0.06})`)
  haloGrad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = haloGrad
  ctx.beginPath()
  ctx.arc(cx, cy, haloR, 0, Math.PI * 2)
  ctx.fill()

  const rotSpeed = 0.0012 * (1 + cpuPct / 80 + threads / 6000)
  const rot = t * rotSpeed
  const leftX = cx - 135 * scale
  const rightX = cx + 135 * scale

  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(-0.22)
  ctx.translate(-cx, -cy)

  drawShieldSection(ctx, leftX, cy, scale, rot, cpuPct)
  drawCoreSection(ctx, cx, cy, scale, t, cpuPct, coreTemp)
  drawTurbineSection(ctx, rightX, cy, scale, -rot * 1.2, cpuPct)

  // 能量通道：左磁盘 I/O，右网络
  drawEnergyChannel(ctx, leftX + 45 * scale, cy, cx - 38 * scale, cy, diskIO, t, CYAN)
  drawEnergyChannel(ctx, cx + 38 * scale, cy, rightX - 45 * scale, cy, netFlow, t, PURPLE)

  // 连接桥
  ctx.strokeStyle = 'rgba(0,229,255,0.12)'
  ctx.lineWidth = 1 * scale
  ctx.setLineDash([3 * scale, 5 * scale])
  ctx.beginPath()
  ctx.moveTo(leftX + 58 * scale, cy - 12 * scale)
  ctx.lineTo(cx - 30 * scale, cy - 8 * scale)
  ctx.moveTo(cx + 30 * scale, cy + 8 * scale)
  ctx.lineTo(rightX - 58 * scale, cy + 12 * scale)
  ctx.stroke()
  ctx.setLineDash([])

  // 告警红闪
  if (alert > 0.01) {
    const flash = (Math.sin(t * 0.015) * 0.5 + 0.5) * alert
    ctx.strokeStyle = `rgba(255,40,40,${flash * 0.85})`
    ctx.lineWidth = 2.5 * scale
    ctx.shadowColor = '#ff2222'
    ctx.shadowBlur = 18 * scale
    ctx.beginPath()
    ctx.ellipse(cx, cy, 195 * scale, 72 * scale, 0, 0, Math.PI * 2)
    ctx.stroke()
    ctx.shadowBlur = 0
  }

  ctx.restore()
}
