import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import axios from 'axios';
import { spawn } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// AutoKitteh API configuration
const AK_API_BASE = process.env.AK_API_URL || 'http://localhost:9980';
const AK_CLI_PATH = process.env.AK_CLI_PATH || 'ak';

class AutoKittehMCP {
  constructor() {
    this.server = new Server(
      {
        name: 'autokitteh-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {}
        },
      }
    );

    this.setupHandlers();
    this.activeWorkflows = new Map();
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler({ method: 'tools/list' }, async () => ({
      tools: [
        {
          name: 'start_workflow',
          description: 'Start a new AutoKitteh workflow',
          inputSchema: {
            type: 'object',
            properties: {
              workflow_name: { type: 'string', description: 'Name of the workflow to start' },
              params: { type: 'object', description: 'Parameters to pass to the workflow' },
              project: { type: 'string', description: 'Project name (optional)' }
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
              project: { type: 'string', description: 'Filter by project (optional)' }
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
      ]
    }));

    // Tool call handler
    this.server.setRequestHandler({ method: 'tools/call' }, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case 'start_workflow':
          return await this.startWorkflow(args);
        case 'list_workflows':
          return await this.listWorkflows(args);
        case 'query_workflow':
          return await this.queryWorkflow(args);
        case 'signal_workflow':
          return await this.signalWorkflow(args);
        case 'cancel_workflow':
          return await this.cancelWorkflow(args);
        case 'schedule_workflow':
          return await this.scheduleWorkflow(args);
        case 'deploy_project':
          return await this.deployProject(args);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async executeAkCommand(args) {
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

  async startWorkflow({ workflow_name, params = {}, project = 'default' }) {
    try {
      // Start workflow via CLI
      const args = ['session', 'start', '--project', project];

      // Add workflow trigger
      args.push('--trigger', workflow_name);

      // Add parameters as JSON
      if (Object.keys(params).length > 0) {
        args.push('--data', JSON.stringify(params));
      }

      const output = await this.executeAkCommand(args);
      const sessionId = output.trim().split('\n').pop(); // Get session ID from output

      // Store active workflow
      this.activeWorkflows.set(sessionId, {
        name: workflow_name,
        startTime: new Date(),
        params
      });

      return {
        content: [{
          type: 'text',
          text: `Started workflow '${workflow_name}' with session ID: ${sessionId}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to start workflow: ${error.message}`
        }]
      };
    }
  }

  async listWorkflows({ project = 'default' }) {
    try {
      const output = await this.executeAkCommand(['deployment', 'list', '--project', project, '-J']);
      const deployments = JSON.parse(output);

      return {
        content: [{
          type: 'text',
          text: `Available deployments:\n${deployments.map(d => `- ${d.name}: ${d.description || 'No description'}`).join('\n')}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list workflows: ${error.message}`
        }]
      };
    }
  }

  async queryWorkflow({ workflow_id }) {
    try {
      const output = await this.executeAkCommand(['session', 'get', workflow_id, '-J']);
      const session = JSON.parse(output);

      return {
        content: [{
          type: 'text',
          text: `Workflow ${workflow_id}:\nStatus: ${session.state}\nStarted: ${session.created_at}\nLogs: ${session.log_summary || 'No recent logs'}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to query workflow: ${error.message}`
        }]
      };
    }
  }

  async signalWorkflow({ workflow_id, signal_name, data = {} }) {
    try {
      // AutoKitteh doesn't have direct signal support via CLI yet
      // This would integrate with Temporal's signal mechanism
      return {
        content: [{
          type: 'text',
          text: `Signal '${signal_name}' would be sent to workflow ${workflow_id} (feature pending AutoKitteh API support)`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to signal workflow: ${error.message}`
        }]
      };
    }
  }

  async cancelWorkflow({ workflow_id }) {
    try {
      await this.executeAkCommand(['session', 'cancel', workflow_id]);
      this.activeWorkflows.delete(workflow_id);

      return {
        content: [{
          type: 'text',
          text: `Cancelled workflow ${workflow_id}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to cancel workflow: ${error.message}`
        }]
      };
    }
  }

  async scheduleWorkflow({ workflow_name, cron, params = {} }) {
    try {
      // Create a scheduled trigger configuration
      const scheduleConfig = {
        name: `scheduled_${workflow_name}`,
        type: 'schedule',
        schedule: cron,
        workflow: workflow_name,
        data: params
      };

      // This would be added to the project manifest
      return {
        content: [{
          type: 'text',
          text: `Scheduled workflow '${workflow_name}' with cron: ${cron}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to schedule workflow: ${error.message}`
        }]
      };
    }
  }

  async deployProject({ manifest_path, env = {} }) {
    try {
      const args = ['deploy', '--manifest', manifest_path];

      // Add environment variables
      Object.entries(env).forEach(([key, value]) => {
        args.push('--env', `${key}=${value}`);
      });

      const output = await this.executeAkCommand(args);

      return {
        content: [{
          type: 'text',
          text: `Deployed project from ${manifest_path}:\n${output}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to deploy project: ${error.message}`
        }]
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('AutoKitteh MCP server running');
  }
}

const server = new AutoKittehMCP();
server.run().catch(console.error);