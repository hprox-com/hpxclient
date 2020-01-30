import time
import struct
import asyncio
import msgpack

from hpxclient import consts


class ReconnectingProtocol(asyncio.Protocol):
    MIN_SLEEP_TIME = 2
    MAX_SLEEP_TIME = 60

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.host = None
        self.port = None

        # When last time connection was made successfully
        self.last_connection_time = None

        self.proto_factory = None

    def connection_lost(self, exc):
        print("Lost.", self.__class__, self.port, self.host)
        def onexit(future):
            yield future.result()

        task = asyncio.ensure_future(self._create_conn(
            self.proto_factory,
            self.host,
            self.port,
            self.last_connection_time
        ))
        task.add_done_callback(onexit)

    @classmethod
    async def _create_conn(cls,
                           proto_factory,
                           host, port,
                           last_connection_time=None,
                           ssl=None):
        loop = asyncio.get_event_loop()
        sleep_time = cls.MIN_SLEEP_TIME

        while True:
            # Allow connection once per 60s only
            if last_connection_time and time.time() - last_connection_time < 60:
                await asyncio.sleep(10)
                continue

            connection_params = dict(
                protocol_factory = proto_factory,
                host=host,
                port=port,
                ssl=ssl)
            if ssl:
                connection_params['server_hostname'] = 'hprox.com'

            try:
                transport, protocol = await loop.create_connection(**connection_params)
                protocol.host = host
                protocol.port = port
                protocol.proto_factory = proto_factory
                protocol.last_connection_time = time.time()

                return transport, protocol
            except OSError as e:
                await asyncio.sleep(sleep_time)
                sleep_time = min(sleep_time * 2, cls.MAX_SLEEP_TIME)
                print("Disconnected. Reconnecting in %s seconds" % sleep_time)

    @classmethod
    async def create_conn(cls, proto_factory, host, port, ssl=None):
        await cls._create_conn(proto_factory, host, port, ssl=ssl)


class MsgpackReconnectingProtocol(ReconnectingProtocol):
    LENGTH_SIZE = struct.calcsize("<L")
    REGISTERED_CONSUMERS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buff = b''
        self._content_size = None
        self.last_chunk_time = None
        self.transport = None

        self._queue = asyncio.Queue()

    def connection_made(self, transport):
        print('Connection made %s %s' % (self.__class__, id(self)))
        self.transport = transport
        self.last_chunk_time = time.time()

        def onexit(future):
            yield future.result()

        task = asyncio.ensure_future(activate_proto_watcher(self))
        task.add_done_callback(onexit)

        task = asyncio.ensure_future(activate_message_processor(self))
        task.add_done_callback(onexit)

    def connection_lost(self, exc):
        self.close()
        super().connection_lost(exc)

    def process_data(self):
        if self._content_size is None:
            if len(self._buff) >= self.LENGTH_SIZE:
                self._content_size = struct.unpack(
                    "<L", self._buff[:self.LENGTH_SIZE])[0]
                self._buff = self._buff[self.LENGTH_SIZE:]
                return self.process_data()

        if self._content_size is None:
            return

        if len(self._buff) >= self._content_size:
            message = self._buff[:self._content_size]
            self.process_msg(msgpack.unpackb(message))

            self._buff = self._buff[self._content_size:]
            self._content_size = None
            return self.process_data()

    def data_received(self, data):
        self.last_chunk_time = time.time()
        self._buff += data
        self.process_data()

    def process_msg(self, message):
        self._queue.put_nowait(message)

    def write_data(self, msg_producer):
        if self.transport and not self.transport.is_closing():
            self.transport.write(encode_msg(msg_producer.msg2str()))

    def close(self):
        print('Connection closed %s %s' % (self.__class__, id(self)))
        if self.transport:
            self.transport.close()
            self.transport = None
            self.last_chunk_time = None


async def activate_message_processor(proto):
    consumer_list = proto.REGISTERED_CONSUMERS

    while proto.transport is not None:
        data = await proto._queue.get()

        consumer_kind = data[b'kind'].decode()

        consumer_cls = None
        for cls in consumer_list:
            if consumer_kind != cls.KIND:
                continue
            consumer_cls = cls
            break

        if consumer_cls is None:
            print('Consumer not found [kind=%s]' %consumer_kind)
            continue

        consumer = consumer_cls(proto, data[b'data'])
        if asyncio.iscoroutinefunction(getattr(consumer, 'process')):
            await consumer.process()
            continue

        consumer.process()


async def activate_proto_watcher(proto, sleep_time=30):
    while proto.transport is not None:
        # For 60 seconds no chunks. Connection is dead.
        if time.time() - proto.last_chunk_time > 60:
            proto.close()
            return

        # For 30 seconds no chunks. Ping server.
        if time.time() - proto.last_chunk_time > 30:
            print('Sending ping %s %s' % (proto.__class__, id(proto)))
            proto.write_data(PingProducer())

        await asyncio.sleep(sleep_time)


class MessageProducer(object):
    KIND = None

    def get_data(self):
        return self.__dict__

    def msg2str(self):
        return {
            'kind': self.KIND,
            'data': self.get_data()
        }


class PingProducer(MessageProducer):
    KIND = consts.PING_KIND

    def get_data(self):
        return None


class MessageConsumer(object):
    def __init__(self, protocol, data):
        self.data = data
        self.protocol = protocol

    def process(self):
        raise NotImplementedError()


def encode_msg(msg):
    data = msgpack.packb(msg, use_bin_type=False)
    return struct.pack("<L", len(data)) + data
