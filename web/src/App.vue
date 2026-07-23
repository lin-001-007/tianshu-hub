<template>
  <div class="hud-root" :class="{ 'desktop-mode': isDesktop, 'alert-active': hasAlert }">
    <canvas ref="bgCanvas" class="bg-canvas"></canvas>

    <div class="scanlines"></div>
    <div class="vignette"></div>

    <div class="hud-shell">
      <!-- 顶栏 -->
      <header class="hud-top">
        <div class="brand">
          <span class="diamond">◆</span>
          <span class="brand-text">天枢系统检测<span class="accent">HUD</span></span>
          <span class="ver">SYS.TELEMETRY v3.1</span>
        </div>
        <div class="header-gauge">
          <div class="hg-ring">
            <svg viewBox="0 0 120 120" class="hg-svg">
              <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(0,229,255,0.12)" stroke-width="8"/>
              <circle cx="60" cy="60" r="52" fill="none" stroke="#00e5ff" stroke-width="8"
                :stroke-dasharray="`${(data.cpu?.percent ?? 0) * 3.27} 327`"
                stroke-linecap="round" transform="rotate(-90 60 60)"/>
            </svg>
            <span class="hg-pct">{{ fmt(data.cpu?.percent ?? 0) }}%</span>
          </div>
          <div class="hg-info">
            <span class="hg-title">CPU {{ data.cpu?.cores ?? '--' }}核 · {{ data.cpu?.freq_mhz ?? '--' }}MHz</span>
            <span class="hg-hint">背景环带 ∝ 负载</span>
          </div>
        </div>
        <div class="top-status" :class="connState">
          <span class="dot"></span>
          {{ connLabel }}
        </div>
        <div class="clock">{{ clockStr }}</div>
      </header>

      <div class="hud-main">
      <!-- 左：反应堆 + 内存 -->
      <div class="col-reactor" :style="{ width: reactorWidth + 'px' }">
        <section class="panel panel-reactor">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 反应堆全息 · REACTOR CORE</div>
          <canvas ref="reactorCanvas" class="reactor-panel-canvas" :style="{ height: reactorCanvasHeight + 'px' }"></canvas>
          <div class="reactor-mini">
            <div class="rm-row"><span>GPU 负载</span><strong>{{ gpuLoadLabel }}</strong></div>
            <div v-if="gpuNameShort" class="rm-row rm-sub"><span>显卡</span><strong>{{ gpuNameShort }}</strong></div>
            <div class="rm-row"><span>CPU 负载</span><strong>{{ fmt(data.cpu?.percent ?? 0) }}%</strong></div>
            <div class="rm-row"><span>综合负载指数</span><strong>{{ fmt(systemLoadIndex) }}%</strong></div>
          </div>
        </section>

        <section class="panel panel-memres">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 内存资源 · MEMORY</div>
          <div class="memres-body">
            <div class="memres-donut">
              <canvas ref="memDonutCanvas" class="mem-donut-canvas"></canvas>
            </div>
            <div class="memres-tiles">
              <div v-for="r in memoryTiles" :key="r.id" class="memres-tile" :class="{ hot: r.hot }">
                <div class="memres-head">
                  <span class="memres-label">{{ r.label }}</span>
                  <span class="memres-val">{{ r.val }}</span>
                </div>
                <div class="memres-bar">
                  <div class="memres-fill" :style="{ width: r.pct + '%', background: r.color }"></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="v-resizer" @mousedown.prevent="startReactorResize" title="拖拽调整反应堆栏宽度">
        <span class="resizer-grip">⋮⋮</span>
      </div>

      <!-- 中：传感 + 核心 + 日志 -->
      <aside class="col-mid" :style="{ width: midWidth + 'px' }">
        <section class="panel panel-sensors">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 关键传感 · QUICK READ</div>
          <div class="sensor-strip">
            <div v-for="s in keySensors" :key="s.id" class="sensor-row" :class="{ hot: s.hot }">
              <span class="sr-label">{{ s.label }}</span>
              <div class="sr-track">
                <div class="sr-fill" :style="{ width: s.pct + '%', background: s.color }"></div>
              </div>
              <span class="sr-val">{{ fmt(s.val) }}{{ s.unit }}</span>
            </div>
          </div>
        </section>

        <section class="panel panel-cores">
          <div class="panel-title">CPU 核心负载</div>
          <div class="core-bars">
            <div v-for="(v, i) in perCore" :key="i" class="core-col">
              <div class="core-fill" :style="{ height: v + '%' }"></div>
              <span class="core-id">C{{ i }}</span>
            </div>
          </div>
        </section>

        <section class="panel panel-logs">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 系统重要日志 · {{ logs.length }} 条</div>
          <div class="log-stream" ref="logStreamRef">
            <div v-if="!logs.length" class="log-empty">正在接入系统日志流…</div>
            <div v-for="(log, i) in logs" :key="`${log.time}-${log.source}-${i}`"
              class="log-card" :class="logLevelClass(log.level)">
              <div class="log-meta">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level">{{ log.level }}</span>
                <span class="log-src">{{ log.source }}</span>
                <span v-if="log.summarized" class="log-ai-tag">已翻译</span>
              </div>
              <div class="log-msg">{{ log.message }}</div>
              <button v-if="log.raw" type="button" class="log-toggle" @click="toggleLogRaw(i)">
                {{ expandedLogs[i] ? '收起原文' : '查看英文原文' }}
              </button>
              <div v-if="log.raw && expandedLogs[i]" class="log-raw">{{ log.raw }}</div>
            </div>
          </div>
        </section>
      </aside>

      <div class="v-resizer" @mousedown.prevent="startMidResize" title="拖拽调整中间栏宽度">
        <span class="resizer-grip">⋮⋮</span>
      </div>

      <!-- 右：数据分析 + 遥测矩阵（填满剩余宽度） -->
      <aside class="col-right">
        <section class="panel panel-analysis">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="analysis-row">
            <div class="analysis-left">
              <div class="panel-title inline">◈ 数据分析引擎</div>
              <div class="analysis-bar"><div class="analysis-fill" :style="{ width: analysisPct + '%' }"></div></div>
              <div class="analysis-label">SCAN {{ analysisPct.toFixed(0) }}%</div>
            </div>
            <div class="mini-stats">
              <div v-for="s in topStats" :key="s.k" class="mini-stat">
                <span class="ms-val">{{ s.v }}</span>
                <span class="ms-lbl">{{ s.l }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="panel panel-metrics">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 遥测指标矩阵 · {{ cards.length }} 项</div>
          <div class="metrics-scroll">
            <div class="metrics-grid">
            <div v-for="c in cards" :key="c.id" class="metric-card" :class="{ hot: cardPct(c) > 85 }">
              <div class="mc-top">
                <span class="mc-label">{{ c.label }}</span>
                <span class="mc-val">{{ fmt(c.value) }}{{ c.unit }}</span>
              </div>
              <div class="mc-track">
                <div class="mc-fill" :style="{ width: cardPct(c) + '%', background: cardColor(c) }"></div>
              </div>
            </div>
            </div>
          </div>
        </section>
      </aside>
      </div>

      <div class="h-resizer" @mousedown.prevent="startBottomResize" title="拖拽调整底部区域高度">
        <span class="resizer-grip-h">⋯⋯</span>
      </div>

      <div class="hud-bottom" :style="{ height: bottomHeight + 'px' }">
      <!-- 底栏左：辐射检测 -->
      <footer class="row-bottom" :style="{ width: bottomLeftWidth + 'px' }">
        <section class="panel panel-wave">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-title">◈ 系统负载监测 · LOAD MONITOR</div>
          <canvas ref="barCanvas" class="bar-canvas"></canvas>
          <canvas ref="waveCanvas" class="wave-canvas"></canvas>
        </section>
      </footer>

      <div class="v-resizer v-resizer-sm" @mousedown.prevent="startBottomColResize" title="拖拽调整底栏左右宽度">
        <span class="resizer-grip">⋮⋮</span>
      </div>

      <!-- 底栏右：系统概览 -->
      <aside class="col-br">
        <section class="panel panel-overview">
          <div class="panel-corner tl"></div><div class="panel-corner tr"></div>
          <div class="panel-corner bl"></div><div class="panel-corner br"></div>
          <div class="panel-title">◈ 系统概览 · SYSTEM OVERVIEW</div>
          <div class="overview-body">
            <div class="overview-left">
              <canvas ref="radarCanvas" class="radar-canvas"></canvas>
              <div class="ov-gauges">
                <div v-for="b in horizBars" :key="b.id" class="ov-gauge">
                  <span class="ov-gauge-label">{{ b.label }}</span>
                  <div class="ov-gauge-track">
                    <div class="ov-gauge-fill" :style="{ width: b.val + '%', background: b.color }"></div>
                  </div>
                  <span class="ov-gauge-pct">{{ Math.round(b.val) }}%</span>
                </div>
              </div>
            </div>
            <div class="overview-main">
              <div class="overview-cards">
                <div v-for="s in overviewDetail" :key="s.k" class="ov-card" :class="{ hot: s.hot }">
                  <span class="ov-card-label">{{ s.label }}</span>
                  <span class="ov-card-val">{{ s.val }}</span>
                </div>
              </div>
              <div class="ov-spark-wrap">
                <span class="ov-spark-title">网络流量趋势</span>
                <canvas ref="netSparkCanvas" class="net-spark-canvas"></canvas>
              </div>
            </div>
          </div>
          <div class="code-stream">{{ codeLine }}</div>
        </section>
      </aside>
      </div>
    </div>

    <div v-if="isDesktop" class="desktop-hint">按 Esc 退出全屏桌面模式</div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { connectHudStream } from './stream.js'
import { pctOf, colorOf, drawDonutChart, drawBarChart, drawMultiLine, drawSparkline } from './charts.js'
import { drawReactor } from './reactor.js'

const data = ref({})
const cards = ref([])
const logs = ref([])
const connState = ref('connecting')
const clockStr = ref('')
const codeLine = ref('')
const analysisPct = ref(0)
const isDesktop = ref(false)

const bgCanvas = ref(null)
const reactorCanvas = ref(null)
const waveCanvas = ref(null)
const barCanvas = ref(null)
const radarCanvas = ref(null)
const memDonutCanvas = ref(null)
const netSparkCanvas = ref(null)
const logStreamRef = ref(null)
const expandedLogs = reactive({})

const reactorWidth = ref(0)
const midWidth = ref(0)
const bottomHeight = ref(0)
const bottomLeftWidth = ref(0)

function clampLayout() {
  const pad = 28
  const resizerW = 20
  const maxW = window.innerWidth - pad
  const maxH = window.innerHeight
  const minMetrics = 300

  let reactor = Number(localStorage.getItem('hud-reactor-w')) || 208
  let mid = Number(localStorage.getItem('hud-mid-w')) || Number(localStorage.getItem('hud-right-w')) || 268
  let bottom = Number(localStorage.getItem('hud-bottom-h')) || Math.round(maxH * 0.30)
  let bottomLeft = Number(localStorage.getItem('hud-bottom-left-w')) || Math.round(maxW * 0.44)

  reactor = Math.max(168, Math.min(248, reactor))
  mid = Math.max(200, Math.min(280, mid))

  const used = reactor + mid + resizerW * 2 + minMetrics
  if (used > maxW) {
    mid = Math.max(200, Math.min(mid, Math.round((maxW - minMetrics - resizerW * 2) * 0.42)))
    reactor = Math.max(168, maxW - resizerW * 2 - minMetrics - mid)
  }

  bottom = Math.max(200, Math.min(Math.round(maxH * 0.36), bottom))
  bottomLeft = Math.max(280, Math.min(maxW - 280, bottomLeft))

  reactorWidth.value = reactor
  midWidth.value = mid
  bottomHeight.value = bottom
  bottomLeftWidth.value = bottomLeft
}

reactorWidth.value = 208
midWidth.value = 268
bottomHeight.value = Math.round(window.innerHeight * 0.26)
bottomLeftWidth.value = Math.round(window.innerWidth * 0.46)
clampLayout()

let resizeMode = null
let resizeStartX = 0
let resizeStartY = 0
let resizeStartVal = 0

const history = { cpu: [], mem: [], net: [], disk: [], swap: [], io: [] }
const cardHist = reactive({})
const particles = Array.from({ length: 80 }, () => ({
  x: Math.random(), y: Math.random(), vx: (Math.random() - 0.5) * 0.0004, vy: (Math.random() - 0.5) * 0.0004, r: 0.5 + Math.random() * 1.5,
}))

let disconnect = null
let animId = null
let clockTimer = null
let logTimer = null

const connLabel = computed(() => ({
  connecting: '链路建立中…', connected: '遥测链路正常', reconnecting: '重连中…',
}[connState.value] || '…'))

const perCore = computed(() => data.value.cpu?.per_core || [])

const hasAlert = computed(() =>
  logs.value.some(l => ['警告', '错误', '严重'].includes(l.level)),
)

const alertLevel = computed(() => {
  if (logs.value.some(l => l.level === '错误' || l.level === '严重')) return 1
  if (logs.value.some(l => l.level === '警告')) return 0.55
  return 0
})

const topStats = computed(() => {
  const d = data.value
  return [
    { k: 'cores', l: '逻辑核心', v: d.cpu?.cores ?? '--' },
    { k: 'proc', l: '进程', v: d.system?.processes ?? '--' },
    { k: 'thr', l: '线程', v: d.system?.threads ?? '--' },
    { k: 'conn', l: '连接', v: d.network?.connections ?? '--' },
  ]
})

const horizBars = computed(() => {
  const d = data.value
  return [
    { id: 'cpu', label: 'CPU', val: d.cpu?.percent ?? 0, color: '#00e5ff' },
    { id: 'mem', label: 'MEM', val: d.memory?.percent ?? 0, color: '#9d4edd' },
    { id: 'disk', label: 'DISK', val: d.disk?.percent ?? 0, color: '#00e5ff' },
    { id: 'swap', label: 'SWAP', val: d.swap?.percent ?? 0, color: '#ff6b35' },
    { id: 'net', label: 'NET', val: Math.min(100, (d.network?.down_mbps ?? 0) * 20), color: '#9d4edd' },
    { id: 'io', label: 'I/O', val: Math.min(100, ((d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)) * 10), color: '#ff6b35' },
  ]
})

/** 综合负载指数：CPU/内存/磁盘/网络等维度的平均占用（科幻主题里的「辐射」即此意） */
const systemLoadIndex = computed(() => {
  const bars = horizBars.value
  if (!bars.length) return 0
  return Math.round(bars.reduce((s, b) => s + b.val, 0) / bars.length)
})

const resolvedGpu = computed(() => {
  const g = data.value.gpu || {}
  const card = cards.value.find(c => c.id === 'gpu')
  if (g.available && g.name && g.name !== '未检测到 GPU') return g
  if (g.name && g.name !== '未检测到 GPU') {
    return { ...g, available: true, load_percent: g.load_percent ?? card?.value ?? 0 }
  }
  if (card) return { available: true, load_percent: card.value, name: g.name || 'GPU' }
  return g
})

const gpuLoadLabel = computed(() => {
  const g = resolvedGpu.value
  if (!g?.available) return '未检测到'
  return `${fmt(g.load_percent ?? 0)}%`
})

const gpuNameShort = computed(() => {
  const name = resolvedGpu.value?.name || ''
  if (!name || name === '未检测到 GPU') return ''
  return name.replace(/\(R\)/gi, '').replace(/\(TM\)/gi, '').replace(/\s+/g, ' ').trim().slice(0, 20)
})

const reactorHeat = computed(() => {
  const g = resolvedGpu.value
  const load = g?.available ? (g.load_percent ?? 0) : (data.value.cpu?.percent ?? 0)
  return 40 + (load / 100) * 45
})

const reactorCanvasHeight = computed(() =>
  Math.round(reactorWidth.value * 0.46),
)

const memSlices = computed(() => {
  const m = data.value.memory
  if (!m) return [{ label: 'used', value: 1, color: '#9d4edd' }]
  const used = m.percent ?? 0
  return [
    { label: 'used', value: used, color: '#9d4edd' },
    { label: 'free', value: Math.max(0, 100 - used), color: 'rgba(0,229,255,0.25)' },
  ]
})

function cardPct(c) { return pctOf(c.value, c.unit) }
function cardColor(c) { return colorOf(cardPct(c)) }

function cardViz(c, i) {
  if (c.unit === '%') return i % 3 === 0 ? 'donut' : 'bar'
  if (c.unit === 'MB/s' || c.id?.includes('net')) return 'spark'
  if (c.unit === 'GB' || c.unit === 'MHz' || c.unit === 'h') return 'bar'
  return ['donut', 'spark', 'bar'][i % 3]
}

function pushCardHist(id, val, unit) {
  const pct = pctOf(val, unit)
  if (!cardHist[id]) cardHist[id] = []
  cardHist[id].push(pct)
  if (cardHist[id].length > 14) cardHist[id].shift()
}

function sparkPoints(id, c) {
  const arr = cardHist[id] || [cardPct(c)]
  return arr.map((v, i) => `${(i / Math.max(arr.length - 1, 1)) * 60},${18 - (v / 100) * 16}`).join(' ')
}

function barMini(id, c) {
  const arr = cardHist[id] || [cardPct(c)]
  const tail = arr.slice(-5)
  while (tail.length < 5) tail.unshift(0)
  return tail
}

function toggleLogRaw(i) {
  expandedLogs[i] = !expandedLogs[i]
}

function saveLayout() {
  localStorage.setItem('hud-reactor-w', String(reactorWidth.value))
  localStorage.setItem('hud-mid-w', String(midWidth.value))
  localStorage.setItem('hud-bottom-h', String(bottomHeight.value))
  localStorage.setItem('hud-bottom-left-w', String(bottomLeftWidth.value))
}

function onResizeMove(e) {
  if (!resizeMode) return
  if (resizeMode === 'mid') {
    const maxW = window.innerWidth - 28
    midWidth.value = Math.max(200, Math.min(maxW - reactorWidth.value - 300 - 20, resizeStartVal + (e.clientX - resizeStartX)))
  } else if (resizeMode === 'reactor') {
    const maxW = window.innerWidth - 28
    reactorWidth.value = Math.max(168, Math.min(maxW - midWidth.value - 300 - 20, Math.min(248, resizeStartVal + (e.clientX - resizeStartX))))
  } else if (resizeMode === 'bottom') {
    bottomHeight.value = Math.max(200, Math.min(window.innerHeight * 0.40, resizeStartVal - (e.clientY - resizeStartY)))
  } else if (resizeMode === 'bottom-col') {
    bottomLeftWidth.value = Math.max(280, Math.min(window.innerWidth - 280, resizeStartVal + (e.clientX - resizeStartX)))
  }
}

function onResizeEnd() {
  if (!resizeMode) return
  resizeMode = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  clampLayout()
  saveLayout()
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeEnd)
}

