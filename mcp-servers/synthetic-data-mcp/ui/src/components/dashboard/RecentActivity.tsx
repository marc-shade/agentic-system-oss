import React from 'react'
import { formatDate } from '@/lib/utils'
import { ActivityItem } from '@/types'
import { Badge } from '@/components/ui/badge'
import {
  Database,
  Zap,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Shield,
  FileText,
} from 'lucide-react'

interface RecentActivityProps {
  activities: ActivityItem[]
}

const activityIcons = {
  job_created: Zap,
  job_completed: CheckCircle,
  database_connected: Database,
  schema_updated: RefreshCw,
  privacy_alert: Shield,
  export_completed: FileText,
}

const activityColors = {
  job_created: 'text-blue-600',
  job_completed: 'text-green-600',
  database_connected: 'text-purple-600',
  schema_updated: 'text-indigo-600',
  privacy_alert: 'text-red-600',
  export_completed: 'text-orange-600',
}

export function RecentActivity({ activities }: RecentActivityProps) {
  // Mock data if no activities provided
  const mockActivities: ActivityItem[] = [
    {
      id: '1',
      type: 'job_completed',
      description: 'Synthetic data generation completed for users table',
      timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      user: 'john.doe@company.com',
      metadata: { table: 'users', rows: 10000 }
    },
    {
      id: '2',
      type: 'database_connected',
      description: 'New PostgreSQL database connected: prod-analytics',
      timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      user: 'admin@company.com',
    },
    {
      id: '3',
      type: 'privacy_alert',
      description: 'Privacy budget usage reached 80% for customer table',
      timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    },
    {
      id: '4',
      type: 'job_created',
      description: 'New generation job created for orders dataset',
      timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
      user: 'data.scientist@company.com',
    },
    {
      id: '5',
      type: 'export_completed',
      description: 'Data export completed: synthetic_customers.csv',
      timestamp: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
      user: 'analyst@company.com',
    },
  ]

  const displayActivities = activities.length > 0 ? activities : mockActivities

  if (displayActivities.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-muted-foreground">
          No recent activity to display
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {displayActivities.slice(0, 10).map((activity) => {
        const Icon = activityIcons[activity.type] || CheckCircle
        const colorClass = activityColors[activity.type] || 'text-gray-600'

        return (
          <div key={activity.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
            <div className={`flex-shrink-0 mt-0.5 ${colorClass}`}>
              <Icon className="h-4 w-4" />
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-5">
                {activity.description}
              </p>
              
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">
                  {formatDate(activity.timestamp, 'relative')}
                </span>
                
                {activity.user && (
                  <>
                    <span className="text-xs text-muted-foreground">•</span>
                    <span className="text-xs text-muted-foreground">
                      {activity.user}
                    </span>
                  </>
                )}
              </div>

              {/* Activity-specific metadata */}
              {activity.metadata && (
                <div className="flex items-center gap-2 mt-2">
                  {activity.metadata.table && (
                    <Badge variant="outline" size="sm">
                      {activity.metadata.table}
                    </Badge>
                  )}
                  {activity.metadata.rows && (
                    <Badge variant="secondary" size="sm">
                      {activity.metadata.rows.toLocaleString()} rows
                    </Badge>
                  )}
                </div>
              )}
            </div>

            {/* Status indicator */}
            <div className="flex-shrink-0">
              {activity.type === 'job_completed' && (
                <div className="h-2 w-2 bg-green-500 rounded-full" />
              )}
              {activity.type === 'privacy_alert' && (
                <div className="h-2 w-2 bg-red-500 rounded-full" />
              )}
              {activity.type === 'job_created' && (
                <div className="h-2 w-2 bg-blue-500 rounded-full" />
              )}
              {activity.type === 'database_connected' && (
                <div className="h-2 w-2 bg-purple-500 rounded-full" />
              )}
            </div>
          </div>
        )
      })}

      {displayActivities.length > 10 && (
        <div className="text-center pt-4">
          <button className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            View all activity →
          </button>
        </div>
      )}
    </div>
  )
}