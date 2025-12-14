import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Database, Plus, RefreshCw } from 'lucide-react'

export function SchemaExplorerPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Schema Explorer</h1>
          <p className="text-muted-foreground">
            Browse and manage your database connections and schemas
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="synthetic">
            <Plus className="h-4 w-4 mr-2" />
            New Connection
          </Button>
        </div>
      </div>

      <Card variant="synthetic">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Database Connections
          </CardTitle>
          <CardDescription>
            Manage your database connections and explore schemas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Connections Found</h3>
            <p className="text-muted-foreground mb-6">
              Get started by connecting to your first database
            </p>
            <Button variant="synthetic">
              <Plus className="h-4 w-4 mr-2" />
              Add Database Connection
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}