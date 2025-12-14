// Core data types
export interface Database {
  id: string
  name: string
  type: 'postgresql' | 'mysql' | 'sqlite' | 'mongodb' | 'oracle'
  host: string
  port: number
  username: string
  status: 'connected' | 'disconnected' | 'error'
  last_connected?: string
  schemas?: Schema[]
  metadata?: DatabaseMetadata
}

export interface Schema {
  id: string
  name: string
  database_id: string
  tables: Table[]
  views?: View[]
  functions?: Function[]
  permissions?: Permission[]
}

export interface Table {
  id: string
  name: string
  schema: string
  columns: Column[]
  row_count?: number
  size?: string
  privacy_level: PrivacyLevel
  compliance_tags: ComplianceTag[]
  sensitive_columns?: string[]
  relationships?: Relationship[]
}

export interface Column {
  id: string
  name: string
  type: string
  nullable: boolean
  default_value?: any
  is_primary_key?: boolean
  is_foreign_key?: boolean
  foreign_key_reference?: ForeignKeyReference
  privacy_level: PrivacyLevel
  data_category: DataCategory
  is_sensitive?: boolean
  anonymization_method?: AnonymizationMethod
}

export interface View {
  id: string
  name: string
  definition: string
  columns: Column[]
  base_tables: string[]
}

export interface Function {
  id: string
  name: string
  return_type: string
  parameters: Parameter[]
  definition: string
}

export interface Parameter {
  name: string
  type: string
  mode: 'IN' | 'OUT' | 'INOUT'
}

export interface Relationship {
  id: string
  type: 'one-to-one' | 'one-to-many' | 'many-to-many'
  source_table: string
  source_column: string
  target_table: string
  target_column: string
}

export interface ForeignKeyReference {
  table: string
  column: string
  schema?: string
}

// Privacy and compliance types
export type PrivacyLevel = 'public' | 'internal' | 'confidential' | 'restricted'
export type ComplianceTag = 'HIPAA' | 'GDPR' | 'CCPA' | 'PCI-DSS' | 'SOX' | 'FERPA'
export type DataCategory = 'personal' | 'financial' | 'health' | 'biometric' | 'location' | 'behavioral' | 'derived' | 'anonymous'
export type AnonymizationMethod = 'mask' | 'hash' | 'encrypt' | 'generalize' | 'suppress' | 'synthetic' | 'differential_privacy'

// Synthetic data generation types
export interface GenerationJob {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  created_at: string
  updated_at: string
  completed_at?: string
  source_table: string
  target_rows: number
  generated_rows: number
  privacy_budget: number
  privacy_spent: number
  parameters: GenerationParameters
  results?: GenerationResults
  error_message?: string
}

export interface GenerationParameters {
  method: 'gan' | 'vae' | 'ctgan' | 'copula' | 'statistical' | 'llm'
  quality_threshold: number
  privacy_epsilon?: number
  correlation_preservation: boolean
  constraints: DataConstraint[]
  seed?: number
  batch_size?: number
  max_iterations?: number
}

export interface DataConstraint {
  id: string
  type: 'range' | 'categorical' | 'pattern' | 'foreign_key' | 'unique' | 'custom'
  column: string
  parameters: Record<string, any>
  weight: number
}

export interface GenerationResults {
  quality_metrics: QualityMetric[]
  privacy_metrics: PrivacyMetric[]
  performance_metrics: PerformanceMetric[]
  sample_data?: Record<string, any>[]
}

export interface QualityMetric {
  name: string
  value: number
  description: string
  threshold: number
  passed: boolean
}

export interface PrivacyMetric {
  name: string
  value: number
  description: string
  budget_used: number
  risk_level: 'low' | 'medium' | 'high'
}

export interface PerformanceMetric {
  name: string
  value: number
  unit: string
  description: string
}

// Query builder types
export interface Query {
  id: string
  name: string
  sql: string
  database_id: string
  created_by: string
  created_at: string
  updated_at: string
  is_public: boolean
  tags: string[]
  description?: string
  parameters?: QueryParameter[]
}

export interface QueryParameter {
  name: string
  type: string
  default_value?: any
  required: boolean
  description?: string
}

export interface QueryResult {
  columns: string[]
  rows: any[][]
  total_rows: number
  execution_time: number
  query_plan?: any
  warnings?: string[]
}

