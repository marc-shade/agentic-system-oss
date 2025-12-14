import React, { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, MetricCard, StatusCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Database, 
  Table, 
  Activity, 
  Shield, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  TrendingUp,
  TrendingDown,
  Clock,
  Users,
  Zap,
  Eye,
  Download,
  Plus,
  ArrowRight,
} from 'lucide-react'
import { RecentActivity } from '@/components/dashboard/RecentActivity'
import { SystemHealth } from '@/components/dashboard/SystemHealth'
import { PrivacyBudgetChart } from '@/components/dashboard/PrivacyBudgetChart'
import { JobsOverview } from '@/components/dashboard/JobsOverview'
import { QuickActions } from '@/components/dashboard/QuickActions'

interface DashboardPageProps {}

export function DashboardPage({}: DashboardPageProps) {
  // Fetch dashboard metrics
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => api.getDashboardMetrics(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: systemHealth } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => api.getSystemHealth(),
    refetchInterval: 15000, // Refresh every 15 seconds
  })

  const dashboardData = metrics?.data || {
    total_databases: 0,
    total_tables: 0,
    total_columns: 0,
    active_jobs: 0,
    completed_jobs_today: 0,
    privacy_budget_used: 0,
    privacy_budget_total: 100,
    system_health: 'healthy',
    recent_activity: [],
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
      },
    },
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card variant="privacy" className="p-6">
          <div className="text-center">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to load dashboard</h3>
            <p className="text-muted-foreground mb-4">
              Unable to fetch dashboard metrics. Please try again.
            </p>
            <Button onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your synthetic data platform
          </p>
        </div>
        <QuickActions />
      </motion.div>

      {/* System Health Alert */}
      {dashboardData.system_health !== 'healthy' && (
        <motion.div variants={itemVariants}>
          <Card variant="privacy" className="border-2 border-yellow-200 dark:border-yellow-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <div>
                  <h4 className="font-semibold">System Health Warning</h4>
                  <p className="text-sm text-muted-foreground">
                    Some services are experiencing issues. Check system status for details.
                  </p>
                </div>
                <Button variant="outline" size="sm" className="ml-auto">
                  View Details
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Key Metrics */}
      <motion.div variants={itemVariants} className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Connected Databases"
          value={dashboardData.total_databases}
          change="+2 this week"
          changeType="positive"
          icon={<Database className="h-5 w-5" />}
        />
        
        <MetricCard
          title="Total Tables"
          value={dashboardData.total_tables}
          change="+12 this week"
          changeType="positive"
          icon={<Table className="h-5 w-5" />}
        />
        
        <MetricCard
          title="Active Jobs"
          value={dashboardData.active_jobs}
          change="2 running now"
          changeType="neutral"
          icon={<Activity className="h-5 w-5" />}
        />
        
        <MetricCard
          title="Privacy Budget"
          value={`${Math.round((dashboardData.privacy_budget_used / dashboardData.privacy_budget_total) * 100)}%`}
          change={dashboardData.privacy_budget_used > dashboardData.privacy_budget_total * 0.8 ? "High usage" : "Within limits"}
          changeType={dashboardData.privacy_budget_used > dashboardData.privacy_budget_total * 0.8 ? "negative" : "positive"}
          icon={<Shield className="h-5 w-5" />}
        />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          {/* Privacy Budget Chart */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Privacy Budget Usage
                </CardTitle>
                <CardDescription>
                  Track differential privacy budget consumption over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PrivacyBudgetChart 
                  used={dashboardData.privacy_budget_used}
                  total={dashboardData.privacy_budget_total}
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Jobs Overview */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Generation Jobs
                  </CardTitle>
                  <CardDescription>
                    Recent synthetic data generation activities
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  View All <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </CardHeader>
              <CardContent>
                <JobsOverview />
              </CardContent>
            </Card>
          </motion.div>

          {/* Recent Activity */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Activity
                </CardTitle>
                <CardDescription>
                  Latest system events and user actions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RecentActivity activities={dashboardData.recent_activity} />
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Right Column - 1/3 width */}
        <div className="space-y-6">
          {/* System Health */}
          <motion.div variants={itemVariants}>
            <StatusCard
              title="System Health"
              status={dashboardData.system_health}
              description="All services operational"
              lastUpdate="2 minutes ago"
            />
          </motion.div>

          {/* Quick Stats */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle>Today's Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Jobs Completed</span>
                  <span className="font-semibold">{dashboardData.completed_jobs_today}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">Active Users</span>
                  <span className="font-semibold">12</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">Data Generated</span>
                  <span className="font-semibold">2.4M rows</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">Exports</span>
                  <span className="font-semibold">8</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Quick Actions */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="outline">
                  <Plus className="h-4 w-4 mr-2" />
                  New Connection
                </Button>
                
                <Button className="w-full justify-start" variant="outline">
                  <Zap className="h-4 w-4 mr-2" />
                  Generate Data
                </Button>
                
                <Button className="w-full justify-start" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Preview Data
                </Button>
                
                <Button className="w-full justify-start" variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export Data
                </Button>
              </CardContent>
            </Card>
          </motion.div>

          {/* Compliance Status */}
          <motion.div variants={itemVariants}>
            <Card variant="compliance">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  Compliance Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">HIPAA</span>
                  <Badge variant="hipaa">Compliant</Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">GDPR</span>
                  <Badge variant="gdpr">Compliant</Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">CCPA</span>
                  <Badge variant="ccpa">Compliant</Badge>
                </div>
                
                <div className="pt-2">
                  <Button variant="outline" size="sm" className="w-full">
                    View Compliance Report
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}