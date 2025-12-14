import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge, ComplianceBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle, FileText, Download } from 'lucide-react'

export function CompliancePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compliance Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor HIPAA, GDPR, and other compliance requirements
          </p>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export Report
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card variant="compliance">
          <CardHeader>
            <CardTitle>HIPAA Compliance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="font-medium">Compliant</span>
              </div>
              <ComplianceBadge tag="HIPAA" />
              <p className="text-sm text-muted-foreground">
                Last audit: 2 days ago
              </p>
            </div>
          </CardContent>
        </Card>

        <Card variant="compliance">
          <CardHeader>
            <CardTitle>GDPR Compliance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="font-medium">Compliant</span>
              </div>
              <ComplianceBadge tag="GDPR" />
              <p className="text-sm text-muted-foreground">
                Last audit: 1 week ago
              </p>
            </div>
          </CardContent>
        </Card>

        <Card variant="compliance">
          <CardHeader>
            <CardTitle>CCPA Compliance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="font-medium">Compliant</span>
              </div>
              <ComplianceBadge tag="CCPA" />
              <p className="text-sm text-muted-foreground">
                Last audit: 3 days ago
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Compliance Reports
          </CardTitle>
          <CardDescription>
            Generated compliance documentation and audit trails
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No compliance reports available. Generate your first report to get started.
            </p>
            <Button variant="outline" className="mt-4">
              Generate Report
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}