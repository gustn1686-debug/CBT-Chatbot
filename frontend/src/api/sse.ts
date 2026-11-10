export type SseMessage = { event: string; data: string }

// fetch 응답 본문(text/event-stream)을 이벤트 단위로 읽는다.
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<SseMessage> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replaceAll('\r\n', '\n')

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const message = parseBlock(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (message) yield message
        boundary = buffer.indexOf('\n\n')
      }
    }
    const rest = parseBlock(buffer)
    if (rest) yield rest
  } finally {
    reader.releaseLock()
  }
}

function parseBlock(block: string): SseMessage | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
  }
  return data.length ? { event, data: data.join('\n') } : null
}
