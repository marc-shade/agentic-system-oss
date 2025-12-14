import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, token } = useAuthStore()
  const location = useLocation()

  if (!user || !token) {
    // Redirect to login page with return url
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}