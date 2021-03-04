from ia_scribe.uix.slips.book_slips import BookScannedNoMARCSlip
from testapps.book_slip_app import BookSlipApp, BOOK_SLIP_MD


class BookScannedNoMARCSlipApp(BookSlipApp):

    def build_slip(self):
        slip = BookScannedNoMARCSlip()
        slip.set_metadata(BOOK_SLIP_MD)
        return slip


if __name__ == '__main__':
    BookScannedNoMARCSlipApp().run()
