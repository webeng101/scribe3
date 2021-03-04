from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.scrollview import ScrollView

from ia_scribe.utils import get_string_value_if_list

Builder.load_file(join(dirname(__file__), 'book_info_panel.kv'))

NONE_STR = u'-'


class BookInfoPanel(ScrollView):

    cover_image = StringProperty()
    title = StringProperty(NONE_STR)
    creator = StringProperty(NONE_STR)
    collection = StringProperty(NONE_STR)
    shiptracking_id = StringProperty(NONE_STR)
    scandate = StringProperty(NONE_STR)
    ppi = StringProperty(NONE_STR)
    scribe_operator = StringProperty(NONE_STR)
    republisher_operator = StringProperty(NONE_STR)
    scanner = StringProperty(NONE_STR)
    curator = StringProperty(NONE_STR)
    claimer = StringProperty(NONE_STR)
    curatenote = StringProperty(NONE_STR)

    def update_from_metadata(self, metadata):
        md = metadata
        get = get_string_value_if_list
        self.title = get(md, 'title') or NONE_STR
        self.creator = get(md, 'creator') or get(md, 'author') or NONE_STR
        self.collection = get(md, 'collection') or NONE_STR
        self.shiptracking_id = get(md, 'shiptracking') or NONE_STR
        self.scandate = get(md, 'scandate') or NONE_STR
        ppi = get(md, 'ppi')
        self.ppi = NONE_STR if ppi is None else str(ppi)
        self.scribe_operator = get(md, 'operator') or NONE_STR
        self.republisher_operator = get(md, 'uploader') or NONE_STR
        self.scanner = get(md, 'scanner') or NONE_STR
        self.curator = get(md, 'curator') or NONE_STR
        self.curatenote = get(md, 'curatenote') or NONE_STR
