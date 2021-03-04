

import os
import urllib.request, urllib.parse, urllib.error
from io import StringIO
from PIL import Image, ImageDraw, ImageFont
import textwrap, qrcode
from ia_scribe.scribe_globals import IMAGES_DIR

'''
# Original Libraries                                     Decoupling
# ------------------------------------------------------------------
import iaclient                                             # Done
from iaclient.hw.printing import Printer, LabelPrinter      # Done
from archivecd.config.constants import ARCHIVE_URL          # Done
from archivecd.lib import identifier                        # Done
from archivecd.lib.formutils import strlist_to_str          # Done
'''


ARCHIVE_URL = "https://archive.org"
FONT = 'assets/fonts/DejaVuSansMono-Bold.ttf'


DETAILS_URL = "%s/%s/" % (ARCHIVE_URL, 'details')
DOWNLOAD_URL = "%s/%s" % (ARCHIVE_URL, 'download')
TEXT_FONT_SIZE = 65
TEXT_SIZE = TEXT_FONT_SIZE + 2
TEXT_BASE = 17      # Meh ...
URL_FONT_SIZE = 50  # 34 (URLs) or 50 (barcodes)
URL_TEXT_SIZE = URL_FONT_SIZE + 4
IMAGE_DIMENSIONS = (350, 350)
LABEL_DIMENSIONS = (2100, 675)  # TODO: 300x600 DPI @ 1.125" x 3.5"
ORIGIN_DIMENSIONS = (0, 0)
WIDTH, HEIGHT = [0, 1]
LOGO = Image.open(os.path.join(IMAGES_DIR, 'logo_larger_notrans.png'))


