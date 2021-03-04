import os, glob

from ia_scribe.book.states import cd_state_machine
from ia_scribe.book.item import Scribe3Item
from ia_scribe.tasks.book_tasks.checks \
    import (item_ready_for_upload,\
            verify_uploaded, \
            has_valid_preimage_zip, \
            was_image_stack_processed,
            has_full_imgstack)
from ia_scribe.book.smau import  path_to_success

class CD(Scribe3Item):
    state_machine = cd_state_machine

    def __init__(self, book_dict, callback=None, delete_callback=None):
        print("[CD::init()] Creating CD object from ->", book_dict)
        super(CD, self).__init__(book_dict, callback, delete_callback)

    def get_path_to_upload(self, human_readable=False):
        return_value = []
        if self.get_numeric_status() >= 888:
            return return_value
        return_value = path_to_success(self.status)
        if human_readable:
            return_value = self.humanify(return_value)
        return return_value

    def has_slip(self):
        return False

    def get_cover_image(self):
        ret = os.path.join(self.path, 'cover.png')
        return ret

    def has_minimal_metadata(self):
        return True

    def has_full_image_stack(self):
        return has_full_imgstack(self)

    def has_full_image_stack_wrapper(self, e):
        self.logger.info('checking that {} has a full imgstack...'.format(self.identifier))
        ret, msg = has_full_imgstack(self)
        self.logger.info('Result is {} {}'.format(ret, msg))
        if ret == False:
            self.raise_exception('has_full_imgstack_wrapper', msg)
        return ret

    def item_clear_for_upload_wrapper(self, e):
        self.logger.info('checking that {} is clear for upload'.format(self.identifier))
        return True

    def was_image_stack_processed_wrapper(self, e):
        self.logger.info('checking that imagestack was formed properly')
        ret = was_image_stack_processed(self)
        self.logger.info('Result is {}'.format(ret))
        return ret

    def has_valid_preimage_zip_wrapper(self, e):
        self.logger.info('checking that preimage.zip archive was built properly')
        ret = has_valid_preimage_zip(self)
        self.logger.info('Result is {}'.format(ret))
        return ret

    def get_jpegs(self):
        jpegs = sorted(glob.glob(os.path.join(self.path, '[0-9][0-9][0-9][0-9].jpg')))
        return jpegs

    def get_thumb_jpegs(self):
        jpegs = sorted(glob.glob(os.path.join(self.path, 'thumbnails', '[0-9][0-9][0-9][0-9].jpg')))
        return jpegs

    def get_imagestack(self):
        jp2s = sorted(glob.glob(os.path.join(self.path, '[0-9][0-9][0-9][0-9].jp2')))
        if len(jp2s) == 0:
            jp2s = self.get_jpegs()
        return jp2s


