from os.path import join, dirname
import pickle
import base64
import zlib

from PIL import Image
from kivy.compat import text_type
from kivy.graphics.context_instructions import Scale, Translate
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearColor, ClearBuffers
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import sp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from qrcode import QRCode, ERROR_CORRECT_H
import unidecode

from ia_scribe.libraries import barcode
from ia_scribe.libraries.barcode.writer import ImageWriter
from ia_scribe.libraries.qrcode_label import DETAILS_URL
from ia_scribe.utils import get_string_value_if_list
from ia_scribe import scribe_globals

Builder.load_file(join(dirname(__file__), 'book_slips.kv'))

NONE_STR = u'-'


class BookSlipItem(BoxLayout):

    key = StringProperty()
    text = StringProperty()


class BookSlipBase(GridLayout):
    _isbn = None


    def purify_string(self, string):
        if string:
            try:
                return unidecode.unidecode(string)
            except:
                return string.encode('utf-8').decode('utf-8').encode('ascii', 'ignore')
        else:
            return None

    def set_metadata(self, md):
        pass

    def create_qr_label_image(self, data=''):
        qr = QRCode(box_size=3,
                    error_correction=ERROR_CORRECT_H,
                    border=0)
        qr.add_data(data)
        qr.make()
        return qr.make_image().convert('RGB')

    def create_isbn_label_image(self, isbn):
        options = {
            'module_width': 0.3,
            'module_height': 15.0,
            'quiet_zone': 1.0,
            'font_size': 15,
            'text_distance': 1.0,
            'background': 'white',
            'foreground': 'black',
            'write_text': True,
            'text': '',
        }
        isbn_code = None
        '''
        if is_isbn13(isbn):
            isbn_code = barcode.ISBN13(isbn, writer=ImageWriter())
        elif is_isbn10(isbn):
            isbn_code = barcode.ISBN10(isbn, writer=ImageWriter())
        '''
        isbn_code = barcode.get('code128', isbn, writer=ImageWriter())
        if isbn_code:
            #print 'isbn is ->', isbn, '| generated ->', isbn_code
            return isbn_code.render(writer_options=options)
        return None

    def set_isbn_image(self, isbn, isbn_image):
        isbn_label = self.create_isbn_label_image(isbn)
        texture = isbn_image.texture
        if not texture or texture.size != isbn_label.size:
            isbn_image.texture = texture = Texture.create(size=isbn_label.size)
            print('[DEBUG] isbn texture size before flip:', isbn_image.texture.size)
            texture.flip_vertical()
        print('[DEBUG] isbn texture size:', isbn_image.texture.size)
        texture.blit_buffer(isbn_label.tobytes())

    def set_qr_image(self, data, qr_image):
        qr_label = self.create_qr_label_image(data)
        texture = qr_image.texture
        if not texture or texture.size != qr_label.size:
            qr_image.texture = texture = Texture.create(size=qr_label.size)
            print('[DEBUG] qr texture size before flipping:', qr_image.texture.size)
            texture.flip_vertical()
        print('[DEBUG] qr texture size:', qr_image.texture.size)
        texture.blit_buffer(qr_label.tobytes())

    def create_image(self):
        parent = self.parent
        if parent:
            canvas_parent_index = parent.canvas.indexof(self.canvas)
            if canvas_parent_index > -1:
                parent.canvas.remove(self.canvas)
        fbo = Fbo(size=self.size, with_stencilbuffer=True)
        with fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            Scale(1, -1, 1)
            Translate(-self.x, -self.y - self.height, 0)
        fbo.add(self.canvas)
        fbo.draw()
        image = Image.frombytes('RGBA', list(map(int, self.size)),
                                fbo.texture.pixels,
                                'raw', 'RGBA', 0, 1)
        fbo.remove(self.canvas)
        if parent is not None and canvas_parent_index > -1:
            parent.canvas.insert(canvas_parent_index, self.canvas)
        return image

    def export_image(self, filename, *args):
        image = self.create_image()
        image.save(filename)


class BookScannedNoMARCSlip(BookSlipBase):

    def set_metadata(self, md):
        ids = self.ids
        get = get_string_value_if_list
        ids.date.text = md['datetime'].strftime('%Y-%m-%d')
        ids.time.text = md['datetime'].strftime('%H:%M')
        ids.operator.text = (md.get('operator', None) or NONE_STR)\
            .replace('@archive.org', '', 1)
        ids.scanner.text = (md.get('scanner', None) or NONE_STR)\
            .replace('.archive.org', '', 1)
        self._isbn = md.get('isbn', None)
        ids.isbn.text = self._isbn  or NONE_STR
        ids.boxid.text = md.get('boxid', None) or NONE_STR
        ids.old_pallet.text = md.get('old_pallet', None) or NONE_STR
        ids.title.text = self.purify_string(md.get('title', None)) or NONE_STR
        ids.creator.text = self.purify_string(get(md, 'creator', u'; ')) or NONE_STR
        ids.pages.text = text_type(md.get('pages', None) or NONE_STR)
        identifier = md.get('identifier', None)
        ids.identifier.text = identifier if identifier else NONE_STR
        url = DETAILS_URL + identifier if identifier else NONE_STR
        ids.url.text = url
        self._set_qr_label(url)

    def _set_qr_label(self, data):
        qr_label = self.ids.qr_label
        qr_image = self.create_qr_label_image(data)
        texture = qr_label.texture
        if not texture:
            qr_label.texture = texture = Texture.create(size=qr_image.size)
        texture.blit_buffer(qr_image.tobytes())


