/**
 * Comprehensive Dashboard Testing Script (Dashboards 6-10)
 * Tests: Custom Agents, Usage Analytics, Telemetry Monitoring,
 *        Overnight Automation, and Workflow Automation
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;

const BASE_URL = 'http://localhost:3101';
const API_URL = 'http://localhost:3002';

const DASHBOARDS = [
  {
    id: 6,
    name: 'Custom Agents Dashboard',
    url: '/custom-agents',
    component: 'CustomAgentsDashboard',
    apiEndpoints: ['/api/agents', '/api/agent-templates']
  },
  {
    id: 7,
    name: 'Usage Analytics Dashboard',
    url: '/usage-analytics',
    component: 'UsageAnalyticsDashboard',
    apiEndpoints: ['/api/usage/stats']
  },
  {
    id: 8,
    name: 'Telemetry Monitoring Dashboard',
    url: '/telemetry-monitoring',
    component: 'TelemetryMonitoringDashboard',
    apiEndpoints: [
      '/api/telemetry/stats',
      '/api/telemetry/sessions',
      '/api/telemetry/model-performance',
      '/api/telemetry/tool-summary',
      '/api/telemetry/cost-breakdown',
      '/api/telemetry/api-errors'
    ]
  },
  {
    id: 9,
    name: 'Overnight Automation Dashboard',
    url: '/overnight-automation',
    component: 'OvernightDashboard',
    apiEndpoints: ['/api/overnight/status']
  },
  {
    id: 10,
    name: 'Workflow Automation Dashboard',
    url: '/agentic/workflow',
    component: 'AgenticWorkflowPage',
    apiEndpoints: ['/api/workflows']
  }
];

class DashboardTester {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      summary: {
        total: DASHBOARDS.length,
        working: 0,
        broken: 0,
        partial: 0
      },
      dashboards: []
    };
  }

  async init() {
    this.browser = await chromium.launch({
      headless: false, // Set to true for CI/CD
      slowMo: 100
    });
    this.context = await this.browser.newContext({
      viewport: { width: 1920, height: 1080 },
      recordVideo: { dir: '/tmp/dashboard-tests/' }
    });
    this.page = await this.context.newPage();

    // Capture console errors
    this.consoleErrors = [];
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        this.consoleErrors.push({
          text: msg.text(),
          location: msg.location()
        });
      }
    });

    // Capture network failures
    this.networkErrors = [];
    this.page.on('requestfailed', request => {
      this.networkErrors.push({
        url: request.url(),
        failure: request.failure()
      });
    });
  }

  async testDashboard(dashboard) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Testing Dashboard #${dashboard.id}: ${dashboard.name}`);
    console.log('='.repeat(60));

    const result = {
      id: dashboard.id,
      name: dashboard.name,
      url: dashboard.url,
      component: dashboard.component,
      status: 'unknown',
      consoleErrors: [],
      networkErrors: [],
      apiEndpointResults: [],
      interactiveElements: {
        found: [],
        tested: []
      },
      loadTime: 0,
      screenshots: [],
      issues: [],
      workingFeatures: []
    };

    try {
      // Clear errors from previous test
      this.consoleErrors = [];
      this.networkErrors = [];

      // Navigate to dashboard
      const startTime = Date.now();
      console.log(`📍 Navigating to: ${BASE_URL}${dashboard.url}`);

      const response = await this.page.goto(`${BASE_URL}${dashboard.url}`, {
        waitUntil: 'networkidle',
        timeout: 30000
      });

      result.loadTime = Date.now() - startTime;
      console.log(`⏱️  Page loaded in ${result.loadTime}ms`);
      console.log(`📊 Response status: ${response?.status() || 'N/A'}`);

      // Wait for React to render
      await this.page.waitForTimeout(2000);

      // Take initial screenshot
      const screenshotPath = `/tmp/dashboard-${dashboard.id}-initial.png`;
      await this.page.screenshot({ path: screenshotPath, fullPage: true });
      result.screenshots.push(screenshotPath);
      console.log(`📸 Screenshot saved: ${screenshotPath}`);

      // Check for console errors
      if (this.consoleErrors.length > 0) {
        result.consoleErrors = [...this.consoleErrors];
        console.log(`❌ Console Errors (${this.consoleErrors.length}):`);
        this.consoleErrors.forEach((err, i) => {
          console.log(`   ${i + 1}. ${err.text}`);
          if (err.location) {
            console.log(`      at ${err.location.url}:${err.location.lineNumber}`);
          }
        });
      } else {
        console.log('✅ No console errors');
        result.workingFeatures.push('No console errors');
      }

      // Check for network errors
      if (this.networkErrors.length > 0) {
        result.networkErrors = [...this.networkErrors];
        console.log(`❌ Network Errors (${this.networkErrors.length}):`);
        this.networkErrors.forEach((err, i) => {
          console.log(`   ${i + 1}. ${err.url}`);
          console.log(`      Reason: ${err.failure?.errorText || 'Unknown'}`);
        });
      } else {
        console.log('✅ No network failures');
        result.workingFeatures.push('All network requests successful');
      }

      // Test API endpoints
      console.log('\n🔌 Testing API Endpoints:');
      for (const endpoint of dashboard.apiEndpoints) {
        const apiResult = await this.testAPIEndpoint(endpoint);
        result.apiEndpointResults.push(apiResult);

        const status = apiResult.success ? '✅' : '❌';
        console.log(`   ${status} ${endpoint} - ${apiResult.status} (${apiResult.responseTime}ms)`);

        if (!apiResult.success) {
          result.issues.push(`API endpoint ${endpoint} failed: ${apiResult.error}`);
        }
      }

      // Check for loading indicators
      const loadingElements = await this.page.$$('css=[role="progressbar"], css=.MuiCircularProgress-root');
      if (loadingElements.length > 0) {
        console.log(`⏳ Waiting for ${loadingElements.length} loading indicators to disappear...`);
        await this.page.waitForTimeout(3000);
      }

      // Detect interactive elements
      console.log('\n🔘 Detecting Interactive Elements:');
      const buttons = await this.page.$$('button:not([disabled])');
      const inputs = await this.page.$$('input:not([disabled])');
      const tabs = await this.page.$$('[role="tab"]');

      console.log(`   Found ${buttons.length} buttons, ${inputs.length} inputs, ${tabs.length} tabs`);
      result.interactiveElements.found = [
        `${buttons.length} buttons`,
        `${inputs.length} inputs`,
        `${tabs.length} tabs`
      ];

      // Test interactive elements
      console.log('\n🖱️  Testing Interactive Elements:');

      // Test first tab if exists
      if (tabs.length > 0) {
        try {
          await tabs[0].click();
          await this.page.waitForTimeout(500);
          console.log('   ✅ Tab navigation works');
          result.interactiveElements.tested.push('Tab navigation');
          result.workingFeatures.push('Tab navigation functional');
        } catch (e) {
          console.log(`   ❌ Tab click failed: ${e.message}`);
          result.issues.push('Tab navigation not working');
        }
      }

      // Test refresh button if exists
      const refreshButton = await this.page.$('button:has-text("Refresh"), button[aria-label*="refresh" i]');
      if (refreshButton) {
        try {
          const beforeErrors = this.consoleErrors.length;
          await refreshButton.click();
          await this.page.waitForTimeout(1000);
          const afterErrors = this.consoleErrors.length;

          if (afterErrors === beforeErrors) {
            console.log('   ✅ Refresh button works');
            result.interactiveElements.tested.push('Refresh button');
            result.workingFeatures.push('Refresh functionality');
          } else {
            console.log('   ⚠️  Refresh button triggered errors');
            result.issues.push('Refresh button causes errors');
          }
        } catch (e) {
          console.log(`   ⚠️  Refresh button test failed: ${e.message}`);
        }
      }

      // Check for data rendering
      console.log('\n📊 Checking Data Rendering:');
      const cards = await this.page.$$('.MuiCard-root, [class*="Card"]');
      const tables = await this.page.$$('table');
      const charts = await this.page.$$('svg, canvas');

      console.log(`   Found ${cards.length} cards, ${tables.length} tables, ${charts.length} charts`);

      if (cards.length > 0) {
        result.workingFeatures.push(`${cards.length} data cards rendered`);
      }
      if (tables.length > 0) {
        result.workingFeatures.push(`${tables.length} data tables rendered`);
      }
      if (charts.length > 0) {
        result.workingFeatures.push(`${charts.length} charts/visualizations rendered`);
      }

      // Check for "No data" messages
      const noDataText = await this.page.textContent('body');
      const hasNoData = /no data|no.*available|empty/i.test(noDataText);
      if (hasNoData) {
        console.log('   ⚠️  Dashboard shows "no data" messages');
        result.issues.push('Dashboard shows no data available');
      }

      // Final screenshot after interactions
      const finalScreenshot = `/tmp/dashboard-${dashboard.id}-final.png`;
      await this.page.screenshot({ path: finalScreenshot, fullPage: true });
      result.screenshots.push(finalScreenshot);

      // Determine overall status
      const hasErrors = result.consoleErrors.length > 0 || result.networkErrors.length > 0;
      const hasFailedAPIs = result.apiEndpointResults.some(r => !r.success);
      const hasCriticalIssues = result.issues.length > 0;

      if (!hasErrors && !hasFailedAPIs && !hasCriticalIssues) {
        result.status = 'working';
        this.results.summary.working++;
        console.log('\n✅ Dashboard Status: WORKING');
      } else if (hasErrors || hasFailedAPIs) {
        result.status = 'broken';
        this.results.summary.broken++;
        console.log('\n❌ Dashboard Status: BROKEN');
      } else {
        result.status = 'partial';
        this.results.summary.partial++;
        console.log('\n⚠️  Dashboard Status: PARTIAL');
      }

    } catch (error) {
      result.status = 'error';
      result.issues.push(`Test error: ${error.message}`);
      this.results.summary.broken++;
      console.log(`\n💥 Test Error: ${error.message}`);
    }

    this.results.dashboards.push(result);
    return result;
  }

  async testAPIEndpoint(endpoint) {
    const fullUrl = `${API_URL}${endpoint}`;
    const startTime = Date.now();

    try {
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });

      const responseTime = Date.now() - startTime;
      const success = response.ok;
      let data = null;
      let error = null;

      try {
        data = await response.json();
      } catch (e) {
        error = 'Invalid JSON response';
      }

      return {
        endpoint,
        success,
        status: response.status,
        statusText: response.statusText,
        responseTime,
        hasData: !!data,
        error: !success ? (data?.error || error || response.statusText) : null
      };
    } catch (error) {
      return {
        endpoint,
        success: false,
        status: 0,
        statusText: 'Network Error',
        responseTime: Date.now() - startTime,
        hasData: false,
        error: error.message
      };
    }
  }

  async generateReport() {
    console.log('\n' + '='.repeat(60));
    console.log('COMPREHENSIVE TEST REPORT');
    console.log('='.repeat(60));

    console.log('\n📊 SUMMARY:');
    console.log(`   Total Dashboards: ${this.results.summary.total}`);
    console.log(`   ✅ Working: ${this.results.summary.working}`);
    console.log(`   ❌ Broken: ${this.results.summary.broken}`);
    console.log(`   ⚠️  Partial: ${this.results.summary.partial}`);

    console.log('\n📋 DETAILED RESULTS:\n');

    for (const dashboard of this.results.dashboards) {
      const statusIcon = dashboard.status === 'working' ? '✅' :
                        dashboard.status === 'broken' ? '❌' : '⚠️';

      console.log(`${statusIcon} Dashboard #${dashboard.id}: ${dashboard.name}`);
      console.log(`   URL: ${dashboard.url}`);
      console.log(`   Status: ${dashboard.status.toUpperCase()}`);
      console.log(`   Load Time: ${dashboard.loadTime}ms`);

      if (dashboard.workingFeatures.length > 0) {
        console.log(`   Working Features:`);
        dashboard.workingFeatures.forEach(f => console.log(`      • ${f}`));
      }

      if (dashboard.issues.length > 0) {
        console.log(`   Issues:`);
        dashboard.issues.forEach(i => console.log(`      ⚠️  ${i}`));
      }

      if (dashboard.consoleErrors.length > 0) {
        console.log(`   Console Errors: ${dashboard.consoleErrors.length}`);
      }

      if (dashboard.networkErrors.length > 0) {
        console.log(`   Network Errors: ${dashboard.networkErrors.length}`);
      }

      console.log('');
    }

    // Save JSON report
    const reportPath = '/Volumes/SSDRAID0/agentic-system/dashboard-test-report.json';
    await fs.writeFile(reportPath, JSON.stringify(this.results, null, 2));
    console.log(`📄 Full JSON report saved: ${reportPath}`);

    // Generate markdown report
    const markdown = this.generateMarkdownReport();
    const markdownPath = '/Volumes/SSDRAID0/agentic-system/dashboard-test-report.md';
    await fs.writeFile(markdownPath, markdown);
    console.log(`📝 Markdown report saved: ${markdownPath}`);
  }

  generateMarkdownReport() {
    let md = `# KutiraAI Dashboard Testing Report\n\n`;
    md += `**Date:** ${new Date(this.results.timestamp).toLocaleString()}\n\n`;

    md += `## Summary\n\n`;
    md += `| Metric | Count |\n`;
    md += `|--------|-------|\n`;
    md += `| Total Dashboards | ${this.results.summary.total} |\n`;
    md += `| ✅ Working | ${this.results.summary.working} |\n`;
    md += `| ❌ Broken | ${this.results.summary.broken} |\n`;
    md += `| ⚠️ Partial | ${this.results.summary.partial} |\n\n`;

    md += `## Dashboard Details\n\n`;

    for (const dashboard of this.results.dashboards) {
      const statusEmoji = dashboard.status === 'working' ? '✅' :
                         dashboard.status === 'broken' ? '❌' : '⚠️';

      md += `### ${statusEmoji} Dashboard #${dashboard.id}: ${dashboard.name}\n\n`;
      md += `- **URL:** ${dashboard.url}\n`;
      md += `- **Component:** ${dashboard.component}\n`;
      md += `- **Status:** ${dashboard.status.toUpperCase()}\n`;
      md += `- **Load Time:** ${dashboard.loadTime}ms\n\n`;

      if (dashboard.workingFeatures.length > 0) {
        md += `#### ✅ Working Features\n\n`;
        dashboard.workingFeatures.forEach(f => {
          md += `- ${f}\n`;
        });
        md += `\n`;
      }

      if (dashboard.issues.length > 0) {
        md += `#### ⚠️ Issues Found\n\n`;
        dashboard.issues.forEach(i => {
          md += `- ${i}\n`;
        });
        md += `\n`;
      }

      if (dashboard.consoleErrors.length > 0) {
        md += `#### 🐛 Console Errors (${dashboard.consoleErrors.length})\n\n`;
        md += `\`\`\`\n`;
        dashboard.consoleErrors.slice(0, 5).forEach(err => {
          md += `${err.text}\n`;
        });
        if (dashboard.consoleErrors.length > 5) {
          md += `... and ${dashboard.consoleErrors.length - 5} more\n`;
        }
        md += `\`\`\`\n\n`;
      }

      if (dashboard.apiEndpointResults.length > 0) {
        md += `#### 🔌 API Endpoints\n\n`;
        md += `| Endpoint | Status | Response Time |\n`;
        md += `|----------|--------|---------------|\n`;
        dashboard.apiEndpointResults.forEach(api => {
          const status = api.success ? '✅' : '❌';
          md += `| ${api.endpoint} | ${status} ${api.status} | ${api.responseTime}ms |\n`;
        });
        md += `\n`;
      }

      md += `---\n\n`;
    }

    return md;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// Main execution
async function main() {
  const tester = new DashboardTester();

  try {
    await tester.init();

    for (const dashboard of DASHBOARDS) {
      await tester.testDashboard(dashboard);
      // Small delay between tests
      await tester.page.waitForTimeout(1000);
    }

    await tester.generateReport();

  } catch (error) {
    console.error('Fatal error:', error);
  } finally {
    await tester.cleanup();
  }
}

main();
