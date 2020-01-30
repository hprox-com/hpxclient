import asyncio

from hpxclient import protocols

from hpxclient import consts
from hpxclient import producers
from hpxclient.fetcher.central import utils as fetcher_central_utils
from hpxclient.processor.local import service as processor_local_service


class AuthResponseConsumer(protocols.MessageConsumer):
    KIND = consts.AUTH_KIND

    def process(self):
        error = self.data[b'error']
        if error:
            print("Unexpected error: %s", error.decode())
            self.protocol.close()
            return

        user_id = self.data[b'user_id']
        session_id = self.data[b'session_id']
        public_key = self.data[b'public_key']


class InitConnConsumer(protocols.MessageConsumer):
    KIND = consts.INIT_CONN_KIND
    
    async def process(self):
        conn_id = self.data[b'conn_id']
        url = self.data[b'url'].decode()
        port = int(self.data[b'port'])

        lpt, lpp = await processor_local_service.start_client(
            conn_id, url, port, self.protocol
        )
        if lpt is None:
            self.protocol.write_data(producers.CloseConnProducer(conn_id))
            return

        fetcher_central_utils.add_processor(conn_id, lpp)


class TransferDataConsumer(protocols.MessageConsumer):
    KIND = consts.TRANS_DATA_KIND
    
    def process(self):
        conn_id = self.data[b'conn_id']

        processor_proto = fetcher_central_utils.get_processor(conn_id)
        if processor_proto is None:
            return

        processor_proto.write_data(self.data[b'data'])


class CloseConnConsumer(protocols.MessageConsumer):
    KIND = consts.CLOSE_CONN_KIND
    
    def process(self):
        conn_id = self.data[b'conn_id']

        processor_proto = fetcher_central_utils.get_processor(conn_id)
        if processor_proto is None:
            return

        if processor_proto.transport:
            processor_proto.transport.close()
        fetcher_central_utils.remove_processor(conn_id)
