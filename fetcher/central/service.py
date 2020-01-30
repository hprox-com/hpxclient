from hpxclient import protocols
from hpxclient import settings

from hpxclient import producers
from hpxclient.fetcher.central import consumers


class CentralFetcherProtocol(protocols.MsgpackReconnectingProtocol):
    REGISTERED_CONSUMERS = [
        consumers.InitConnConsumer,
        consumers.TransferDataConsumer,
        consumers.CloseConnConsumer
    ]

    def __init__(self, email, password, public_key, secret_key):
        super().__init__()
        self.email = email
        self.password = password
        self.public_key = public_key
        self.secret_key = secret_key

    def connection_made(self, transport):
        super().connection_made(transport)

        self.write_data(
            producers.AuthRequestProducer(
                email=self.email,
                password=self.password,
                public_key=self.public_key,
                secret_key=self.secret_key
            )
        )

    def processor_closed(self, conn_id):
        self.write_data(producers.CloseConnProducer(conn_id))

    def processor_data_received(self, conn_id, data):
        self.write_data(producers.TransferDataProducer(conn_id, data))


def get_protocol_factory(email=None, password=None, public_key=None, secret_key=None):
    def wrapper():
        return CentralFetcherProtocol(
            email=email,
            password=password,
            public_key=public_key,
            secret_key=secret_key
        )
    return wrapper


async def start_client(
        email=None,
        password=None,
        public_key=None,
        secret_key=None,
        ssl=None):

    return await CentralFetcherProtocol.create_conn(
        proto_factory=get_protocol_factory(
            email=email,
            password=password,
            public_key=public_key,
            secret_key=secret_key),
        host=settings.PROXY_FETCHER_SERVER_IP,
        port=settings.PROXY_FETCHER_SERVER_PORT,
        ssl=ssl
    )
