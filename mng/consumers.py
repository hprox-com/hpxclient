from hpxclient import protocols, consts


class InfoBalanceConsumer(protocols.MessageConsumer):
    KIND = consts.INFO_BALANCE_KIND

    def process(self):
        balance_amount = self.data[b'balance_amount']
        print("[InfoBalanceConsumer] GB amount %s" %balance_amount)


class InfoVersionConsumer(protocols.MessageConsumer):
    KIND = consts.INFO_VERSION_KIND

    def process(self):
        version = self.data[b'version']
        print("[InfoVersionConsumer] Last version", version)