function startMidResize(e) {
  resizeMode = 'mid'
  resizeStartX = e.clientX
  resizeStartVal = midWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}

function startReactorResize(e) {
  resizeMode = 'reactor'
  resizeStartX = e.clientX
  resizeStartVal = reactorWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}

function startBottomResize(e) {
  resizeMode = 'bottom'
  resizeStartY = e.clientY
  resizeStartVal = bottomHeight.value
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}

function startBottomColResize(e) {
  resizeMode = 'bottom-col'
  resizeStartX = e.clientX
  resizeStartVal = bottomLeftWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}

function logLevelClass(level) {
  if (level === '严重' || level === '错误') return 'crit'
  if (level === '警告') return 'warn'
  return 'info'
}

const keySensors = computed(() => {
  const d = data.value
  return [
    { id: 'cpu', label: 'CPU 占用', val: d.cpu?.percent ?? 0, unit: '%', pct: d.cpu?.percent ?? 0, color: '#00e5ff', hot: (d.cpu?.percent ?? 0) > 80 },
    { id: 'mem', label: '内存占用', val: d.memory?.percent ?? 0, unit: '%', pct: d.memory?.percent ?? 0, color: '#9d4edd', hot: (d.memory?.percent ?? 0) > 85 },
    { id: 'disk', label: '磁盘占用', val: d.disk?.percent ?? 0, unit: '%', pct: d.disk?.percent ?? 0, color: '#00e5ff', hot: false },
    { id: 'net', label: '网络下行', val: d.network?.down_mbps ?? 0, unit: 'MB/s', pct: Math.min(100, (d.network?.down_mbps ?? 0) * 20), color: '#00e5ff', hot: false },
    { id: 'swap', label: '交换分区', val: d.swap?.percent ?? 0, unit: '%', pct: d.swap?.percent ?? 0, color: '#ff6b35', hot: (d.swap?.percent ?? 0) > 50 },
    { id: 'io', label: '磁盘 I/O', val: ((d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)), unit: 'MB/s', pct: Math.min(100, ((d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)) * 10), color: '#ff6b35', hot: false },
  ]
})

