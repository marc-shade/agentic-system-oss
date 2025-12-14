import React, { useEffect } from 'react'
import { Toaster } from 'sonner'
import { useUiStore } from '@/stores/ui'
import { X } from 'lucide-react'

interface NotificationProviderProps {
  children: React.ReactNode
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const { theme } = useUiStore()

  return (
    <>
      {children}
      <Toaster
        theme={theme === 'system' ? 'system' : theme}
        className="toaster group"
        position="top-right"
        richColors
        expand
        visibleToasts={5}
        closeButton
        toastOptions={{
          classNames: {
            toast: 'group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg',
            description: 'group-[.toast]:text-muted-foreground',
            actionButton: 'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground',
            cancelButton: 'group-[.toast]:bg-muted group-[.toast]:text-muted-foreground',
          },
        }}
      />
    </>
  )
}