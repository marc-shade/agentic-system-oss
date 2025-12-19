#!/usr/bin/env python3
"""
Gamepad UI - Beautiful Terminal Interface for NES Controller Integration

Provides:
- Real-time gamepad state display
- Agent list with status indicators
- Visual feedback for button presses
- Animated transitions
- Cheat sheet overlay
- Color-coded status system
- 60Hz refresh rate support

Author: Phoenix AI System
Created: 2025-10-23
"""

import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich import box
from rich.style import Style


class AgentStatus(Enum):
    """Agent status types"""
    RUNNING = ("●", "green", "Running")
    WAITING = ("●", "yellow", "Waiting")
    PAUSED = ("●", "red", "Paused")
    ERROR = ("●", "red", "Error")
    SPAWNING = ("◐", "cyan", "Spawning")


class ButtonState(Enum):
    """Button press states"""
    RELEASED = 0
    PRESSED = 1
    HELD = 2


@dataclass
class Agent:
    """Agent information"""
    id: int
    name: str
    type: str
    priority: int
    status: AgentStatus
    task: str = ""
    spawn_time: float = 0.0


@dataclass
class GamepadState:
    """Current gamepad state"""
    dpad_up: ButtonState = ButtonState.RELEASED
    dpad_down: ButtonState = ButtonState.RELEASED
    dpad_left: ButtonState = ButtonState.RELEASED
    dpad_right: ButtonState = ButtonState.RELEASED
    button_a: ButtonState = ButtonState.RELEASED
    button_b: ButtonState = ButtonState.RELEASED
    button_select: ButtonState = ButtonState.RELEASED
    button_start: ButtonState = ButtonState.RELEASED

    # Hold detection
    start_held: bool = False
    select_held: bool = False

    # Animation frame counter
    frame: int = 0