const systemOverview = computed(() => {
  const d = data.value
  const bat = d.battery
  return [
    { k: 'uptime', label: '运行时长', val: `${fmt(d.system?.uptime_hours ?? 0)} 小时`, hot: false },
    { k: 'proc', label: '活跃进程', val: d.system?.processes ?? '--', hot: false },
    { k: 'thr', label: '系统线程', val: d.system?.threads ?? '--', hot: false },
    { k: 'conn', label: '网络连接', val: d.network?.connections ?? '--', hot: false },
    { k: 'read', label: '磁盘读取', val: `${fmt(d.disk?.read_mbps ?? 0)} MB/s`, hot: false },
    { k: 'write', label: '磁盘写入', val: `${fmt(d.disk?.write_mbps ?? 0)} MB/s`, hot: false },
    { k: 'up', label: '网络上行', val: `${fmt(d.network?.up_mbps ?? 0)} MB/s`, hot: false },
    { k: 'bat', label: '电池状态', val: bat ? `${bat.percent}%${bat.plugged ? ' 充电中' : ''}` : '桌面设备', hot: bat && bat.percent < 20 },
  ]
})

const memoryTiles = computed(() => {
  const d = data.value
  const memPct = d.memory?.percent ?? 0
  const swapPct = d.swap?.percent ?? 0
  return [
    {
      id: 'mem',
      label: '物理内存',
      val: `${fmt(d.memory?.used_gb ?? 0)} / ${fmt(d.memory?.total_gb ?? 0)} GB`,
      pct: memPct,
      color: '#9d4edd',
      hot: memPct > 85,
    },
    {
      id: 'avail',
      label: '可用内存',
      val: `${fmt(d.memory?.available_gb ?? 0)} GB`,
      pct: Math.max(0, 100 - memPct),
      color: '#00ff88',
      hot: false,
    },
    {
      id: 'swap',
      label: '交换分区',
      val: `${fmt(d.swap?.used_gb ?? 0)} GB · ${fmt(swapPct)}%`,
      pct: swapPct,
      color: '#ff6b35',
      hot: swapPct > 50,
    },
  ]
})

