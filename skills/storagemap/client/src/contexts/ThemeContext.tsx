import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'

type ThemeMode = 'default' | 'enterprise'

interface ThemeContextType {
  theme: ThemeMode
  setTheme: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('default')

  useEffect(() => {
    const saved = localStorage.getItem('storagemap-theme') as ThemeMode
    if (saved === 'default' || saved === 'enterprise') {
      setThemeState(saved)
    }
  }, [])

  const setTheme = (mode: ThemeMode) => {
    localStorage.setItem('storagemap-theme', mode)
    setThemeState(mode)
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
