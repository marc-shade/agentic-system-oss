import os
import json
import asyncio
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
from loguru import logger
import uuid

class NotificationType(Enum):
    """Notification types."""
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'

class NotificationManager:
    """
    Manages notifications and real-time updates for the Software Planning MCP.
    Handles message delivery, alert management, and subscription-based updates.
    """
    
    def __init__(self):
        self.notifications_dir = Path(os.path.expanduser("~/.mcp/notifications"))
        self.notifications_dir.mkdir(parents=True, exist_ok=True)
        self.messages_file = self.notifications_dir / "messages.json"
        self.subscriptions_file = self.notifications_dir / "subscriptions.json"
        
        # Initialize notification files
        self._initialize_notification_files()
        
        # Load notification data
        self.messages = self._load_messages()
        self.subscriptions = self._load_subscriptions()
        
        # Active subscriptions
        self.active_subscribers: Dict[str, Set[Callable]] = {}
        
        # Message queue
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Start message processor
        self.processor_task = asyncio.create_task(self._process_messages())
    
    def _initialize_notification_files(self):
        """Initialize notification files with default values."""
        if not self.messages_file.exists():
            with open(self.messages_file, "w") as f:
                json.dump({"messages": []}, f, indent=2)
        
        if not self.subscriptions_file.exists():
            with open(self.subscriptions_file, "w") as f:
                json.dump({"subscriptions": []}, f, indent=2)
    
    def _load_messages(self) -> Dict[str, Any]:
        """Load message history."""
        try:
            with open(self.messages_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load messages: {e}")
            return {"messages": []}
    
    def _load_subscriptions(self) -> Dict[str, Any]:
        """Load subscription configurations."""
        try:
            with open(self.subscriptions_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load subscriptions: {e}")
            return {"subscriptions": []}
    
    def _save_messages(self):
        """Save message history."""
        try:
            with open(self.messages_file, "w") as f:
                json.dump(self.messages, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save messages: {e}")
    
    def _save_subscriptions(self):
        """Save subscription configurations."""
        try:
            with open(self.subscriptions_file, "w") as f:
                json.dump(self.subscriptions, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save subscriptions: {e}")
    
    async def send_notification(
        self,
        message: str,
        notification_type: Union[str, NotificationType],
        priority: Union[str, NotificationPriority],
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            topic: Optional topic to associate with the notification
            
        Returns:
            Notification details
        """
        if isinstance(notification_type, str):
            notification_type = NotificationType(notification_type)
        if isinstance(priority, str):
            priority = NotificationPriority(priority)
        
        notification = {
            "id": str(uuid.uuid4()),
            "message": message,
            "type": notification_type.value,
            "priority": priority.value,
            "timestamp": datetime.now().isoformat(),
            "topic": topic
        }
        
        # Add to message history
        self.messages["messages"].append(notification)
        
        # Keep only last 1000 messages
        if len(self.messages["messages"]) > 1000:
            self.messages["messages"] = self.messages["messages"][-1000:]
        
        self._save_messages()
        
        # Add to message queue for processing
        await self.message_queue.put(notification)
        
        return notification
    
    async def _process_messages(self):
        """Process messages from the queue."""
        while True:
            try:
                notification = await self.message_queue.get()
                
                # Get subscribers for this topic
                subscribers = set()
                if notification.get("topic"):
                    subscribers.update(self.active_subscribers.get(notification["topic"], set()))
                
                # Also notify global subscribers
                subscribers.update(self.active_subscribers.get("*", set()))
                
                # Deliver to subscribers
                for callback in subscribers:
                    try:
                        await callback(notification)
                    except Exception as e:
                        logger.error(f"Failed to deliver notification: {e}")
                
                # Mark as delivered
                notification["delivered"] = True
                self._save_messages()
                
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
    async def subscribe(
        self,
        callback: Callable,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Subscribe to notifications.
        
        Args:
            callback: Callback function for notifications
            topic: Optional topic to subscribe to
        """
        topic = topic or "*"
        
        if topic not in self.active_subscribers:
            self.active_subscribers[topic] = set()
        
        self.active_subscribers[topic].add(callback)
        
        subscription = {
            "id": str(len(self.subscriptions["subscriptions"]) + 1),
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        self.subscriptions["subscriptions"].append(subscription)
        self._save_subscriptions()
        
        return subscription
    
    async def unsubscribe(
        self,
        callback: Callable,
        topic: Optional[str] = None
    ):
        """
        Unsubscribe from notifications.
        
        Args:
            callback: Callback function to remove
            topic: Optional topic to unsubscribe from
        """
        topic = topic or "*"
        
        if topic in self.active_subscribers:
            self.active_subscribers[topic].discard(callback)
            
            if not self.active_subscribers[topic]:
                del self.active_subscribers[topic]
    
    async def get_notifications(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        notification_type: Optional[NotificationType] = None,
        priority: Optional[NotificationPriority] = None,
        topic: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get notifications with filtering.
        
        Args:
            start_time: Optional start time in ISO format
            end_time: Optional end time in ISO format
            notification_type: Optional type filter
            priority: Optional priority filter
            topic: Optional topic filter
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications matching criteria
        """
        notifications = self.messages["messages"]
        
        if start_time:
            notifications = [n for n in notifications if n["timestamp"] >= start_time]
        
        if end_time:
            notifications = [n for n in notifications if n["timestamp"] <= end_time]
        
        if notification_type:
            notifications = [n for n in notifications if n["type"] == notification_type.value]
        
        if priority:
            notifications = [n for n in notifications if n["priority"] == priority.value]
        
        if topic:
            notifications = [n for n in notifications if n["topic"] == topic]
        
        return notifications[-limit:]
    
    async def get_active_subscriptions(
        self,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active subscriptions.
        
        Args:
            topic: Optional topic filter
            
        Returns:
            List of active subscriptions
        """
        subscriptions = [
            s for s in self.subscriptions["subscriptions"]
            if s["active"]
        ]
        
        if topic:
            subscriptions = [s for s in subscriptions if s["topic"] == topic]
        
        return subscriptions
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for notification management."""
        return [
            {
                "name": "send_notification",
                "description": "Send a notification",
                "parameters": [
                    {
                        "name": "message",
                        "description": "Notification message",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "notification_type",
                        "description": "Type of notification",
                        "type": "string",
                        "enum": [t.value for t in NotificationType],
                        "required": True,
                    },
                    {
                        "name": "priority",
                        "description": "Priority level",
                        "type": "string",
                        "enum": [p.value for p in NotificationPriority],
                        "required": True,
                    },
                    {
                        "name": "topic",
                        "description": "Optional topic to associate with the notification",
                        "type": "string",
                        "required": False
                    }
                ],
                "handler": self.tool_send_notification,
            },
            {
                "name": "get_notifications",
                "description": "Get notifications with filtering",
                "parameters": [
                    {
                        "name": "start_time",
                        "description": "Optional start time in ISO format",
                        "type": "string",
                        "enum": [
                            "day",
                            "week",
                            "month",
                            "year",
                            "d",
                            "w",
                            "m",
                            "y"
                          ],
                        "required": False,
                    },
                    {
                        "name": "end_time",
                        "description": "Optional end time in ISO format",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "notification_type",
                        "description": "Optional type filter",
                        "type": "string",
                        "enum": [t.value for t in NotificationType],
                        "required": False,
                    },
                    {
                        "name": "priority",
                        "description": "Optional priority filter",
                        "type": "string",
                        "enum": [p.value for p in NotificationPriority],
                        "required": False,
                    },
                    {
                        "name": "topic",
                        "description": "Optional topic filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "limit",
                        "description": "Maximum number of notifications to return",
                        "type": "integer",
                        "required": False
                    }
                ],
                "handler": self.tool_get_notifications,
            },
            {
                "name": "get_active_subscriptions",
                "description": "Get active subscriptions",
                "parameters": [
                    {
                        "name": "topic",
                        "description": "Optional topic filter",
                        "type": "string",
                        "required": False
                    }
                ],
                "handler": self.tool_get_active_subscriptions,
            },
        ]
    
    async def tool_send_notification(
        self,
        message: str,
        notification_type: str,
        priority: str,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for sending a notification."""
        try:
            notification = await self.send_notification(
                message,
                notification_type,
                priority,
                topic
            )
            return {
                "notification": notification,
                "message": "Sent notification"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_get_notifications(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Tool handler for getting notifications."""
        try:
            notifications = await self.get_notifications(
                start_time,
                end_time,
                notification_type,
                priority,
                topic,
                limit
            )
            return notifications
        except ValueError as e:
            logger.error(f"Error getting notifications: {e}")
            return []
    
    async def tool_get_active_subscriptions(
        self,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Tool handler for getting active subscriptions."""
        try:
            subscriptions = await self.get_active_subscriptions(topic)
            return subscriptions
        except ValueError as e:
            logger.error(f"Error getting active subscriptions: {e}")
            return []
    
    async def cleanup(self):
        """Clean up resources."""
        # Cancel message processor
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # Clear subscriptions
        self.active_subscribers.clear()
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    def set_config_manager(self, config_manager):
        self.config_manager = config_manager
        config_manager.watch("*", self.config_change_handler)

    async def config_change_handler(self, change):
        # Send notification. Key is change.keys()[0].
        for key in change.keys():
          await self.send_notification(f"Configuration changed: {key} = {change[key]}", "INFO", "LOW", topic=key)
