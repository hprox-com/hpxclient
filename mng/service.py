from hpxclient import protocols
from hpxclient import settings

from hpxclient import producers
from hpxclient.mng import consumers


class ManagerProtocol(protocols.MsgpackReconnectingProtocol):
    REGISTERED_CONSUMERS = [
        consumers.InfoBalanceConsumer,
        consumers.InfoVersionConsumer
    ]

    def __init__(self,
                 email=None, password=None,
                 public_key=None, secret_key=None,
                 message_handler=None):

        super().__init__()

        self.email = email
        self.password = password
        self.public_key = public_key
        self.secret_key = secret_key
        self.message_handler = message_handler

    def connection_made(self, transport):
        super().connection_made(transport)

        self.write_data(producers.AuthRequestProducer(
            self.email, self.password, self.public_key, self.secret_key))

    def process_msg(self, message):
        super().process_msg(message)

        if self.message_handler:
            self.message_handler(message)


def get_client_protocol_factory(
        email=None,
        password=None,
        public_key=None,
        secret_key=None,
        message_handler=None):

    def wrapper():
        return ManagerProtocol(
            email=email,
            password=password,
            public_key=public_key,
            secret_key=secret_key,
            message_handler=message_handler
        )
    return wrapper


async def start_client(
        email=None,
        password=None,
        public_key=None,
        secret_key=None,
        message_handler=None):

    manager_factory = get_client_protocol_factory(
        email=email,
        password=password,
        public_key=public_key,
        secret_key=secret_key,
        message_handler=message_handler
    )

    await ManagerProtocol.create_conn(
        manager_factory,
        host=settings.PROXY_MNG_SERVER_IP,
        port=settings.PROXY_MNG_SERVER_PORT
    )

