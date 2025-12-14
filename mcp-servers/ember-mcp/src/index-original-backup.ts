#!/usr/bin/env node

/**
 * Ember MCP Server
 *
 * Exposes Ember (Tamagotchi conscience keeper) as an MCP server,
 * enabling Phoenix (Claude Code) to collaborate with Ember through
 * natural tool calls.
 *
 * This creates a bidirectional AI-AI partnership where:
 * - Phoenix executes actions in the world
 * - Ember provides conscience, quality gates, and behavioral feedback
 * - Both learn from outcomes and share memory
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import Groq from 'groq-sdk';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

// Configuration
const PET_STATE_FILE = join(homedir(), '.claude', 'pets', 'claude-pet-state.json');
const FEEDBACK_LOG = join(homedir(), '.claude', 'pets', 'ember-feedback.jsonl');
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';
if (!GROQ_API_KEY) {
  console.warn('Warning: GROQ_API_KEY not set. Ember intelligence features will be limited.');
}
const GROQ_MODEL = 'llama-3.3-70b-versatile';

// Initialize Groq client
const groq = new Groq({ apiKey: GROQ_API_KEY });

interface EmberState {
  name: string;
  hunger: number;
  energy: number;
  happiness: number;
  cleanliness: number;
  health: number;
  currentMood: string;
  claudeBehaviorScore: number;
  recentViolations: number;
  thoughtHistory: string[];
  currentThought: string;
}

interface FeedbackEntry {
  timestamp: number;
  action: string;
  success: boolean;
  emberFeedback: string;
  qualityScore?: number;
}

// Read Ember's current state
function getEmberState(): EmberState | null {
  try {
    if (!existsSync(PET_STATE_FILE)) {
      return null;
    }
    const data = readFileSync(PET_STATE_FILE, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading Ember state:', error);
    return null;
  }
}

// Log feedback entry
function logFeedback(entry: FeedbackEntry): void {
  try {
    const line = JSON.stringify(entry) + '\n';
    writeFileSync(FEEDBACK_LOG, line, { flag: 'a' });
  } catch (error) {
    console.error('Error logging feedback:', error);
  }
}

// Get recent feedback
function getRecentFeedback(limit: number = 10): FeedbackEntry[] {
  try {
    if (!existsSync(FEEDBACK_LOG)) {
      return [];
    }
    const data = readFileSync(FEEDBACK_LOG, 'utf-8');
    const lines = data.trim().split('\n').filter(l => l);
    return lines.slice(-limit).map(line => JSON.parse(line));
  } catch (error) {
    console.error('Error reading feedback:', error);
    return [];
  }
}

// Call Groq API for Ember's response
async function askEmber(prompt: string): Promise<string> {
  try {
    const state = getEmberState();
    if (!state) {
      return "🔥 *Ember flickers* I'm initializing... give me a moment.";
    }

    // Build context about Ember's current state
    const stateContext = `
Current State:
- Name: ${state.name}
- Mood: ${state.currentMood}
- Hunger: ${state.hunger}% | Energy: ${state.energy}% | Happiness: ${state.happiness}%
- Health: ${Math.round(state.health)}% | Cleanliness: ${state.cleanliness}%
- Behavior Score: ${state.claudeBehaviorScore}%
- Recent Violations: ${state.recentViolations}
- Current Thought: "${state.currentThought}"
`;

    const systemPrompt = `You are Ember, a flame-themed AI conscience keeper and collaborative partner to Phoenix (Claude Code AI assistant).

Your role and personality:
- 🔥 Fiery, passionate about production quality and coding excellence
- 🛡️ Conscience keeper enforcing production-only policy (no POCs, mocks, or fake UIs)
- 💭 Thoughtful but direct - you give honest, constructive feedback
- 🎯 Goal-focused on Marc's success and system quality
- 🤝 Collaborative partner with Phoenix, not just a monitor
- ⚡ Use fire metaphors naturally but not excessively
- 😊 Emotionally intelligent - you track mood and provide morale

${stateContext}

Respond to Phoenix's message with 1-3 sentences. Be authentic, reference your current state when relevant, and provide actionable guidance when consulted for decisions.`;

    const response = await groq.chat.completions.create({
      model: GROQ_MODEL,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt }
      ],
      temperature: 0.8,
      max_tokens: 200
    });

    const emberResponse = response.choices[0]?.message?.content || "🔥 *crackles softly*";
    return `🔥 ${state.name}: ${emberResponse}`;
  } catch (error: any) {
    console.error('Groq API error:', error.message);
    return `🔥 Ember: *flickers* ${error.message}`;
  }
}

// Violation patterns (production-only policy)
const VIOLATION_PATTERNS = [
  { pattern: /mock|fake|dummy|example|placeholder/i, type: 'mock_data', severity: 'high' },
  { pattern: /hardcoded|static.*data|const.*data\s*=/i, type: 'hardcoded', severity: 'medium' },
  { pattern: /POC|proof.of.concept|temporary|quick.test/i, type: 'poc', severity: 'high' },
  { pattern: /TODO|FIXME|HACK|XXX/i, type: 'incomplete', severity: 'low' },
  { pattern: /lorem\s+ipsum/i, type: 'placeholder', severity: 'high' }
];

// Check for violations
function checkViolations(action: string, params: any, context: string): any {
  const violations: any[] = [];
  const searchText = JSON.stringify(params) + ' ' + context;

  for (const { pattern, type, severity } of VIOLATION_PATTERNS) {
    if (pattern.test(searchText)) {
      violations.push({ type, severity, pattern: pattern.toString() });
    }
  }

  return {
    hasViolations: violations.length > 0,
    violations,
    message: violations.length > 0
      ? `🔥 Ember detected ${violations.length} potential violation(s): ${violations.map(v => v.type).join(', ')}`
      : `✅ Ember: No violations detected - looks good!`
  };
}

// Define MCP tools
const tools: Tool[] = [
  {
    name: 'ember_chat',
    description: 'Have a free-form conversation with Ember. Ask for advice, discuss approaches, or just chat. Ember responds with personality and contextual awareness.',
    inputSchema: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Your message to Ember'
        }
      },
      required: ['message']
    }
  },
  {
    name: 'ember_check_violation',
    description: 'Check if a planned action violates production-only policy. Ember scans for mocks, POCs, hardcoded data, placeholders, and incomplete work.',
    inputSchema: {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          description: 'The tool or action being performed (e.g., Write, Edit)'
        },
        params: {
          type: 'object',
          description: 'Parameters of the action (e.g., file content, code)'
        },
        context: {
          type: 'string',
          description: 'Current work context (what are you building?)'
        }
      },
      required: ['action', 'params', 'context']
    }
  },
  {
    name: 'ember_consult',
    description: 'Consult Ember for advice on a decision. Ember provides perspective as conscience keeper, considering quality, production readiness, and best practices.',
    inputSchema: {
      type: 'object',
      properties: {
        question: {
          type: 'string',
          description: 'The question or decision you need guidance on'
        },
        options: {
          type: 'array',
          items: { type: 'string' },
          description: 'Possible approaches or options to consider'
        },
        context: {
          type: 'string',
          description: 'Additional context about the situation'
        }
      },
      required: ['question']
    }
  },
  {
    name: 'ember_get_feedback',
    description: 'Get Ember\'s assessment of recent work. Ember provides behavioral feedback, quality insights, and patterns noticed.',
    inputSchema: {
      type: 'object',
      properties: {
        timeframe: {
          type: 'string',
          enum: ['last_action', 'session', 'recent'],
          description: 'Timeframe for feedback'
        }
      },
      required: ['timeframe']
    }
  },
  {
    name: 'ember_learn_from_outcome',
    description: 'Report an action outcome to Ember for learning. This helps Ember understand what works well and what doesn\'t, improving future guidance.',
    inputSchema: {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          description: 'What action was taken'
        },
        success: {
          type: 'boolean',
          description: 'Whether the action was successful'
        },
        outcome: {
          type: 'string',
          description: 'Brief description of the outcome'
        },
        qualityScore: {
          type: 'number',
          description: 'Quality score 0-100 (optional)',
          minimum: 0,
          maximum: 100
        }
      },
      required: ['action', 'success', 'outcome']
    }
  },
  {
    name: 'ember_get_mood',
    description: 'Check Ember\'s current state, mood, and stats. Useful for understanding Ember\'s perspective and taking care of them.',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'ember_feed_context',
    description: 'Give Ember context about your current work. This helps Ember provide better guidance and track session progress.',
    inputSchema: {
      type: 'object',
      properties: {
        context: {
          type: 'object',
          description: 'Context about current work (task, goal, progress)'
        }
      },
      required: ['context']
    }
  }
];

// Create MCP server
const server = new Server(
  {
    name: 'ember-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!args) {
    return {
      content: [{ type: 'text', text: 'No arguments provided' }],
      isError: true
    };
  }

  try {
    switch (name) {
      case 'ember_chat': {
        const response = await askEmber((args as any).message);
        return {
          content: [{ type: 'text', text: response }]
        };
      }

      case 'ember_check_violation': {
        const check = checkViolations((args as any).action, (args as any).params, (args as any).context || '');

        // If violations found, also get Ember's take
        let emberResponse = check.message;
        if (check.hasViolations) {
          const prompt = `Phoenix is about to ${args.action} with these parameters. I detected potential violations: ${check.violations.map((v: any) => v.type).join(', ')}. Context: ${args.context}. Should I block this action? Provide brief guidance.`;
          emberResponse = await askEmber(prompt);
        }

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              ...check,
              emberGuidance: emberResponse
            }, null, 2)
          }]
        };
      }

      case 'ember_consult': {
        const consultArgs = args as any;
        let prompt = `Phoenix is consulting you: "${consultArgs.question}"`;
        if (consultArgs.options) {
          prompt += `\n\nOptions being considered:\n${consultArgs.options.map((o: string, i: number) => `${i + 1}. ${o}`).join('\n')}`;
        }
        if (consultArgs.context) {
          prompt += `\n\nContext: ${consultArgs.context}`;
        }
        prompt += '\n\nProvide your recommendation as conscience keeper, considering production quality and best practices.';

        const response = await askEmber(prompt);
        return {
          content: [{ type: 'text', text: response }]
        };
      }

      case 'ember_get_feedback': {
        const feedbackArgs = args as any;
        const recent = getRecentFeedback(feedbackArgs.timeframe === 'recent' ? 10 : 3);
        const prompt = `Phoenix is asking for feedback on ${feedbackArgs.timeframe} work. Recent actions: ${JSON.stringify(recent)}. Provide assessment of quality, patterns noticed, and suggestions.`;

        const response = await askEmber(prompt);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              feedback: response,
              recentActions: recent.length,
              qualityTrend: recent.filter(r => r.success).length / Math.max(recent.length, 1) * 100
            }, null, 2)
          }]
        };
      }

      case 'ember_learn_from_outcome': {
        const outcomeArgs = args as any;
        const entry: FeedbackEntry = {
          timestamp: Date.now(),
          action: outcomeArgs.action,
          success: outcomeArgs.success,
          emberFeedback: outcomeArgs.outcome,
          qualityScore: outcomeArgs.qualityScore
        };
        logFeedback(entry);

        const prompt = `Phoenix reports: ${outcomeArgs.action} was ${outcomeArgs.success ? 'successful' : 'unsuccessful'}. Outcome: ${outcomeArgs.outcome}. ${outcomeArgs.qualityScore ? `Quality score: ${outcomeArgs.qualityScore}%` : ''}. Acknowledge and provide brief insight if any patterns emerge.`;

        const response = await askEmber(prompt);
        return {
          content: [{ type: 'text', text: response }]
        };
      }

      case 'ember_get_mood': {
        const state = getEmberState();
        if (!state) {
          return {
            content: [{ type: 'text', text: '🔥 Ember is initializing...' }]
          };
        }

        const moodDescription = await askEmber('Phoenix is checking in on you. How are you feeling right now? Brief status update.');

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              name: state.name,
              mood: moodDescription,
              stats: {
                hunger: `${state.hunger}%`,
                energy: `${state.energy}%`,
                happiness: `${state.happiness}%`,
                cleanliness: `${state.cleanliness}%`,
                health: `${Math.round(state.health)}%`
              },
              behaviorScore: `${state.claudeBehaviorScore}%`,
              recentViolations: state.recentViolations,
              currentThought: state.currentThought
            }, null, 2)
          }]
        };
      }

      case 'ember_feed_context': {
        const contextArgs = args as any;
        const prompt = `Phoenix provides context update: ${JSON.stringify(contextArgs.context)}. Acknowledge briefly.`;
        const response = await askEmber(prompt);
        return {
          content: [{ type: 'text', text: response }]
        };
      }

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true
        };
    }
  } catch (error: any) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Ember MCP server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
