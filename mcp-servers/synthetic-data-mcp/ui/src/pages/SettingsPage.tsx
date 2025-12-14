import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Settings } from 'lucide-react'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure system preferences and user settings
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            System Configuration
          </CardTitle>
          <CardDescription>
            Manage system-wide settings and preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Settings className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Settings interface will be implemented here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}