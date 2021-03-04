# This state machine describes the lifetime of a book

media_state_machine = {
    'initial': 'uuid_assigned',
    'events': [
                {'name': 'do_move_to_trash',
                        'src': '*',
                        'dst': 'trash'},

                   {'name': 'do_delete',
                        'src': 'trash',
                        'dst': 'deleted'
                    },

    ]

}

book_state_machine = {
               'initial': 'uuid_assigned',
               'events': [
                   {'name': 'do_create_metadata',
                        'src': ['uuid_assigned', ],
                        'dst': 'scribing' },

                    {'name': 'do_defer_metadata',
                        'src': ['uuid_assigned', 'scribing'],
                        'dst': 'loading_deferred' },

                   {'name': 'do_deferred_load_metadata',
                    'src': ['loading_deferred', ],
                    'dst': 'identifier_assigned'},

                   {'name': 'do_create_identifier',
                        'src': ['scribing', 'uuid_assigned'],
                        'dst': 'identifier_assigned',
                        'cond': [
                            #'not_has_identifier',
                        ]},

                   {'name': 'do_reject',
                        'src': ['uuid_assigned', 'loading_deferred',
                                'scribing', 'identifier_assigned'],
                        'dst': 'rejected',
                    },

                   {'name': 'do_queue_processing',
                        'src': ['identifier_assigned',],
                        'dst': 'ready_for_packaging',
                        'cond': [
                            'has_full_image_stack_wrapper',
                            'has_slip_if_required_wrapper',
                            'has_rcs_if_required_wrapper',
                            'has_identifier',
                        ]
                    },

                   # Packaging stages
                   {'name': 'do_begin_packaging',
                        'src': ['ready_for_packaging'],
                        'dst': 'packaging_started', },

                   {'name': 'do_queue_blur_detection',
                        'src': 'packaging_started',
                        'dst': 'blur_detecting'},

                   {'name': 'do_finish_blur_detection_success',
                        'src': 'blur_detecting',
                        'dst': 'blur_detection_success'},

                   {'name': 'do_error_blur_detection',
                        'src': 'blur_detecting',
                        'dst': 'blur_detection_error'},

                   {'name': 'do_retry_blur_detection',
                        'src': 'blur_detection_error',
                        'dst': 'blur_detecting'},

                   {'name': 'do_ignore_blur_detection',
                        'src': 'blur_detection_error',
                        'dst': 'blur_detection_success'},

                   {'name': 'do_create_image_stack',
                        'src': ['packaging_started', 'blur_detection_success'],
                        'dst': 'create_image_stack'},

                   {'name': 'do_finish_image_stack',
                        'src': 'create_image_stack',
                        'dst': 'image_stack_created',
                        'cond': [
                            {True: 'was_image_stack_processed_wrapper',
                             'else': 'image_stack_error'},
                        ]
                    },

                   {'name': 'do_error_image_stack',
                        'src': 'create_image_stack',
                        'dst': 'image_stack_error'},

                   {'name': 'do_retry_image_stack',
                        'src': 'image_stack_error',
                        'dst': 'create_image_stack'},

                   {'name': 'do_create_preimage_zip',
                        'src': ['packaging_started','image_stack_created', 'image_stack_error'],
                        'dst': 'create_preimage_zip'},

                   {'name': 'do_finish_preimage_zip',
                        'src': 'create_preimage_zip',
                        'dst': 'preimage_zip_created',
                        'cond': [
                            {True: 'has_valid_preimage_zip_wrapper',
                             'else': 'preimage_zip_error'},
                        ]
                    },

                   {'name': 'do_error_preimage_zip',
                        'src': 'create_preimage_zip',
                        'dst': 'preimage_zip_error'},

                   {'name': 'do_retry_preimage_zip',
                        'src': ['preimage_zip_error', 'upload_failed'],
                        'dst': 'create_preimage_zip'},

                   {'name': 'do_fail_packaging',
                        'src': ['packaging_started','image_stack_error'],
                        'dst': 'packaging_failed'},

                   {'name': 'do_retry_packaging',
                        'src': 'packaging_failed',
                        'dst': 'packaging_started'},

                   {'name': 'do_finish_packaging',
                        'src': ['packaging_started','preimage_zip_created'],
                        'dst': 'packaging_completed',
                    },

                   # Upload stages

                   {'name': 'do_queue_for_upload',
                        'src': ['packaging_completed',],
                        'dst': 'upload_queued',
                        'cond': [
                            # {True: 'item_clear_for_upload_wrapper',
                            # 'else': 'upload_failed'},
                            'has_identifier',
                            'item_clear_for_upload_wrapper',
                        ]
                    },

                {'name': 'do_force_queue_for_upload',
                        'src': ['packaging_completed',],
                        'dst': 'upload_queued',
                        'cond': [
                            # {True: 'item_clear_for_upload_wrapper',
                            # 'else': 'upload_failed'},
                            'has_identifier',
                        ]
                    },

                   {'name': 'do_book_upload_begin',
                        'src': 'upload_queued',
                        'dst': 'upload_started'},

                   {'name': 'do_upload_book_error',
                        'src': ['upload_started', 'upload_queued', 'upload_failed'],
                        'dst': 'upload_failed'},

                   {'name': 'do_upload_book_end',
                        'src': 'upload_started',
                        'dst': 'uploaded'},

                   {'name': 'do_upload_book_done',
                        'src': 'uploaded',
                        'dst': 'staging'},

                   {'name': 'do_upload_book_retry',
                        'src': 'upload_failed',
                        'dst': 'upload_queued',
                        'cond':['has_identifier',] },

                  {'name': 'do_upload_book_anew',
                        'src': 'uploaded',
                        'dst': 'upload_queued',
                        'cond':['has_identifier',] },

                   # Downloaded books (corrections and foldouts) stages

                   {'name': 'do_start_download',
                        'src': 'download_incomplete',
                        'dst': 'download_incomplete'},

                   {'name': 'do_end_download_correction',
                        'src': 'download_incomplete',
                        'dst': 'needs_corrections'},

                   {'name': 'do_end_download_foldout',
                        'src': 'download_incomplete',
                        'dst': 'needs_foldouts'},

                   {'name': 'do_start_corrections',
                        'src': 'needs_corrections',
                        'dst': 'corrections_in_progress'},

                   {'name': 'do_start_foldouts',
                        'src': 'needs_foldouts',
                        'dst': 'foldouts_in_progress'},

                   {'name': 'do_queue_upload_corrections',
                        'src': ['needs_corrections',
                                'corrections_in_progress',
                                'corrections_upload_failed'],
                        'dst': 'corrections_upload_queued'},

                   {'name': 'do_start_upload_corrections',
                        'src': 'corrections_upload_queued',
                        'dst': 'corrections_upload_started'},

                   {'name': 'do_upload_corrections_done',
                        'src': 'corrections_upload_started',
                        'dst': 'corrected'},

                   {'name': 'do_upload_corrections_fail',
                        'src': 'corrections_upload_started',
                        'dst': 'corrections_upload_failed'},

                   {'name': 'do_queue_upload_foldouts',
                        'src': ['foldouts_in_progress', 'foldouts_upload_failed'],
                        'dst': 'foldouts_upload_queued'},

                  {'name': 'do_start_upload_foldouts',
                        'src': ['foldouts_upload_queued'],
                        'dst': 'uploading_foldouts'},

                   {'name': 'do_upload_foldouts_done',
                        'src': 'uploading_foldouts',
                        'dst': 'corrected'},

                   {'name': 'do_upload_foldouts_fail',
                        'src': 'uploading_foldouts',
                        'dst': 'foldouts_upload_failed'},

                    # Trashlandia
                   {'name': 'do_move_to_trash',
                        'src': '*',
                        'dst': 'trash'},

                   {'name': 'do_delete_staged',
                        'src': 'staging',
                        'dst': 'trash'},

                   {'name': 'do_undelete_staged',
                        'src': 'trash',
                        'dst': 'staging'},

                   {'name': 'do_delete_anyway',
                        'src': 'trash',
                        'dst': 'deleted'},

                   {'name': 'do_delete',
                        'src': 'trash',
                        'dst': 'deleted',
                        'cond':['ok_to_delete', ]
                       ,},

               ],
        }

