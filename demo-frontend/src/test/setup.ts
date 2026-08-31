import { afterEach } from 'vitest'

const values = new Map<string, string>()
const testStorage: Storage = {
  get length() { return values.size },
  clear: () => values.clear(),
  getItem: key => values.get(key) ?? null,
  key: index => [...values.keys()][index] ?? null,
  removeItem: key => { values.delete(key) },
  setItem: (key, value) => { values.set(key, String(value)) },
}
Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: testStorage })
Object.defineProperty(window, 'localStorage', { configurable: true, value: testStorage })

afterEach(() => {
  localStorage.clear()
  document.documentElement.lang = 'en'
})
