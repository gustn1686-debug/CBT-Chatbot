import { readSse } from './sse'

function streamOf(...chunks: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(encoder.encode(c)))
      controller.close()
    },
  })
}

async function collect(body: ReadableStream<Uint8Array>) {
  const out = []
  for await (const m of readSse(body)) out.push(m)
  return out
}

describe('readSse', () => {
  it('이벤트가 청크 중간에서 끊겨도 하나로 합친다', async () => {
    const messages = await collect(
      streamOf('event: meta\ndata: {"a":1}\n\nevent: tok', 'en\ndata: {"delta":"안"}\n\n'),
    )
    expect(messages).toEqual([
      { event: 'meta', data: '{"a":1}' },
      { event: 'token', data: '{"delta":"안"}' },
    ])
  })

  it('CRLF 줄바꿈과 마지막 빈 줄이 없는 이벤트도 읽는다', async () => {
    const messages = await collect(streamOf('event: done\r\ndata: {}\r\n\r\nevent: error\r\ndata: {"code":"x"}'))
    expect(messages.map((m) => m.event)).toEqual(['done', 'error'])
  })
})
