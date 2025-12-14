import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Sparkles, Play, Settings } from 'lucide-react'

export function DataGeneratorPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Generator</h1>
          <p className="text-muted-foreground">
            Generate high-quality synthetic data with advanced AI models
          </p>
        </div>
        <Button variant="synthetic">
          <Play className="h-4 w-4 mr-2" />
          Start Generation
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card variant="synthetic">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Quick Generate
            </CardTitle>
            <CardDescription>
              Generate synthetic data from existing tables
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Select a source table and generate synthetic data with default parameters
            </p>
            <Button variant="outline" className="w-full">
              Choose Source Table
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Advanced Generation
            </CardTitle>
            <CardDescription>
              Configure generation parameters and constraints
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Fine-tune generation models, privacy settings, and quality thresholds
            </p>
            <Button variant="outline" className="w-full">
              Configure Parameters
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}