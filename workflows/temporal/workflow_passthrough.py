#!/usr/bin/env python3
"""
Temporal Workflow Sandbox Passthrough Configuration
Allows safe modules to be used during workflow import
"""

from temporalio.worker import WorkflowRunner

# Configure passthrough modules
# These modules are safe for deterministic workflow execution
PASSTHROUGH_MODULES = [
    "pathlib",
    "os.path",
    "sys.path",
]

def get_worker_config():
    """
    Returns worker configuration with passthrough modules

    Usage in worker scripts:
        from workflow_passthrough import get_worker_config

        worker = Worker(
            client,
            task_queue="my-queue",
            workflows=[MyWorkflow],
            activities=[my_activity],
            workflow_runner=WorkflowRunner(
                **get_worker_config()
            )
        )
    """
    return {
        "sandbox_unrestricted_modules": PASSTHROUGH_MODULES
    }
