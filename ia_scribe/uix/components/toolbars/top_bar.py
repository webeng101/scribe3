from os.path import dirname, join

from kivy.animation import Animation
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (StringProperty, BooleanProperty,
                             ObjectProperty, ListProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown

from ia_scribe.uix.components.buttons.buttons import ColorButton

Builder.load_file(join(dirname(__file__), 'top_bar.kv'))


class TopBar(BoxLayout):
    """Top bar widget displaying title, user button with dropdown list
    of options and go-back button.

    .. note::
        Go-back button is "hidden" when top bar is created, it's width is 0.
        Width of back-button's texture is used as button's width when
        :attr:`use_back_button` is set to True.
    """

    username = StringProperty()
    machine_id = StringProperty()
    use_back_button = BooleanProperty(False)

    back_button = ObjectProperty()
    dropdown = ObjectProperty()
    has_notification = BooleanProperty(False)
    notification_icon_path = StringProperty('notification_white.png')

    __events__ = ('on_option_select',)

    def __init__(self, **kwargs):
        super(TopBar, self).__init__(**kwargs)
        self.dropdown = dropdown = TopBarDropDown()
        dropdown.bind(on_select=self._on_dropdown_select)

    def on_use_back_button(self, top_bar, use_back_button):
        if use_back_button:
            anim = Animation(width=dp(50), d=0.4)
        else:
            anim = Animation(width=0, d=0.4)
        anim.start(self.back_button)

    def _on_dropdown_select(self, dropdown, option):
        self.dispatch('on_option_select', option)

    def on_option_select(self, option):
        pass

    def open_notifications_center(self):
        self.dispatch('on_option_select', 'notification_center')

    def highlight_notification(self, *args, **kwargs):
        self.has_notification = True

    def remove_highlight_notification(self):
        self.has_notification = False

    def on_has_notification(self, *args, **kwargs):
        self.notification_icon_path = \
            'notification_active_white_dot.png' if self.has_notification \
            else 'notification_white.png'


class TopBarUserButton(ButtonBehavior, BoxLayout):

    color_normal = ListProperty([0, 0, 0, 1.0])
    color_down = ListProperty([0.5, 0.5, 0.5, 1.0])


class TopBarDropDown(DropDown):

    def on_container(self, instance, container):
        container.padding = [0, dp(8), 0, dp(8)]
        container.spacing = dp(2)
        super(TopBarDropDown, self).on_container(instance, container)


class TopBarDropDownButton(ColorButton):

    icon = StringProperty()
