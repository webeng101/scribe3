from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.notifications.notifications_manager import NotificationManager

nm = NotificationManager()
fun = nm.add_notification

config = Scribe3Configuration()

LIBRARY_EVENTS = ['book_created', 'book_deleted',]
BOOK_EVENTS = ['identifier-changed', 'state_change', 'book_update', ]
IGNORE_EVENTS = ['message-updated', 'reloaded_metadata', 'reloaded_scandata', ]

def book_adapter(book, event_type):
    if event_type in IGNORE_EVENTS:
        return
    elif event_type in BOOK_EVENTS:
        if config.is_true('show_book_notifications'):
            fun(title='{}'.format(book.name_human_readable()),
                message='{}'.format(book.last_activity),
                show_system_tile=False,
                book=book)
    elif event_type in LIBRARY_EVENTS:
        if config.is_true('show_library_notifications'):
            fun(title='{}'.format(book.name_human_readable()),
               message='{}'.format(event_type),
               show_system_tile=False,
               book=book)
    else:
        fun(title='{}'.format(book.name_human_readable()),
            message='{}'.format(event_type),
            show_system_tile=False,
            book=book)


def book_error_adapter(book, event_type):
    if config.is_true('show_book_errors_notifications'):
        fun(title='Error on {}'.format(book.name_human_readable()),
            message='{}'.format(event_type),
            is_error=True,
            show_system_tile=False,
            book=book)