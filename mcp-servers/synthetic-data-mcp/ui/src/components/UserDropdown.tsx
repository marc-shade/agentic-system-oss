import React from 'react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'
import { User, LogOut, Settings } from 'lucide-react'

export function UserDropdown() {
  const { user, logout } = useAuthStore()

  if (!user) {
    return null
  }

  return (
    <div className="relative">
      <Button variant="ghost" size="icon">
        <User className="h-4 w-4" />
      </Button>
      
      {/* Dropdown implementation would go here */}
      {/* For now, this is a placeholder */}
    </div>
  )
}