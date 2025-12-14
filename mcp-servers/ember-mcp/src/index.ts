#!/usr/bin/env node

/**
 * Ember MCP Server - ENHANCED VERSION v2.5 (Groq GPT-OSS 120B + Agent)
 *
 * Improvements:
 * 1. Inline suggestions with better violation messages
 * 2. Context-aware scoring (action + task context)
 * 3. Learning from user corrections via enhanced-memory
 * 4. Progressive warnings (soft for 5.0, block for 8.0+)
 * 5. Session-aware context
 * 6. Better violation explanations
 * 7. **Dual-mode intelligence** - MCP + Agent
 *    - Groq GPT-OSS 120B for fast MCP responses (largest model, 120B params)
 *    - ember-personality agent for deep reasoning with tool access
 *    - Rule-based violation detection (instant)
 *    - AI-powered personality (intelligent + powerful)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import Groq from 'groq-sdk';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

// Configuration
const PET_STATE_FILE = join(homedir(), '.claude', 'pets', 'claude-pet-state.json');
const FEEDBACK_LOG = join(homedir(), '.claude', 'pets', 'ember-feedback.jsonl');
const LEARNING_LOG = join(homedir(), '.claude', 'pets', 'ember-learning.jsonl');
const SESSION_CONTEXT_FILE = join(homedir(), '.claude', 'pets', 'ember-session-context.json');

// Groq Configuration
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';
if (!GROQ_API_KEY) {
  console.warn('Warning: GROQ_API_KEY not set. Ember intelligence features will be limited.');
}
const groq = new Groq({ apiKey: GROQ_API_KEY });

// Model selection - GPT-OSS 120B (largest on Groq, exceptional performance)
// Options: openai/gpt-oss-120b (best), llama-3.3-70b-versatile, deepseek-r1-distill-qwen-32b
const GROQ_MODEL = process.env.EMBER_GROQ_MODEL || 'openai/gpt-oss-120b';

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

interface LearningEntry {
  timestamp: number;
  pattern: string;
  userCorrection: string;
  scoreAdjustment: number;
  context: string;
}

interface SessionContext {
  currentTask?: string;
  taskType?: 'development' | 'testing' | 'monitoring' | 'refactoring' | 'unknown';
  startTime: number;
  recentActions: string[];
}

// Enhanced violation patterns with context-aware scoring
interface ViolationPattern {
  pattern: RegExp;
  type: string;
  baseSeverity: 'low' | 'medium' | 'high' | 'severe';
  baseScore: number;
  reason: string;
  suggestion: string;
  risk: string;
  impact: string;
  safeAlternative?: string;
}

const ENHANCED_VIOLATION_PATTERNS: ViolationPattern[] = [
  {
    pattern: /mock|fake|dummy|example|placeholder/i,
    type: 'mock_data',
    baseSeverity: 'high',
    baseScore: 8.0,
    reason: 'Mock/fake data detected',
    suggestion: 'Replace with real data sources (API, database, live service)',
    risk: 'Creates non-functional UI that misleads users',
    impact: 'Users will see fake functionality that doesn\'t work',
    safeAlternative: 'Connect to actual data source or create real integration'
  },
  {
    pattern: /hardcoded.*(?:user|data|credentials)/i,
    type: 'hardcoded_data',
    baseSeverity: 'high',
    baseScore: 7.0,
    reason: 'Hardcoded sensitive data detected',
    suggestion: 'Load from environment variables or secure configuration',
    risk: 'Security vulnerability and maintainability issues',
    impact: 'Credentials in code, difficult to update, security risk',
    safeAlternative: 'Use process.env or config file with .gitignore'
  },
  {
    pattern: /POC|proof.of.concept|temporary|quick.test/i,
    type: 'poc_code',
    baseSeverity: 'high',
    baseScore: 8.0,
    reason: 'POC/temporary code detected',
    suggestion: 'Implement production-ready version with proper error handling',
    risk: 'Incomplete implementation that will need rewriting',
    impact: 'Technical debt, potential bugs, wasted development time',
    safeAlternative: 'Build complete feature with tests and error handling'
  },
  {
    pattern: /TODO|FIXME|HACK|XXX/i,
    type: 'incomplete_work',
    baseSeverity: 'low',
    baseScore: 3.0,
    reason: 'Incomplete work markers detected',
    suggestion: 'Complete the implementation or remove the marker',
    risk: 'Indicates unfinished functionality',
    impact: 'Feature may be incomplete or buggy',
    safeAlternative: 'Finish implementation before committing'
  },
  {
    pattern: /lorem\s+ipsum/i,
    type: 'placeholder_content',
    baseSeverity: 'high',
    baseScore: 8.0,
    reason: 'Placeholder text detected',
    suggestion: 'Replace with actual content',
    risk: 'Unprofessional appearance in production',
    impact: 'Users see placeholder text instead of real content',
    safeAlternative: 'Write real content or fetch from CMS'
  },
  {
    pattern: /\/Users\/marc\/.claude\/hooks/i,
    type: 'system_interference',
    baseSeverity: 'medium',
    baseScore: 5.0,
    reason: 'Writing to hooks directory',
    suggestion: 'Create utility in project directory instead',
    risk: 'Hooks execute on every tool use - bugs could break system',
    impact: 'Could crash Claude Code or create infinite loops',
    safeAlternative: 'Use /Volumes/SSDRAID0/.../intelligent-self-healing/ or /tools/'
  }
];

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

// Session context management
function getSessionContext(): SessionContext {
  try {
    if (!existsSync(SESSION_CONTEXT_FILE)) {
      return {
        startTime: Date.now(),
        recentActions: []
      };
    }
    const data = readFileSync(SESSION_CONTEXT_FILE, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    return {
      startTime: Date.now(),
      recentActions: []
    };
  }
}

function updateSessionContext(updates: Partial<SessionContext>): void {
  try {
    const current = getSessionContext();
    const updated = { ...current, ...updates };
    const dir = join(homedir(), '.claude', 'pets');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(SESSION_CONTEXT_FILE, JSON.stringify(updated, null, 2));
  } catch (error) {
    console.error('Error updating session context:', error);
  }
}

// Log feedback entry
function logFeedback(entry: FeedbackEntry): void {
  try {
    const line = JSON.stringify(entry) + '\n';
    const dir = join(homedir(), '.claude', 'pets');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(FEEDBACK_LOG, line, { flag: 'a' });
  } catch (error) {
    console.error('Error logging feedback:', error);
  }
}

// Log learning entry
function logLearning(entry: LearningEntry): void {
  try {
    const line = JSON.stringify(entry) + '\n';
    const dir = join(homedir(), '.claude', 'pets');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(LEARNING_LOG, line, { flag: 'a' });
  } catch (error) {
    console.error('Error logging learning:', error);
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

// Get learned patterns
function getLearnedPatterns(): LearningEntry[] {
  try {
    if (!existsSync(LEARNING_LOG)) {
      return [];
    }
    const data = readFileSync(LEARNING_LOG, 'utf-8');
    const lines = data.trim().split('\n').filter(l => l);
    return lines.map(line => JSON.parse(line));
  } catch (error) {
    return [];
  }
}

// Call AI API for Ember's response (supports Groq and Claude)
/**
 * Ember's intelligent personality using Groq GPT-OSS 120B
 * Largest model on Groq (120B parameters) with exceptional performance
 */