// User and authentication types
export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  permissions: Permission[]
  created_at: string
  last_login?: string
  preferences: UserPreferences
  avatar_url?: string
}

export type UserRole = 'admin' | 'data_engineer' | 'data_scientist' | 'analyst' | 'viewer'

export interface Permission {
  id: string
  resource: string
  action: string
  conditions?: Record<string, any>
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  language: string
  timezone: string
  notifications: NotificationPreferences
  data_preview_rows: number
  default_privacy_level: PrivacyLevel
}

export interface NotificationPreferences {
  email: boolean
  browser: boolean
  job_completion: boolean
  privacy_alerts: boolean
  system_updates: boolean
}

// API types
export interface ApiResponse<T = any> {
  data: T
  status: 'success' | 'error'
  message?: string
  pagination?: Pagination
  metadata?: Record<string, any>
}

export interface Pagination {
  page: number
  limit: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  timestamp: string
  request_id: string
}

// UI state types
export interface UiState {
  theme: 'light' | 'dark'
  sidebar_collapsed: boolean
  loading_states: Record<string, boolean>
  error_messages: Record<string, string>
  notifications: Notification[]
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
  auto_dismiss?: number
  actions?: NotificationAction[]
}

export interface NotificationAction {
  label: string
  action: () => void
  variant?: 'default' | 'destructive'
}

// Dashboard types
export interface DashboardMetrics {
  total_databases: number
  total_tables: number
  total_columns: number
  active_jobs: number
  completed_jobs_today: number
  privacy_budget_used: number
  privacy_budget_total: number
  system_health: 'healthy' | 'warning' | 'critical'
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'job_created' | 'job_completed' | 'database_connected' | 'schema_updated' | 'privacy_alert'
  description: string
  timestamp: string
  user?: string
  metadata?: Record<string, any>
}

// WebSocket types
export interface WebSocketMessage {
  type: string
  payload: any
  timestamp: string
  id?: string
}

export interface JobUpdate {
  job_id: string
  status: string
  progress: number
  message?: string
  results?: any
}

// Export types
export interface ExportJob {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  format: 'csv' | 'json' | 'parquet' | 'sql' | 'excel'
  source_query: string
  row_count: number
  file_size?: number
  download_url?: string
  created_at: string
  expires_at?: string
  privacy_review_required: boolean
}

// Database metadata
export interface DatabaseMetadata {
  version: string
  size: string
  connection_pool_size: number
  active_connections: number
  uptime: number
  last_backup?: string
  performance_metrics?: DatabasePerformanceMetrics
}

export interface DatabasePerformanceMetrics {
  queries_per_second: number
  avg_query_time: number
  slow_queries: number
  cache_hit_ratio: number
  connection_utilization: number
}

// Utility types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface SelectOption<T = any> {
  label: string
  value: T
  disabled?: boolean
  description?: string
}

export interface TableColumn<T = any> {
  id: string
  header: string
  accessor?: string
  cell?: (row: T) => React.ReactNode
  sortable?: boolean
  width?: number
  minWidth?: number
  maxWidth?: number
}

export interface FilterOption {
  field: string
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'like' | 'in' | 'not_in' | 'is_null' | 'is_not_null'
  value: any
  type: 'string' | 'number' | 'date' | 'boolean'
}

export interface SortOption {
  field: string
  direction: 'asc' | 'desc'
}

// Form types
export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'multi-select' | 'checkbox' | 'radio' | 'textarea' | 'date' | 'file'
  placeholder?: string
  description?: string
  required?: boolean
  disabled?: boolean
  options?: SelectOption[]
  validation?: any // Zod schema
  defaultValue?: any
}

// Component prop types
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

export interface DataTableProps<T = any> {
  data: T[]
  columns: TableColumn<T>[]
  loading?: boolean
  pagination?: Pagination
  onPageChange?: (page: number) => void
  onSort?: (sort: SortOption) => void
  onFilter?: (filters: FilterOption[]) => void
  selection?: boolean
  onSelectionChange?: (selected: T[]) => void
}

export interface ChartProps {
  data: any[]
  width?: number
  height?: number
  margin?: { top: number; right: number; bottom: number; left: number }
  responsive?: boolean
}

// Error boundary types
export interface ErrorInfo {
  componentStack: string
  errorBoundary?: string
}