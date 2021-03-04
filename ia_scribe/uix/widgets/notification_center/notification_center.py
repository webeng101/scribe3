from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import (
    StringProperty,
    NumericProperty,
    ObjectProperty,
    BooleanProperty,
    ListProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior

Builder.load_file(join(dirname(__file__), 'notification_center.kv'))


class NotificationView(RecycleDataViewBehavior, BoxLayout):

    index = NumericProperty(-1)
    uuid = StringProperty()
    title = StringProperty()
    message = StringProperty()
    type = StringProperty()
    creation_date = ObjectProperty('')
    expiration_date = ObjectProperty('')
    show_system_tile = BooleanProperty(False)
    is_error = BooleanProperty()
    is_sticky = BooleanProperty()
    color = ListProperty()

    __events__ = ['on_notification_dismiss', 'on_notification_select']

    def __init__(self):
        super(NotificationView, self).__init__()

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.uuid = data.get('uuid')
        self.message = data.get('message')
        self.is_error = data.get('is_error')
        self.is_sticky = data.get('is_sticky')
        self.title = data.get('title')
        self.creation_date = str(data.get('creation_date'))
        self.expiration_date = str(data.get('expiration_date'))
        self.type = data.get('type')
        self.resolve_color()

    def resolve_color(self):
        if self.is_error:
            self.color = [1, 0, 0, .3]
        elif self.is_sticky:
            self.color = [0.5, 0.5, 0.5, .7]
        else:
            self.color = [0.5, 0.5, 0.5, .2]

    def _dismiss_notification(self):
        self.dispatch('on_notification_dismiss', self.uuid)

    def _select_notification(self):
        self.dispatch('on_notification_select', self.uuid)

    def force_update(self, *args):
        ids = self.ids
        self._trigger_layout.cancel()
        self.do_layout()
        ids.title_and_message._trigger_layout.cancel()
        ids.title_and_message.do_layout()
        ids.message_label._trigger_texture.cancel()
        ids.message_label.texture_update()
        height = ids.message_label.height + ids.title_label.height
        height += self.padding[1] + self.padding[3]
        self.height = height

    def on_notification_dismiss(self, *args):
        pass

    def on_notification_select(self, *args):
        pass


class NotificationsContainer(RecycleGridLayout):

    def __init__(self, **kwargs):
        super(NotificationsContainer, self).__init__(**kwargs)

    __events__ = ('on_view_added', 'on_view_removed')

    def add_widget(self, widget, index=0):
        super(NotificationsContainer, self).add_widget(widget, index)
        self.dispatch('on_view_added', widget)

    def remove_widget(self, widget):
        super(NotificationsContainer, self).remove_widget(widget)
        self.dispatch('on_view_removed', widget)

    def on_view_added(self, view):
        pass

    def on_view_removed(self, view):
        pass

class NotificationsRecycleView(RecycleView):

    EVENT_ENTRY_SELECTED = 'on_entry_selected'
    EVENT_ENTRY_DISMISSED = 'on_entry_dismiss'

    __events__ = (EVENT_ENTRY_SELECTED,EVENT_ENTRY_DISMISSED,)

    def __init__(self, **kwargs):
        super(NotificationsRecycleView, self).__init__(**kwargs)

    def on_layout_manager(self, view, layout_manager):
        if layout_manager:
            layout_manager.bind(on_view_added=self._on_view_added,
                                on_view_removed=self._on_view_removed)

    def _on_view_added(self, layout_manager, view):
        if isinstance(view, NotificationView):
            view.fbind('on_notification_dismiss', self._on_view_dismiss)
            view.fbind('on_notification_select', self._on_view_select)

    def _on_view_removed(self, layout_manager, view):
        if isinstance(view, NotificationView):
            view.funbind('on_notification_dismiss', self._on_view_dismiss)
            view.funbind('on_notification_select', self._on_view_select)

    def _on_view_select(self, widget, uuid):
        self.dispatch(self.EVENT_ENTRY_SELECTED, uuid)

    def _on_view_dismiss(self, widget, uuid):
        self.dispatch(self.EVENT_ENTRY_DISMISSED, uuid)

    def on_entry_selected(self, *args):
        pass

    def on_entry_dismiss(self, *args):
        pass


class NotificationCenterWidget(BoxLayout):
    notifications = ListProperty()
    filtered_notifications = ListProperty()
    backend = ObjectProperty(allownone=True)
    book_handler = ObjectProperty(allownone=True)
    filter_types = ObjectProperty(['all'])
    filter_option = StringProperty('all')

    _notification_view = NotificationView()

    def __init__(self, **kwargs):
        super(NotificationCenterWidget, self).__init__(**kwargs)
        self.ids.rv.bind(on_entry_selected=self.select_notification)
        self.ids.rv.bind(on_entry_dismiss=self.dismiss_notification)

    def _update_rv_data(self):
        self._do_filtering()
        rv = self.ids.rv
        rv.data = self.filtered_notifications[:]
        rv.scroll_y = 1.0
        self._update_filter_types()

    def _update_filter_types(self, *args):
        all_types = set([item['type'] for item in self.notifications])
        self.filter_types = ['all'] + list(all_types)

    def _update_filter_option(self, input, value):
        self.filter_option = value

    def _do_filtering(self):
        if self.filter_option == 'all':
            self.filtered_notifications = self.notifications
        else:
            self.filtered_notifications = [x for x in self.notifications if x['type'] == self.filter_option]

    def attach(self, manager, book_handler):
        self.notifications = manager.get_all_notifications()
        for notification in self.notifications:
            self._update_notification_height(notification)
        manager.fbind('on_notification_added', self._on_notification_added)
        manager.fbind('on_notification_removed', self._on_notification_removed)
        self.backend = manager
        self.book_handler = book_handler
        self._update_rv_data()

    def detach(self, *args, **kwargs):
        manager = self.backend
        manager.funbind('on_notification_added', self._on_notification_added)
        manager.funbind('on_notification_removed', self._on_notification_removed)
        self.backend = None
        self.book_handler = None

    def dismiss_notification(self, widget, uuid):
        notification = self.backend.get_notification_by_uuid(uuid)
        self.backend.remove_notification(notification)
        self._update_rv_data()

    def select_notification(self, widget, uuid):
        notification = self.backend.get_notification_by_uuid(uuid)
        if self.book_handler and hasattr(notification, 'book'):
            self.book_handler.on_select(None, notification.book)

    def clear_all(self):
        for notification in self.notifications:
            self.dismiss_notification(None, notification.uuid)

    def clear_visible(self):
        for notification in self.filtered_notifications:
            self.dismiss_notification(None, notification.uuid)

    def _on_notification_added(self, manager, notification, *args, **kwargs):
        self._update_notification_height(notification)
        self.notifications = self.backend.get_all_notifications()
        self._update_rv_data()

    def _on_notification_removed(self, *args, **kwargs):
        self.notifications = self.backend.get_all_notifications()
        self._update_rv_data()

    def _on_notification_selected(self, *args, **kwargs):
        pass

    def on_filter_option(self, *args):
        self._update_rv_data()

    def _update_notification_height(self, notification):
        view = self._notification_view
        view.width = self.width
        view.refresh_view_attrs(self.ids.rv, 0, notification)
        view.force_update()
        notification.height = self._notification_view.height
