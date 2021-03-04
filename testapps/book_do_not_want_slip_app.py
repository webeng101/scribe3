from ia_scribe.uix.slips.book_slips import BookDoNotWantSlip
from testapps.book_slip_app import BookSlipApp, BOOK_SLIP_MD


class BookRejectedSlipApp(BookSlipApp):

    def build_slip(self):
        slip = BookDoNotWantSlip()
        md = BOOK_SLIP_MD
        md['reason'] = 'Duplicate'
        md['comment'] = 'BOXED'
        md['keep_dupe_status_code'] = 1
        md['selector'] = '0123456789'
        slip.set_metadata(md)
        return slip


if __name__ == '__main__':
    BookRejectedSlipApp().run()