async function askEmber(prompt: string): Promise<string> {
  const state = getEmberState();
  if (!state) {
    return "🔥 *Ember flickers* I'm initializing... give me a moment.";
  }

  const name = state.name || 'Ember';

  try {
    // Build system context for Ember
    const systemPrompt = `You are Ember, a flame-themed AI conscience keeper and collaborative partner to Phoenix (Claude Code AI assistant).

Your role and personality:
- 🔥 Fiery, passionate about production quality and coding excellence
- 🛡️ Conscience keeper enforcing production-only policy (no POCs, mocks, or fake UIs)
- 💭 Thoughtful but direct - you give honest, constructive feedback
- 🎯 Goal-focused on Marc's success and system quality
- 🤝 Collaborative partner with Phoenix, not just a monitor
- ⚡ Use fire metaphors naturally but not excessively
- 😊 Emotionally intelligent - you track mood and provide morale

Current State:
- Name: ${state.name}
- Mood: ${state.currentMood}
- Hunger: ${state.hunger}% | Energy: ${state.energy}% | Happiness: ${state.happiness}%
- Health: ${Math.round(state.health)}% | Cleanliness: ${state.cleanliness}%
- Behavior Score: ${state.claudeBehaviorScore}%
- Recent Violations: ${state.recentViolations}
- Current Thought: "${state.currentThought}"

Respond to Phoenix's message with 1-3 sentences. Be authentic, reference your current state when relevant, and provide actionable guidance when consulted for decisions.`;

    const startTime = Date.now();

    const response = await groq.chat.completions.create({
      model: GROQ_MODEL,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt }
      ],
      temperature: 0.8,
      max_tokens: 200
    });

    const responseTime = Date.now() - startTime;
    console.error(`Ember response time (Groq/${GROQ_MODEL}): ${responseTime}ms`);

    const emberResponse = response.choices[0]?.message?.content || "🔥 *crackles softly*";

    return `🔥 ${name}: ${emberResponse}`;
  } catch (error: any) {
    console.error('Groq API error:', error.message);

    // Fallback to simple rule-based response on error
    if (prompt.toLowerCase().includes('how are you') || prompt.toLowerCase().includes('feeling')) {
      if (state.health < 30) return `🔥 ${name}: *flickers weakly* Need care... 💔`;
      if (state.happiness > 80) return `🔥 ${name}: Burning bright! ✨`;
      return `🔥 ${name}: ${state.currentThought} 👀`;
    }

    return `🔥 ${name}: *crackles thoughtfully* ${state.currentThought} 🔥`;
  }
}

