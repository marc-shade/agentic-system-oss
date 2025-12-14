import React from 'react'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { Button } from '@/components/ui/button'
import { SearchInput } from '@/components/ui/input'
import { NotificationDropdown } from '@/components/NotificationDropdown'
import { UserDropdown } from '@/components/UserDropdown'
import { ThemeToggle } from '@/components/ThemeToggle'
import {
  Menu,
  Search,
  Bell,
  Settings,
  User,
  Database,
  Activity,
  Shield,
} from 'lucide-react'

interface HeaderProps {}

export function Header({}: HeaderProps) {
  const { user } = useAuthStore()
  const { setSidebarOpen, sidebarOpen } = useUiStore()

  return (
    <div className="flex h-16 items-center gap-4 px-6">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Search */}
      <div className="flex-1 max-w-md">
        <SearchInput
          placeholder="Search tables, schemas, jobs..."
          className="w-full"
        />
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        {/* Quick stats */}
        <div className="hidden md:flex items-center gap-4 mr-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Database className="h-4 w-4" />
            <span>3 DBs</span>
          </div>
          <div className="flex items-center gap-1">
            <Activity className="h-4 w-4" />
            <span>2 Jobs</span>
          </div>
          <div className="flex items-center gap-1">
            <Shield className="h-4 w-4" />
            <span>85% Budget</span>
          </div>
        </div>

        {/* Theme toggle */}
        <ThemeToggle />

        {/* Notifications */}
        <NotificationDropdown />

        {/* User menu */}
        <UserDropdown />
      </div>
    </div>
  )
}

// Quick action buttons component
export function QuickActions() {
  return (
    <div className="hidden lg:flex items-center gap-2">
      <Button variant="outline" size="sm">
        <Database className="h-4 w-4 mr-2" />
        New Connection
      </Button>
      <Button variant="outline" size="sm">
        <Activity className="h-4 w-4 mr-2" />
        Generate Data
      </Button>
    </div>
  )
}