import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

// Store initializers
import { initializeAuth } from '@/stores/auth'
import { initializeTheme } from '@/stores/ui'

// Layout components
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'

// Page components
import { DashboardPage } from '@/pages/DashboardPage'
import { SchemaExplorerPage } from '@/pages/SchemaExplorerPage'
import { DataGeneratorPage } from '@/pages/DataGeneratorPage'
import { PrivacyControlsPage } from '@/pages/PrivacyControlsPage'
import { CompliancePage } from '@/pages/CompliancePage'
import { QueryBuilderPage } from '@/pages/QueryBuilderPage'
import { PreviewPage } from '@/pages/PreviewPage'
import { ExportPage } from '@/pages/ExportPage'
import { ApiExplorerPage } from '@/pages/ApiExplorerPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'

// Global components
import { NotificationProvider } from '@/components/providers/NotificationProvider'
import { WebSocketProvider } from '@/components/providers/WebSocketProvider'
import { ErrorBoundary } from '@/components/ErrorBoundary'

// Guards
import { ProtectedRoute } from '@/components/guards/ProtectedRoute'
import { PublicRoute } from '@/components/guards/PublicRoute'

// Initialize stores
const initializeApp = async () => {
  // Initialize theme system
  initializeTheme()
  
  // Initialize authentication
  await initializeAuth()
}

function App() {
  useEffect(() => {
    initializeApp().catch(console.error)
  }, [])

  return (
    <ErrorBoundary>
      <NotificationProvider>
        <WebSocketProvider>
          <div className="min-h-screen bg-background text-foreground">
            <Routes>
              {/* Public routes */}
              <Route
                path="/login"
                element={
                  <PublicRoute>
                    <AuthLayout>
                      <LoginPage />
                    </AuthLayout>
                  </PublicRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicRoute>
                    <AuthLayout>
                      <RegisterPage />
                    </AuthLayout>
                  </PublicRoute>
                }
              />
              
              {/* Protected routes */}
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Routes>
                        {/* Dashboard */}
                        <Route index element={<DashboardPage />} />
                        <Route path="dashboard" element={<DashboardPage />} />
                        
                        {/* Data Discovery */}
                        <Route path="schema/*" element={<SchemaExplorerPage />} />
                        <Route path="generator/*" element={<DataGeneratorPage />} />
                        <Route path="query/*" element={<QueryBuilderPage />} />
                        <Route path="preview/*" element={<PreviewPage />} />
                        
                        {/* Privacy & Compliance */}
                        <Route path="privacy/*" element={<PrivacyControlsPage />} />
                        <Route path="compliance/*" element={<CompliancePage />} />
                        
                        {/* Data Management */}
                        <Route path="export/*" element={<ExportPage />} />
                        <Route path="api/*" element={<ApiExplorerPage />} />
                        
                        {/* System */}
                        <Route path="settings/*" element={<SettingsPage />} />
                        
                        {/* Redirects */}
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="*" element={<Navigate to="/dashboard" replace />} />
                      </Routes>
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              
              {/* Fallback redirect */}
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </div>
          
          {/* Development tools */}
          {import.meta.env.DEV && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </WebSocketProvider>
      </NotificationProvider>
    </ErrorBoundary>
  )
}

export default App