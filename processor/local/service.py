import asyncio


class LocalProcessorProtocol(asyncio.Protocol):
    def __init__(self, conn_id, fetcher_proto, loop=None):
        self.fetcher_proto = fetcher_proto
        self.conn_id = conn_id

        self.transport = None
        self.buff = b''

    def connection_made(self, transport):
        self.transport = transport
        if not self.buff:
            return

        self.transport.write(self.buff)
        self.buff = b''

    def connection_lost(self, exc):
        self.fetcher_proto.processor_closed(self.conn_id)

    def data_received(self, data):
        self.fetcher_proto.processor_data_received(self.conn_id, data)

    def write_data(self, data):
        if not self.transport:
            self.buff += data
            return
        self.transport.write(data)


async def start_client(conn_id, host, port, fetcher_proto):
    """
        Client started every time, url need to be processed.
        It connects to local transparent proxy to fetch data.
        Communication is handled by LocalProcessorProtocol.
    """

    print("processing for host", host, port)

    loop = asyncio.get_event_loop()
    processor_proto = LocalProcessorProtocol(conn_id, fetcher_proto)

    try:
        return await loop.create_connection(lambda: processor_proto,
                                            host=host,
                                            port=port)
    except Exception as e:
        return None, None
