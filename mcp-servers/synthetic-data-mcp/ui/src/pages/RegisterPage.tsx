import React from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Database } from 'lucide-react'

export function RegisterPage() {
  return (
    <div className="w-full max-w-md mx-auto">
      <Card>
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 text-white">
              <Database className="h-6 w-6" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">Create Account</CardTitle>
          <CardDescription>
            Registration is currently by invitation only
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <div className="text-center space-y-4">
            <p className="text-muted-foreground">
              Contact your system administrator to request access to the synthetic data platform.
            </p>
            
            <div className="p-4 bg-muted/50 rounded-lg text-left">
              <h4 className="font-medium mb-2">Contact Information</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <div>Email: admin@synthdata.com</div>
                <div>Phone: (555) 123-4567</div>
              </div>
            </div>
            
            <div className="pt-4">
              <Link to="/login">
                <Button variant="outline" className="w-full">
                  Back to Sign In
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}