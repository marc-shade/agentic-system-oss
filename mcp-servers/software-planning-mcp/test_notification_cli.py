#!/usr/bin/env python
import asyncio
from src.core.notification_manager import NotificationManager, NotificationType, NotificationPriority

async def test():
    manager = NotificationManager()
    try:
        # Send a test notification
        await manager.send_notification(
            'Test from CLI', 
            NotificationType.INFO, 
            NotificationPriority.MEDIUM
        )
        
        # Get all notifications
        notifications = await manager.get_notifications()
        print(f'Notifications: {notifications}')
        
        # Get active subscriptions
        subscriptions = await manager.get_active_subscriptions()
        print(f'Active subscriptions: {subscriptions}')
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
