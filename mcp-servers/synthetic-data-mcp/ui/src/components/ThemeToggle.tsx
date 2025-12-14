import React from 'react'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/stores/ui'
import { Sun, Moon, Monitor } from 'lucide-react'

export function ThemeToggle() {
  const { theme, setTheme } = useUiStore()

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'system'] as const
    const currentIndex = themes.indexOf(theme)
    const nextIndex = (currentIndex + 1) % themes.length
    setTheme(themes[nextIndex])
  }

  const getIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className="h-4 w-4" />
      case 'dark':
        return <Moon className="h-4 w-4" />
      case 'system':
        return <Monitor className="h-4 w-4" />
      default:
        return <Sun className="h-4 w-4" />
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={cycleTheme}
      title={`Current theme: ${theme}`}
    >
      {getIcon()}
    </Button>
  )
}