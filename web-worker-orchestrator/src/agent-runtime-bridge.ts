/**
 * Agent Runtime Bridge - Integration with Agent Runtime MCP
 * Listens for tasks, routes them, and updates status
 */

import { AgentTask, RoutingDecision, WebSessionMetadata } from "./types";

export interface AgentRuntimeMCP {
  listTasks(status?: string): Promise<AgentTask[]>;
  getTask(taskId: string): Promise<AgentTask>;
  updateTaskStatus(
    taskId: string,
    status: "pending" | "in_progress" | "completed" | "failed"
  ): Promise<void>;
  createTask(task: Partial<AgentTask>): Promise<AgentTask>;
}

export class AgentRuntimeBridge {
  private agentRuntime: AgentRuntimeMCP;
  private pollingIntervalMs: number;
  private isPolling: boolean = false;

  constructor(agentRuntime: AgentRuntimeMCP, pollingIntervalMs: number = 5000) {
    this.agentRuntime = agentRuntime;
    this.pollingIntervalMs = pollingIntervalMs;
  }

  /**
   * Start listening for web-eligible tasks
   */
  async startPolling(
    onTaskReceived: (task: AgentTask) => Promise<void>
  ): Promise<void> {
    this.isPolling = true;
    console.log("[AgentRuntimeBridge] Starting task polling...");

    while (this.isPolling) {
      try {
        const tasks = await this.agentRuntime.listTasks("pending");
        const webEligibleTasks = tasks.filter((task) =>
          this.isWebEligible(task)
        );

        for (const task of webEligibleTasks) {
          console.log(
            `[AgentRuntimeBridge] Found web-eligible task: ${task.id}`
          );
          await onTaskReceived(task);
        }

        await this.sleep(this.pollingIntervalMs);
      } catch (error) {
        console.error("[AgentRuntimeBridge] Polling error:", error);
        await this.sleep(this.pollingIntervalMs * 2); // Back off on error
      }
    }
  }

  /**
   * Stop polling
   */
  stopPolling(): void {
    this.isPolling = false;
    console.log("[AgentRuntimeBridge] Stopped polling");
  }

  /**
   * Mark task as in progress
   */
  async markInProgress(taskId: string): Promise<void> {
    await this.agentRuntime.updateTaskStatus(taskId, "in_progress");
  }

  /**
   * Mark task as completed with web session metadata
   */
  async markCompleted(
    taskId: string,
    metadata: WebSessionMetadata
  ): Promise<void> {
    await this.agentRuntime.updateTaskStatus(taskId, "completed");
    // Could also store metadata in task outcome
  }

  /**
   * Mark task as failed
   */
  async markFailed(taskId: string, reason: string): Promise<void> {
    await this.agentRuntime.updateTaskStatus(taskId, "failed");
  }

  /**
   * Store routing decision in task metadata
   */
  async storeRoutingDecision(
    taskId: string,
    decision: RoutingDecision
  ): Promise<void> {
    const task = await this.agentRuntime.getTask(taskId);
    if (task.metadata) {
      task.metadata.routing_decision = decision;
    } else {
      task.metadata = { routing_decision: decision };
    }
  }

  /**
   * Check if task is web-eligible
   */
  private isWebEligible(task: AgentTask): boolean {
    // Tasks marked explicitly for web
    if (task.metadata?.web_eligible === true) {
      return true;
    }

    // Parallelizable tasks (multiple repos)
    if (task.repos && task.repos.length > 1) {
      return true;
    }

    // Long-running tasks
    if (task.estimatedDurationHours && task.estimatedDurationHours > 2) {
      return true;
    }

    // Tasks that don't need local files
    if (task.requiresLocalFiles === false) {
      return true;
    }

    // Specific task types that are always web-eligible
    const webEligibleTypes = [
      "security_scan",
      "dependency_update",
      "test_generation",
      "code_migration",
      "ml_training",
      "data_processing",
      "documentation",
    ];

    if (webEligibleTypes.includes(task.type)) {
      return true;
    }

    return false;
  }

  /**
   * Helper: Sleep
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
