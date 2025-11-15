/**
 * Task Router - Routes tasks to optimal backend (Temporal, AutoKitteh, Local CLI, or Claude Code Web)
 * Core decision engine for offloading decisions
 */

import { AgentTask, RoutingDecision, RoutingConfig } from "./types";

export interface RoutingContext {
  parallelizable: boolean;
  repoCount?: number;
  estimatedDurationHours?: number;
  requiresLocalFiles: boolean;
  requiresImmediateFeedback: boolean;
  isDeterministicSchedule: boolean;
  isEventDriven: boolean;
}

export class TaskRouter {
  private config: RoutingConfig;

  constructor(config: RoutingConfig) {
    this.config = config;
  }

  /**
   * Route a task to the optimal backend
   * Returns: "temporal" | "autokitteh" | "local_cli" | "claude_web"
   */
  async route(task: AgentTask): Promise<RoutingDecision> {
    const context = this.analyzeTask(task);

    // Priority 1: Deterministic schedules
    if (context.isDeterministicSchedule) {
      return {
        route: "temporal",
        reason: "Deterministic schedule - use Temporal for reliability",
        estimatedCost: 0,
        estimatedDuration: "as scheduled",
      };
    }

    // Priority 2: Event-driven
    if (context.isEventDriven) {
      return {
        route: "autokitteh",
        reason: "Event-driven trigger - use AutoKitteh for reaction",
        estimatedCost: 0,
        estimatedDuration: "real-time",
      };
    }

    // Priority 3: Highly parallelizable tasks
    if (context.parallelizable && context.repoCount && context.repoCount > 5) {
      const workerCount = Math.ceil(context.repoCount / 10);
      const estimatedHours = context.estimatedDurationHours || 2;
      const estimatedCost = this.estimateCost(estimatedHours, workerCount);

      return {
        route: "claude_web",
        reason: `Parallelizable across ${context.repoCount} repos - spawn ${workerCount} workers`,
        workerCount,
        estimatedCost,
        estimatedDuration: `${estimatedHours / workerCount} hours`,
        parallelFactor: workerCount,
      };
    }

    // Priority 4: Long-running tasks
    if (context.estimatedDurationHours && context.estimatedDurationHours > 2) {
      const estimatedCost = this.estimateCost(context.estimatedDurationHours, 1);

      return {
        route: "claude_web",
        reason: "Long-running task (>2 hours) - avoid blocking local machine",
        workerCount: 1,
        estimatedCost,
        estimatedDuration: `${context.estimatedDurationHours} hours`,
      };
    }

    // Priority 5: No local files required
    if (!context.requiresLocalFiles) {
      const estimatedCost = this.estimateCost(
        context.estimatedDurationHours || 1,
        1
      );

      return {
        route: "claude_web",
        reason: "No local files required - can run in isolated VM",
        estimatedCost,
        estimatedDuration: `${context.estimatedDurationHours || 1} hours`,
      };
    }

    // Priority 6: Immediate feedback needed
    if (context.requiresImmediateFeedback) {
      return {
        route: "local_cli",
        reason: "Requires immediate feedback - use local Claude Code CLI",
        estimatedCost: 0,
        estimatedDuration: "interactive",
      };
    }

    // Default: Local CLI
    return {
      route: "local_cli",
      reason: "Default - local execution with immediate feedback",
      estimatedCost: 0,
      estimatedDuration: "interactive",
    };
  }

  /**
   * Analyze task to build routing context
   */
  private analyzeTask(task: AgentTask): RoutingContext {
    return {
      parallelizable: this.isParallelizable(task),
      repoCount: task.repos?.length || 0,
      estimatedDurationHours: task.estimatedDurationHours,
      requiresLocalFiles: task.requiresLocalFiles ?? false,
      requiresImmediateFeedback: task.requiresImmediateFeedback ?? false,
      isDeterministicSchedule: this.isDeterministicSchedule(task),
      isEventDriven: this.isEventDriven(task),
    };
  }

  /**
   * Determine if task is parallelizable
   */
  private isParallelizable(task: AgentTask): boolean {
    return (
      task.type !== "single_repo_fix" &&
      task.type !== "interactive_debugging" &&
      (task.repos?.length ?? 0) > 1
    );
  }

  /**
   * Check if task is deterministic schedule
   */
  private isDeterministicSchedule(task: AgentTask): boolean {
    return (
      task.schedule !== undefined ||
      task.type === "nightly_scan" ||
      task.type === "weekly_report"
    );
  }

  /**
   * Check if task is event-driven
   */
  private isEventDriven(task: AgentTask): boolean {
    return task.trigger !== undefined || task.type === "webhook_trigger";
  }

  /**
   * Estimate cost based on duration and worker count
   * Rough estimate: $0.02 per Sonnet 4.5 token-second
   * Average task: 100k tokens/hour at $0.003/token = ~$0.30/hour
   */
  private estimateCost(hours: number, workerCount: number): number {
    const costPerHour = 0.3; // Approximate cost for Claude Sonnet 4.5
    return hours * costPerHour * workerCount;
  }
}
