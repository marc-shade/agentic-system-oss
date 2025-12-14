import React from 'react'
import { cn } from '@/lib/utils'

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding/Image */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-20">
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100">
            <defs>
              <pattern
                id="grid"
                width="10"
                height="10"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M 10 0 L 0 0 0 10"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="0.5"
                />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#grid)" />
          </svg>
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center p-12 text-white">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
                <svg
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 7v10c0 2.21 3.79 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.79 4 8 4s8-1.79 8-4M4 7c0-2.21 3.79-4 8-4s8 1.79 8 4"
                  />
                </svg>
              </div>
              <h1 className="text-3xl font-bold">SynthData</h1>
            </div>
            
            <h2 className="text-4xl font-bold mb-6 leading-tight">
              Enterprise Synthetic Data Platform
            </h2>
            
            <p className="text-xl text-white/90 mb-8 leading-relaxed">
              Generate privacy-compliant synthetic data with enterprise-grade security, 
              HIPAA/GDPR compliance, and advanced AI models.
            </p>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-white/90">Privacy-first architecture</span>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="text-white/90">Advanced AI generation</span>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <span className="text-white/90">Enterprise security</span>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <span className="text-white/90">HIPAA/GDPR compliance</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  )
}