from ia_scribe.uix.actions.info import ShowInfoActionPopupMixin


class ShowErrorAction(ShowInfoActionPopupMixin):
    def __init__(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Error'
        super(ShowErrorAction, self).__init__(**kwargs)
