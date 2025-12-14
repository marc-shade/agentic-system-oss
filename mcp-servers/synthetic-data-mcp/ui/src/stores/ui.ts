import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { Notification } from '@/types'

interface UiState {
  // Theme
  theme: 'light' | 'dark' | 'system'
  
  // Layout
  sidebarCollapsed: boolean
  sidebarOpen: boolean // For mobile
  
  // Loading states
  loadingStates: Record<string, boolean>
  
  // Notifications
  notifications: Notification[]
  
  // Dialogs and modals
  modals: Record<string, boolean>
  
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setLoading: (key: string, loading: boolean) => void
  clearAllLoading: () => void
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  removeNotification: (id: string) => void
  markNotificationRead: (id: string) => void
  clearAllNotifications: () => void
  openModal: (modalId: string) => void
  closeModal: (modalId: string) => void
  toggleModal: (modalId: string) => void
  closeAllModals: () => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'system',
      sidebarCollapsed: false,
      sidebarOpen: false,
      loadingStates: {},
      notifications: [],
      modals: {},

      // Theme actions
      setTheme: (theme) => {
        set({ theme })
        
        // Apply theme to document
        const root = document.documentElement
        
        if (theme === 'system') {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
          root.classList.toggle('dark', systemTheme === 'dark')
        } else {
          root.classList.toggle('dark', theme === 'dark')
        }
      },

      // Sidebar actions
      toggleSidebar: () => {
        set(state => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setSidebarOpen: (open) => {
        set({ sidebarOpen: open })
      },

      // Loading state actions
      setLoading: (key, loading) => {
        set(state => ({
          loadingStates: {
            ...state.loadingStates,
            [key]: loading
          }
        }))
      },

      clearAllLoading: () => {
        set({ loadingStates: {} })
      },

      // Notification actions
      addNotification: (notification) => {
        const id = `notification_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: new Date().toISOString(),
          read: false,
        }
        
        set(state => ({
          notifications: [newNotification, ...state.notifications]
        }))
        
        // Auto-dismiss if specified
        if (notification.auto_dismiss) {
          setTimeout(() => {
            get().removeNotification(id)
          }, notification.auto_dismiss)
        }
      },

      removeNotification: (id) => {
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== id)
        }))
      },

      markNotificationRead: (id) => {
        set(state => ({
          notifications: state.notifications.map(n => 
            n.id === id ? { ...n, read: true } : n
          )
        }))
      },

      clearAllNotifications: () => {
        set({ notifications: [] })
      },

      // Modal actions
      openModal: (modalId) => {
        set(state => ({
          modals: {
            ...state.modals,
            [modalId]: true
          }
        }))
      },

      closeModal: (modalId) => {
        set(state => ({
          modals: {
            ...state.modals,
            [modalId]: false
          }
        }))
      },

      toggleModal: (modalId) => {
        set(state => ({
          modals: {
            ...state.modals,
            [modalId]: !state.modals[modalId]
          }
        }))
      },

      closeAllModals: () => {
        set({ modals: {} })
      },
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)

// Theme system initialization
export const initializeTheme = () => {
  const { theme, setTheme } = useUiStore.getState()
  
  // Apply initial theme
  setTheme(theme)
  
  // Listen for system theme changes
  if (theme === 'system') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const root = document.documentElement
      root.classList.toggle('dark', mediaQuery.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }
}

// Notification helpers
export const useNotifications = () => {
  const { addNotification } = useUiStore()
  
  return {
    success: (message: string, title?: string) => {
      addNotification({
        type: 'success',
        title: title || 'Success',
        message,
        auto_dismiss: 5000,
      })
    },
    
    error: (message: string, title?: string) => {
      addNotification({
        type: 'error',
        title: title || 'Error',
        message,
        auto_dismiss: 8000,
      })
    },
    
    warning: (message: string, title?: string) => {
      addNotification({
        type: 'warning',
        title: title || 'Warning',
        message,
        auto_dismiss: 6000,
      })
    },
    
    info: (message: string, title?: string) => {
      addNotification({
        type: 'info',
        title: title || 'Info',
        message,
        auto_dismiss: 4000,
      })
    },
  }
}

// Loading helpers
export const useLoading = (key?: string) => {
  const { loadingStates, setLoading } = useUiStore()
  
  const isLoading = key ? loadingStates[key] || false : Object.values(loadingStates).some(Boolean)
  
  const startLoading = (loadingKey?: string) => {
    const finalKey = loadingKey || key || 'default'
    setLoading(finalKey, true)
  }
  
  const stopLoading = (loadingKey?: string) => {
    const finalKey = loadingKey || key || 'default'
    setLoading(finalKey, false)
  }
  
  return {
    isLoading,
    startLoading,
    stopLoading,
  }
}