class GamepadUI:
    """Beautiful terminal UI for NES controller gamepad integration"""

    def __init__(self):
        self.console = Console()
        self.agents: List[Agent] = []
        self.selected_index: int = 0
        self.gamepad_state = GamepadState()
        self.system_status = "All services healthy"
        self.show_cheatsheet = False
        self.last_action = ""
        self.last_action_time = 0.0

        # Animation states
        self.button_flash_frames = {}  # button_name -> frames_remaining
        self.spawn_animation_agents = {}  # agent_id -> frames_remaining

        # Performance tracking
        self.fps = 60
        self.frame_time = 1.0 / self.fps
        self.last_render = time.time()

    def add_agent(self, agent: Agent):
        """Add agent to list"""
        self.agents.append(agent)
        self.spawn_animation_agents[agent.id] = 30  # 0.5s animation at 60fps

    def remove_agent(self, agent_id: int):
        """Remove agent from list"""
        self.agents = [a for a in self.agents if a.id != agent_id]
        if self.selected_index >= len(self.agents):
            self.selected_index = max(0, len(self.agents) - 1)

    def update_agent(self, agent_id: int, **kwargs):
        """Update agent properties"""
        for agent in self.agents:
            if agent.id == agent_id:
                for key, value in kwargs.items():
                    setattr(agent, key, value)
                break

    def select_next_agent(self):
        """Select next agent in list"""
        if self.agents:
            self.selected_index = (self.selected_index + 1) % len(self.agents)
            self.flash_button('dpad_down')
            self.set_action(f"Selected: {self.agents[self.selected_index].name}")

    def select_previous_agent(self):
        """Select previous agent in list"""
        if self.agents:
            self.selected_index = (self.selected_index - 1) % len(self.agents)
            self.flash_button('dpad_up')
            self.set_action(f"Selected: {self.agents[self.selected_index].name}")

    def increase_priority(self):
        """Increase selected agent priority"""
        if self.agents and self.selected_index < len(self.agents):
            agent = self.agents[self.selected_index]
            agent.priority = min(10, agent.priority + 1)
            self.flash_button('dpad_right')
            self.set_action(f"Priority increased: {agent.priority}/10")

    def decrease_priority(self):
        """Decrease selected agent priority"""
        if self.agents and self.selected_index < len(self.agents):
            agent = self.agents[self.selected_index]
            agent.priority = max(1, agent.priority - 1)
            self.flash_button('dpad_left')
            self.set_action(f"Priority decreased: {agent.priority}/10")

    def flash_button(self, button_name: str):
        """Trigger button flash animation"""
        self.button_flash_frames[button_name] = 10  # 0.16s flash at 60fps

    def set_action(self, message: str):
        """Set last action message"""
        self.last_action = message
        self.last_action_time = time.time()

    def update_gamepad_state(self, state: Dict[str, Any]):
        """Update gamepad state from controller"""
        # Map state dict to GamepadState
        self.gamepad_state.dpad_up = ButtonState(state.get('dpad_up', 0))
        self.gamepad_state.dpad_down = ButtonState(state.get('dpad_down', 0))
        self.gamepad_state.dpad_left = ButtonState(state.get('dpad_left', 0))
        self.gamepad_state.dpad_right = ButtonState(state.get('dpad_right', 0))
        self.gamepad_state.button_a = ButtonState(state.get('button_a', 0))
        self.gamepad_state.button_b = ButtonState(state.get('button_b', 0))
        self.gamepad_state.button_select = ButtonState(state.get('button_select', 0))
        self.gamepad_state.button_start = ButtonState(state.get('button_start', 0))
        self.gamepad_state.start_held = state.get('start_held', False)
        self.gamepad_state.select_held = state.get('select_held', False)

    def render_header(self) -> Panel:
        """Render header panel"""
        title_text = Text()
        title_text.append("PHOENIX AGENT CONTROLLER", style="bold cyan")
        title_text.append(" (NES Mode)", style="dim")

        # Add animation to title
        frame_indicator = "▁▂▃▄▅▆▇█"[self.gamepad_state.frame % 8]
        title_text.append(f" {frame_indicator}", style="cyan")

        return Panel(
            Align.center(title_text),
            box=box.DOUBLE,
            style="cyan"
        )

    def render_agent_list(self) -> Panel:
        """Render agent list with status indicators"""
        if not self.agents:
            empty_text = Text("No active agents", style="dim")
            empty_text.append("\n\n")
            empty_text.append("Press ", style="dim")
            empty_text.append("START + A", style="bold cyan")
            empty_text.append(" to spawn Worker Agent", style="dim")
            return Panel(
                Align.center(empty_text),
                title="Active Agents",
                border_style="blue",
                box=box.ROUNDED
            )

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Selector", style="blue", width=4)
        table.add_column("ID", style="dim", width=4)
        table.add_column("Name", style="white")
        table.add_column("Priority", style="yellow", justify="right", width=14)
        table.add_column("Status", width=10)

        for i, agent in enumerate(self.agents):
            # Selection indicator with animation
            if i == self.selected_index:
                selector_frame = "◀" if (self.gamepad_state.frame // 15) % 2 == 0 else "◁"
                selector = Text(selector_frame, style="bold blue")
            else:
                selector = Text("  ", style="dim")

            # Agent ID
            agent_id = Text(f"#{agent.id}", style="dim")

            # Agent name with spawn animation
            agent_name = Text()
            if agent.id in self.spawn_animation_agents:
                frames_left = self.spawn_animation_agents[agent.id]
                alpha = 1.0 - (frames_left / 30.0)
                if frames_left > 15:
                    agent_name.append("◐ ", style="cyan")
                else:
                    agent_name.append("● ", style="cyan")
                agent_name.append(agent.name, style=f"bold on rgb({int(0*alpha)},{int(50*alpha)},{int(80*alpha)})")
            else:
                agent_name.append(agent.name, style="bold white" if i == self.selected_index else "white")

            # Priority display
            priority_bar = "█" * agent.priority + "░" * (10 - agent.priority)
            priority_text = Text()
            priority_text.append(f"[{priority_bar}]", style="yellow")
            priority_text.append(f" {agent.priority}", style="bold yellow")

            # Status indicator
            status_symbol, status_color, status_label = agent.status.value
            status_text = Text()
            status_text.append(status_symbol, style=status_color)
            status_text.append(f" {status_label}", style=f"dim {status_color}")

            table.add_row(selector, agent_id, agent_name, priority_text, status_text)

            # Add task description if available
            if agent.task and i == self.selected_index:
                task_text = Text(f"    └─ {agent.task}", style="dim italic")
                table.add_row("", "", task_text, "", "")

        return Panel(
            table,
            title=f"Active Agents ({len(self.agents)})",
            border_style="blue",
            box=box.ROUNDED
        )

    def render_system_status(self) -> Panel:
        """Render system status"""
        status_text = Text()

        # System health indicator
        if "healthy" in self.system_status.lower():
            status_text.append("✅ ", style="green")
        elif "warning" in self.system_status.lower():
            status_text.append("⚠️  ", style="yellow")
        else:
            status_text.append("❌ ", style="red")

        status_text.append(self.system_status)

        # Add last action with fade effect
        if self.last_action:
            age = time.time() - self.last_action_time
            if age < 3.0:  # Show for 3 seconds
                status_text.append("\n\n")
                alpha = max(0, 1.0 - (age / 3.0))
                opacity = int(alpha * 255)
                status_text.append("⚡ ", style=f"rgb({opacity},{opacity},0)")
                status_text.append(self.last_action, style=f"rgb({opacity},{opacity},{opacity})")

        return Panel(
            status_text,
            title="System Status",
            border_style="green" if "healthy" in self.system_status.lower() else "yellow",
            box=box.ROUNDED
        )

    def render_controller_state(self) -> Panel:
        """Render visual controller state"""
        # Create ASCII art controller with real-time state
        controller = Text()

        # Helper to style button based on state and flash
        def button_style(button_name: str, state: ButtonState) -> str:
            if button_name in self.button_flash_frames:
                return "bold white on blue"
            elif state == ButtonState.PRESSED or state == ButtonState.HELD:
                return "bold yellow on red"
            else:
                return "dim white"

        # D-Pad
        controller.append("       ", style="dim")
        controller.append("↑", style=button_style('dpad_up', self.gamepad_state.dpad_up))
        controller.append("                      ", style="dim")

        if self.gamepad_state.start_held:
            controller.append("START", style="bold black on white")
        else:
            controller.append("START", style=button_style('button_start', self.gamepad_state.button_start))

        controller.append("\n")

        controller.append("   ", style="dim")
        controller.append("←", style=button_style('dpad_left', self.gamepad_state.dpad_left))
        controller.append(" + ", style="dim")
        controller.append("→", style=button_style('dpad_right', self.gamepad_state.dpad_right))
        controller.append("           ", style="dim")

        if self.gamepad_state.select_held:
            controller.append("SELECT", style="bold black on white")
        else:
            controller.append("SELECT", style=button_style('button_select', self.gamepad_state.button_select))

        controller.append("    ")
        controller.append("●", style=button_style('button_b', self.gamepad_state.button_b))
        controller.append("\n")

        controller.append("       ", style="dim")
        controller.append("↓", style=button_style('dpad_down', self.gamepad_state.dpad_down))
        controller.append("                           ")
        controller.append("●", style=button_style('button_a', self.gamepad_state.button_a))

        return Panel(
            Align.center(controller),
            title="Controller State",
            border_style="cyan",
            box=box.ROUNDED
        )

    def render_controls_footer(self) -> Panel:
        """Render control hints footer"""
        controls = Table(show_header=False, box=None, padding=(0, 2))
        controls.add_column(justify="center")
        controls.add_column(justify="center")
        controls.add_column(justify="center")
        controls.add_column(justify="center")

        # Row 1: Navigation and Actions
        row1 = [
            Text("[↑↓] Select", style="cyan"),
            Text("[←→] Priority", style="yellow"),
            Text("[A] Execute", style="green"),
            Text("[B] Pause", style="red")
        ]
        controls.add_row(*row1)

        # Row 2: System controls
        row2 = [
            Text("[SELECT] Status", style="blue"),
            Text("[START] Listen 🎤", style="magenta"),
            Text("[?] Cheat Sheet", style="dim"),
            Text("[Q] Quit", style="dim")
        ]
        controls.add_row(*row2)

        return Panel(
            controls,
            border_style="white",
            box=box.ROUNDED
        )

    def render_cheatsheet(self) -> Panel:
        """Render cheat sheet overlay"""
        cheat = Text()

        cheat.append("NINTENDO CONTROLLER CHEAT SHEET\n\n", style="bold cyan")

        cheat.append("NAVIGATION\n", style="bold yellow")
        cheat.append("  ↑↓  Select agent in list\n", style="white")
        cheat.append("  ←→  Adjust agent priority (1-10)\n\n", style="white")

        cheat.append("ACTIONS\n", style="bold green")
        cheat.append("  A   Execute/Confirm selected agent\n", style="white")
        cheat.append("  B   Pause/Cancel selected agent\n\n", style="white")

        cheat.append("SYSTEM\n", style="bold blue")
        cheat.append("  SELECT  Show Phoenix Monitor status\n", style="white")
        cheat.append("  START   Activate voice listening mode\n\n", style="white")

        cheat.append("COMBINATIONS (Hold + Press)\n", style="bold magenta")
        cheat.append("  START + A   Spawn Worker Agent (research)\n", style="white")
        cheat.append("  START + B   Emergency stop ALL agents 🚨\n", style="white")
        cheat.append("  SELECT + A  Spawn Dev Agent (coding)\n", style="white")
        cheat.append("  SELECT + B  Spawn Analysis Agent (debug)\n\n", style="white")

        cheat.append("Press [?] or [ESC] to close", style="dim")

        return Panel(
            cheat,
            title="Quick Reference",
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2)
        )

    def render(self) -> Layout:
        """Render complete UI"""
        # Update frame counter
        self.gamepad_state.frame += 1

        # Decay button flash animations
        expired = []
        for button_name, frames in self.button_flash_frames.items():
            if frames <= 0:
                expired.append(button_name)
            else:
                self.button_flash_frames[button_name] -= 1
        for button_name in expired:
            del self.button_flash_frames[button_name]

        # Decay spawn animations
        expired_agents = []
        for agent_id, frames in self.spawn_animation_agents.items():
            if frames <= 0:
                expired_agents.append(agent_id)
            else:
                self.spawn_animation_agents[agent_id] -= 1
        for agent_id in expired_agents:
            del self.spawn_animation_agents[agent_id]

        # Show cheatsheet overlay if enabled
        if self.show_cheatsheet:
            return Layout(self.render_cheatsheet())

        # Main layout
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="status", size=5),
            Layout(name="controller", size=6),
            Layout(name="footer", size=5)
        )

        layout["header"].update(self.render_header())
        layout["main"].update(self.render_agent_list())
        layout["status"].update(self.render_system_status())
        layout["controller"].update(self.render_controller_state())
        layout["footer"].update(self.render_controls_footer())

        return layout

    def toggle_cheatsheet(self):
        """Toggle cheat sheet display"""
        self.show_cheatsheet = not self.show_cheatsheet

    def run(self):
        """Run UI loop with live updates"""
        try:
            with Live(self.render(), console=self.console, refresh_per_second=self.fps, screen=True) as live:
                while True:
                    # Throttle to target FPS
                    current_time = time.time()
                    elapsed = current_time - self.last_render
                    if elapsed < self.frame_time:
                        time.sleep(self.frame_time - elapsed)
                    self.last_render = time.time()

                    # Update display
                    live.update(self.render())

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Gamepad UI stopped[/yellow]")