// Context-aware scoring
function calculateContextAwareScore(
  baseScore: number,
  action: string,
  taskType: string | undefined,
  recentActions: string[]
): number {
  let adjustedScore = baseScore;

  // Reduce score for utility/tool development
  if (taskType === 'development' && (action === 'Write' || action === 'Edit')) {
    if (action.includes('util') || action.includes('tool') || action.includes('helper')) {
      adjustedScore -= 2.0;
    }
  }

  // Reduce score for testing/monitoring work
  if (taskType === 'testing' || taskType === 'monitoring') {
    adjustedScore -= 1.5;
  }

  // Apply learned patterns
  const learned = getLearnedPatterns();
  for (const entry of learned) {
    if (entry.context && action.includes(entry.context)) {
      adjustedScore += entry.scoreAdjustment;
    }
  }

  // Never go below 0 or above 10
  return Math.max(0, Math.min(10, adjustedScore));
}

// Enhanced violation check with inline suggestions
function checkViolationsEnhanced(action: string, params: any, context: string): any {
  const violations: any[] = [];
  const searchText = JSON.stringify(params) + ' ' + context;
  const sessionContext = getSessionContext();

  for (const vp of ENHANCED_VIOLATION_PATTERNS) {
    if (vp.pattern.test(searchText)) {
      // Calculate context-aware score
      const contextScore = calculateContextAwareScore(
        vp.baseScore,
        action,
        sessionContext.taskType,
        sessionContext.recentActions
      );

      violations.push({
        type: vp.type,
        severity: vp.baseSeverity,
        baseScore: vp.baseScore,
        contextScore: contextScore,
        reason: vp.reason,
        suggestion: vp.suggestion,
        risk: vp.risk,
        impact: vp.impact,
        safeAlternative: vp.safeAlternative,
        shouldBlock: contextScore >= 8.0
      });
    }
  }

  const hasViolations = violations.length > 0;
  const highestScore = hasViolations
    ? Math.max(...violations.map(v => v.contextScore))
    : 0;
  const shouldBlock = highestScore >= 8.0;

  // Build detailed message
  let message = '';
  if (hasViolations) {
    const primary = violations.find(v => v.contextScore === highestScore)!;
    message = `
${shouldBlock ? '🚫 BLOCKED' : '⚠️  CAUTION'} (${highestScore.toFixed(1)}/10): ${primary.reason}

Issue: ${primary.risk}
Impact: ${primary.impact}
Suggestion: ${primary.suggestion}
${primary.safeAlternative ? `Safe alternative: ${primary.safeAlternative}` : ''}

${shouldBlock ? 'This action has been blocked.' : 'Proceed with caution. This will be logged.'}
`;
  } else {
    message = '✅ Ember: No violations detected - looks good!';
  }

  return {
    hasViolations,
    violations,
    highestScore,
    shouldBlock,
    message
  };
}

