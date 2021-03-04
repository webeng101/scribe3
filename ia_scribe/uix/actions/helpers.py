from kivy.uix.popup import Popup


class PopupCreator(object):
    """
    A base class that spawns popups and is used in the Actions hierarchy
    as there is an expectation that often actions require interacting with the user.
    This is meant to become a one-stop-shop to spawn dialog popups throughout the app.

    This class is agnostic and does not keep a reference to a specific popup class.
    Users are expected to implement their own call to create_popup
    """
    popup = None

    def __init__(self, on_popup_open=None, on_popup_dismiss=None, **kwargs):
        self._on_popup_open = on_popup_open
        self._on_popup_dismiss = on_popup_dismiss
        super(PopupCreator, self).__init__(**kwargs)

    def popup_setup_callback(self):
        self.popup.bind(on_submit=self.on_submit)

    def create_popup(self, **kwargs):
        popup_cls = kwargs.pop('popup_cls', Popup)
        self.popup = popup_cls(**kwargs)
        self.popup_setup_callback()
        if self._on_popup_open:
            self.popup.bind(on_open=self._on_popup_open)
        if self._on_popup_dismiss:
            self.popup.bind(on_dismiss=self._on_popup_dismiss)

    def display(self):
        self.popup.open()

    def on_submit(self, popup, option, *args):
        pass