# Demo mode for testing
def demo_mode():
    """Run UI in demo mode with mock data"""
    ui = GamepadUI()

    # Add some demo agents
    ui.add_agent(Agent(
        id=1,
        name="Worker Agent #1",
        type="research",
        priority=5,
        status=AgentStatus.RUNNING,
        task="Researching API documentation",
        spawn_time=time.time()
    ))

    ui.add_agent(Agent(
        id=2,
        name="Dev Agent #2",
        type="development",
        priority=8,
        status=AgentStatus.RUNNING,
        task="Implementing authentication system",
        spawn_time=time.time()
    ))

    ui.add_agent(Agent(
        id=3,
        name="Analysis Agent #3",
        type="analysis",
        priority=3,
        status=AgentStatus.WAITING,
        spawn_time=time.time()
    ))

    ui.system_status = "All services healthy"

    # Simulate some button presses in a separate thread
    import threading

    def simulate_input():
        time.sleep(2)
        ui.select_next_agent()
        time.sleep(1)
        ui.increase_priority()
        time.sleep(1)
        ui.set_action("Executing task...")
        time.sleep(2)
        ui.select_previous_agent()

    thread = threading.Thread(target=simulate_input, daemon=True)
    thread.start()

    # Run UI
    ui.run()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Gamepad UI - NES Controller Terminal Interface")
    parser.add_argument('--demo', action='store_true', help="Run in demo mode with mock data")

    args = parser.parse_args()

    if args.demo:
        demo_mode()
    else:
        print("Gamepad UI - Ready for integration")
        print("Use --demo flag to test UI with mock data")