class BookScannedSlip(BookSlipBase):

    def set_metadata(self, md):
        ids = self.ids
        ids.datetime.text = md['datetime'].strftime('%Y-%m-%d %H:%M')
        ids.operator.text = (md.get('operator', None) or NONE_STR) \
            .replace('@archive.org', '', 1)
        ids.scanner.text = (md.get('scanner', None) or NONE_STR) \
            .replace('@archive.org', '', 1)
        text = ('Box: [size={}][b]{}[/b][/size]'
                .format(int(sp(20)), md.get('boxid', None) or NONE_STR))
        ids.boxid.text = text
        text = ('Orig pallet: [size={}][b]{}[/b][/size]'
                .format(int(sp(20)), md.get('old_pallet', None) or NONE_STR))
        ids.original_pallet.text = text
        identifier = md.get('identifier', None)
        ids.title_identifier.text = identifier or NONE_STR
        url = DETAILS_URL + identifier if identifier else NONE_STR
        ids.url.text = url
        self.set_qr_image(url, ids.qr_label)
        ids.identifier.text = identifier or NONE_STR
        ids.title.text = self.purify_string(md.get('title', None)) or 'Unknown title'
        creator = (self.purify_string(get_string_value_if_list(md, 'creator', u'; '))
                   or 'Unknown creator')
        ids.creator.text = 'by [b]{}[/b]'.format(creator)
        ids.pages.text = ('[b]{}[/b] pages'
                          .format(md.get('pages', None) or NONE_STR))

        self.set_isbn_image(self._isbn, ids.isbn_label)


class BookRejectedSlip(BookSlipBase):

    title = StringProperty(NONE_STR)
    comment = StringProperty('')
    _line_offset = NumericProperty('30dp')

    def __init__(self, **kwargs):
        super(BookRejectedSlip, self).__init__(**kwargs)

    def set_metadata(self, md):
        # We end up here if the user selects the "Reject button"
        self.title = (u'[b]{}\n[size={}]UNSCANNED[/size][/b]'
                      .format(md['reason'], int(sp(22))))
        self.comment = u'[u]Comments[/u]: {}'.format(md['comment'])
        ids = self.ids
        #print(self, dir(self), self._isbn, md)
        ids.datetime.text = md['datetime'].strftime('%Y-%m-%d %H:%M')
        ids.operator.text = md.get('operator', None) or NONE_STR
        ids.scanner.text = md.get('scanner', None) or NONE_STR
        text = ('Orig pallet: [size={}][b]{}[/b][/size]'
                .format(int(sp(20)), md.get('old_pallet', None) or NONE_STR))
        ids.original_pallet.text = text
        self.set_qr_image(md.get('old_pallet', None) or NONE_STR, ids.qr_label)

        if self._isbn:
            self.set_isbn_image(self._isbn, ids.isbn_label)


class BookDoNotWantSlip(BookSlipBase):

    title = StringProperty(NONE_STR)
    comment = StringProperty('')
    _line_offset = NumericProperty('30dp')
    status_code = StringProperty('')

    def __init__(self, **kwargs):
        super(BookDoNotWantSlip, self).__init__(**kwargs)

    def set_metadata(self, md):
        self.title = md['reason'].upper()
        self.comment = md['comment']
        self.status_code = str(md.get('keep_dupe_status_code', ''))
        ids = self.ids
        # print(self, dir(self), self._isbn, md)
        ids.datetime.text = md['datetime'].strftime('%Y-%m-%d %H:%M')
        ids.operator.text = md.get('operator', None) or NONE_STR
        ids.scanner.text = md.get('scanner', None) or NONE_STR
        ids.original_pallet.text = ('Orig pallet: [size={}][b]{}[/b][/size]'
                .format(int(sp(20)), md.get('old_pallet', None) or NONE_STR))
        ids.boxid.text = ('BOXID: [size={}][b]{}[/b][/size]'
                                    .format(int(sp(20)), md.get('boxid', None) or NONE_STR))
        ids.selector.text = ('Selector: [size={}][b]{}[/b][/size]'
                                    .format(int(sp(20)), md.get('selector', None) or NONE_STR))

        self.make_qr(md)

    def make_qr(self, md):
        data_for_boxing_station = {
            'origin_scanner': md.get('scanner'),
            'origin_operator': md.get('operator'),
            'selector': md.get('selector'),
            'keep_dupe_status': md.get('keep_dupe_status'),
            'keep_dupe_status_code': str(md.get('keep_dupe_status_code')),
            'old_pallet': md.get('old_pallet'),
        }

        pickled_object = pickle.dumps(data_for_boxing_station, protocol=scribe_globals.PICKLE_PROTOCOL)
        compressed_pickled_object = zlib.compress(pickled_object)
        print(len(pickled_object), len(compressed_pickled_object))
        encoded_data_for_boxing_station = base64.b64encode(compressed_pickled_object).decode('utf-8')

        print(encoded_data_for_boxing_station)
        self.set_qr_image(encoded_data_for_boxing_station, self.ids.qr_label)


