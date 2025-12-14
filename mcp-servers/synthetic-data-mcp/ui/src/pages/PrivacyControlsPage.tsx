import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Shield, Lock, Eye, AlertTriangle } from 'lucide-react'

export function PrivacyControlsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Privacy Controls</h1>
          <p className="text-muted-foreground">
            Monitor and manage privacy budgets and data protection settings
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card variant="privacy">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Privacy Budget
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm">Used</span>
                <span className="text-sm font-medium">85%</span>
              </div>
              <Progress value={85} variant="warning" />
              <Badge variant="warning">High Usage</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Sensitive Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold">247</div>
              <div className="text-sm text-muted-foreground">
                Columns identified
              </div>
              <Badge variant="restricted">PII Detected</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Access Controls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold">12</div>
              <div className="text-sm text-muted-foreground">
                Active policies
              </div>
              <Badge variant="success">All Applied</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Privacy Alerts
          </CardTitle>
          <CardDescription>
            Recent privacy-related events and recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium">High Privacy Budget Usage</p>
                <p className="text-sm text-muted-foreground">
                  Consider optimizing generation parameters or increasing budget allocation
                </p>
              </div>
            </div>
            
            <div className="text-center text-muted-foreground">
              <p className="text-sm">No other privacy alerts at this time</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}