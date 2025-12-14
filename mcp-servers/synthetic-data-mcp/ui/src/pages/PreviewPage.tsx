import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye } from 'lucide-react'

export function PreviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Data Preview</h1>
        <p className="text-muted-foreground">
          Preview and explore your data with advanced filtering and sorting
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Data Grid
          </CardTitle>
          <CardDescription>
            Interactive data exploration interface
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Eye className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Data preview grid will be implemented here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}