const overviewDetail = computed(() => {
  const d = data.value
  const diskPct = d.disk?.percent ?? 0
  const load = d.cpu?.load_1m ?? 0
  const cores = d.cpu?.cores ?? 1
  const io = (d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)
  return [
    ...systemOverview.value,
    { k: 'freq', label: 'CPU 频率', val: `${fmt(d.cpu?.freq_mhz ?? 0)} MHz`, hot: false },
    { k: 'load', label: '系统负载', val: `${fmt(load)} / ${cores} 核`, hot: load > cores * 0.9 },
    { k: 'diskpct', label: '磁盘占用', val: `${fmt(diskPct)}%`, hot: diskPct > 90 },
    { k: 'diskfree', label: '磁盘剩余', val: `${fmt(d.disk?.free_gb ?? 0)} GB`, hot: false },
    { k: 'down', label: '网络下行', val: `${fmt(d.network?.down_mbps ?? 0)} MB/s`, hot: false },
    { k: 'io', label: '磁盘 I/O', val: `${fmt(io)} MB/s`, hot: false },
  ]
})

function fmt(v) { return typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(1)) : v }

function pushHist(key, val, max = 80) {
  history[key].push(val)
  if (history[key].length > max) history[key].shift()
}

function onMetrics(d, c, lg) {
  data.value = d
  cards.value = c || []
  if (Array.isArray(lg)) logs.value = lg
  ;(c || []).forEach(item => pushCardHist(item.id, item.value, item.unit))
  pushHist('cpu', d.cpu?.percent ?? 0)
  pushHist('mem', d.memory?.percent ?? 0)
  pushHist('net', d.network?.down_mbps ?? 0)
  pushHist('disk', d.disk?.percent ?? 0)
  pushHist('swap', d.swap?.percent ?? 0)
  pushHist('io', Math.min(100, ((d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)) * 10))
  analysisPct.value = Math.min(100, analysisPct.value + 0.5 + Math.random() * 2)
  if (analysisPct.value > 99) analysisPct.value = 20 + Math.random() * 10
}