class BookLabel():

    def __init__(self, itemid, title, artists, logo=None):
        self.itemid = itemid
        self.item_url = DETAILS_URL + itemid
        self.title = title
        self.artists = artists
        self.logo = logo or LOGO
        self.qr = to_qrcode(self.item_url)


    def _draw_label_url(self, draw, url_start=40, always_wrap=False):
        """Draws the item's URL"""
        url_allowed_size = LABEL_DIMENSIONS[WIDTH] - url_start
        cpl = self.chars_possible(URL_FONT_SIZE, url_allowed_size)

        if always_wrap:
            lines = len(wrap(DETAILS_URL, cpl))
            url_start_height = LABEL_DIMENSIONS[HEIGHT] - (URL_TEXT_SIZE) * (lines + 2)
            lines = self.draw_text(draw, (url_start, url_start_height), DETAILS_URL,
                                   URL_FONT_SIZE, URL_TEXT_SIZE, wrap_lines=cpl,
                                   row_limit=2)

            url_start_height = LABEL_DIMENSIONS[HEIGHT] - (URL_TEXT_SIZE * (lines + 1))
            lines = self.draw_text(draw, (url_start, url_start_height), self.itemid,
                                           URL_FONT_SIZE, URL_TEXT_SIZE, wrap_lines=cpl,
                                           row_limit=2)
        else:
            lines = len(wrap(self.item_url, cpl))
            url_start_height = LABEL_DIMENSIONS[HEIGHT] - (URL_TEXT_SIZE * (lines + 1))
            lines = self.draw_text(draw, (url_start, url_start_height),
                                           self.item_url, URL_FONT_SIZE, URL_TEXT_SIZE,
                                           wrap_lines=cpl, row_limit=2)
        url_height = URL_TEXT_SIZE + URL_TEXT_SIZE * lines
        return url_height


    def _draw_label_qr(self, label, height):
        """Resize QR code to make the URL fit below the qr code (possibly making the
        QR code larger even
        """
        width = height  # QR code is square
        qr_dimensions = (width, height)
        qr = self.qr.resize(qr_dimensions, resample=Image.ANTIALIAS)
        qr_pos = (LABEL_DIMENSIONS[WIDTH] - width + 25, -25)
        label.paste(qr, qr_pos)


    def _draw_label_text(self, draw, qr_width):
        """Calculate # chars per line possible with the static font size"""
        text_start = IMAGE_DIMENSIONS[WIDTH] + 32
        text_stop = LABEL_DIMENSIONS[WIDTH] - qr_width - 30
        cpl = self.chars_possible(TEXT_FONT_SIZE, text_stop - text_start)

        # Draw metadata text
        tot = self.draw_text(draw, (text_start, TEXT_BASE),
                                   'Identifier: ' + self.itemid, TEXT_FONT_SIZE,
                                   TEXT_SIZE, wrap_lines=cpl, row_limit=2)

        # The next metadata starts higher
        start_height = TEXT_BASE + (tot + 1) * TEXT_SIZE
        self.draw_text(draw, (text_start, start_height),
                       'Title: ' + self.title,
                       TEXT_FONT_SIZE, TEXT_SIZE, wrap_lines=cpl,
                       row_limit=2)

        start_height = TEXT_BASE + (tot + 3) * TEXT_SIZE
        self.draw_text(draw, (text_start, start_height),
                       'Authors: ' + strlist_to_str(self.artists),
                       TEXT_FONT_SIZE, TEXT_SIZE, wrap_lines=cpl,
                       row_limit=3)


    def _draw_label_logo(self, label):
        logo = self.logo.resize(IMAGE_DIMENSIONS, resample=Image.ANTIALIAS)
        label.paste(logo, ORIGIN_DIMENSIONS)


    def create_label(self, always_wrap=False):
        """Generates a label image which contain the item id, the url to the item, the
        barcode encoding of the url, and some metadata. Can be converted to pdf using
        the `pdf` function.

        Return:
            A label (PIL.Image) with text, a qr code, url, title, and logo
        """
        label = Image.new('RGB', LABEL_DIMENSIONS)
        draw = ImageDraw.Draw(label)  # Image starts black
        draw.rectangle([ORIGIN_DIMENSIONS, LABEL_DIMENSIONS], fill='white')

        url_height = self._draw_label_url(draw, always_wrap=always_wrap)
        qr_dimensions = [label.size[HEIGHT] - url_height] * 2
        self._draw_label_qr(label, qr_dimensions[HEIGHT] + 35)
        self._draw_label_logo(label)
        self._draw_label_text(draw, qr_dimensions[WIDTH])
        return label


    def chars_possible(self, font_size, width):
        """A heuristic which approximates the number of characters which can
        fit within a given width.

        Note: Monospace fonts offer more reliable and predictable results

        Args:
            font_size - size of font in... (unit?)
            width (int) - a width in pixels

        Usage:
            >>> Label.chars_possible(12, 200)
        """
        return int(float(width) / (font_size * 0.6))

    def draw_text(self, img, top, text, font_size, text_size,
                  wrap_lines=50, row_limit=5, font=FONT, dowrap=True):
        """Renders text wrapping on an image

        Args:
            img (PIL.ImageDraw.Draw(PIL.Image)) - an image on which to draw
        """
        # TODO: Loading the font every time is not OK
        f = ImageFont.truetype(font, font_size)

        texts = wrap(text, wrap_lines, row_limit) if dowrap else [[]]

        for cnt, t in enumerate(texts):
            pos = (top[0], top[1] + text_size * cnt)
            img.text(pos, t, fill='black', font=f)

        return cnt + 1


def strlist_to_str(x):
    """Given a list of strings, flatten them into one '; ' separated string.

    Args:
        x : None, or list or tuple (possibly empty) of strings
    """
    if not x:
        return ''

    # definitely shouldn't be a string
    if isinstance(x, str):
        raise TypeError(x)

    return '; '.join(x)

def wrap(text, linelength, row_limit=None):
    """Takes a long string of `text` and splits it into a list of
    `row_limit` strings of length `linelength`.

    Args:
        text (unicode) - the text to wrap
        linelength     - the limit of number of chars for each line
        row_limit      - the max number of rows/lines to keep
    """
    return textwrap.wrap(text, width=linelength + 1)[:row_limit]

def to_qrcode(url, size=20):
    """Converts a url (or text) into a QR Code.

    Args:
        url (unicode) - the url or text to turn into a QR Code
        size (int)    - the box size of the QR Code

    Result:
        A (PIL.Image) QR Code or a pdf (tempfile.NamedTemporaryFile) as
        returned by converters.image.to_pdf if pdf=True
    """
    qr = qrcode.QRCode(
        box_size=size, error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(url)
    qr.make()
    img = qr.make_image()
    return img
