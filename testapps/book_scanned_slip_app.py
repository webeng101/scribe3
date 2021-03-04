from ia_scribe.uix.slips.book_slips import BookScannedSlip
from testapps.book_slip_app import BookSlipApp, BOOK_SLIP_MD


class BookScannedSlipApp(BookSlipApp):

    def build_slip(self):
        slip = BookScannedSlip()
        slip.set_metadata(BOOK_SLIP_MD)
        return slip


if __name__ == '__main__':
    BookScannedSlipApp().run()
