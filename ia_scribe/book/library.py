'''

This book library object is meant to serve a chokepoint through which all book objects are served

'''
from ia_scribe.book.book import Book
from ia_scribe.book.cd import CD
from ia_scribe import scribe_globals
from ia_scribe.abstract import singleton
import glob, os, time
from collections import Counter

# TODO: Add logger

REGISTERED_MEDIATYPES = {
    'Book': Book,
    'CD': CD,

}

@singleton
class Library(object):

    library_list = set()

    def __init__(self, root_dir = scribe_globals.BOOKS_DIR):
        self.__dict__['observers'] = {'events': [],
                                      'errors': [],}
        self.library_list = self._load_from_drive(root_dir)
        print('loaded {} items'.format(len(self.library_list)))

    def __iter__(self):
        for item in self.library_list:
            yield item

    def _book_constructor(self, id, **kwargs):
        return self._item_constructor(id, Book, **kwargs)

    def _item_constructor(self, id, item_type=None, **kwargs):
        init_dict = {'uuid': id}
        if len(kwargs) > 0:
            for k, v in kwargs.items():
                init_dict[k] = v
        if not item_type:
            item_type = self._infer_type(id)
        ret = item_type(init_dict, self.receive_item_event, self.delete_book)
        return ret

    def _get_id_from_path(self, path):
        ret = path.split('/')[-1:][0]
        return ret

    def _infer_type(self, id):
        return_type = Book
        path = os.path.expanduser(os.path.join(scribe_globals.BOOKS_DIR, id))
        type_file = os.path.join(path, 'type')
        if os.path.exists(type_file):
            file_content = ''
            with open(type_file, 'r') as f:
                file_content = f.read()
            if file_content in REGISTERED_MEDIATYPES:
                return_type = REGISTERED_MEDIATYPES[file_content]
        return return_type


    def _load_from_drive(self, root_dir):
        paths = glob.glob(os.path.join(root_dir, '*'))
        ids = list(map(self._get_id_from_path, paths))
        books_list = list(map(self._item_constructor, ids))
        return books_list

    def get_item(self, uuid):
        first_or_default = next((x for x in self.library_list
                                 if x.uuid == uuid), None)
        return first_or_default

    def get_book(self, uuid):
        first_or_default = next((x for x in self.library_list
                                 if x.uuid == uuid and type(x) is Book), None)
        return first_or_default

    def get_books(self, key, value, formatter=None, *args):
        if not formatter:
            ret = [x for x in self.library_list if x.get(key) == value and type(x) is Book]
        else:
            ret = [getattr(x , formatter)(*args) for x in self.library_list if x.get(key) == value and type(x) is Book]
        return ret

    def get_items(self, key, value, formatter=None, * args):
        if not formatter:
            ret = [x for x in self.library_list if x.get(key) == value ]
        else:
            ret = [getattr(x, formatter)(*args) for x in self.library_list if x.get(key) == value ]
        return ret

    def get_all_books(self):
        for book in [x for x in self.library_list if type(x) is Book]:
            yield book

    def get_all_items(self):
        for item in self.library_list:
            yield item

    # This is mostly used by the CLI
    def list_all_books(self, formatter=False, *args):
        if not formatter:
            formatter = '__repr__'
        return [getattr(x , formatter)(*args) for x in self.get_all_books()]

    # This is mostly used by the CLI
    def dict_all_books(self, formatter=False, *args):
        if not formatter:
            formatter = '__repr__'
        return {x.uuid: getattr(x, formatter)(*args) for x in self.get_all_books()}

    def get_stats(self):
        books_by_state = Counter(book.status for book in self.library_list)
        payload = {
                   'books_total': len(self.library_list),
                   'books_by_tts_state': dict(books_by_state),
                    }
        return payload

    def new_book(self, uuid, **kwargs):
        book = self._item_constructor(uuid, Book, **kwargs)
        self.library_list.append(book)
        self.notify('book_created', book)
        return self.get_item(book.uuid)

    def new_cd(self, uuid, **kwargs):
        new_cd = self._item_constructor(uuid, CD, **kwargs)
        self.library_list.append(new_cd)
        self.notify('cd_created', new_cd)
        return self.get_item(new_cd.uuid)

    def delete_book(self, book):
        return self.delete_item(book)

    def delete_item(self, item):
        item = self.library_list.remove(item)
        self.notify('item_deleted', item)
        return True

    def new_book_from_dict(self, init_dict):
        if 'uuid' not in init_dict:
            return False
        uuid = init_dict.pop('uuid')
        return self.new_book(uuid, **init_dict)

    # This is what books will call to send an event
    def receive_item_event(self, event, book, topic='events'):
        book.date = time.time()
        self.notify(event, book, topic)

    # Publisher methods
    def subscribe(self, observer, topic='events'):
        if observer not in self.observers[topic]:
            self.observers[topic].append(observer)

    def unsubcribe(self,  observer, topic='events'):
        self.observers[topic].remove(observer)

    # 'payload' instead of 'book' because we may want to
    #  use this for things like task % completion or library events
    def notify(self, event_type, payload, topic='events'):
        for observer in self.observers[topic][:]:
            if scribe_globals.DEBUG:
                print("\n}}}}}}}}}}}}}}}}}}}}\nnotifying", observer,
                      '\nevent type', event_type,
                      '\npayload', payload,
                      '\ntopic', topic,
                      '\n{{{{{{{{{{{{{{{{{{{{{{{{\n')
            observer(payload, event_type)

    def refresh(self):
        for item in self.library_list:
            self.notify('ping', item)

    def update(self, delta, uuid_dict):
        uuid = uuid_dict['uuid']
        item = self.get_item(uuid)
        return item.update(delta)
