import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Download } from 'lucide-react'

export function ExportPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Export Manager</h1>
        <p className="text-muted-foreground">
          Export your data in multiple formats
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Jobs
          </CardTitle>
          <CardDescription>
            Manage and monitor data export operations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Download className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Export management interface will be implemented here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}