function drawBg(ctx, W, H, t) {
  ctx.fillStyle = '#010610'
  ctx.fillRect(0, 0, W, H)

  const cx = W / 2, cy = H / 2
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(W, H) * 0.55)
  grad.addColorStop(0, 'rgba(0, 50, 80, 0.12)')
  grad.addColorStop(0.4, 'rgba(0, 25, 50, 0.06)')
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, W, H)

  ctx.strokeStyle = 'rgba(0,229,255,0.035)'
  ctx.lineWidth = 1
  const g = 60
  for (let x = 0; x < W; x += g) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke() }
  for (let y = 0; y < H; y += g) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke() }

  for (let ring = 1; ring <= 6; ring++) {
    ctx.strokeStyle = `rgba(0,229,255,${0.04 + ring * 0.012})`
    ctx.beginPath()
    ctx.arc(cx, cy, (60 + ring * 65) * (Math.max(W, H) / 900), 0, Math.PI * 2)
    ctx.stroke()
  }

  particles.forEach(p => {
    p.x += p.vx; p.y += p.vy
    if (p.x < 0 || p.x > 1) p.vx *= -1
    if (p.y < 0 || p.y > 1) p.vy *= -1
    ctx.fillStyle = 'rgba(0,229,255,0.35)'
    ctx.beginPath()
    ctx.arc(p.x * W, p.y * H, p.r, 0, Math.PI * 2)
    ctx.fill()
  })
}

function drawWave(ctx, W, H) {
  drawMultiLine(ctx, W, H, [
    { data: history.cpu, color: '#00e5ff' },
    { data: history.mem, color: '#9d4edd' },
    { data: history.net, color: '#ff6b35', max: 10 },
    { data: history.disk, color: '#00e5ff' },
    { data: history.swap, color: '#ff6b35' },
    { data: history.io, color: '#9d4edd' },
  ])
}

