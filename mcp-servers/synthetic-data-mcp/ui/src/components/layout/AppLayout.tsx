import React from 'react'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/stores/ui'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { Footer } from './Footer'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { sidebarCollapsed, sidebarOpen, setSidebarOpen } = useUiStore()

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          // Base styles
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-card border-r transition-all duration-300",
          // Desktop styles
          "lg:static lg:z-auto",
          // Width based on collapsed state
          sidebarCollapsed ? "w-16" : "w-64",
          // Mobile visibility
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <Sidebar />
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
          <Header />
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto p-6">
            {children}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t bg-card/50 backdrop-blur">
          <Footer />
        </footer>
      </div>
    </div>
  )
}