import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'

interface PublicRouteProps {
  children: React.ReactNode
}

export function PublicRoute({ children }: PublicRouteProps) {
  const { user, token } = useAuthStore()

  if (user && token) {
    // Redirect authenticated users to dashboard
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}