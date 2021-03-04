from enum import Enum

ERROR_STATES = [150, 419, 429,
                451, 470, 520, 840, 841]

class UploadStatus(Enum):
    '''Defines possible statuses of a book during the process this value is
    used by the UI and by the dispatcher an aliases dictionary for the status
    '''

    uuid_assigned = 100

    loading_deferred = 150

    scribing = 200

    identifier_assigned = 300

    ready_for_packaging = 400
    packaging_started = 401

    create_image_stack = 410
    image_stack_created = 415
    image_stack_error = 419

    create_preimage_zip = 420
    preimage_zip_created = 425
    preimage_zip_error = 429

    blur_detecting = 450
    blur_detection_success = 455
    blur_detection_error = 458

    packaging_failed = 470
    packaging_completed = 490

    upload_queued = 500
    upload_started = 510
    upload_failed = 520
    uploaded = 590

    # Corrections land
    download_incomplete = 798
    downloaded = 799
    needs_corrections = 800
    needs_foldouts = 801
    corrections_in_progress = 825
    foldouts_in_progress = 826

    corrections_upload_queued = 830
    foldouts_upload_queued = 831

    corrections_upload_started = 835
    uploading_foldouts = 836

    corrections_upload_failed = 840
    foldouts_upload_failed = 841

    corrected = 850

    # deletion land
    done = 888
    rejected = 899
    staging = 901
    trash = 996
    deleted = 999

status_human_readable = {
    'uuid_assigned': 'Created',
    'loading_deferred': 'MD load deferred',
    'scribing': 'Scribing',
    'identifier_invalid': 'Identifier invalid!',
    'identifier_assigned': 'Identifier assigned',
    'identifier_reserved': 'Identifier reserved',
    'item_exists_nonempty': 'Item already has data',
    'ready_for_packaging': 'Packaging queued',
    'packaging_started': 'Packaging started',
    'blur_detecting': 'Detecting blur',
    'blur_detection_success': 'No blur found',
    'blur_detection_error': 'Blurry images found',
    'create_preimage_zip': 'Creating images bundle',
    'preimage_zip_created': 'Created images bundle',
    'preimage_zip_error': 'Error creating bundle',
    'upload_queued': 'Upload queued',
    'upload_started':'Uploading',
    'upload_failed' : 'Upload failed',
    'uploaded': 'Uploaded',
    'downloaded': 'Downloaded',
    'packaging_completed': 'Packaging complete',
    'packaging_failed': 'Packaging error',
    'create_image_stack': 'Compressing images',
    'image_stack_created': 'Compressed images',
    'image_stack_error': 'Error compressing images',
    'download_incomplete': 'Downloading',
    'needs_corrections':'Corrections Requested',
    'corrections_in_progress': 'Corrections in Progress',
    'corrections_upload_queued': 'Queued corrections upload',
    'corrections_upload_started': 'Corrections uploading',
    'corrections_upload_failed': 'Corrections upload failed',
    'needs_foldouts':'Foldouts Requested',
    'foldouts_in_progress': 'Foldouts in Progress',
    'foldouts_upload_queued': 'Foldouts upload queued',
    'uploading_foldouts': 'Foldouts Uploading',
    'foldouts_upload_failed': 'Foldouts Upload Failed',
    'corrected': 'Uploaded to Republisher',
    'done': 'Uploaded (awaiting deletion)',
    'rejected': 'Rejected (awaiting deletion)',
    'trash': 'Trash',
    'delete_queued': 'Awaiting deletion',
    'deleted': 'Deleted',
    'staging': 'Staging',
}
