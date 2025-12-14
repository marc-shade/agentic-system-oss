import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { formatPercentage } from '@/lib/utils'

interface PrivacyBudgetChartProps {
  used: number
  total: number
}

export function PrivacyBudgetChart({ used, total }: PrivacyBudgetChartProps) {
  const percentage = (used / total) * 100
  const remaining = total - used

  const data = [
    { name: 'Used', value: used, color: '#ef4444' },
    { name: 'Remaining', value: remaining, color: '#10b981' },
  ]

  const getStatusVariant = (percentage: number) => {
    if (percentage >= 90) return 'error'
    if (percentage >= 75) return 'warning'
    return 'success'
  }

  const getStatusColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-600'
    if (percentage >= 75) return 'text-yellow-600'
    return 'text-green-600'
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-background border rounded-lg p-3 shadow-lg">
          <p className="font-medium">{data.name}</p>
          <p className="text-sm text-muted-foreground">
            {data.value.toFixed(2)} / {formatPercentage(data.value, total)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Privacy Budget Usage</span>
          <span className={`text-sm font-semibold ${getStatusColor(percentage)}`}>
            {formatPercentage(used, total)}
          </span>
        </div>
        <Progress
          value={percentage}
          variant={getStatusVariant(percentage)}
          className="h-3"
        />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>0</span>
          <span>{total}</span>
        </div>
      </div>

      {/* Pie Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={5}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-red-600">{used.toFixed(1)}</div>
          <div className="text-xs text-muted-foreground">Used</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">{remaining.toFixed(1)}</div>
          <div className="text-xs text-muted-foreground">Remaining</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-muted-foreground">Total</div>
        </div>
      </div>

      {/* Status Badges */}
      <div className="flex gap-2">
        {percentage >= 90 && (
          <Badge variant="error">Critical Usage</Badge>
        )}
        {percentage >= 75 && percentage < 90 && (
          <Badge variant="warning">High Usage</Badge>
        )}
        {percentage < 50 && (
          <Badge variant="success">Healthy Usage</Badge>
        )}
      </div>

      {/* Recommendations */}
      {percentage >= 75 && (
        <div className="p-3 bg-muted/50 rounded-lg">
          <h4 className="text-sm font-medium mb-2">Recommendations</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• Consider increasing privacy budget allocation</li>
            <li>• Review active generation jobs</li>
            <li>• Optimize generation parameters for better efficiency</li>
          </ul>
        </div>
      )}
    </div>
  )
}