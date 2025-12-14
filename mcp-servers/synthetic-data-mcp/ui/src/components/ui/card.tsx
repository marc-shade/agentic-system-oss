import * as React from "react"

import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    variant?: 'default' | 'glass' | 'synthetic' | 'privacy' | 'compliance'
  }
>(({ className, variant = 'default', ...props }, ref) => {
  const variantClasses = {
    default: "border bg-card text-card-foreground shadow-sm",
    glass: "synthetic-glass border-white/20 text-white shadow-xl",
    synthetic: "border-2 border-purple-200 dark:border-purple-800 bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950/50 dark:to-blue-950/50 shadow-lg",
    privacy: "border-2 border-red-200 dark:border-red-800 bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-950/50 dark:to-orange-950/50 shadow-lg",
    compliance: "border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 shadow-lg",
  }
  
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-lg",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
})
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement> & {
    as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
  }
>(({ className, as: Component = 'h3', ...props }, ref) => (
  <Component
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

// Specialized card components
const MetricCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title: string
    value: string | number
    change?: string
    changeType?: 'positive' | 'negative' | 'neutral'
    icon?: React.ReactNode
  }
>(({ className, title, value, change, changeType = 'neutral', icon, ...props }, ref) => {
  const changeColors = {
    positive: 'text-green-600 dark:text-green-400',
    negative: 'text-red-600 dark:text-red-400',
    neutral: 'text-gray-600 dark:text-gray-400',
  }
  
  return (
    <Card ref={ref} className={cn("p-6", className)} {...props}>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-3xl font-bold">{value}</p>
          {change && (
            <p className={cn("text-sm", changeColors[changeType])}>
              {change}
            </p>
          )}
        </div>
        {icon && (
          <div className="text-muted-foreground">
            {icon}
          </div>
        )}
      </div>
    </Card>
  )
})
MetricCard.displayName = "MetricCard"

const StatusCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title: string
    status: 'healthy' | 'warning' | 'critical' | 'offline'
    description?: string
    lastUpdate?: string
  }
>(({ className, title, status, description, lastUpdate, ...props }, ref) => {
  const statusColors = {
    healthy: 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/50',
    warning: 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/50',
    critical: 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/50',
    offline: 'border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-950/50',
  }
  
  const statusDots = {
    healthy: 'bg-green-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500',
    offline: 'bg-gray-500',
  }
  
  return (
    <Card
      ref={ref}
      className={cn(
        "border-2 p-6",
        statusColors[status],
        className
      )}
      {...props}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className={cn("h-2 w-2 rounded-full", statusDots[status])} />
            <h3 className="font-semibold">{title}</h3>
          </div>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
          {lastUpdate && (
            <p className="text-xs text-muted-foreground">
              Last updated: {lastUpdate}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
})
StatusCard.displayName = "StatusCard"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, MetricCard, StatusCard }