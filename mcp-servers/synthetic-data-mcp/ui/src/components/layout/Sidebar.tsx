import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/stores/ui'
import { Button } from '@/components/ui/button'
import {
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Database,
  Sparkles,
  Shield,
  CheckSquare,
  Search,
  Eye,
  Download,
  Code,
  Settings,
  Home,
  Table,
  Cpu,
  Lock,
  FileText,
  Activity,
} from 'lucide-react'

interface SidebarProps {}

const navigationItems = [
  {
    title: 'Overview',
    items: [
      {
        title: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
        description: 'System overview and metrics'
      }
    ]
  },
  {
    title: 'Data Discovery',
    items: [
      {
        title: 'Schema Explorer',
        href: '/schema',
        icon: Database,
        description: 'Browse database schemas and tables'
      },
      {
        title: 'Data Generator',
        href: '/generator',
        icon: Sparkles,
        description: 'Generate synthetic data'
      },
      {
        title: 'Query Builder',
        href: '/query',
        icon: Search,
        description: 'Visual query construction'
      },
      {
        title: 'Preview',
        href: '/preview',
        icon: Eye,
        description: 'Data preview and exploration'
      }
    ]
  },
  {
    title: 'Privacy & Compliance',
    items: [
      {
        title: 'Privacy Controls',
        href: '/privacy',
        icon: Shield,
        description: 'Privacy settings and budgets'
      },
      {
        title: 'Compliance',
        href: '/compliance',
        icon: CheckSquare,
        description: 'HIPAA, GDPR compliance monitoring'
      }
    ]
  },
  {
    title: 'Data Management',
    items: [
      {
        title: 'Export',
        href: '/export',
        icon: Download,
        description: 'Export data in multiple formats'
      },
      {
        title: 'API Explorer',
        href: '/api',
        icon: Code,
        description: 'Interactive API documentation'
      }
    ]
  },
  {
    title: 'System',
    items: [
      {
        title: 'Settings',
        href: '/settings',
        icon: Settings,
        description: 'System configuration'
      }
    ]
  }
]

export function Sidebar({}: SidebarProps) {
  const { sidebarCollapsed, toggleSidebar, setSidebarOpen } = useUiStore()
  const location = useLocation()

  return (
    <div className="flex h-full flex-col">
      {/* Logo and collapse toggle */}
      <div className="flex items-center justify-between p-4 border-b">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 text-white">
              <Database className="h-4 w-4" />
            </div>
            <div className="font-semibold text-lg">SynthData</div>
          </div>
        )}
        
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="hidden lg:flex"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4">
        <div className="space-y-6">
          {navigationItems.map((section) => (
            <div key={section.title}>
              {!sidebarCollapsed && (
                <h3 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {section.title}
                </h3>
              )}
              
              <div className="space-y-1">
                {section.items.map((item) => {
                  const isActive = location.pathname.startsWith(item.href)
                  
                  return (
                    <NavLink
                      key={item.href}
                      to={item.href}
                      onClick={() => setSidebarOpen(false)} // Close mobile sidebar
                      className={({ isActive: navIsActive }) =>
                        cn(
                          // Base styles
                          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-accent hover:text-accent-foreground",
                          // Active styles
                          (isActive || navIsActive) && "bg-accent text-accent-foreground",
                          // Collapsed styles
                          sidebarCollapsed && "justify-center px-2"
                        )
                      }
                      title={sidebarCollapsed ? item.description : undefined}
                    >
                      <item.icon className={cn("h-4 w-4 flex-shrink-0", isActive && "text-primary")} />
                      {!sidebarCollapsed && (
                        <span className="truncate">{item.title}</span>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </nav>

      {/* Status indicator */}
      {!sidebarCollapsed && (
        <div className="border-t p-4">
          <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
            <div className="flex h-2 w-2 rounded-full bg-green-500" />
            <div className="flex-1 text-sm">
              <div className="font-medium">System Healthy</div>
              <div className="text-xs text-muted-foreground">
                All services running
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}