function drawRadar(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H)
  const cx = W / 2, cy = H / 2, r = Math.min(W, H) / 2 - 16
  const labels = ['CPU', 'MEM', 'DSK', 'SWP', 'NET', 'I/O']
  const axes = [
    d.cpu?.percent ?? 0, d.memory?.percent ?? 0, d.disk?.percent ?? 0,
    d.swap?.percent ?? 0, Math.min(100, (d.network?.down_mbps ?? 0) * 20),
    Math.min(100, ((d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)) * 10),
  ]
  ctx.strokeStyle = 'rgba(0,229,255,0.2)'
  for (let ring = 1; ring <= 3; ring++) {
    ctx.beginPath(); ctx.arc(cx, cy, (r / 3) * ring, 0, Math.PI * 2); ctx.stroke()
  }
  labels.forEach((lbl, i) => {
    const a = (i / labels.length) * Math.PI * 2 - Math.PI / 2
    const x = cx + Math.cos(a) * (r + 14)
    const y = cy + Math.sin(a) * (r + 14)
    ctx.fillStyle = 'rgba(0,229,255,0.5)'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(lbl, x, y + 3)
  })
  ctx.beginPath()
  axes.forEach((v, i) => {
    const a = (i / axes.length) * Math.PI * 2 - Math.PI / 2
    const dist = (v / 100) * r
    const x = cx + Math.cos(a) * dist
    const y = cy + Math.sin(a) * dist
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.closePath()
  ctx.fillStyle = 'rgba(0,229,255,0.2)'
  ctx.fill()
  ctx.strokeStyle = '#00e5ff'
  ctx.lineWidth = 2
  ctx.shadowColor = '#00e5ff'
  ctx.shadowBlur = 10
  ctx.stroke()
  ctx.shadowBlur = 0
}

function resizeCanvas(canvas) {
  if (!canvas) return null
  const dpr = devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  if (rect.width < 1 || rect.height < 1) return null
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  const ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  return { ctx, w: rect.width, h: rect.height }
}

function animate(t) {
  const d = data.value
  const cpu = d.cpu?.percent ?? 0
  const diskIO = (d.disk?.read_mbps ?? 0) + (d.disk?.write_mbps ?? 0)
  const netFlow = (d.network?.down_mbps ?? 0) + (d.network?.up_mbps ?? 0)

  const bg = resizeCanvas(bgCanvas.value)
  if (bg) drawBg(bg.ctx, bg.w, bg.h, t)

  const rc = resizeCanvas(reactorCanvas.value)
  if (rc) {
    drawReactor(rc.ctx, rc.w, rc.h, t, {
      cpuPct: cpu,
      threads: d.system?.threads ?? 0,
      coreTemp: reactorHeat.value,
      diskIO,
      netFlow,
      radiation: systemLoadIndex.value,
      alert: alertLevel.value,
    })
  }

  const wc = resizeCanvas(waveCanvas.value)
  if (wc) drawWave(wc.ctx, wc.w, wc.h)

  const bc = resizeCanvas(barCanvas.value)
  if (bc) drawBarChart(bc.ctx, bc.w, bc.h, horizBars.value, t, alertLevel.value)

  const md = resizeCanvas(memDonutCanvas.value)
  if (md) {
    const memPct = Math.round(d.memory?.percent ?? 0)
    drawDonutChart(md.ctx, md.w, md.h, memSlices.value, t, `${memPct}%`)
  }

  const ns = resizeCanvas(netSparkCanvas.value)
  if (ns) {
    const netHist = history.net.map(v => Math.min(100, v * 20))
    drawSparkline(ns.ctx, ns.w, ns.h, netHist.length ? netHist : [0], '#00e5ff')
  }

  const rd = resizeCanvas(radarCanvas.value)
  if (rd) drawRadar(rd.ctx, rd.w, rd.h, d)

  animId = requestAnimationFrame(animate)
}

const codeSnippets = [
  'HRESULT InitTelemetry() { return S_OK; }',
  'DWORD coreLoad = QueryPerformanceCounter(&pc);',
  'if (memUsage > THRESHOLD) TriggerAlert();',
  'ReadProcessMemory(hProc, addr, &buf, sizeof(buf));',
  'NTSTATUS status = ZwQuerySystemInformation(...);',
]

function enterDesktopMode() {
  const params = new URLSearchParams(location.search)
  isDesktop.value = params.has('desktop') || params.get('mode') === 'desktop'
  if (!isDesktop.value) return
  document.documentElement.classList.add('desktop-mode')
  setTimeout(() => {
    document.documentElement.requestFullscreen?.().catch(() => {})
  }, 300)
}

function onWindowResize() {
  clampLayout()
}

function onKeyDown(e) {
  if (e.key === 'Escape' && isDesktop.value) {
    document.exitFullscreen?.().catch(() => {})
    window.close()
  }
}

onMounted(() => {
  enterDesktopMode()
  clampLayout()
  saveLayout()
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', onWindowResize)

  const tick = () => {
    clockStr.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    codeLine.value = codeSnippets[Math.floor(Date.now() / 2000) % codeSnippets.length]
  }
  tick()
  clockTimer = setInterval(tick, 1000)

  disconnect = connectHudStream(onMetrics, s => { connState.value = s })

  const pollLogs = () => {
    fetch(`${import.meta.env.DEV ? '' : 'http://127.0.0.1:8799'}/api/logs`)
      .then(r => r.json())
      .then(j => { if (Array.isArray(j.logs)) logs.value = j.logs })
      .catch(() => {})
  }
  pollLogs()
  logTimer = setInterval(pollLogs, 2000)

  animId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearInterval(logTimer)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onWindowResize)
  onResizeEnd()
  disconnect?.()
  cancelAnimationFrame(animId)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+SC:wght@400;700&display=swap');

.hud-root {
  position: relative;
  width: 100vw;
  height: 100vh;
  background: #020810;
  color: #b8e4ff;
  font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  opacity: 0.6;
}

.scanlines {
  position: absolute; inset: 0; z-index: 50; pointer-events: none;
  background: repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.03) 3px, rgba(0,0,0,0.03) 6px);
}
.vignette {
  position: absolute; inset: 0; z-index: 49; pointer-events: none;
  background: radial-gradient(ellipse at center, transparent 72%, rgba(0,0,0,0.12) 100%);
}

.hud-shell {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  padding: 12px 14px;
  box-sizing: border-box;
  gap: 0;
  overflow: hidden;
}

.hud-main {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  gap: 0;
  margin-top: 10px;
  overflow: hidden;
}

.hud-bottom {
  flex-shrink: 0;
  display: flex;
  gap: 0;
  min-height: 200px;
  min-width: 0;
  margin-top: 0;
  overflow: hidden;
}

.v-resizer {
  width: 10px;
  flex-shrink: 0;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 20;
}
.v-resizer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: transparent;
}
.v-resizer:hover { background: rgba(0,229,255,0.06); }
.v-resizer-sm { width: 8px; }
.resizer-grip {
  font-size: 10px;
  color: rgba(0,229,255,0.35);
  letter-spacing: -2px;
  pointer-events: none;
  user-select: none;
}

.h-resizer {
  height: 10px;
  flex-shrink: 0;
  cursor: row-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2px 0;
}
.h-resizer:hover { background: rgba(0,229,255,0.06); }
.resizer-grip-h {
  font-size: 10px;
  color: rgba(0,229,255,0.35);
  pointer-events: none;
  user-select: none;
}

