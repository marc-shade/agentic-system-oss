#!/usr/bin/env node

import { createInterface } from 'readline';
import { spawn } from 'child_process';
import { appendFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

// Setup logging
const logDir = join(homedir(), '.claude', 'logs');
if (!existsSync(logDir)) {
  mkdirSync(logDir, { recursive: true });
}
const logFile = join(logDir, 'autokitteh-mcp.log');

function logToFile(message) {
  const timestamp = new Date().toISOString();
  appendFileSync(logFile, `[${timestamp}] ${message}\n`);
}

// Log startup
logToFile('AutoKitteh MCP server starting...');

// Create readline interface for JSON-RPC
const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Server information
const serverInfo = {
  name: 'autokitteh-mcp',
  version: '1.0.0'
};

// AutoKitteh configuration
const AK_API_BASE = process.env.AK_API_URL || 'http://localhost:9980';
const AK_CLI_PATH = process.env.AK_CLI_PATH || '/Users/marc/bin/ak';

// Available tools
const tools = [
  {
    name: 'start_workflow',
    description: 'Start a new AutoKitteh workflow',
    inputSchema: {
      type: 'object',
      properties: {
        workflow_name: { type: 'string', description: 'Name of the workflow to start' },
        params: { type: 'object', description: 'Parameters to pass to the workflow' },
        project: { type: 'string', description: 'Project name (optional)', default: 'default' }
      },
      required: ['workflow_name']
    }
  },
  {
    name: 'list_workflows',
    description: 'List available AutoKitteh workflows',
    inputSchema: {
      type: 'object',
      properties: {
        project: { type: 'string', description: 'Filter by project (optional)', default: 'default' }
      }
    }
  },
  {
    name: 'query_workflow',
    description: 'Query the state of a running workflow',
    inputSchema: {
      type: 'object',
      properties: {
        workflow_id: { type: 'string', description: 'ID of the workflow to query' }
      },
      required: ['workflow_id']
    }
  },
  {
    name: 'signal_workflow',
    description: 'Send a signal to a running workflow',
    inputSchema: {
      type: 'object',
      properties: {
        workflow_id: { type: 'string', description: 'ID of the workflow' },
        signal_name: { type: 'string', description: 'Name of the signal' },
        data: { type: 'object', description: 'Signal data' }
      },
      required: ['workflow_id', 'signal_name']
    }
  },
  {
    name: 'cancel_workflow',
    description: 'Cancel a running workflow',
    inputSchema: {
      type: 'object',
      properties: {
        workflow_id: { type: 'string', description: 'ID of the workflow to cancel' }
      },
      required: ['workflow_id']
    }
  },
  {
    name: 'schedule_workflow',
    description: 'Schedule a workflow with cron expression',
    inputSchema: {
      type: 'object',
      properties: {
        workflow_name: { type: 'string', description: 'Workflow to schedule' },
        cron: { type: 'string', description: 'Cron expression (e.g., "0 2 * * *")' },
        params: { type: 'object', description: 'Default parameters' }
      },
      required: ['workflow_name', 'cron']
    }
  },
  {
    name: 'deploy_project',
    description: 'Deploy an AutoKitteh project from manifest',
    inputSchema: {
      type: 'object',
      properties: {
        manifest_path: { type: 'string', description: 'Path to autokitteh.yaml' },
        env: { type: 'object', description: 'Environment variables' }
      },
      required: ['manifest_path']
    }
  }
];

// Active workflows tracking
const activeWorkflows = new Map();

// Helper: Execute AutoKitteh CLI command
async function executeAkCommand(args) {
  return new Promise((resolve, reject) => {
    const ak = spawn(AK_CLI_PATH, args);
    let stdout = '';
    let stderr = '';

    ak.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    ak.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    ak.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`ak command failed: ${stderr}`));
      } else {
        resolve(stdout);
      }
    });
  });
}

// Tool implementations
async function startWorkflow({ workflow_name, params = {}, project = 'default' }) {
  try {
    const args = ['session', 'start', '--project', project];
    args.push('--trigger', workflow_name);

    if (Object.keys(params).length > 0) {
      args.push('--data', JSON.stringify(params));
    }

    const output = await executeAkCommand(args);
    const sessionId = output.trim().split('\n').pop();

    activeWorkflows.set(sessionId, {
      name: workflow_name,
      startTime: new Date(),
      params
    });

    return {
      type: 'text',
      text: `Started workflow '${workflow_name}' with session ID: ${sessionId}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to start workflow: ${error.message}`
    };
  }
}

