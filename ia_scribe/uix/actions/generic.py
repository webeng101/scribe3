from ia_scribe.uix.actions.helpers import PopupCreator
from ia_scribe.uix.components.poppers.popups import QuestionPopup


class Action(object):

    def __init__(self, **kwargs):
        self._action_function = kwargs.pop('action_function', None)
        super(Action, self).__init__(**kwargs)

    def do_action(self, *args, **kwargs):
        self._action_function(*args, **kwargs)


class YesNoActionPopupMixin(Action, PopupCreator):
    """
    this class captures the pattern of
    "ask the user for something, then depending on the answer do it or not"
    Action is the thing to do
    PopupCreator is how we ask for input
    """
    def __init__(self, title, message, **kwargs):
        self.title = title
        self.message = message
        self.extra_args = kwargs.pop('extra', None)
        super(YesNoActionPopupMixin, self).__init__(**kwargs)
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': self.title,
                           'message': self.message,
                           'extra': self.extra_args, }
        self.create_popup(popup_cls=self.popup_cls, **self.popup_args)

    def on_submit(self, popup, option, *args, **kwargs):
        if option == self.popup.OPTION_YES:
            self.popup.dismiss(animation=False)
            self.do_action(self, popup, *args, **kwargs)


class ColoredYesNoActionPopupMixin(YesNoActionPopupMixin):

    def popup_setup_callback(self):
        self.popup.bind(on_submit=self.on_submit)
        self.popup.set_option_attrs(self.popup.OPTION_YES,
                                    color_normal=[0, 0.5, 0, 1],
                                    color_down=[0, 1, 0, 1])
        self.popup.set_option_attrs(self.popup.OPTION_NO,
                                    color_normal=[0.5, 0, 0, 1],
                                    color_down=[1, 0, 0, 1])

