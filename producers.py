from hpxclient import consts
from hpxclient import protocols as hpxclient_protocols


class AuthRequestProducer(hpxclient_protocols.MessageProducer):
    KIND = consts.AUTH_KIND

    def __init__(self, email, password, public_key, secret_key):
        self.email = email
        self.password = password
        self.public_key = public_key
        self.secret_key = secret_key


class InitDataTransferProducer(hpxclient_protocols.MessageProducer):
    KIND = consts.INIT_CONN_KIND

    def __init__(self, conn_id):
        self.conn_id = conn_id


class TransferDataProducer(hpxclient_protocols.MessageProducer):
    KIND = consts.TRANS_DATA_KIND

    def __init__(self, conn_id, data):
        self.conn_id = conn_id
        self.data = data


class CloseConnProducer(hpxclient_protocols.MessageProducer):
    KIND = consts.CLOSE_CONN_KIND

    def __init__(self, conn_id):
        self.conn_id = conn_id
