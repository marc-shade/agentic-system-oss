import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Code } from 'lucide-react'

export function ApiExplorerPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">API Explorer</h1>
        <p className="text-muted-foreground">
          Interactive API documentation and testing interface
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            API Documentation
          </CardTitle>
          <CardDescription>
            Explore and test API endpoints
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Code className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              API explorer interface will be implemented here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}