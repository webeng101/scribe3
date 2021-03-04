from ia_scribe.tasks.ui_handlers.ui_handler import TaskUIHandler
from ia_scribe.tasks.metadata import DeferredMetadataViaWonderfetch


class DeferredMetadataViaWonderfetchUIHandler(TaskUIHandler):

    def __init__(self, **kwargs):
        self.task = DeferredMetadataViaWonderfetch(book=kwargs['book'])
        super(DeferredMetadataViaWonderfetchUIHandler, self).__init__(**kwargs)
