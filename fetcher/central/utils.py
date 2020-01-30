PROCESSORS = {}


def get_processors():
    from hpxclient.fetcher.central import utils
    return utils.PROCESSORS


def get_processor(conn_id):
    return get_processors().get(conn_id)


def add_processor(conn_id, processor):
    if get_processor(conn_id):
        raise Exception('Processor already exists for connection %s' %conn_id)

    processors = get_processors()
    processors[conn_id] = processor
    return processor


def remove_processor(conn_id):
    if not get_processor(conn_id):
        return

    processors = get_processors()
    del processors[conn_id]
