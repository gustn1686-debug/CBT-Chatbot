import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from './ChatInput'

const setup = (props: Partial<Parameters<typeof ChatInput>[0]> = {}) => {
  const onSend = vi.fn()
  render(<ChatInput onSend={onSend} {...props} />)
  return { onSend, user: userEvent.setup(), box: screen.getByLabelText('메시지 입력') as HTMLTextAreaElement }
}

afterEach(() => vi.unstubAllGlobals())

describe('ChatInput', () => {
  it('여러 줄 입력칸이다 (글이 길어져도 다음 줄로 넘어간다)', () => {
    const { box } = setup()
    expect(box.tagName).toBe('TEXTAREA')
    expect(box.rows).toBe(1)
  })

  it('서버가 받는 길이(4000자)로 제한한다', () => {
    const { box } = setup()
    expect(box.maxLength).toBe(4000)
  })

  it('Enter 로 보내고 입력칸을 비운다', async () => {
    const { onSend, user, box } = setup()
    await user.type(box, '안녕하세요{Enter}')
    expect(onSend).toHaveBeenCalledWith('안녕하세요')
    expect(box).toHaveValue('')
  })

  it('Shift+Enter 는 보내지 않고 줄바꿈이 된다', async () => {
    const { onSend, user, box } = setup()
    await user.type(box, '첫 줄{Shift>}{Enter}{/Shift}둘째 줄')
    expect(onSend).not.toHaveBeenCalled()
    expect(box).toHaveValue('첫 줄\n둘째 줄')

    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(onSend).toHaveBeenCalledWith('첫 줄\n둘째 줄')
  })

  it('한글 조합 중에 누른 Enter 는 보내지 않는다', async () => {
    const { onSend, user, box } = setup()
    await user.type(box, '안녕')
    fireEvent.keyDown(box, { key: 'Enter', isComposing: true })
    fireEvent.keyDown(box, { key: 'Enter', keyCode: 229 })
    expect(onSend).not.toHaveBeenCalled()
    expect(box).toHaveValue('안녕')
  })

  it('공백뿐이면 보내지 못한다', async () => {
    const { onSend, user, box } = setup()
    await user.type(box, '   {Enter}')
    expect(onSend).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled()
  })

  it('답변을 받는 중이거나 연결이 끊기면 Enter 로도 보내지 못한다', async () => {
    const { onSend, user, box } = setup({ disabled: true })
    await user.type(box, '안녕{Enter}')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('터치 기기에서는 Enter 가 줄바꿈이고 보내기 버튼으로 보낸다', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({ matches: query.includes('coarse'), media: query }))
    const { onSend, user, box } = setup()
    await user.type(box, '안녕{Enter}반가워요')
    expect(onSend).not.toHaveBeenCalled()
    expect(box).toHaveValue('안녕\n반가워요')

    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(onSend).toHaveBeenCalledWith('안녕\n반가워요')
  })
})
