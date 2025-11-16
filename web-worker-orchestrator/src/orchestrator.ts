/**
 * Main Web-Worker Orchestrator
 * Coordinates task routing, submission, and collection
 */

import * as fs from "fs";
import * as path from "path";
import { TaskRouter } from "./router";
import { WebSubmitter } from "./submitter";
import { ResultCollector } from "./collector";
import { AgentRuntimeBridge } from "./agent-runtime-bridge";
import { MemoryBridge } from "./memory-bridge";
import {
  AgentTask,
  RoutingDecision,
  RoutingConfig,
  WebSessionMetadata,
} from "./types";
import { AgentRuntimeMCP } from "./agent-runtime-bridge";
import { EnhancedMemoryMCP } from "./memory-bridge";

interface OrchestrationStats {
  totalTasksProcessed: number;
  routedToTemporal: number;
  routedToAutoKitteh: number;
  routedToLocalCli: number;
  routedToWebWorkers: number;
  totalWebSessions: number;
  totalCostSpent: number;
  totalHoursSaved: number;
  activeSessions: Map<string, WebSessionMetadata>;
}

export class WebWorkerOrchestrator {
  private router: TaskRouter;
  private submitter: WebSubmitter;
  private collector: ResultCollector;
  private agentRuntimeBridge: AgentRuntimeBridge;
  private memoryBridge: MemoryBridge;
  private stats: OrchestrationStats;
  private isRunning: boolean = false;

  constructor(config: RoutingConfig) {
    const apiKey = process.env.CLAUDE_API_KEY || "";
    const githubToken = process.env.GITHUB_TOKEN || "";

    if (!apiKey || !githubToken) {
      throw new Error(
        "Missing CLAUDE_API_KEY or GITHUB_TOKEN environment variables"
      );
    }

    this.router = new TaskRouter(config);
    this.submitter = new WebSubmitter(apiKey, githubToken);
    this.collector = new ResultCollector(githubToken);
    this.agentRuntimeBridge = new AgentRuntimeBridge({} as any); // Would be injected
    this.memoryBridge = new MemoryBridge({} as any); // Would be injected

    this.stats = {
      totalTasksProcessed: 0,
      routedToTemporal: 0,
      routedToAutoKitteh: 0,
      routedToLocalCli: 0,
      routedToWebWorkers: 0,
      totalWebSessions: 0,
      totalCostSpent: 0,
      totalHoursSaved: 0,
      activeSessions: new Map(),
    };

    this.setupLogging();
  }

  /**
   * Start the orchestrator
   */
  async start(): Promise<void> {
    this.isRunning = true;
    console.log(
      "[Orchestrator] Starting Web-Worker Orchestrator service..."
    );

    // Start listening for tasks from Agent Runtime
    await this.agentRuntimeBridge.startPolling(
      this.handleTask.bind(this)
    );
  }

  /**
   * Stop the orchestrator
   */
  stop(): void {
    this.isRunning = false;
    this.agentRuntimeBridge.stopPolling();
    console.log("[Orchestrator] Orchestrator stopped");
  }