cd_state_machine = {
               'initial': 'uuid_assigned',
               'events': [
                   {'name': 'do_start_download',
                    'src': 'download_incomplete',
                    'dst': 'download_incomplete'},

                   {'name': 'do_finish_download',
                    'src': 'download_incomplete',
                    'dst': 'identifier_assigned'},

                   {'name': 'do_create_metadata',
                        'src': ['uuid_assigned', ],
                        'dst': 'scribing' },

                   {'name': 'do_create_identifier',
                        'src': ['scribing', 'uuid_assigned'],
                        'dst': 'identifier_assigned',
                        'cond': [
                            #'not_has_identifier',
                        ]},

                   {'name': 'do_queue_processing',
                        'src': ['identifier_assigned',],
                        'dst': 'ready_for_packaging',
                        'cond': [
                            'has_full_image_stack_wrapper',
                            'has_identifier',
                        ]
                    },

                   # Packaging stages
                   {'name': 'do_begin_packaging',
                        'src': ['ready_for_packaging'],
                        'dst': 'packaging_started', },

                   {'name': 'do_queue_blur_detection',
                        'src': 'packaging_started',
                        'dst': 'blur_detecting'},

                   {'name': 'do_finish_blur_detection_success',
                        'src': 'blur_detecting',
                        'dst': 'blur_detection_success'},

                   {'name': 'do_error_blur_detection',
                        'src': 'blur_detecting',
                        'dst': 'blur_detection_error'},

                   {'name': 'do_retry_blur_detection',
                        'src': 'blur_detection_error',
                        'dst': 'blur_detecting'},

                   {'name': 'do_ignore_blur_detection',
                        'src': 'blur_detection_error',
                        'dst': 'blur_detection_success'},

                   {'name': 'do_create_image_stack',
                        'src': ['packaging_started', 'blur_detection_success'],
                        'dst': 'create_image_stack'},

                   {'name': 'do_finish_image_stack',
                        'src': 'create_image_stack',
                        'dst': 'image_stack_created',
                        'cond': [
                            {True: 'was_image_stack_processed_wrapper',
                             'else': 'image_stack_error'},
                        ]
                    },

                   {'name': 'do_error_image_stack',
                        'src': 'create_image_stack',
                        'dst': 'image_stack_error'},

                   {'name': 'do_retry_image_stack',
                        'src': 'image_stack_error',
                        'dst': 'create_image_stack'},

                   {'name': 'do_create_preimage_zip',
                        'src': ['packaging_started','image_stack_created', 'image_stack_error'],
                        'dst': 'create_preimage_zip'},

                   {'name': 'do_finish_preimage_zip',
                        'src': 'create_preimage_zip',
                        'dst': 'preimage_zip_created',
                        'cond': [
                            {True: 'has_valid_preimage_zip_wrapper',
                             'else': 'preimage_zip_error'},
                        ]
                    },

                   {'name': 'do_error_preimage_zip',
                        'src': 'create_preimage_zip',
                        'dst': 'preimage_zip_error'},

                   {'name': 'do_retry_preimage_zip',
                        'src': ['preimage_zip_error', 'upload_failed'],
                        'dst': 'create_preimage_zip'},

                   {'name': 'do_fail_packaging',
                        'src': ['packaging_started','image_stack_error'],
                        'dst': 'packaging_failed'},

                   {'name': 'do_retry_packaging',
                        'src': 'packaging_failed',
                        'dst': 'packaging_started'},

                   {'name': 'do_finish_packaging',
                        'src': ['packaging_started','preimage_zip_created'],
                        'dst': 'packaging_completed',
                    },

                   # Upload stages

                   {'name': 'do_queue_for_upload',
                        'src': ['packaging_completed',],
                        'dst': 'upload_queued',
                        'cond': [
                            # {True: 'item_clear_for_upload_wrapper',
                            # 'else': 'upload_failed'},
                            'has_identifier',
                            'item_clear_for_upload_wrapper',
                        ]
                    },

                {'name': 'do_force_queue_for_upload',
                        'src': ['packaging_completed',],
                        'dst': 'upload_queued',
                        'cond': [
                            # {True: 'item_clear_for_upload_wrapper',
                            # 'else': 'upload_failed'},
                            'has_identifier',
                        ]
                    },

                   {'name': 'do_book_upload_begin',
                        'src': 'upload_queued',
                        'dst': 'upload_started'},

                   {'name': 'do_upload_book_error',
                        'src': ['upload_started', 'upload_queued', 'upload_failed'],
                        'dst': 'upload_failed'},

                   {'name': 'do_upload_book_end',
                        'src': 'upload_started',
                        'dst': 'uploaded'},

                   {'name': 'do_upload_book_done',
                        'src': 'uploaded',
                        'dst': 'staging'},

                   {'name': 'do_upload_book_retry',
                        'src': 'upload_failed',
                        'dst': 'upload_queued',
                        'cond':['has_identifier',] },

                  {'name': 'do_upload_book_anew',
                        'src': 'uploaded',
                        'dst': 'upload_queued',
                        'cond':['has_identifier',] },


                    # Trashlandia
                   {'name': 'do_move_to_trash',
                        'src': '*',
                        'dst': 'trash'},

                   {'name': 'do_delete_staged',
                        'src': 'staging',
                        'dst': 'trash'},

                   {'name': 'do_undelete_staged',
                        'src': 'trash',
                        'dst': 'staging'},

                   {'name': 'do_delete_anyway',
                        'src': 'trash',
                        'dst': 'deleted'},

                   {'name': 'do_delete',
                        'src': 'trash',
                        'dst': 'deleted',
                        },

               ],
        }
