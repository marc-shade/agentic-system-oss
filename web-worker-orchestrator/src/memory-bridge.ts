/**
 * Enhanced Memory Bridge - Integration with Enhanced Memory MCP
 * Stores session metadata, results, and learnings
 */

import { WebSessionMetadata, TaskResult } from "./types";

export interface EnhancedMemoryMCP {
  createEntity(entity: {
    name: string;
    entityType: string;
    observations: Record<string, unknown>[];
  }): Promise<{ id: string; name: string }>;

  searchNodes(query: string, limit?: number): Promise<
    Array<{
      id: string;
      name: string;
      type: string;
      observations: Record<string, unknown>[];
    }>
  >;

  getMemoryStatus(): Promise<{
    totalEntities: number;
    compression: number;
    indexSize: number;
  }>;
}

export class MemoryBridge {
  private memory: EnhancedMemoryMCP;

  constructor(memory: EnhancedMemoryMCP) {
    this.memory = memory;
  }

  /**
   * Store web session metadata
   */
  async storeSessionMetadata(metadata: WebSessionMetadata): Promise<string> {
    const entity = {
      name: `web-session-${metadata.sessionId}`,
      entityType: "web_worker_session",
      observations: [
        {
          taskId: metadata.taskId,
          sessionId: metadata.sessionId,
          repo: metadata.repo,
          branch: metadata.branch,
          status: metadata.status,
          cost: metadata.cost,
          createdAt: metadata.createdAt.toISOString(),
          completedAt: metadata.completedAt?.toISOString(),
          workerId: metadata.workerId,
        },
      ],
    };

    const result = await this.memory.createEntity(entity);
    console.log(
      `[MemoryBridge] Stored session metadata: ${result.name} (${result.id})`
    );
    return result.id;
  }

  /**
   * Store task results
   */
  async storeTaskResult(result: TaskResult): Promise<string> {
    const entity = {
      name: `task-result-${result.taskId}`,
      entityType: "task_result",
      observations: [
        {
          taskId: result.taskId,
          status: result.status,
          outcome: result.outcome,
          costActual: result.costActual,
          durationActual: result.durationActual,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    const res = await this.memory.createEntity(entity);
    console.log(`[MemoryBridge] Stored task result: ${res.name} (${res.id})`);
    return res.id;
  }

  /**
   * Store routing decision and statistics
   */
  async storeRoutingStatistics(stats: {
    totalTasks: number;
    routedToWeb: number;
    routedToLocal: number;
    routedToTemporal: number;
    routedToAutoKitteh: number;
    averageCost: number;
    totalSavingsHours: number;
  }): Promise<string> {
    const entity = {
      name: `routing-stats-${Date.now()}`,
      entityType: "routing_statistics",
      observations: [
        {
          ...stats,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    const result = await this.memory.createEntity(entity);
    console.log(
      `[MemoryBridge] Stored routing statistics: ${result.name} (${result.id})`
    );
    return result.id;
  }

  /**
   * Search for similar past tasks
   */
  async findSimilarTasks(
    taskType: string,
    limit: number = 10
  ): Promise<
    Array<{
      id: string;
      name: string;
      observations: Record<string, unknown>[];
    }>
  > {
    return this.memory.searchNodes(
      `task_result type:${taskType}`,
      limit
    );
  }

  /**
   * Store web worker performance metrics
   */
  async storePerformanceMetrics(metrics: {
    workerId: number;
    tasksCompleted: number;
    averageDuration: number;
    averageCost: number;
    successRate: number;
    commitsGenerated: number;
    prsCreated: number;
  }): Promise<string> {
    const entity = {
      name: `worker-metrics-${metrics.workerId}-${Date.now()}`,
      entityType: "worker_performance",
      observations: [
        {
          ...metrics,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    const result = await this.memory.createEntity(entity);
    console.log(
      `[MemoryBridge] Stored worker metrics: ${result.name} (${result.id})`
    );
    return result.id;
  }

  /**
   * Get memory system status
   */
  async getStatus(): Promise<{ totalEntities: number; indexSize: number }> {
    const status = await this.memory.getMemoryStatus();
    return {
      totalEntities: status.totalEntities,
      indexSize: status.indexSize,
    };
  }

  /**
   * Store cost analysis for decision optimization
   */
  async storeCostAnalysis(analysis: {
    taskId: string;
    estimatedCostWeb: number;
    estimatedCostLocal: number;
    actualCostWeb: number;
    savingsPercent: number;
    recommendation: string;
  }): Promise<string> {
    const entity = {
      name: `cost-analysis-${analysis.taskId}`,
      entityType: "cost_analysis",
      observations: [
        {
          ...analysis,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    const result = await this.memory.createEntity(entity);
    console.log(
      `[MemoryBridge] Stored cost analysis: ${result.name} (${result.id})`
    );
    return result.id;
  }
}
