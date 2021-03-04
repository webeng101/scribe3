from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.notifications.notifications_manager import NotificationManager


class NotificationsCleanerTask(TaskBase):

    def __init__(self, **kwargs):
        super(NotificationsCleanerTask, self).__init__(**kwargs)
        self._notification_manager = NotificationManager()

    def create_pipeline(self):
        return [
            self._clean_expired_notifications,
        ]

    def _clean_expired_notifications(self):
        for notification in self._notification_manager.get_all_notifications():
            if notification.is_expired() and not notification.is_sticky:
                self._notification_manager.remove_notification(notification)

