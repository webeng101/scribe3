from ia_scribe.ia_services.rejection_tracker import send_rejection_event
from ia_scribe.ia_services.btserver import get_ia_session

def get_rejection_namespace(slip_metadata):
    '''
    Within the context of tracking rejections, items within the `books_rejection_data` collection
    are named as specified in  ia_scribe.ia_services.rejection_tracker.ITEM_NAME_SCHEMA, a template
    in three parts: {mediatype}_{rejection_type}_{bucket}. Mediatype could be "CD" as used by ArchiveCD,
    and Bucket indicates the active time span. Rejection_type is te piece of this namespace that we use
    to track different rejection types.

    The current policy is that we want to treat all rejections coming from the scribe stations as uniform,
    even if they are later forwarded to a boxing station for fanning out. WHen that haappens, we want to
    track the boxing station rejection activity separately.

    :param slip_metadata:
    :return:
    '''
    namespace = 'boxed_rejections' if slip_metadata.get('boxed') else 'rejections'
    return namespace

def send_rejection(book):
    book.logger.info('Sending metrics to IA')
    metadata = book.metadata
    slip_metadata = book.get_slip_metadata()
    metadata.update(slip_metadata)
    book.logger.info('Sending this metadata to the upst')
    session = get_ia_session()
    namespace = get_rejection_namespace(slip_metadata)
    result, payload = send_rejection_event(session, book, metadata, namespace)
    if result:
        book.logger.info('Metric successfully sent. Now deleting....')
        book.do_move_to_trash()
    else:
        raise payload
