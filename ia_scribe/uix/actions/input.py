from ia_scribe.uix.components.poppers.popups import InputPopup
from ia_scribe.uix.actions.generic import Action
from ia_scribe.uix.actions.helpers import PopupCreator

class InputActionPopupMixin(Action, PopupCreator):
    """
    A base class that captures the use case of asking for the user for
    an explicit input, like a number or a string
    """
    def __init__(self, title, message='', **kwargs):
        self.title = title
        self.message = message
        self.input_value = kwargs.pop('input_value', '')
        self.extra_args = kwargs.pop('extra', None)
        super(InputActionPopupMixin, self).__init__(**kwargs)
        self.popup_cls = InputPopup
        self.popup_args = {'title': self.title,
                           'message': self.message,
                           'input_value': self.input_value,
                           'extra': kwargs.get('extra'), }
        self.create_popup(popup_cls=self.popup_cls, **self.popup_args)

    def on_submit(self, popup, value, *args):
        self.popup.dismiss(animation=False)
        self.do_action(self, popup, value)