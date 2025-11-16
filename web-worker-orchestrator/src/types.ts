/**
 * Type definitions for web-worker-orchestrator
 */

export type RouteName = "temporal" | "autokitteh" | "local_cli" | "claude_web";

export interface AgentTask {
  id: string;
  type: TaskType;
  description: string;
  repos?: string[];
  estimatedDurationHours?: number;
  requiresLocalFiles?: boolean;
  requiresImmediateFeedback?: boolean;
  schedule?: string; // Cron expression for Temporal
  trigger?: string; // Event trigger for AutoKitteh
  priority?: number;
  metadata?: Record<string, unknown>;
}

export type TaskType =
  | "security_scan"
  | "dependency_update"
  | "test_generation"
  | "code_migration"
  | "refactoring"
  | "documentation"
  | "ml_training"
  | "data_processing"
  | "single_repo_fix"
  | "interactive_debugging"
  | "nightly_scan"
  | "weekly_report"
  | "webhook_trigger"
  | "custom";

export interface RoutingDecision {
  route: RouteName;
  reason: string;
  workerCount?: number;
  estimatedCost?: number;
  estimatedDuration?: string;
  parallelFactor?: number;
}

export interface WebWorkerTask {
  id: string;
  type: TaskType;
  description: string;
  constraints?: string;
  successCriteria?: string;
  environment?: string;
  estimatedDurationHours?: number;
  maxDurationHours?: number;
}

export interface WebSessionMetadata {
  taskId: string;
  sessionId: string;
  repo: string;
  branch: string;
  status: "pending" | "running" | "completed" | "failed";
  createdAt: Date;
  completedAt?: Date;
  cost: number;
  workerId?: number;
}

export interface TaskResult {
  taskId: string;
  status: "success" | "partial" | "failed";
  outcome: Record<string, unknown>;
  costActual: number;
  durationActual: number;
}

export interface RoutingConfig {
  maxConcurrentWorkers?: number;
  defaultWorkerCount?: number;
  creditBudgetPerMonth?: number;
  enableAutoParallelization?: boolean;
  defaultEnvironment?: string;
}

export interface TaskDispatchEvent {
  task: AgentTask;
  decision: RoutingDecision;
  timestamp: Date;
}
