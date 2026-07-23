const HOST = import.meta.env.DEV ? '' : 'http://127.0.0.1:8799'

export function connectHudStream(onData, onState) {
  let es = null
  let closed = false
  let retry = 0
  let timer = null

  function connect() {
    if (closed) return
    onState?.('connecting')
    es?.close()
    const url = `${HOST}/api/stream`
    es = new EventSource(url)
    es.onopen = () => { retry = 0; onState?.('connected') }
    es.onmessage = (e) => {
      try {
        const p = JSON.parse(e.data)
        if (p.type === 'metrics') onData(p.data, p.cards, p.logs)
      } catch {}
    }
    es.onerror = () => {
      onState?.('reconnecting')
      es.close()
      timer = setTimeout(connect, Math.min(1000 * 1.5 ** retry++, 8000))
    }
  }

  connect()
  return () => { closed = true; clearTimeout(timer); es?.close() }
}