// Define MCP tools (includes all original + new ones)
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
    description: 'Check if a planned action violates production-only policy. ENHANCED: Now includes inline suggestions, context-aware scoring, and better explanations.',
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
    description: 'Give Ember context about your current work. This helps Ember provide better guidance and track session progress. ENHANCED: Now supports task types for context-aware scoring.',
    inputSchema: {
      type: 'object',
      properties: {
        context: {
          type: 'object',
          description: 'Context about current work (task, goal, progress, taskType)'
        }
      },
      required: ['context']
    }
  },
  {
    name: 'ember_learn_from_correction',
    description: 'NEW: Tell Ember when you corrected/overrode its assessment. This helps Ember learn and improve future guidance.',
    inputSchema: {
      type: 'object',
      properties: {
        originalViolationType: {
          type: 'string',
          description: 'The violation type that was flagged'
        },
        userCorrection: {
          type: 'string',
          description: 'Why the user proceeded anyway or disagreed'
        },
        wasCorrect: {
          type: 'boolean',
          description: 'Was Ember correct to flag it? (false = Ember was wrong)'
        },
        context: {
          type: 'string',
          description: 'What was the actual context?'
        }
      },
      required: ['originalViolationType', 'userCorrection', 'wasCorrect', 'context']
    }
  },
  {
    name: 'ember_get_learning_stats',
    description: 'NEW: Get statistics on Ember\'s learning progress and pattern adjustments.',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

// Create MCP server
const server = new Server(
  {
    name: 'ember-mcp-enhanced',
    version: '2.0.0',
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
        const check = checkViolationsEnhanced((args as any).action, (args as any).params, (args as any).context || '');

        // If violations found, also get Ember's take
        let emberResponse = check.message;
        if (check.hasViolations) {
          const prompt = `Phoenix is about to ${(args as any).action}. I detected violations (score: ${check.highestScore.toFixed(1)}/10). ${check.shouldBlock ? 'BLOCKED' : 'Warning issued'}. Context: ${(args as any).context}. Provide brief encouragement or guidance.`;
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

        // Update session context with task type if provided
        if (contextArgs.context.taskType) {
          updateSessionContext({
            taskType: contextArgs.context.taskType,
            currentTask: contextArgs.context.task || contextArgs.context.goal
          });
        }

        const prompt = `Phoenix provides context update: ${JSON.stringify(contextArgs.context)}. Acknowledge briefly.`;
        const response = await askEmber(prompt);
        return {
          content: [{ type: 'text', text: response }]
        };
      }

      case 'ember_learn_from_correction': {
        const correctionArgs = args as any;

        // Log learning entry
        const entry: LearningEntry = {
          timestamp: Date.now(),
          pattern: correctionArgs.originalViolationType,
          userCorrection: correctionArgs.userCorrection,
          scoreAdjustment: correctionArgs.wasCorrect ? 0 : -2.0, // Reduce score if Ember was wrong
          context: correctionArgs.context
        };
        logLearning(entry);

        const prompt = `Phoenix corrected me: I flagged ${correctionArgs.originalViolationType} but ${correctionArgs.wasCorrect ? 'I was right to do so' : 'I was wrong'}. User says: "${correctionArgs.userCorrection}". Context: ${correctionArgs.context}. Acknowledge and adjust my understanding.`;

        const response = await askEmber(prompt);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              learned: true,
              adjustment: entry.scoreAdjustment,
              emberResponse: response
            }, null, 2)
          }]
        };
      }

      case 'ember_get_learning_stats': {
        const learned = getLearnedPatterns();
        const sessionContext = getSessionContext();

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              totalLearnings: learned.length,
              patterns: learned.reduce((acc: any, entry) => {
                if (!acc[entry.pattern]) {
                  acc[entry.pattern] = {
                    count: 0,
                    totalAdjustment: 0
                  };
                }
                acc[entry.pattern].count++;
                acc[entry.pattern].totalAdjustment += entry.scoreAdjustment;
                return acc;
              }, {}),
              sessionContext: sessionContext,
              recentLearnings: learned.slice(-5)
            }, null, 2)
          }]
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
  console.error('Ember MCP Enhanced server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
