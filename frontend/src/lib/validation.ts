// Figma 회원가입 화면의 안내 문구("영문, 숫자 포함 8자 이상")와 같은 규칙. 서버 규칙이 정해지면 맞춘다.
export const isEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)

export const isValidPassword = (value: string) =>
  value.length >= 8 && /[A-Za-z]/.test(value) && /\d/.test(value)

export const NICKNAME_MAX = 20
