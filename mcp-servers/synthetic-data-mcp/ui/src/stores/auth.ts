import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User } from '@/types'
import { api, apiClient } from '@/lib/api'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (credentials: { email: string; password: string }) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  clearError: () => void
  setUser: (user: User) => void
  setToken: (token: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await api.login(credentials)
          const { user, token } = response.data
          
          // Set token in API client
          apiClient.setAuthToken(token)
          
          set({ 
            user, 
            token, 
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({ 
            isLoading: false, 
            error: error.message || 'Login failed' 
          })
          throw error
        }
      },

      logout: () => {
        // Clear token from API client
        apiClient.removeAuthToken()
        
        // Clear stored state
        set({ 
          user: null, 
          token: null, 
          error: null 
        })
        
        // Call logout API in background
        api.logout().catch(console.error)
      },

      refreshUser: async () => {
        const { token } = get()
        if (!token) return
        
        try {
          const response = await api.getCurrentUser()
          set({ user: response.data })
        } catch (error: any) {
          // If user refresh fails, token might be invalid
          if (error.code === 'UNAUTHORIZED') {
            get().logout()
          }
        }
      },

      clearError: () => {
        set({ error: null })
      },

      setUser: (user) => {
        set({ user })
      },

      setToken: (token) => {
        apiClient.setAuthToken(token)
        set({ token })
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token 
      }),
      onRehydrateStorage: () => (state) => {
        // Restore token in API client after rehydration
        if (state?.token) {
          apiClient.setAuthToken(state.token)
        }
      },
    }
  )
)

// Initialize auth state on app start
export const initializeAuth = async () => {
  const { token, refreshUser } = useAuthStore.getState()
  
  if (token) {
    // Set token in API client
    apiClient.setAuthToken(token)
    
    // Refresh user data to ensure it's current
    try {
      await refreshUser()
    } catch (error) {
      console.error('Failed to refresh user on initialization:', error)
    }
  }
}