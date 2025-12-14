import React from 'react'
import { cn } from '@/lib/utils'

interface FooterProps {}

export function Footer({}: FooterProps) {
  return (
    <div className="flex h-12 items-center justify-between px-6 text-sm text-muted-foreground">
      <div className="flex items-center gap-4">
        <span>© 2024 Synthetic Data Platform</span>
        <span className="text-xs">v1.0.0</span>
      </div>
      
      <div className="flex items-center gap-4">
        <a
          href="#"
          className="hover:text-foreground transition-colors"
        >
          Documentation
        </a>
        <a
          href="#"
          className="hover:text-foreground transition-colors"
        >
          Support
        </a>
        <a
          href="#"
          className="hover:text-foreground transition-colors"
        >
          Privacy Policy
        </a>
      </div>
    </div>
  )
}