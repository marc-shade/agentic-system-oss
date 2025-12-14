import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { formatDate, formatNumber } from '@/lib/utils'
import { GenerationJob } from '@/types'
import { api } from '@/lib/api'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import {
  Play,
  Pause,
  Square,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MoreHorizontal,
} from 'lucide-react'

interface JobsOverviewProps {}

export function JobsOverview({}: JobsOverviewProps) {
  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs-overview'],
    queryFn: () => api.getJobs({ limit: 5 }),
    refetchInterval: 5000, // Refresh every 5 seconds for running jobs
  })

  // Mock data if no jobs available
  const mockJobs: GenerationJob[] = [
    {
      id: '1',
      name: 'Customer Data Synthesis',
      status: 'running',
      progress: 65,
      created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
      source_table: 'customers',
      target_rows: 100000,
      generated_rows: 65000,
      privacy_budget: 10.0,
      privacy_spent: 6.5,
      parameters: {
        method: 'ctgan',
        quality_threshold: 0.85,
        correlation_preservation: true,
        constraints: [],
      }
    },
    {
      id: '2',
      name: 'Orders Dataset Generation',
      status: 'completed',
      progress: 100,
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      completed_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      source_table: 'orders',
      target_rows: 50000,
      generated_rows: 50000,
      privacy_budget: 8.0,
      privacy_spent: 7.8,
      parameters: {
        method: 'gan',
        quality_threshold: 0.90,
        correlation_preservation: true,
        constraints: [],
      }
    },
    {
      id: '3',
      name: 'User Profiles Synthesis',
      status: 'failed',
      progress: 25,
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      source_table: 'user_profiles',
      target_rows: 75000,
      generated_rows: 18750,
      privacy_budget: 12.0,
      privacy_spent: 3.0,
      error_message: 'Insufficient memory for model training',
      parameters: {
        method: 'vae',
        quality_threshold: 0.80,
        correlation_preservation: false,
        constraints: [],
      }
    },
  ]

  const displayJobs = jobs?.data || mockJobs

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Play className="h-3 w-3" />
      case 'completed':
        return <CheckCircle className="h-3 w-3" />
      case 'failed':
        return <XCircle className="h-3 w-3" />
      case 'pending':
        return <Clock className="h-3 w-3" />
      case 'cancelled':
        return <Square className="h-3 w-3" />
      default:
        return <Clock className="h-3 w-3" />
    }
  }

  const getProgressVariant = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'running':
        return 'default'
      default:
        return 'default'
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-muted rounded w-3/4 mb-2" />
            <div className="h-2 bg-muted rounded w-full mb-2" />
            <div className="h-3 bg-muted rounded w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (displayJobs.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-muted-foreground">
          No generation jobs found. Create your first job to get started.
        </div>
        <Button variant="outline" size="sm" className="mt-2">
          Create Job
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {displayJobs.map((job) => (
        <div
          key={job.id}
          className="border rounded-lg p-4 hover:bg-muted/30 transition-colors"
        >
          {/* Job Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="font-medium">{job.name}</h4>
                <StatusBadge status={job.status} />
              </div>
              <p className="text-sm text-muted-foreground">
                Table: <code className="text-xs bg-muted px-1 py-0.5 rounded">{job.source_table}</code>
              </p>
            </div>
            
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-3 w-3" />
              </Button>
            </div>
          </div>

          {/* Progress Bar */}
          {job.status !== 'pending' && (
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Progress</span>
                <span className="text-xs text-muted-foreground">{job.progress}%</span>
              </div>
              <Progress
                value={job.progress}
                variant={getProgressVariant(job.status)}
                className="h-2"
              />
            </div>
          )}

          {/* Job Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Rows:</span>
              <span className="ml-2 font-medium">
                {formatNumber(job.generated_rows)} / {formatNumber(job.target_rows)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Method:</span>
              <span className="ml-2 font-medium uppercase">{job.parameters.method}</span>
            </div>
          </div>

          {/* Privacy Budget */}
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Privacy Budget:</span>
              <span className="font-medium">
                {job.privacy_spent.toFixed(1)} / {job.privacy_budget.toFixed(1)}
              </span>
            </div>
          </div>

          {/* Timestamps */}
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>Created {formatDate(job.created_at, 'relative')}</span>
            {job.completed_at ? (
              <span>Completed {formatDate(job.completed_at, 'relative')}</span>
            ) : (
              <span>Updated {formatDate(job.updated_at, 'relative')}</span>
            )}
          </div>

          {/* Error Message */}
          {job.error_message && (
            <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-700 dark:text-red-300">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">Error:</span>
              </div>
              <p className="mt-1">{job.error_message}</p>
            </div>
          )}
        </div>
      ))}

      {displayJobs.length >= 5 && (
        <div className="text-center pt-2">
          <Button variant="ghost" size="sm">
            View All Jobs
          </Button>
        </div>
      )}
    </div>
  )
}