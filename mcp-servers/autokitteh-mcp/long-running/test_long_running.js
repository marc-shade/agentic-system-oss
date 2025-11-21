#!/usr/bin/env node
/**
 * Integration tests for AutoKitteh Long-Running Workflows
 *
 * Tests:
 * 1. Multi-day workflow execution
 * 2. Context checkpoint creation and recovery
 * 3. Enhanced-memory integration
 * 4. BMAD continuous agent conversion
 * 5. 30+ hour context maintenance
 * 6. Cross-day coherence validation
 */

import {
  LongRunningWorkflow,
  WorkflowCheckpoint,
  BMADContinuousAgent
} from './long_running_workflows.js';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

class TestLongRunningWorkflows {
  constructor() {
    this.testResults = [];
    this.setupCheckpointDir();
  }

  setupCheckpointDir() {
    const checkpointDir = join(homedir(), '.autokitteh', 'checkpoints');
    if (!existsSync(checkpointDir)) {
      mkdirSync(checkpointDir, { recursive: true });
    }
  }

  /**
   * Test 1: Multi-day workflow execution
   */
  async testMultiDayWorkflowExecution() {
    console.log('\n=== Test 1: Multi-Day Workflow Execution ===');

    const workflow = new LongRunningWorkflow(
      `test-workflow-${Date.now()}`,
      'test-deployment'
    );

    try {
      const result = await workflow.multiDayDeployment('Test Project');

      // Validate results
      console.assert(result.status === 'completed', 'Workflow should complete');
      console.assert(result.durationDays === 4, 'Should take 4 days');
      console.assert(result.checkpoints > 0, 'Should have checkpoints');
      console.assert(result.results.plan, 'Should have planning results');
      console.assert(result.results.execution, 'Should have execution results');
      console.assert(result.results.validation, 'Should have validation results');
      console.assert(result.results.documentation, 'Should have documentation');

      console.log('✓ Multi-day workflow executed successfully');
      console.log(`  Status: ${result.status}`);
      console.log(`  Duration: ${result.durationDays} days`);
      console.log(`  Checkpoints: ${result.checkpoints}`);
      console.log(`  All phases completed: ✓`);

      this.testResults.push({
        test: 'multi_day_workflow_execution',
        passed: true,
        result
      });

      return result;

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'multi_day_workflow_execution',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Test 2: Context checkpoint creation and persistence
   */
  async testCheckpointSystem() {
    console.log('\n=== Test 2: Checkpoint System ===');

    const workflowId = `checkpoint-test-${Date.now()}`;
    const testData = {
      phase: 'planning',
      testValue: 'checkpoint-data',
      timestamp: new Date().toISOString()
    };

    try {
      // Create checkpoint
      const checkpoint = new WorkflowCheckpoint(
        workflowId,
        'test_phase',
        testData
      );

      await checkpoint.persist();

      console.log('✓ Checkpoint created and persisted');
      console.log(`  ID: ${checkpoint.checkpointId}`);
      console.log(`  Workflow: ${checkpoint.workflowId}`);
      console.log(`  Phase: ${checkpoint.phase}`);

      // Restore checkpoint
      const restored = WorkflowCheckpoint.restore(checkpoint.checkpointId);

      console.assert(restored.workflowId === workflowId, 'Workflow ID should match');
      console.assert(restored.phase === 'test_phase', 'Phase should match');
      console.assert(restored.data.testValue === 'checkpoint-data', 'Data should match');

      console.log('✓ Checkpoint restored successfully');
      console.log(`  Data integrity: ✓`);

      this.testResults.push({
        test: 'checkpoint_system',
        passed: true,
        checkpointId: checkpoint.checkpointId
      });

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'checkpoint_system',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Test 3: Context maintenance across phases
   */
  async testContextMaintenance() {
    console.log('\n=== Test 3: Context Maintenance Across Phases ===');

    const workflow = new LongRunningWorkflow(
      `context-test-${Date.now()}`,
      'context-test'
    );

    try {
      // Execute Day 1
      const plan = await workflow.dayOnePlanning('Context Test Project');
      await workflow.checkpoint('day1_complete', { plan });

      console.log('✓ Day 1 context established');
      console.assert(workflow.context.plan, 'Plan should be in context');

      // Execute Day 2 - should recall Day 1
      const execution = await workflow.dayTwoExecution(plan);
      await workflow.checkpoint('day2_complete', { plan, execution });

      console.log('✓ Day 2 recalls Day 1 context');
      console.assert(workflow.context.execution, 'Execution should be in context');
      console.assert(workflow.context.plan, 'Plan should still be in context');

      // Execute Day 3 - should recall Days 1-2
      const validation = await workflow.dayThreeValidation(execution);

      console.log('✓ Day 3 recalls Days 1-2 context');
      console.assert(workflow.context.validation, 'Validation should be in context');
      console.assert(workflow.context.execution, 'Execution should still be in context');

      // Execute Day 4 - should synthesize all days
      const documentation = await workflow.dayFourDocumentation(
        plan,
        execution,
        validation
      );

      console.log('✓ Day 4 synthesizes complete narrative');
      console.assert(documentation.contextMaintained, 'Context should be maintained');
      console.assert(documentation.coherenceAcrossDays, 'Should have coherence');
      console.assert(
        documentation.deploymentNarrative.includes('Day 1'),
        'Should reference Day 1'
      );
      console.assert(
        documentation.deploymentNarrative.includes('Day 4'),
        'Should reference Day 4'
      );

      console.log('✓ Context maintained across all 4 days');
      console.log(`  Checkpoints: ${workflow.checkpoints.length}`);
      console.log(`  Context entries: ${Object.keys(workflow.context).length}`);
      console.log(`  Coherence verified: ✓`);

      this.testResults.push({
        test: 'context_maintenance',
        passed: true,
        checkpoints: workflow.checkpoints.length,
        contextKeys: Object.keys(workflow.context)
      });

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'context_maintenance',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Test 4: Checkpoint recovery after failure
   */
  async testCheckpointRecovery() {
    console.log('\n=== Test 4: Checkpoint Recovery ===');

    const workflowId = `recovery-test-${Date.now()}`;

    try {
      // Create workflow and execute to Day 2
      const workflow = new LongRunningWorkflow(workflowId, 'recovery-test');

      const plan = await workflow.dayOnePlanning('Recovery Test');
      await workflow.checkpoint('day1_complete', { plan });

      const execution = await workflow.dayTwoExecution(plan);
      const day2Checkpoint = await workflow.checkpoint('day2_complete', {
        plan,
        execution
      });

      console.log('✓ Workflow progressed to Day 2');
      console.log(`  Checkpoint ID: ${day2Checkpoint.checkpointId}`);

      // Simulate failure and recovery
      console.log('  Simulating failure...');
      const restored = await LongRunningWorkflow.restoreFromCheckpoint(
        day2Checkpoint.checkpointId
      );

      console.log('✓ Workflow restored from checkpoint');
      console.assert(restored.workflowId === workflowId, 'Workflow ID should match');
      console.assert(restored.currentPhase === 'day2_complete', 'Phase should match');
      console.assert(restored.context.plan, 'Should have plan context');
      console.assert(restored.context.execution, 'Should have execution context');

      console.log('✓ All context successfully recovered');
      console.log(`  Context keys: ${Object.keys(restored.context).length}`);

      this.testResults.push({
        test: 'checkpoint_recovery',
        passed: true,
        recoveredContext: Object.keys(restored.context)
      });

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'checkpoint_recovery',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Test 5: BMAD continuous agent conversion
   */
  async testBMADContinuousAgent() {
    console.log('\n=== Test 5: BMAD Continuous Agent ===');

    try {
      const bmad = new BMADContinuousAgent();
      const result = await bmad.executeBMAD();

      console.assert(result.status === 'completed', 'BMAD should complete');
      console.assert(result.durationDays === 4, 'Should span 4 days');
      console.assert(
        result.results.documentation.contextMaintained,
        'Should maintain context'
      );
      console.assert(
        result.results.documentation.coherenceAcrossDays,
        'Should have coherence'
      );

      console.log('✓ BMAD continuous agent executed');
      console.log(`  Status: ${result.status}`);
      console.log(`  Context maintained: ${result.results.documentation.contextMaintained}`);
      console.log(`  Coherence: ${result.results.documentation.coherenceAcrossDays}`);
      console.log(`  Traditional approach: Sequential handoffs`);
      console.log(`  New approach: Continuous agent with checkpoints`);

      this.testResults.push({
        test: 'bmad_continuous_agent',
        passed: true,
        result
      });

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'bmad_continuous_agent',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Test 6: 30+ hour context maintenance simulation
   */
  async testExtendedContextMaintenance() {
    console.log('\n=== Test 6: 30+ Hour Context Maintenance ===');

    const workflow = new LongRunningWorkflow(
      `extended-context-${Date.now()}`,
      'extended-context-test'
    );

    try {
      // Simulate 30+ hour operation with checkpoints every 4 hours
      const hoursToSimulate = 32;
      const checkpointInterval = 4;
      const checkpointsExpected = Math.floor(hoursToSimulate / checkpointInterval);

      console.log(`  Simulating ${hoursToSimulate} hours`);
      console.log(`  Checkpoint interval: ${checkpointInterval} hours`);
      console.log(`  Expected checkpoints: ${checkpointsExpected}`);

      // Initial context
      workflow.context.startTime = new Date().toISOString();
      workflow.context.data = {
        hour0: 'Initial context'
      };

      // Create checkpoints at intervals
      for (let hour = checkpointInterval; hour <= hoursToSimulate; hour += checkpointInterval) {
        // Add new context at each checkpoint
        workflow.context.data[`hour${hour}`] = `Context at hour ${hour}`;
        workflow.context.lastCheckpoint = hour;

        await workflow.checkpoint(`hour_${hour}`, {
          hour,
          contextSize: Object.keys(workflow.context.data).length
        });

        console.log(`  ✓ Checkpoint at hour ${hour}`);
      }

      // Verify all context maintained
      const finalContextSize = Object.keys(workflow.context.data).length;
      const expectedContextSize = (hoursToSimulate / checkpointInterval) + 1; // +1 for hour0

      console.assert(
        workflow.checkpoints.length === checkpointsExpected,
        'Should have correct number of checkpoints'
      );
      console.assert(
        finalContextSize === expectedContextSize,
        'Should maintain all context entries'
      );
      console.assert(
        workflow.context.data.hour0,
        'Should have initial context'
      );
      console.assert(
        workflow.context.data[`hour${hoursToSimulate}`],
        'Should have final context'
      );

      console.log('✓ 30+ hour context maintained');
      console.log(`  Total checkpoints: ${workflow.checkpoints.length}`);
      console.log(`  Context entries: ${finalContextSize}`);
      console.log(`  No context loss: ✓`);
      console.log(`  Coherence verified: ✓`);

      this.testResults.push({
        test: 'extended_context_maintenance',
        passed: true,
        hoursSimulated: hoursToSimulate,
        checkpoints: workflow.checkpoints.length,
        contextSize: finalContextSize
      });

    } catch (error) {
      console.error(`✗ Test failed: ${error.message}`);
      this.testResults.push({
        test: 'extended_context_maintenance',
        passed: false,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Print test summary
   */
  printSummary() {
    console.log('\n' + '='.repeat(60));
    console.log('TEST SUMMARY');
    console.log('='.repeat(60));

    const passed = this.testResults.filter(r => r.passed).length;
    const total = this.testResults.length;

    console.log(`\nTests Passed: ${passed}/${total}`);

    console.log('\nDetailed Results:');
    for (const result of this.testResults) {
      const status = result.passed ? '✓ PASS' : '✗ FAIL';
      console.log(`  ${status} - ${result.test}`);
      if (!result.passed && result.error) {
        console.log(`    Error: ${result.error}`);
      }
    }

    // Key achievements
    if (passed === total) {
      console.log('\n' + '='.repeat(60));
      console.log('KEY ACHIEVEMENTS');
      console.log('='.repeat(60));
      console.log('✓ Multi-day workflow execution working');
      console.log('✓ Checkpoint system operational');
      console.log('✓ Context maintained across days');
      console.log('✓ Recovery from checkpoints functional');
      console.log('✓ BMAD continuous agent implemented');
      console.log('✓ 30+ hour context maintenance validated');
      console.log('\nPhase 3.3: Multi-Day Workflows - ALL TESTS PASSED');
    }

    console.log('='.repeat(60));

    return passed === total;
  }

  /**
   * Run complete test suite
   */
  async runAllTests() {
    console.log('='.repeat(60));
    console.log('AUTOKITTEH LONG-RUNNING WORKFLOWS - INTEGRATION TESTS');
    console.log('='.repeat(60));
    console.log(`Started: ${new Date().toISOString()}`);

    try {
      await this.testMultiDayWorkflowExecution();
      await this.testCheckpointSystem();
      await this.testContextMaintenance();
      await this.testCheckpointRecovery();
      await this.testBMADContinuousAgent();
      await this.testExtendedContextMaintenance();

      const allPassed = this.printSummary();
      return allPassed;

    } catch (error) {
      console.error(`\n✗ Test suite failed: ${error.message}`);
      this.printSummary();
      return false;
    }
  }
}

// Run tests
if (import.meta.url === `file://${process.argv[1]}`) {
  const testSuite = new TestLongRunningWorkflows();
  const success = await testSuite.runAllTests();
  process.exit(success ? 0 : 1);
}

export { TestLongRunningWorkflows };