from ia_scribe.tasks.ui_handlers.ui_handler import TaskUIHandler
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.tasks.composite import MakeAndPrintSlipTask
from ia_scribe.tasks.metadata import LiteMetadataViaIdentifierTask
from ia_scribe.tasks.book import BookTask


class GenerateAndPrintSlipUIHandler(TaskUIHandler):

    def __init__(self, **kwargs):
        self.task = MakeAndPrintSlipTask(type=kwargs['type'],
                                         book=kwargs['book'],
                                         slip_metadata=kwargs['slip_metadata'])
        super(GenerateAndPrintSlipUIHandler, self).__init__(**kwargs)


class LiteMetadataViaIdentifierTaskUIHandler(TaskUIHandler):

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        self.task = LiteMetadataViaIdentifierTask(identifier=kwargs['identifier'],
                                                  book_path=self.book.path,
                                                  book=self.book)
        super(LiteMetadataViaIdentifierTaskUIHandler, self).__init__(**kwargs)


class BookTaskUIHandler(GenericUIHandler):
    def __init__(self, **kwargs):
        super(BookTaskUIHandler, self).__init__(BookTask, **kwargs)
