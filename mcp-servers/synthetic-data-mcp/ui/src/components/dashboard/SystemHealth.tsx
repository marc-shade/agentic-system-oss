import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

interface SystemHealthProps {
  status?: 'healthy' | 'warning' | 'critical'
}

export function SystemHealth({ status = 'healthy' }: SystemHealthProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-600" />
      default:
        return <CheckCircle className="h-5 w-5 text-green-600" />
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'warning':
        return 'warning'
      case 'critical':
        return 'error'
      default:
        return 'success'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getStatusIcon()}
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Badge variant={getStatusColor() as any}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </Badge>
          <p className="text-sm text-muted-foreground">
            All services are operational
          </p>
        </div>
      </CardContent>
    </Card>
  )
}