  /**
   * Handle a task from Agent Runtime
   */
  private async handleTask(task: AgentTask): Promise<void> {
    try {
      console.log(`[Orchestrator] Processing task: ${task.id}`);

      // Route the task
      const decision = await this.router.route(task);
      console.log(
        `[Orchestrator] Routing decision: ${decision.route} (${decision.reason})`
      );

      this.stats.totalTasksProcessed++;
      this.updateStats(decision);

      // Mark task as in progress
      await this.agentRuntimeBridge.markInProgress(task.id);

      // Handle routing
      if (decision.route === "claude_web") {
        await this.handleWebWorkerTask(task, decision);
      } else {
        console.log(
          `[Orchestrator] Task routed to ${decision.route} - not handled by orchestrator`
        );
      }
    } catch (error) {
      console.error(`[Orchestrator] Error handling task:`, error);
      await this.agentRuntimeBridge.markFailed(
        task.id,
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  /**
   * Handle task routed to Claude Code web workers
   */
  private async handleWebWorkerTask(
    task: AgentTask,
    decision: RoutingDecision
  ): Promise<void> {
    console.log(`[Orchestrator] Handling web worker task: ${task.id}`);

    const repos = task.repos || [];
    const workerCount = decision.workerCount || 1;

    // Chunk repos for parallel workers
    const repoChunks = this.chunkRepos(repos, workerCount);

    // Submit to Claude Code web
    console.log(
      `[Orchestrator] Submitting task with ${workerCount} workers...`
    );
    const sessions = await this.submitter.submitBatch(
      {
        id: task.id,
        type: task.type,
        description: task.description,
        estimatedDurationHours: task.estimatedDurationHours,
      },
      repoChunks
    );

    console.log(
      `[Orchestrator] Submitted ${sessions.length} web worker sessions`
    );

    // Store session metadata
    for (const session of sessions) {
      const metadata: WebSessionMetadata = {
        taskId: task.id,
        sessionId: session.sessionId,
        repo: repos[0] || "multi-repo",
        branch: session.gitHubBranch,
        status: "pending",
        createdAt: session.createdAt,
        cost: decision.estimatedCost || 0,
      };

      this.stats.activeSessions.set(session.sessionId, metadata);
      await this.memoryBridge.storeSessionMetadata(metadata);
    }

    this.stats.totalWebSessions += sessions.length;
    this.stats.totalCostSpent +=
      (decision.estimatedCost || 0) * workerCount;

    // Start monitoring for completion
    this.monitorSessions(task.id, sessions);
  }

  /**
   * Monitor web sessions for completion
   */
  private async monitorSessions(
    taskId: string,
    sessions: any[]
  ): Promise<void> {
    console.log(`[Orchestrator] Monitoring ${sessions.length} sessions...`);

    const pollingInterval = setInterval(async () => {
      try {
        let completedCount = 0;

        for (const session of sessions) {
          const status = await this.submitter.checkStatus(
            session.sessionId
          );

          if (
            status.status === "completed" ||
            status.status === "failed"
          ) {
            completedCount++;

            // Collect results
            const results = await this.collector.collectResults({
              taskId,
              sessionId: session.sessionId,
              repo: "",
              branch: status.gitHubBranch,
              status: status.status as any,
              createdAt: session.createdAt,
              cost: 0,
            });

            // Store results in memory
            await this.memoryBridge.storeTaskResult({
              taskId,
              status: results.status,
              outcome: {
                prs: results.prs.length,
                commits: results.commits.length,
              },
              costActual: 0,
              durationActual: 0,
            });

            // Update session status
            const metadata = this.stats.activeSessions.get(
              session.sessionId
            );
            if (metadata) {
              metadata.status = status.status;
              metadata.completedAt = new Date();
            }
          }
        }

        // All sessions complete
        if (completedCount === sessions.length) {
          clearInterval(pollingInterval);
          console.log(`[Orchestrator] All sessions completed for task: ${taskId}`);
          await this.agentRuntimeBridge.markCompleted(
            taskId,
            {} as any
          );
        }
      } catch (error) {
        console.error(`[Orchestrator] Error monitoring sessions:`, error);
      }
    }, 30000); // Check every 30 seconds
  }

  /**
   * Split repos into chunks for parallel workers
   */
  private chunkRepos(repos: string[], chunkSize: number): string[][] {
    const chunks: string[][] = [];
    for (let i = 0; i < repos.length; i += chunkSize) {
      chunks.push(repos.slice(i, i + chunkSize));
    }
    return chunks;
  }

  /**
   * Update statistics based on routing decision
   */
  private updateStats(decision: RoutingDecision): void {
    switch (decision.route) {
      case "temporal":
        this.stats.routedToTemporal++;
        break;
      case "autokitteh":
        this.stats.routedToAutoKitteh++;
        break;
      case "local_cli":
        this.stats.routedToLocalCli++;
        break;
      case "claude_web":
        this.stats.routedToWebWorkers++;
        if (decision.parallelFactor && decision.parallelFactor > 1) {
          // Estimate time saved by parallelization
          this.stats.totalHoursSaved +=
            (decision.parallelFactor - 1) *
            (decision.estimatedDuration
              ? parseFloat(decision.estimatedDuration)
              : 1);
        }
        break;
    }
  }

  /**
   * Get current statistics
   */
  getStats(): OrchestrationStats {
    return { ...this.stats };
  }

  /**
   * Setup logging
   */
  private setupLogging(): void {
    const logsDir = path.join(__dirname, "..", "..", "logs");
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }

    const logFile = path.join(logsDir, "orchestrator.log");
    const logStream = fs.createWriteStream(logFile, { flags: "a" });

    // Would hook console.log to also write to file
    console.log(`[Orchestrator] Logging to ${logFile}`);
  }
}

// Main entry point
async function main() {
  const config: RoutingConfig = {
    maxConcurrentWorkers: 10,
    defaultWorkerCount: 5,
    creditBudgetPerMonth: 1000,
    enableAutoParallelization: true,
  };

  const orchestrator = new WebWorkerOrchestrator(config);

  // Handle graceful shutdown
  process.on("SIGINT", () => {
    console.log("[Orchestrator] Received SIGINT, shutting down gracefully...");
    orchestrator.stop();
    process.exit(0);
  });

  try {
    await orchestrator.start();
  } catch (error) {
    console.error("[Orchestrator] Fatal error:", error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

export default WebWorkerOrchestrator;
