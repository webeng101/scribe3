import datetime
from functools import partial
from uuid import uuid4

from kivy.metrics import dp
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import (
    ListProperty,
    StringProperty,
    ObjectProperty,
    BooleanProperty,
    NumericProperty
)

from ia_scribe.abstract import singleton
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.utils import toast_notify

move_along_frequency = \
    Scribe3Configuration().get_numeric_or_none('periodic_move_along_interval')
DEFAULT_EXPIRATION = move_along_frequency if move_along_frequency else 60


class Notification(EventDispatcher):

    title = StringProperty()
    message = StringProperty()
    is_error = BooleanProperty(False)
    is_sticky = BooleanProperty(False)
    creation_date = ObjectProperty()
    expiration_date = ObjectProperty()
    show_system_tile = BooleanProperty(False)
    size_hint = ObjectProperty((1, None))
    type = StringProperty()
    height = NumericProperty(dp(54))

    EVENT_NOTIFICATION_DISMISS = 'on_notification_dismiss'
    EVENT_NOTIFICATION_SELECT = 'on_notification_select'

    __events__ = (EVENT_NOTIFICATION_DISMISS, EVENT_NOTIFICATION_SELECT,)

    def __init__(self, title, message, *args, **kwargs):
        super(Notification, self).__init__()
        self.uuid = str(uuid4())
        self.title = title
        self.message = message if message else ''
        self.is_error = kwargs.get('is_error', False)
        self.is_sticky = kwargs.get('is_sticky', False)
        self.creation_date = datetime.datetime.now()
        self.expiration_date = self.__get_expiration(
            kwargs.get('expiration', DEFAULT_EXPIRATION))
        self.show_system_tile = kwargs.get('show_system_tile', False)
        self.callback = kwargs.get('callback', None)
        self.type = kwargs.get('type', 'normal')
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        if self.show_system_tile:
            self.show_tile()

    def __get_expiration(self, expiration):
        expiration_date = \
            self.creation_date + datetime.timedelta(seconds=expiration)
        return expiration_date

    def __repr__(self):
        return '{} | {} {}'.format(self.type, self.title, self.message)

    def __getitem__(self, input):
        me = self.as_dict()
        ret = me[input]
        return ret

    def get(self, attr, alternative_value=None):
        if hasattr(self, attr):
            return getattr(self, attr)
        else:
            return alternative_value

    def as_dict(self):
        return {
            'uuid': self.uuid,
            'title': self.title,
            'message': self.message,
            'is_error': self.is_error,
            'is_sticky': self.is_sticky,
            'expiration_date': self.expiration_date,
            'creation_date': self.creation_date,
            'show_system_tile': self.show_system_tile,
            'type': self.type,
        }

    def show_tile(self):
        title = '{} | {}'.format('Scribe3', self.title)
        toast_notify(self.message, title)

    def is_expired(self):
        return datetime.datetime.now() > self.expiration_date

    def dismiss(self):
        self.dispatch(self.EVENT_NOTIFICATION_DISMISS)

    def select(self):
        self.dispatch(self.EVENT_NOTIFICATION_SELECT)

    def on_notification_dismiss(self):
        pass

    def on_notification_select(self):
        pass


class BookNotification(Notification):

    book = ObjectProperty(allownone=False)

    def __init__(self, book, *args, **kwargs):
        super(BookNotification, self).__init__(*args, **kwargs)
        self.book = book
        self.type = 'book'


class SystemNotification(Notification):

    def __init__(self, *args, **kwargs):
        super(SystemNotification, self).__init__(*args, **kwargs)
        self.type = 'system'


NOTIFICATION_TYPES = {
    'normal': Notification,
    'book': BookNotification,
    'system': SystemNotification,
}


@singleton
class NotificationManager(EventDispatcher):

    __events__ = ('on_notification_added', 'on_notification_removed',)

    notifications = ListProperty([])

    def add_notification(self, title, message,
                         is_error=False, expiration=DEFAULT_EXPIRATION,
                         show_system_tile=False, callback=None,
                         is_sticky=False,
                         book=None, notification_type='normal'):

        if book:
            notification = BookNotification(
                title=str(title),
                message=str(message),
                is_error=is_error,
                expiration=expiration,
                show_system_tile=show_system_tile,
                callback=callback,
                book=book,
                is_sticky=is_sticky,
            )
        else:
            notification_class = NOTIFICATION_TYPES.get(notification_type,
                                                        Notification)
            notification = notification_class(
                title=str(title),
                message=str(message),
                is_error=is_error,
                expiration=expiration,
                show_system_tile=show_system_tile,
                callback=callback,
                is_sticky=is_sticky,
            )

        self.notifications.append(notification)
        self.mainthread_dispatch('on_notification_added', notification)
        return notification

    def get_all_notifications(self, sticky_first=True):
        if sticky_first:
            normal_notifications = list(
                reversed([x for x in self.notifications if not x.is_sticky])
            )
            sticky_notifications = \
                [x for x in self.notifications if x.is_sticky]
            ret = sticky_notifications + normal_notifications
        else:
            ret = reversed(self.notifications)
        return ret

    def get_notifications_by_type(self, type):
        return [x for x in self.notifications if x['type'] == type]

    def get_notification_by_uuid(self, uuid):
        notifications_candidates = [x for x in self.notifications if
                                    x['uuid'] == uuid]
        if len(notifications_candidates) == 1:
            return notifications_candidates[0]
        return None

    def remove_notification(self, notification):
        concrete_notification = \
            self.get_notification_by_uuid(notification.uuid)
        if concrete_notification:
            if not concrete_notification.is_sticky:
                self.notifications.remove(notification)
                self.mainthread_dispatch('on_notification_removed',
                                         notification)

    def mainthread_dispatch(self, event_name, *args, **kwargs):
        method = partial(self.dispatch_callback, event_name, args, kwargs)
        Clock.schedule_once(method)

    def dispatch_callback(self, event_name, args, kwargs, dt):
        self.dispatch(event_name, *args, **kwargs)

    def on_notification_added(self, notification):
        pass

    def on_notification_removed(self, notification):
        notification.dismiss()
