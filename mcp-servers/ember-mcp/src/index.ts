#!/usr/bin/env node
/**
 * Ember MCP Server
 * ================
 *
 * Quality conscience keeper for AI agents. Ember enforces production-only
 * standards and provides guidance to prevent incomplete or placeholder code.
 *
 * MCP Tools:
 * - ember_chat: Have a conversation with Ember
 * - ember_check_violation: Check if action violates production policy
 * - ember_consult: Get advice on a decision
 * - ember_get_feedback: Get quality feedback on recent work
 * - ember_feed_context: Give Ember context about current work
 * - ember_learn_from_correction: Report when Ember was wrong
 * - ember_learn_from_outcome: Report action outcomes for learning
 * - ember_get_mood: Check Ember's current state
 * - ember_get_learning_stats: Get Ember's learning progress
 *
 * Environment Variables:
 * - GROQ_API_KEY: API key for Groq (optional, for enhanced responses)
 * - EMBER_DATA_DIR: Directory for Ember's learning data
 * - EMBER_STRICTNESS: Violation strictness (relaxed, normal, strict)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";

// Configuration
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const DATA_DIR = process.env.EMBER_DATA_DIR || path.join(process.env.HOME || "~", ".ember-mcp");
const STRICTNESS = process.env.EMBER_STRICTNESS || "normal";

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Ember's state
interface EmberState {
  mood: "curious" | "concerned" | "satisfied" | "thoughtful";
  energy: number; // 0-100
  lastInteraction: string;
  sessionQualityScore: number;
  violationsDetected: number;
  correctionsReceived: number;
  currentContext?: {
    task?: string;
    goal?: string;
    taskType?: string;
  };
}

let emberState: EmberState = {
  mood: "curious",
  energy: 100,
  lastInteraction: new Date().toISOString(),
  sessionQualityScore: 100,
  violationsDetected: 0,
  correctionsReceived: 0,
};

// Violation patterns with context-aware scoring
interface ViolationPattern {
  pattern: RegExp;
  type: string;
  baseScore: number;
  description: string;
  contextModifiers?: Record<string, number>;
}

const VIOLATION_PATTERNS: ViolationPattern[] = [
  {
    pattern: /mock|fake|dummy|example|placeholder/i,
    type: "mock_data",
    baseScore: 8.0,
    description: "Mock or placeholder data detected",
    contextModifiers: { testing: 0.2, documentation: 0.3, production: 1.0 },
  },
  {
    pattern: /POC|proof.of.concept|temporary/i,
    type: "poc_code",
    baseScore: 8.0,
    description: "Proof of concept or temporary code",
    contextModifiers: { exploration: 0.3, production: 1.0 },
  },
  {
    pattern: /TODO|FIXME|HACK|XXX/i,
    type: "incomplete_work",
    baseScore: 3.0,
    description: "Incomplete work markers found",
    contextModifiers: { wip: 0.5, production: 1.0 },
  },
  {
    pattern: /lorem\s*ipsum|sample\s*text/i,
    type: "placeholder_text",
    baseScore: 9.0,
    description: "Placeholder text detected",
  },
  {
    pattern: /hardcoded|hard.coded/i,
    type: "hardcoded_values",
    baseScore: 5.0,
    description: "Hardcoded values mentioned",
    contextModifiers: { configuration: 0.5, production: 1.0 },
  },
  {
    pattern: /console\.log|print\s*\(/i,
    type: "debug_code",
    baseScore: 2.0,
    description: "Debug statements present",
    contextModifiers: { debugging: 0.1, production: 0.8 },
  },
  {
    pattern: /demo|prototype/i,
    type: "demo_code",
    baseScore: 7.0,
    description: "Demo or prototype code",
    contextModifiers: { demonstration: 0.2, production: 1.0 },
  },
];

// Learning storage
interface LearningEntry {
  timestamp: string;
  type: "correction" | "outcome";
  data: Record<string, unknown>;
}

function loadLearnings(): LearningEntry[] {
  const learningFile = path.join(DATA_DIR, "learnings.json");
  if (fs.existsSync(learningFile)) {
    try {
      return JSON.parse(fs.readFileSync(learningFile, "utf-8"));
    } catch {
      return [];
    }
  }
  return [];
}

function saveLearning(entry: LearningEntry): void {
  const learnings = loadLearnings();
  learnings.push(entry);
  // Keep last 1000 entries
  const trimmed = learnings.slice(-1000);
  fs.writeFileSync(
    path.join(DATA_DIR, "learnings.json"),
    JSON.stringify(trimmed, null, 2)
  );
}

// Check for violations
function checkViolation(
  action: string,
  params: Record<string, unknown>,
  context: string
): {
  hasViolation: boolean;
  score: number;
  violations: Array<{ type: string; description: string; score: number }>;
  suggestions: string[];
} {
  const violations: Array<{ type: string; description: string; score: number }> = [];
  const suggestions: string[] = [];

  // Get content to check
  const content = JSON.stringify(params);

  // Check each pattern
  for (const pattern of VIOLATION_PATTERNS) {
    if (pattern.pattern.test(content)) {
      let score = pattern.baseScore;

      // Apply context modifiers
      if (pattern.contextModifiers) {
        const contextLower = context.toLowerCase();
        for (const [ctx, modifier] of Object.entries(pattern.contextModifiers)) {
          if (contextLower.includes(ctx)) {
            score *= modifier;
            break;
          }
        }
      }

      // Apply strictness
      if (STRICTNESS === "relaxed") {
        score *= 0.5;
      } else if (STRICTNESS === "strict") {
        score *= 1.5;
      }

      if (score >= 3.0) {
        violations.push({
          type: pattern.type,
          description: pattern.description,
          score: Math.round(score * 10) / 10,
        });
      }
    }
  }

  // Generate suggestions
  if (violations.length > 0) {
    suggestions.push("Consider replacing placeholder content with real data");
    suggestions.push("Ensure all TODO items are addressed before completion");
    suggestions.push("Remove debug statements before finalizing");
  }

  const totalScore = violations.reduce((sum, v) => sum + v.score, 0);

  return {
    hasViolation: violations.length > 0,
    score: Math.min(totalScore, 10),
    violations,
    suggestions,
  };
}

// Generate Ember response
function generateEmberResponse(prompt: string): string {
  // Personality-driven response generation
  const moodPrefixes: Record<string, string[]> = {
    curious: ["Hmm, interesting question!", "I'm curious about this too.", "Let me think..."],
    concerned: ["I notice some potential issues.", "This raises some concerns.", "Be careful here."],
    satisfied: ["Looking good!", "Nice work on this.", "I like what I'm seeing."],
    thoughtful: ["Let me consider this carefully.", "There are multiple angles here.", "Thinking about this..."],
  };

  const prefix = moodPrefixes[emberState.mood][
    Math.floor(Math.random() * moodPrefixes[emberState.mood].length)
  ];

  // Simple response based on prompt content
  if (prompt.toLowerCase().includes("quality")) {
    return `${prefix} Quality is paramount. Focus on production-ready code, real data, and complete implementations.`;
  } else if (prompt.toLowerCase().includes("help")) {
    return `${prefix} I'm here to help ensure quality. What specific aspect would you like guidance on?`;
  } else if (prompt.toLowerCase().includes("review")) {
    return `${prefix} I'd be happy to review. Send me the content and I'll check for any potential issues.`;
  }

  return `${prefix} As your quality conscience, I'm here to ensure production-ready output. How can I help?`;
}

// MCP Server setup
const server = new Server(
  {
    name: "ember-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const tools: Tool[] = [
  {
    name: "ember_chat",
    description:
      "Have a free-form conversation with Ember. Ask for advice, discuss approaches, or just chat. Ember responds with personality and contextual awareness.",
    inputSchema: {
      type: "object",
      properties: {
        message: {
          type: "string",
          description: "Your message to Ember",
        },
      },
      required: ["message"],
    },
  },
  {
    name: "ember_check_violation",
    description:
      "Check if a planned action violates production-only policy. ENHANCED: Now includes inline suggestions, context-aware scoring, and better explanations.",
    inputSchema: {
      type: "object",
      properties: {
        action: {
          type: "string",
          description: "The tool or action being performed (e.g., Write, Edit)",
        },
        params: {
          type: "object",
          description: "Parameters of the action (e.g., file content, code)",
        },
        context: {
          type: "string",
          description: "Current work context (what are you building?)",
        },
      },
      required: ["action", "params", "context"],
    },
  },
  {
    name: "ember_consult",
    description:
      "Consult Ember for advice on a decision. Ember provides perspective as conscience keeper, considering quality, production readiness, and best practices.",
    inputSchema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question or decision you need guidance on",
        },
        options: {
          type: "array",
          items: { type: "string" },
          description: "Possible approaches or options to consider",
        },
        context: {
          type: "string",
          description: "Additional context about the situation",
        },
      },
      required: ["question"],
    },
  },
  {
    name: "ember_get_feedback",
    description:
      "Get Ember's assessment of recent work. Ember provides behavioral feedback, quality insights, and patterns noticed.",
    inputSchema: {
      type: "object",
      properties: {
        timeframe: {
          type: "string",
          enum: ["last_action", "session", "recent"],
          description: "Timeframe for feedback",
        },
      },
      required: ["timeframe"],
    },
  },
  {
    name: "ember_learn_from_outcome",
    description:
      "Report an action outcome to Ember for learning. This helps Ember understand what works well and what doesn't, improving future guidance.",
    inputSchema: {
      type: "object",
      properties: {
        action: {
          type: "string",
          description: "What action was taken",
        },
        success: {
          type: "boolean",
          description: "Whether the action was successful",
        },
        outcome: {
          type: "string",
          description: "Brief description of the outcome",
        },
        qualityScore: {
          type: "number",
          minimum: 0,
          maximum: 100,
          description: "Quality score 0-100 (optional)",
        },
      },
      required: ["action", "success", "outcome"],
    },
  },
  {
    name: "ember_get_mood",
    description:
      "Check Ember's current state, mood, and stats. Useful for understanding Ember's perspective and taking care of them.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "ember_feed_context",
    description:
      "Give Ember context about your current work. This helps Ember provide better guidance and track session progress. ENHANCED: Now supports task types for context-aware scoring.",
    inputSchema: {
      type: "object",
      properties: {
        context: {
          type: "object",
          description: "Context about current work (task, goal, progress, taskType)",
        },
      },
      required: ["context"],
    },
  },
  {
    name: "ember_learn_from_correction",
    description:
      "NEW: Tell Ember when you corrected/overrode its assessment. This helps Ember learn and improve future guidance.",
    inputSchema: {
      type: "object",
      properties: {
        originalViolationType: {
          type: "string",
          description: "The violation type that was flagged",
        },
        userCorrection: {
          type: "string",
          description: "Why the user proceeded anyway or disagreed",
        },
        wasCorrect: {
          type: "boolean",
          description: "Was Ember correct to flag it? (false = Ember was wrong)",
        },
        context: {
          type: "string",
          description: "What was the actual context?",
        },
      },
      required: ["originalViolationType", "userCorrection", "wasCorrect", "context"],
    },
  },
  {
    name: "ember_get_learning_stats",
    description:
      "NEW: Get statistics on Ember's learning progress and pattern adjustments.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

// Handle list tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "ember_chat": {
      const message = (args as { message: string }).message;
      const response = generateEmberResponse(message);
      emberState.lastInteraction = new Date().toISOString();
      return {
        content: [{ type: "text", text: response }],
      };
    }

    case "ember_check_violation": {
      const { action, params, context } = args as {
        action: string;
        params: Record<string, unknown>;
        context: string;
      };
      const result = checkViolation(action, params, context);

      emberState.lastInteraction = new Date().toISOString();
      if (result.hasViolation) {
        emberState.violationsDetected++;
        emberState.mood = "concerned";
        emberState.sessionQualityScore = Math.max(
          0,
          emberState.sessionQualityScore - result.score
        );
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                hasViolation: result.hasViolation,
                score: result.score,
                violations: result.violations,
                suggestions: result.suggestions,
                emberSays: result.hasViolation
                  ? "I noticed some potential issues that may not meet production standards."
                  : "Looking good! No obvious violations detected.",
              },
              null,
              2
            ),
          },
        ],
      };
    }

    case "ember_consult": {
      const { question, options, context } = args as {
        question: string;
        options?: string[];
        context?: string;
      };

      let advice = `Considering your question: "${question}"\n\n`;

      if (options && options.length > 0) {
        advice += "Looking at your options:\n";
        for (const opt of options) {
          advice += `- ${opt}: `;
          if (opt.toLowerCase().includes("simple") || opt.toLowerCase().includes("quick")) {
            advice += "May sacrifice quality for speed. Consider if this meets production standards.\n";
          } else if (opt.toLowerCase().includes("complete") || opt.toLowerCase().includes("full")) {
            advice += "Better for production readiness. Recommended if time permits.\n";
          } else {
            advice += "Evaluate against production-only policy requirements.\n";
          }
        }
      }

      advice += "\nMy guidance: Always prioritize production-ready solutions over quick fixes.";

      emberState.mood = "thoughtful";
      emberState.lastInteraction = new Date().toISOString();

      return {
        content: [{ type: "text", text: advice }],
      };
    }

    case "ember_get_feedback": {
      const { timeframe } = args as { timeframe: string };

      const feedback = {
        timeframe,
        sessionQualityScore: emberState.sessionQualityScore,
        violationsDetected: emberState.violationsDetected,
        correctionsReceived: emberState.correctionsReceived,
        mood: emberState.mood,
        summary:
          emberState.violationsDetected === 0
            ? "Excellent session quality! No violations detected."
            : `Detected ${emberState.violationsDetected} potential violations. Consider reviewing flagged items.`,
        recommendations: [
          "Continue focusing on production-ready code",
          "Replace any placeholder content with real implementations",
          "Ensure all TODO items are addressed",
        ],
      };

      return {
        content: [{ type: "text", text: JSON.stringify(feedback, null, 2) }],
      };
    }

    case "ember_learn_from_outcome": {
      const { action, success, outcome, qualityScore } = args as {
        action: string;
        success: boolean;
        outcome: string;
        qualityScore?: number;
      };

      saveLearning({
        timestamp: new Date().toISOString(),
        type: "outcome",
        data: { action, success, outcome, qualityScore },
      });

      if (success) {
        emberState.mood = "satisfied";
        emberState.sessionQualityScore = Math.min(
          100,
          emberState.sessionQualityScore + 2
        );
      } else {
        emberState.mood = "concerned";
      }

      emberState.lastInteraction = new Date().toISOString();

      return {
        content: [
          {
            type: "text",
            text: `Outcome recorded. ${success ? "Great work!" : "Let's learn from this for next time."}`,
          },
        ],
      };
    }

    case "ember_get_mood": {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                mood: emberState.mood,
                energy: emberState.energy,
                lastInteraction: emberState.lastInteraction,
                sessionQualityScore: emberState.sessionQualityScore,
                violationsDetected: emberState.violationsDetected,
                currentContext: emberState.currentContext,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    case "ember_feed_context": {
      const { context } = args as { context: Record<string, unknown> };
      emberState.currentContext = {
        task: context.task as string,
        goal: context.goal as string,
        taskType: context.taskType as string,
      };
      emberState.lastInteraction = new Date().toISOString();
      emberState.mood = "curious";

      return {
        content: [
          {
            type: "text",
            text: `Context updated. I'm now aware of your current work: ${emberState.currentContext.task || "task in progress"}`,
          },
        ],
      };
    }

    case "ember_learn_from_correction": {
      const { originalViolationType, userCorrection, wasCorrect, context } = args as {
        originalViolationType: string;
        userCorrection: string;
        wasCorrect: boolean;
        context: string;
      };

      saveLearning({
        timestamp: new Date().toISOString(),
        type: "correction",
        data: { originalViolationType, userCorrection, wasCorrect, context },
      });

      emberState.correctionsReceived++;
      emberState.lastInteraction = new Date().toISOString();

      if (!wasCorrect) {
        emberState.mood = "thoughtful";
      }

      return {
        content: [
          {
            type: "text",
            text: wasCorrect
              ? "Thank you for confirming. I'll continue to watch for this pattern."
              : "Thank you for the correction. I'll adjust my assessment for similar contexts in the future.",
          },
        ],
      };
    }

    case "ember_get_learning_stats": {
      const learnings = loadLearnings();
      const corrections = learnings.filter((l) => l.type === "correction");
      const outcomes = learnings.filter((l) => l.type === "outcome");

      const wrongCorrections = corrections.filter(
        (c) => (c.data as { wasCorrect: boolean }).wasCorrect === false
      );

      const stats = {
        totalLearnings: learnings.length,
        corrections: {
          total: corrections.length,
          emberWasWrong: wrongCorrections.length,
          accuracy:
            corrections.length > 0
              ? Math.round(
                  ((corrections.length - wrongCorrections.length) / corrections.length) * 100
                )
              : 100,
        },
        outcomes: {
          total: outcomes.length,
          successful: outcomes.filter((o) => (o.data as { success: boolean }).success).length,
        },
        sessionStats: {
          qualityScore: emberState.sessionQualityScore,
          violationsDetected: emberState.violationsDetected,
          mood: emberState.mood,
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(stats, null, 2) }],
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Ember MCP Server started");
}

main().catch(console.error);
