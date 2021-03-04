import os, shutil
import regex as re
from uuid import uuid4
from PIL import Image

from ia_scribe.utils import convert_scandata_angle_to_thumbs_rotation
from ia_scribe.tasks.task_base import TaskBase, CANCELLED_WITH_ERROR
from ia_scribe.book.scandata import ScanData
from ia_scribe.book.metadata import get_metadata, get_sc_metadata, set_metadata
from ia_scribe.config.config import Scribe3Configuration


class ImportFolderTask(TaskBase):

    def __init__(self, **kwargs):
        super(ImportFolderTask, self).__init__(**kwargs)
        self.source_path = kwargs['path']
        self.library = kwargs['library']
        self.book_obj = None
        self.image_stack = None
        self.scandata = None
        self.metadata = None
        self.DEFAULT_FIELDS_AND_VALUES = [
                ('operator',  get_sc_metadata()['operator']),
                ('scanningcenter',  get_sc_metadata()['scanningcenter']),
                ('ppi',  Scribe3Configuration().get_numeric_or_none('ppi')),
            ]
        self.do_not_rotate = True

    def create_pipeline(self):
        return [
            self._load_directory,
            self._verify_preconditions,
            self._make_book_object,
            self._load_metadata,
            self._augment_metadata,
            self._write_metadata,
            self._load_image_stack,
            self._make_scandata,
            self._check_for_missing_images,
            self._move_image_stack,
            self._generate_thumbs,
        ]

    def handle_event(self, event_name, *args, **kwargs):
        if event_name == 'on_state' and self.state == CANCELLED_WITH_ERROR:
            if self.book_obj:
                self.book_obj.do_move_to_trash()
                self.book_obj.do_delete_anyway()

    def _load_directory(self):
        self.dispatch_progress('Loading directory')
        if not [f for f in os.listdir(self.source_path) if not f.startswith('.')]:
            raise Exception('The folder you selected is empty')
        self.directory_list = list(os.walk(os.path.join(self.source_path)))[0]

    def _verify_preconditions(self):
        self.dispatch_progress('Verifying preconditions')
        if '0000.jpg' not in self.directory_list[2]:
            raise Exception('No image stack provided')

    def _make_book_object(self):
        self.dispatch_progress('Making book object')
        generated_uuid = str(uuid4())
        self.book_obj = self.library.new_book(generated_uuid)

    def _load_metadata(self):
        self.dispatch_progress('Loading metadata')
        if 'metadata.xml' in self.directory_list[2]:
            self.metadata = get_metadata(self.source_path)
        else:
            self.metadata = {}

    def _augment_metadata(self):
        for field, default_value in self.DEFAULT_FIELDS_AND_VALUES:
            if field not in self.metadata and default_value is not None:
                self.metadata[field] = default_value

    def _load_image_stack(self):
        self.dispatch_progress('Loading image stack')
        self.image_stack = sorted([k for k
                            in self.directory_list[2]
                            if re.match('\d{4}\.jpg$', os.path.basename(k))])
                            # consider .*[^\d]\d{4}.jpg

    def _make_scandata(self):
        self.dispatch_progress('Generating scandata')
        self.scandata = ScanData(self.book_obj.path)
        for image in self.image_stack:
            if image == '0000.jpg':
                leaf_number = 0
            else:
                leaf_number = self.__extract_number_from_file(image)
            side = 'left' if leaf_number % 2 == 0 else 'right'
            page_type = 'Normal'
            if image == '0000.jpg':
                page_type = 'Color Card'
            elif image == '0001.jpg':
                page_type = 'Cover'
            elif leaf_number == len(self.image_stack) - 1:
                page_type = 'Color Card'
            self.scandata.insert(leaf_number, side, page_type)
            if self.do_not_rotate:
                self.scandata.update_rotate_degree(leaf_number, 0)

    def _check_for_missing_images(self):
        self.dispatch_progress('Checking for image stack integrity')
        if not (self.source_path and self.scandata):
            raise Exception('Cover image is missing!')
        max_leaf_number = self.scandata.get_max_leaf_number()
        if max_leaf_number is None or max_leaf_number < 1:
            raise Exception('Cover image is missing!')
        for leaf_number in range(max_leaf_number + 1):
            leaf_data = self.scandata.get_page_data(leaf_number)
            image_path = os.path.join(self.source_path, '{:04d}.jpg'.format(leaf_number))
            if not (leaf_data and os.path.exists(image_path)):
                if leaf_number == 0 or leaf_number == 1:
                    raise Exception('Cover image is missing!')
                raise Exception('Image #{} is missing'.format(leaf_number))
        self.scandata.save()
        self.book_obj.reload_scandata()

    def _write_metadata(self):
        self.dispatch_progress('Writing metadata')
        set_metadata(self.metadata, self.book_obj.path)
        self.book_obj.reload_metadata()
        self.book_obj.do_create_metadata()

    def _move_image_stack(self):
        self.dispatch_progress('Relocating image stack')
        for image in self.image_stack:
            source = os.path.join(self.source_path, image)
            destination = os.path.join(self.book_obj.path, image)
            shutil.copy(source, destination)

    def _generate_thumbs(self):
        self.dispatch_progress('Generating thumbs')
        for n, image in enumerate(self.image_stack):
            self.dispatch_progress('Generating thumbs [{}/{}]'.format(n, len(self.image_stack)))
            source_image = os.path.join(
                self.book_obj.path, image
            )
            target_image = os.path.join(
                self.book_obj.path, 'thumbnails', image
            )
            current_degree = int(self.scandata.get_page_data(n).get('rotateDegree', 0))
            rotate_by = convert_scandata_angle_to_thumbs_rotation(current_degree, None)

            thumbnail_size = (1500, 1000)
            if Scribe3Configuration().is_true('low_res_proxies'):
                thumbnail_size = (750, 500)
            image = Image.open(source_image)
            image.thumbnail(thumbnail_size)
            image = image.rotate(rotate_by, expand=True)
            image.save(target_image, 'JPEG', quality=90)

    @staticmethod
    def __extract_number_from_file(filename):
        number = filename.split('.jpg')[0]
        ret = number.lstrip('0')
        return int(ret)
