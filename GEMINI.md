# GEMINI.md - Project Overview

## Project Overview

This project is a sophisticated, Python-based system for creating a self-improving Artificial General Intelligence (AGI). It is an autonomous, recursive AGI that can learn from external sources, identify opportunities for self-improvement, generate and test its own code modifications, and deploy them if they are successful. It's a complete, end-to-end system for recursive self-improvement.

The system is designed to be highly modular, with a clear separation of concerns between its various components. It includes a physical interface, the Arduino Surface, which provides a tangible representation of the system's state and allows for human-in-the-loop interaction.

## Building and Running

The system is primarily used as a Python library.

### Running the Demo

To see a demonstration of the full AGI workflow, run the following command:

```bash
python3 demo_agi_workflow.py
```

### Checking System Health

To check the health of the system and all its components, run:

```bash
python3 system_health_check.py
```

## Key Components

*   **AGI Orchestrator:** The main entry point for interacting with the system.
*   **Autonomous Recursive AGI Loop:** The core of the system, responsible for the continuous learning and improvement cycle.
*   **Darwin Gödel Machine:** A component that proposes modifications to the system's own code.
*   **Auto-Implementation Engine:** Implements the proposed code changes.
*   **Sandboxed Testing Environment:** Safely tests the new code.
*   **Self-Evaluation System:** Evaluates the performance of the modified code and decides whether to keep or discard the changes.
*   **Knowledge Synthesis Engine:** Gathers and processes information from external sources like research papers and videos.
*   **RAG Code Generator:** A component that uses Retrieval-Augmented Generation (RAG) to generate optimized code.
*   **Arduino Surface:** A physical interface for interacting with the AGI, providing a tangible representation of the system's state and allowing for human-in-the-loop interaction.

## Development Conventions

*   **Configuration:** The system is configured using the `agi_config.json` file.
*   **Monitoring:** The system is designed to be monitored using tools like Prometheus and Grafana.
*   **Safety:** There is a strong emphasis on safety, with features like sandboxed testing and automated rollbacks.
*   **Modularity:** The project is well-structured, with a clear separation of concerns between the different components.
