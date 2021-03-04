from ia_scribe.uix.slips.book_slips import BookRejectedSlip
from testapps.book_slip_app import BookSlipApp, BOOK_SLIP_MD


class BookRejectedSlipApp(BookSlipApp):

    def build_slip(self):
        slip = BookRejectedSlip()
        md = BOOK_SLIP_MD
        md['reason'] = 'Margins too tight'
        md['comment'] = 'The inner margin does not allow for ' \
                        'scanning on current equipment.'
        slip.set_metadata(BOOK_SLIP_MD)
        return slip


if __name__ == '__main__':
    BookRejectedSlipApp().run()
