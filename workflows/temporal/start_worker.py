#!/usr/bin/env python3
"""Start the Task Queue Processor worker with Claude + Ollama fallback"""
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from task_queue_processor_workflow import (
    TaskQueueProcessorWorkflow, 
    fetch_next_task, 
    execute_task, 
    update_task_status, 
    record_task_outcome, 
    update_goal_progress
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Connecting to Temporal...")
    client = await Client.connect('localhost:7233')
    
    logger.info("Starting Task Queue Processor worker...")
    worker = Worker(
        client,
        task_queue='task-queue-processor',
        workflows=[TaskQueueProcessorWorkflow],
        activities=[
            fetch_next_task, 
            execute_task, 
            update_task_status, 
            record_task_outcome, 
            update_goal_progress
        ]
    )
    
    logger.info("Worker started with Claude + Ollama fallback!")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
