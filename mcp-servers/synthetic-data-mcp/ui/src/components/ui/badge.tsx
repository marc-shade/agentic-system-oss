import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        warning:
          "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
        error:
          "border-transparent bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        info:
          "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
        // Privacy levels
        public:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        internal:
          "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
        confidential:
          "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
        restricted:
          "border-transparent bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        // Compliance tags
        hipaa:
          "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
        gdpr:
          "border-transparent bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
        ccpa:
          "border-transparent bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300",
        pci:
          "border-transparent bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
        sox:
          "border-transparent bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
        ferpa:
          "border-transparent bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
        // Status badges
        connected:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        disconnected:
          "border-transparent bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        pending:
          "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
        running:
          "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 animate-pulse",
        completed:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        failed:
          "border-transparent bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        cancelled:
          "border-transparent bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
  dot?: boolean
}

function Badge({ className, variant, size, icon, dot, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span className={cn(
          "mr-1 h-1.5 w-1.5 rounded-full",
          variant === 'connected' || variant === 'completed' || variant === 'success' ? "bg-green-500" :
          variant === 'disconnected' || variant === 'failed' || variant === 'error' ? "bg-red-500" :
          variant === 'pending' || variant === 'warning' ? "bg-yellow-500" :
          variant === 'running' || variant === 'info' ? "bg-blue-500" :
          "bg-gray-500"
        )} />
      )}
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </div>
  )
}

// Specialized badge components
const PrivacyBadge = ({ level, ...props }: { level: 'public' | 'internal' | 'confidential' | 'restricted' } & Omit<BadgeProps, 'variant'>) => {
  const icons = {
    public: "🌐",
    internal: "🏢",
    confidential: "⚠️",
    restricted: "🔒",
  }
  
  return (
    <Badge
      variant={level}
      icon={icons[level]}
      {...props}
    >
      {level.toUpperCase()}
    </Badge>
  )
}

const ComplianceBadge = ({ 
  tag, 
  ...props 
}: { 
  tag: 'HIPAA' | 'GDPR' | 'CCPA' | 'PCI-DSS' | 'SOX' | 'FERPA' 
} & Omit<BadgeProps, 'variant'>) => {
  const variants = {
    'HIPAA': 'hipaa' as const,
    'GDPR': 'gdpr' as const,
    'CCPA': 'ccpa' as const,
    'PCI-DSS': 'pci' as const,
    'SOX': 'sox' as const,
    'FERPA': 'ferpa' as const,
  }
  
  return (
    <Badge variant={variants[tag]} {...props}>
      {tag}
    </Badge>
  )
}

const StatusBadge = ({ 
  status, 
  ...props 
}: { 
  status: 'connected' | 'disconnected' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
} & Omit<BadgeProps, 'variant'>) => {
  return (
    <Badge variant={status} dot {...props}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

const DataTypeBadge = ({ type, ...props }: { type: string } & Omit<BadgeProps, 'variant'>) => {
  const getVariant = (dataType: string) => {
    const lowerType = dataType.toLowerCase()
    if (lowerType.includes('varchar') || lowerType.includes('text') || lowerType.includes('char')) {
      return 'info' as const
    }
    if (lowerType.includes('int') || lowerType.includes('numeric') || lowerType.includes('decimal')) {
      return 'success' as const
    }
    if (lowerType.includes('date') || lowerType.includes('timestamp') || lowerType.includes('time')) {
      return 'warning' as const
    }
    if (lowerType.includes('bool') || lowerType.includes('bit')) {
      return 'secondary' as const
    }
    return 'outline' as const
  }
  
  return (
    <Badge variant={getVariant(type)} size="sm" {...props}>
      {type}
    </Badge>
  )
}

export { Badge, badgeVariants, PrivacyBadge, ComplianceBadge, StatusBadge, DataTypeBadge }