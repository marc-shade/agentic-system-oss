/**
 * Result Collector - Gathers results from completed web worker sessions
 * Handles GitHub PR collection, aggregation, and webhooks
 */

import { WebSessionMetadata, TaskResult } from "./types";

export interface CollectedResult {
  taskId: string;
  sessionId: string;
  status: "success" | "partial" | "failed";
  prs: GitHubPR[];
  commits: GitHubCommit[];
  artifacts?: Record<string, string>;
  logs?: string;
  errors?: string[];
}

export interface GitHubPR {
  number: number;
  title: string;
  branch: string;
  url: string;
  files_changed: number;
  additions: number;
  deletions: number;
}

export interface GitHubCommit {
  hash: string;
  message: string;
  author: string;
  timestamp: string;
}

export class ResultCollector {
  private githubToken: string;
  private githubBaseUrl = "https://api.github.com";

  constructor(githubToken: string) {
    this.githubToken = githubToken;
  }

  /**
   * Collect results from a completed web worker session
   */
  async collectResults(
    metadata: WebSessionMetadata
  ): Promise<CollectedResult> {
    console.log(
      `[ResultCollector] Collecting results for task: ${metadata.taskId}`
    );

    try {
      const [prs, commits] = await Promise.all([
        this.fetchPRs(metadata.repo, metadata.branch),
        this.fetchCommits(metadata.repo, metadata.branch),
      ]);

      const result: CollectedResult = {
        taskId: metadata.taskId,
        sessionId: metadata.sessionId,
        status: prs.length > 0 ? "success" : "partial",
        prs,
        commits,
      };

      console.log(`[ResultCollector] Collected ${prs.length} PRs and ${commits.length} commits`);
      return result;
    } catch (error) {
      console.error(`[ResultCollector] Failed to collect results:`, error);
      throw error;
    }
  }

  /**
   * Aggregate results from multiple web workers
   */
  async aggregateResults(
    results: CollectedResult[]
  ): Promise<CollectedResult> {
    console.log(`[ResultCollector] Aggregating ${results.length} worker results`);

    const aggregated: CollectedResult = {
      taskId: results[0]?.taskId || "aggregated",
      sessionId: "multi-worker",
      status: results.every((r) => r.status === "success") ? "success" : "partial",
      prs: results.flatMap((r) => r.prs),
      commits: results.flatMap((r) => r.commits),
      artifacts: {},
      errors: results.flatMap((r) => r.errors || []),
    };

    // Merge artifacts
    results.forEach((result) => {
      if (result.artifacts && aggregated.artifacts) {
        Object.assign(aggregated.artifacts, result.artifacts);
      }
    });

    return aggregated;
  }

  /**
   * Fetch PRs for a branch
   */
  private async fetchPRs(repo: string, branch: string): Promise<GitHubPR[]> {
    try {
      const [owner, name] = repo.split("/");
      const response = await fetch(
        `${this.githubBaseUrl}/repos/${owner}/${name}/pulls?head=${owner}:${branch}&state=open`,
        {
          headers: {
            Authorization: `Bearer ${this.githubToken}`,
            Accept: "application/vnd.github.v3+json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch PRs: ${response.statusText}`);
      }

      const data = (await response.json()) as Array<{
        number: number;
        title: string;
        head: { ref: string };
        html_url: string;
        changed_files: number;
        additions: number;
        deletions: number;
      }>;

      return data.map((pr) => ({
        number: pr.number,
        title: pr.title,
        branch: pr.head.ref,
        url: pr.html_url,
        files_changed: pr.changed_files,
        additions: pr.additions,
        deletions: pr.deletions,
      }));
    } catch (error) {
      console.error(`[ResultCollector] Failed to fetch PRs:`, error);
      return [];
    }
  }

  /**
   * Fetch commits for a branch
   */
  private async fetchCommits(
    repo: string,
    branch: string
  ): Promise<GitHubCommit[]> {
    try {
      const [owner, name] = repo.split("/");
      const response = await fetch(
        `${this.githubBaseUrl}/repos/${owner}/${name}/commits?sha=${branch}&per_page=50`,
        {
          headers: {
            Authorization: `Bearer ${this.githubToken}`,
            Accept: "application/vnd.github.v3+json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch commits: ${response.statusText}`);
      }

      const data = (await response.json()) as Array<{
        sha: string;
        commit: { message: string; author: { name: string; date: string } };
      }>;

      return data.map((commit) => ({
        hash: commit.sha.substring(0, 7),
        message: commit.commit.message.split("\n")[0],
        author: commit.commit.author.name,
        timestamp: commit.commit.author.date,
      }));
    } catch (error) {
      console.error(`[ResultCollector] Failed to fetch commits:`, error);
      return [];
    }
  }

  /**
   * Webhook handler for session completion
   */
  handleWebhook(payload: Record<string, unknown>): void {
    console.log(`[ResultCollector] Webhook received:`, payload);
    // Implementation would trigger result collection
  }
}