.hud-top {
  flex-shrink: 0;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  border: 1px solid rgba(0,229,255,0.14);
  background: linear-gradient(180deg, rgba(0,20,40,0.34), rgba(0,15,30,0.26));
  backdrop-filter: blur(2px);
}
.header-gauge {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  justify-content: center;
  max-width: 280px;
}
.hg-ring { position: relative; width: 36px; height: 36px; flex-shrink: 0; }
.hg-svg { width: 100%; height: 100%; filter: drop-shadow(0 0 4px #00e5ff); }
.hg-pct {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px; font-weight: 700; color: #fff;
}
.hg-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.hg-title { font-size: 11px; color: rgba(0,229,255,0.85); font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
.hg-hint { font-size: 9px; color: rgba(0,229,255,0.4); }
.brand { display: flex; align-items: center; gap: 12px; }
.diamond { color: #00e5ff; font-size: 18px; }
.brand-text { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; letter-spacing: 3px; color: #fff; }
.accent { color: #00e5ff; }
.ver { font-size: 10px; color: rgba(0,229,255,0.4); letter-spacing: 2px; margin-left: 8px; }
.top-status { display: flex; align-items: center; gap: 8px; font-size: 13px; letter-spacing: 1px; }
.top-status.connected { color: #00ff88; }
.top-status.reconnecting, .top-status.connecting { color: #ffaa00; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 1.5s infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.clock { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: #00e5ff; }

.col-mid {
  display: grid;
  grid-template-rows: min-content min-content minmax(0, 1fr);
  gap: 6px;
  min-height: 0;
  min-width: 0;
  flex-shrink: 0;
  overflow: hidden;
}
.col-right {
  flex: 1;
  min-width: 280px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}
.col-reactor {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  min-width: 0;
  align-self: stretch;
  overflow: hidden;
}
.panel-reactor {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: rgba(0, 8, 20, 0.15);
  border: 1px solid rgba(0,229,255,0.22);
  box-shadow: inset 0 0 30px rgba(0,229,255,0.04);
}
.panel-memres {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.memres-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.memres-body::-webkit-scrollbar { width: 3px; }
.memres-body::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); }
.memres-donut { flex-shrink: 0; }
.mem-donut-canvas { width: 76px; height: 76px; display: block; }
.memres-tiles { width: 100%; display: flex; flex-direction: column; gap: 5px; flex: 1; justify-content: space-evenly; }
.memres-tile {
  padding: 5px 7px;
  background: rgba(0,229,255,0.04);
  border: 1px solid rgba(0,229,255,0.1);
  border-radius: 2px;
}
.memres-tile.hot { border-color: rgba(255,80,80,0.4); background: rgba(255,60,60,0.06); }
.memres-head { display: flex; justify-content: space-between; align-items: baseline; gap: 4px; margin-bottom: 3px; }
.memres-label { font-size: 9px; color: rgba(200,230,255,0.7); }
.memres-val { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #00e5ff; white-space: nowrap; }
.memres-tile.hot .memres-val { color: #ff7070; }
.memres-bar { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.memres-fill { height: 100%; border-radius: 2px; transition: width 0.35s; }
.reactor-panel-canvas {
  flex: none;
  width: 100%;
  display: block;
  filter: brightness(1.2) contrast(1.08) saturate(1.12);
}
.reactor-mini {
  flex-shrink: 0;
  padding: 5px 10px 7px;
  border-top: 1px solid rgba(0,229,255,0.1);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.rm-row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: rgba(200,230,255,0.55);
}
.rm-row strong {
  font-family: 'JetBrains Mono', monospace;
  color: #00e5ff;
  font-weight: 700;
}
.rm-sub { opacity: 0.85; }
.rm-sub strong { font-size: 9px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.col-br { min-height: 0; min-width: 0; flex: 1; height: 100%; overflow: hidden; }
.row-bottom { display: flex; align-items: stretch; min-height: 0; min-width: 0; height: 100%; flex-shrink: 0; overflow: hidden; }

.panel {
  position: relative;
  background: rgba(0, 12, 28, 0.26);
  border: 1px solid rgba(0,229,255,0.14);
  backdrop-filter: blur(2px);
  border-radius: 3px;
}
.panel-corner { position: absolute; width: 14px; height: 14px; }
.panel-corner.tl { top: 0; left: 0; border-top: 2px solid #00e5ff; border-left: 2px solid #00e5ff; }
.panel-corner.tr { top: 0; right: 0; border-top: 2px solid #00e5ff; border-right: 2px solid #00e5ff; }
.panel-corner.bl { bottom: 0; left: 0; border-bottom: 2px solid #00e5ff; border-left: 2px solid #00e5ff; }
.panel-corner.br { bottom: 0; right: 0; border-bottom: 2px solid #00e5ff; border-right: 2px solid #00e5ff; }
.panel-title { padding: 7px 12px 5px; font-size: 11px; font-weight: 700; color: rgba(0,229,255,0.8); letter-spacing: 1px; border-bottom: 1px solid rgba(0,229,255,0.08); }
.panel-title.inline { border-bottom: none; padding: 0 0 4px; }

.panel-analysis { flex-shrink: 0; }
.analysis-row { display: flex; align-items: center; gap: 10px; padding: 5px 10px 7px; }
.analysis-left { flex: 1; min-width: 0; }
.analysis-bar { margin: 4px 0; height: 4px; background: rgba(0,229,255,0.1); border-radius: 2px; }
.analysis-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #9d4edd); transition: width 0.3s; box-shadow: 0 0 8px #00e5ff; border-radius: 2px; }
.analysis-label { font-size: 9px; color: rgba(0,229,255,0.5); font-family: 'JetBrains Mono', monospace; }
.mini-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; flex: 1.2; }
.mini-stat { text-align: center; padding: 4px 3px; background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.12); }
.ms-val { display: block; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #00e5ff; font-weight: 700; }
.ms-lbl { display: block; font-size: 9px; color: rgba(200,230,255,0.55); margin-top: 1px; }

.panel-metrics { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.metrics-scroll {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
.metrics-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 8px 10px 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: 1fr;
  gap: 6px;
  align-content: stretch;
  overflow-y: auto;
}
@media (max-width: 1280px) {
  .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.metrics-grid::-webkit-scrollbar { width: 4px; }
.metrics-grid::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); border-radius: 2px; }
.metric-card {
  padding: 6px 8px;
  background: rgba(0,229,255,0.05);
  border: 1px solid rgba(0,229,255,0.12);
  border-radius: 3px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  min-height: 44px;
}
.metric-card.hot { border-color: rgba(255,80,80,0.35); background: rgba(255,60,60,0.06); }
.mc-top { display: flex; justify-content: space-between; align-items: baseline; gap: 6px; min-width: 0; }
.mc-label {
  font-size: 10px;
  color: rgba(200,230,255,0.78);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.mc-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #00e5ff;
  white-space: nowrap;
  flex-shrink: 0;
}
.metric-card.hot .mc-val { color: #ff7070; }
.mc-track { height: 4px; background: rgba(255,255,255,0.07); border-radius: 2px; overflow: hidden; }
.mc-fill { height: 100%; border-radius: 2px; transition: width 0.35s; box-shadow: 0 0 5px currentColor; }

.sensor-strip { padding: 5px 10px 7px; display: flex; flex-direction: column; gap: 4px; }
.sensor-row {
  display: grid;
  grid-template-columns: 46px 1fr 46px;
  align-items: center;
  gap: 4px;
  padding: 1px 0;
}
.sensor-row.hot .sr-val { color: #ff6060; }
.sr-label { font-size: 9px; color: rgba(200,230,255,0.65); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sr-track { height: 5px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.sr-fill { height: 100%; border-radius: 2px; transition: width 0.35s; box-shadow: 0 0 4px currentColor; }
.sr-val { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #00e5ff; text-align: right; white-space: nowrap; }

.panel-sensors { flex-shrink: 0; overflow: hidden; }
.panel-cores { flex-shrink: 0; overflow: hidden; }
.core-bars { display: flex; gap: 3px; padding: 3px 8px 4px; height: 40px; align-items: flex-end; flex-shrink: 0; }
.core-col { flex: 1; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; }
.core-fill { width: 100%; background: linear-gradient(0deg, #00e5ff, #9d4edd); transition: height 0.35s; box-shadow: 0 0 8px #00e5ff; min-height: 3px; border-radius: 2px 2px 0 0; }
.core-id { font-size: 8px; color: rgba(0,229,255,0.5); margin-top: 2px; font-family: 'JetBrains Mono', monospace; }

.panel-logs { min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.log-stream {
  flex: 1;
  overflow-y: auto;
  padding: 6px 8px 8px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: flex-start;
}
.log-stream::-webkit-scrollbar { width: 4px; }
.log-stream::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); }
.log-empty { padding: 12px; color: rgba(0,229,255,0.45); font-size: 11px; text-align: center; }
.log-card {
  padding: 5px 8px;
  border-radius: 3px;
  border: 1px solid rgba(0,229,255,0.08);
  background: rgba(0, 20, 40, 0.22);
  flex-shrink: 0;
}
.log-card.crit { border-color: rgba(255,80,80,0.35); background: rgba(255,60,60,0.07); }
.log-card.warn { border-color: rgba(255,170,0,0.28); background: rgba(255,140,0,0.05); }
.log-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 3px;
}
.log-time { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: rgba(0,229,255,0.5); }
.log-level { font-size: 10px; font-weight: 700; }
.log-card.crit .log-level { color: #ff5050; }
.log-card.warn .log-level { color: #ffaa00; }
.log-card.info .log-level { color: #00ff88; }
.log-src {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: rgba(0,229,255,0.45);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.log-msg {
  color: rgba(230, 245, 255, 0.92);
  font-size: 12px;
  line-height: 1.45;
  word-break: break-word;
}
.log-ai-tag {
  margin-left: auto;
  padding: 1px 6px;
  font-size: 9px;
  color: #9d4edd;
  border: 1px solid rgba(157,78,221,0.35);
  border-radius: 2px;
}
.log-toggle {
  display: inline-block;
  margin-top: 6px;
  padding: 0;
  border: none;
  background: none;
  color: rgba(0,229,255,0.5);
  font-size: 10px;
  cursor: pointer;
  font-family: inherit;
}
.log-toggle:hover { color: #00e5ff; text-decoration: underline; }
.log-raw {
  margin-top: 6px;
  padding: 6px 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: rgba(160,180,200,0.5);
  background: rgba(0,0,0,0.25);
  border-left: 2px solid rgba(0,229,255,0.15);
  word-break: break-all;
  line-height: 1.4;
}

.panel-overview { height: 100%; min-height: 0; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.overview-body {
  flex: 1;
  display: grid;
  grid-template-columns: 118px 1fr;
  gap: 10px;
  padding: 8px 10px;
  min-height: 0;
  overflow: hidden;
}
.overview-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
  overflow-y: auto;
}
.overview-left::-webkit-scrollbar { width: 3px; }
.overview-left::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); }
.radar-canvas { width: 100px; height: 100px; display: block; flex-shrink: 0; align-self: center; }
.ov-gauges { display: flex; flex-direction: column; gap: 4px; }
.ov-gauge { display: grid; grid-template-columns: 28px 1fr 26px; align-items: center; gap: 4px; }
.ov-gauge-label { font-size: 8px; color: rgba(200,230,255,0.55); font-family: 'JetBrains Mono', monospace; }
.ov-gauge-track { height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.ov-gauge-fill { height: 100%; border-radius: 2px; transition: width 0.35s; }
.ov-gauge-pct { font-family: 'JetBrains Mono', monospace; font-size: 8px; color: #00e5ff; text-align: right; }
.overview-main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}
.overview-cards {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(36px, auto);
  gap: 5px;
  overflow-y: auto;
  align-content: start;
}
.overview-cards::-webkit-scrollbar { width: 3px; }
.overview-cards::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); }
.ov-card {
  padding: 5px 7px;
  background: rgba(0,229,255,0.04);
  border: 1px solid rgba(0,229,255,0.1);
  border-radius: 2px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  min-width: 0;
}
.ov-card.hot { border-color: rgba(255,80,80,0.35); background: rgba(255,60,60,0.06); }
.ov-card-label { font-size: 9px; color: rgba(200,230,255,0.6); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ov-card-val { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #00e5ff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ov-card.hot .ov-card-val { color: #ff7070; }
.ov-spark-wrap {
  flex-shrink: 0;
  padding: 4px 6px 2px;
  border-top: 1px solid rgba(0,229,255,0.08);
}
.ov-spark-title { display: block; font-size: 9px; color: rgba(0,229,255,0.5); margin-bottom: 3px; letter-spacing: 0.5px; }
.net-spark-canvas { width: 100%; height: 36px; display: block; }

.panel-wave { flex: 1; min-width: 0; height: 100%; display: flex; flex-direction: column; }
.bar-canvas { width: 100%; height: 72px; flex-shrink: 0; display: block; padding: 0 8px; box-sizing: border-box; }
.wave-canvas { flex: 1; display: block; width: 100%; min-height: 40px; padding: 0 8px 6px; box-sizing: border-box; }

.code-stream {
  flex-shrink: 0;
  padding: 6px 14px 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: rgba(0,229,255,0.35);
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  border-top: 1px solid rgba(0,229,255,0.06);
}

.desktop-hint {
  position: fixed;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  font-size: 10px;
  color: rgba(0,229,255,0.28);
  pointer-events: none;
  opacity: 0.7;
}

.alert-active .panel-reactor {
  box-shadow: inset 0 0 24px rgba(255,40,40,0.12), 0 0 16px rgba(255,40,40,0.15);
  border-color: rgba(255,80,80,0.35);
}

.desktop-mode .hud-top { border-top: none; }
</style>
