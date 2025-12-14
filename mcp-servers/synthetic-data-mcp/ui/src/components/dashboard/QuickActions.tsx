import React from 'react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { 
  Plus, 
  Zap, 
  Database,
  FileText,
} from 'lucide-react'

interface QuickActionsProps {}

export function QuickActions({}: QuickActionsProps) {
  const navigate = useNavigate()

  const actions = [
    {
      label: 'New Connection',
      icon: Database,
      onClick: () => navigate('/schema'),
      variant: 'synthetic' as const,
    },
    {
      label: 'Generate Data',
      icon: Zap,
      onClick: () => navigate('/generator'),
      variant: 'default' as const,
    },
    {
      label: 'View Reports',
      icon: FileText,
      onClick: () => navigate('/compliance'),
      variant: 'outline' as const,
    },
  ]

  return (
    <div className="flex items-center gap-2">
      {actions.map((action) => {
        const Icon = action.icon
        return (
          <Button
            key={action.label}
            variant={action.variant}
            onClick={action.onClick}
            className="hidden md:flex"
          >
            <Icon className="h-4 w-4 mr-2" />
            {action.label}
          </Button>
        )
      })}
      
      {/* Mobile version - just the plus icon */}
      <Button
        size="icon"
        variant="synthetic"
        className="md:hidden"
        onClick={() => navigate('/generator')}
      >
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  )
}