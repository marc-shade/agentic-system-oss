import React, { createContext, useContext, useEffect, useRef } from 'react'
import { websocketClient, WebSocketClient } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useDataStore } from '@/stores/data'
import { useNotifications } from '@/stores/ui'
import { JobUpdate } from '@/types'

interface WebSocketContextType {
  client: WebSocketClient | null
  isConnected: boolean
}

const WebSocketContext = createContext<WebSocketContextType>({
  client: null,
  isConnected: false,
})

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { user } = useAuthStore()
  const { updateJob } = useDataStore()
  const notifications = useNotifications()
  const isConnectedRef = useRef(false)

  useEffect(() => {
    if (!user) return

    // Connect WebSocket when user is authenticated
    websocketClient.connect()
    isConnectedRef.current = true

    // Set up event listeners
    websocketClient.on('job_update', (data: JobUpdate) => {
      updateJob(data.job_id, {
        status: data.status as any,
        progress: data.progress,
        updated_at: new Date().toISOString(),
      })

      // Show notification for important status changes
      if (data.status === 'completed') {
        notifications.success(`Job completed successfully`, 'Generation Complete')
      } else if (data.status === 'failed') {
        notifications.error(`Job failed: ${data.message || 'Unknown error'}`, 'Generation Failed')
      }
    })

    websocketClient.on('system_alert', (data: any) => {
      notifications.warning(data.message, 'System Alert')
    })

    websocketClient.on('privacy_alert', (data: any) => {
      notifications.warning(
        `Privacy budget usage is at ${data.percentage}%`,
        'Privacy Budget Alert'
      )
    })

    websocketClient.on('compliance_alert', (data: any) => {
      notifications.error(
        `Compliance violation detected: ${data.message}`,
        'Compliance Alert'
      )
    })

    websocketClient.on('database_status', (data: any) => {
      if (data.status === 'disconnected') {
        notifications.error(
          `Database connection lost: ${data.database_name}`,
          'Connection Error'
        )
      } else if (data.status === 'connected') {
        notifications.success(
          `Database reconnected: ${data.database_name}`,
          'Connection Restored'
        )
      }
    })

    // Cleanup on unmount
    return () => {
      websocketClient.disconnect()
      isConnectedRef.current = false
    }
  }, [user, updateJob, notifications])

  const contextValue: WebSocketContextType = {
    client: websocketClient,
    isConnected: isConnectedRef.current,
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}