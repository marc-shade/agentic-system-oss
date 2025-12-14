import React from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useUiStore } from '@/stores/ui'
import { Bell, Check, X } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export function NotificationDropdown() {
  const { notifications, markNotificationRead, removeNotification } = useUiStore()
  
  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="relative">
      <Button variant="ghost" size="icon" className="relative">
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <Badge 
            variant="destructive" 
            className="absolute -top-1 -right-1 h-5 w-5 p-0 text-xs flex items-center justify-center"
          >
            {unreadCount}
          </Badge>
        )}
      </Button>
      
      {/* Dropdown implementation would go here */}
      {/* For now, this is a placeholder */}
    </div>
  )
}