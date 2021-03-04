from ia_scribe.uix.actions.generic import Action
from ia_scribe.uix.actions.helpers import PopupCreator
from ia_scribe.uix.components.poppers.popups import InfoPopup, CompositeInfoPopup
from ia_scribe.uix.components.plots.path_visualization import PathVisualizationWidget



class InfoActionPopupMixin(Action, PopupCreator):
    """
    A base class that implements a no-op action and an info popup.
    It's used to show things to the user where no further action is required.
    """
    def __init__(self, **kwargs):
        self.popup_cls = InfoPopup
        super(InfoActionPopupMixin, self).__init__(**kwargs)


class ShowInfoActionPopupMixin(InfoActionPopupMixin):
    def __init__(self, **kwargs):
        self.message = kwargs.pop('message', '')
        self.title = kwargs.pop('title', 'Information')
        super(ShowInfoActionPopupMixin, self).__init__(on_popup_dismiss=kwargs.get('on_popup_dismiss'),
                                                       on_popup_open=kwargs.get('on_popup_open'))

    def display(self):
        create_popup_kwargs = {'popup_cls': self.popup_cls,
                               'title': self.title,
                               'message': self.message}
        self.create_popup(**create_popup_kwargs)
        self.popup.bind(on_submit=self.popup.dismiss)
        self.popup.open()


class ShowGenericInfoAction(ShowInfoActionPopupMixin):
    def __init__(self, **kwargs):
        self.additional_content = kwargs.get('additional_content', None)
        super(ShowGenericInfoAction, self).__init__(**kwargs)
        self.popup_cls = CompositeInfoPopup

    def build_additional_content(self):
        return self.additional_content

    def display(self):
        additional_content = self.build_additional_content()
        create_popup_kwargs = {'popup_cls': self.popup_cls,
                               'title': self.title,
                               'message': self.message,
                               'additional_content': additional_content}
        self.create_popup(**create_popup_kwargs)
        self.popup.bind(on_submit=self.popup.dismiss)
        self.popup.open()


class ShowPathAction(ShowGenericInfoAction):
    def __init__(self, **kwargs):
        self.book = kwargs.pop('book')
        super(ShowPathAction, self).__init__(**kwargs)
        self.title = 'Path to upload'

    def build_additional_content(self):
        path_widget = PathVisualizationWidget()
        path_widget.make_data(self.book.get_path_to_upload(human_readable=True), )
        return path_widget