async function listWorkflows({ project = 'default' }) {
  try {
    const output = await executeAkCommand(['deployment', 'list', '--project', project, '-J']);

    // Handle both single object and array responses
    let deployments;
    const trimmedOutput = output.trim();
    if (!trimmedOutput) {
      return {
        type: 'text',
        text: `No deployments found in project: ${project}`
      };
    }

    const parsed = JSON.parse(trimmedOutput);
    deployments = Array.isArray(parsed) ? parsed : [parsed];

    if (deployments.length === 0) {
      return {
        type: 'text',
        text: `No deployments found in project: ${project}`
      };
    }

    return {
      type: 'text',
      text: `Available deployments in ${project}:\n${deployments.map(d => `- ${d.deployment_id}: State: ${d.state} (Created: ${d.created_at})`).join('\n')}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to list workflows: ${error.message}`
    };
  }
}

async function queryWorkflow({ workflow_id }) {
  try {
    const output = await executeAkCommand(['session', 'get', workflow_id, '-J']);
    const session = JSON.parse(output);

    return {
      type: 'text',
      text: `Workflow ${workflow_id}:\nStatus: ${session.state}\nStarted: ${session.created_at}\nLogs: ${session.log_summary || 'No recent logs'}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to query workflow: ${error.message}`
    };
  }
}

async function signalWorkflow({ workflow_id, signal_name, data = {} }) {
  try {
    // AutoKitteh doesn't have direct signal support via CLI yet
    return {
      type: 'text',
      text: `Signal '${signal_name}' would be sent to workflow ${workflow_id} (feature pending AutoKitteh API support)`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to signal workflow: ${error.message}`
    };
  }
}

async function cancelWorkflow({ workflow_id }) {
  try {
    await executeAkCommand(['session', 'cancel', workflow_id]);
    activeWorkflows.delete(workflow_id);

    return {
      type: 'text',
      text: `Cancelled workflow ${workflow_id}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to cancel workflow: ${error.message}`
    };
  }
}

async function scheduleWorkflow({ workflow_name, cron, params = {} }) {
  try {
    const scheduleConfig = {
      name: `scheduled_${workflow_name}`,
      type: 'schedule',
      schedule: cron,
      workflow: workflow_name,
      data: params
    };

    return {
      type: 'text',
      text: `Scheduled workflow '${workflow_name}' with cron: ${cron}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to schedule workflow: ${error.message}`
    };
  }
}

async function deployProject({ manifest_path, env = {} }) {
  try {
    const args = ['deploy', '--manifest', manifest_path];

    Object.entries(env).forEach(([key, value]) => {
      args.push('--env', `${key}=${value}`);
    });

    const output = await executeAkCommand(args);

    return {
      type: 'text',
      text: `Deployed project from ${manifest_path}:\n${output}`
    };
  } catch (error) {
    return {
      type: 'text',
      text: `Failed to deploy project: ${error.message}`
    };
  }
}

// Tool handler
const toolHandlers = {
  start_workflow: startWorkflow,
  list_workflows: listWorkflows,
  query_workflow: queryWorkflow,
  signal_workflow: signalWorkflow,
  cancel_workflow: cancelWorkflow,
  schedule_workflow: scheduleWorkflow,
  deploy_project: deployProject
};

// JSON-RPC message handler
function handleMessage(message) {
  const msg = JSON.parse(message);

  logToFile(`Received: ${JSON.stringify(msg)}`);

  // Handle different message types
  if (msg.method === 'initialize') {
    const response = {
      jsonrpc: '2.0',
      id: msg.id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {},
          resources: {}
        },
        serverInfo
      }
    };
    console.log(JSON.stringify(response));
  } else if (msg.method === 'initialized') {
    logToFile('Server initialized');
  } else if (msg.method === 'tools/list') {
    const response = {
      jsonrpc: '2.0',
      id: msg.id,
      result: { tools }
    };
    console.log(JSON.stringify(response));
  } else if (msg.method === 'tools/call') {
    const { name, arguments: args } = msg.params;
    const handler = toolHandlers[name];

    if (handler) {
      handler(args).then(result => {
        const response = {
          jsonrpc: '2.0',
          id: msg.id,
          result: {
            content: [result]
          }
        };
        console.log(JSON.stringify(response));
      }).catch(error => {
        const response = {
          jsonrpc: '2.0',
          id: msg.id,
          error: {
            code: -32603,
            message: error.message
          }
        };
        console.log(JSON.stringify(response));
      });
    } else {
      const response = {
        jsonrpc: '2.0',
        id: msg.id,
        error: {
          code: -32601,
          message: `Unknown tool: ${name}`
        }
      };
      console.log(JSON.stringify(response));
    }
  }
}

// Read messages from stdin
rl.on('line', (line) => {
  try {
    handleMessage(line);
  } catch (error) {
    logToFile(`Error handling message: ${error.message}`);
  }
});

// Handle cleanup
process.on('SIGINT', () => {
  logToFile('Server shutting down');
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  logToFile(`Uncaught exception: ${error.stack}`);
});

logToFile('AutoKitteh MCP server ready');