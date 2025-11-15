/**
 * Web Submitter - Submit tasks to Claude Code on the web
 * Handles GitHub API interactions and session creation
 */

import { WebWorkerTask, WebSessionMetadata } from "./types";

export interface ClaudeWebSession {
  sessionId: string;
  gitHubBranch: string;
  status: "pending" | "running" | "completed" | "failed";
  createdAt: Date;
  completedAt?: Date;
}

export class WebSubmitter {
  private claudeApiKey: string;
  private githubToken: string;
  private baseUrl = "https://claude.ai/api/code";

  constructor(claudeApiKey: string, githubToken: string) {
    this.claudeApiKey = claudeApiKey;
    this.githubToken = githubToken;
  }

  /**
   * Submit a single web worker task
   */
  async submitTask(
    task: WebWorkerTask,
    repos: string[]
  ): Promise<ClaudeWebSession> {
    const branch = this.generateBranchName(task);

    const requestPayload = {
      github_repo: repos[0], // Primary repo (for single worker)
      branch,
      task: this.buildTaskPrompt(task, repos),
      environment: task.environment || "default",
      callback_url: process.env.WEBHOOK_CALLBACK_URL || "",
      max_duration_hours: task.maxDurationHours || 8,
    };

    console.log(`[WebSubmitter] Submitting task to Claude Code web:`, {
      task: task.id,
      repos: repos.length,
      branch,
      estimatedDuration: task.estimatedDurationHours,
    });

    try {
      const response = await fetch(`${this.baseUrl}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.claudeApiKey}`,
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(
          `Failed to submit task: ${response.status} ${response.statusText}`
        );
      }

      const data = (await response.json()) as {
        session_id: string;
        branch: string;
      };

      const session: ClaudeWebSession = {
        sessionId: data.session_id,
        gitHubBranch: data.branch,
        status: "pending",
        createdAt: new Date(),
      };

      console.log(
        `[WebSubmitter] Task submitted successfully: ${session.sessionId}`
      );
      return session;
    } catch (error) {
      console.error(`[WebSubmitter] Failed to submit task:`, error);
      throw error;
    }
  }

  /**
   * Submit multiple tasks in parallel (batch submission)
   */
  async submitBatch(
    task: WebWorkerTask,
    repoChunks: string[][]
  ): Promise<ClaudeWebSession[]> {
    console.log(
      `[WebSubmitter] Submitting batch of ${repoChunks.length} workers`
    );

    const submissions = repoChunks.map((chunk, index) =>
      this.submitTask({ ...task, id: `${task.id}-worker-${index}` }, chunk)
    );

    return Promise.all(submissions);
  }

  /**
   * Check status of a running session
   */
  async checkStatus(sessionId: string): Promise<ClaudeWebSession> {
    try {
      const response = await fetch(`${this.baseUrl}/status/${sessionId}`, {
        headers: {
          Authorization: `Bearer ${this.claudeApiKey}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to check status: ${response.statusText}`);
      }

      const data = (await response.json()) as {
        session_id: string;
        status: string;
        branch: string;
        completed_at?: string;
      };

      return {
        sessionId: data.session_id,
        gitHubBranch: data.branch,
        status: data.status as ClaudeWebSession["status"],
        createdAt: new Date(), // Would need to fetch from API
        completedAt: data.completed_at ? new Date(data.completed_at) : undefined,
      };
    } catch (error) {
      console.error(`[WebSubmitter] Failed to check status:`, error);
      throw error;
    }
  }

  /**
   * Cancel a running session
   */
  async cancelSession(sessionId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/cancel/${sessionId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.claudeApiKey}`,
        },
      });

      return response.ok;
    } catch (error) {
      console.error(`[WebSubmitter] Failed to cancel session:`, error);
      return false;
    }
  }

  /**
   * Build the task prompt for Claude Code web
   */
  private buildTaskPrompt(task: WebWorkerTask, repos: string[]): string {
    let prompt = `# Task: ${task.description}\n\n`;

    if (repos.length === 1) {
      prompt += `Repository: ${repos[0]}\n\n`;
    } else {
      prompt += `Repositories:\n${repos.map((r) => `- ${r}`).join("\n")}\n\n`;
    }

    if (task.constraints) {
      prompt += `## Constraints\n${task.constraints}\n\n`;
    }

    if (task.successCriteria) {
      prompt += `## Success Criteria\n${task.successCriteria}\n\n`;
    }

    prompt += `## Instructions\n`;
    prompt += `1. Complete all required tasks\n`;
    prompt += `2. Run tests to verify functionality\n`;
    prompt += `3. Create PRs with detailed descriptions\n`;
    prompt += `4. Ensure no breaking changes\n`;
    prompt += `5. Follow existing code patterns and conventions\n`;

    return prompt;
  }

  /**
   * Generate a unique branch name for the task
   */
  private generateBranchName(task: WebWorkerTask): string {
    const timestamp = Date.now();
    const taskPrefix = task.type.toLowerCase().replace(/_/g, "-");
    return `web-worker/${taskPrefix}/${timestamp}`;
  }
}
