from ioscreen.asyn import *


def test_feed():
    with open('./fixtures/asyn-feed', "rb") as f:
        data = f.read()
        BufPacket = AsynCmSampleBufPacket.from_bytes(data[4:])
        print(BufPacket)


def test_feed_eat():
    with open('./fixtures/asyn-eat', "rb") as f:
        data = f.read()
        BufPacket = AsynCmSampleBufPacket.from_bytes(data)
        print(BufPacket)


def test_rels():
    with open('./fixtures/asyn-rels', "rb") as f:
        data = f.read()
        BufPacket = AsynRelsPacket.from_bytes(data[4:])
        print(BufPacket)


def test_sprp():
    with open('./fixtures/asyn-sprp', "rb") as f:
        data = f.read()
        BufPacket = AsynSprpPacket.from_bytes(data)
        print(BufPacket)


def test_srat():
    with open('./fixtures/asyn-srat', "rb") as f:
        data = f.read()
        BufPacket = AsynSratPacket.from_bytes(data)
        print(BufPacket)


def test_tbas():
    with open('./fixtures/asyn-tbas', "rb") as f:
        data = f.read()
        BufPacket = AsynTbasPacket.from_bytes(data)
        print(BufPacket)

def test_tjmp():
    with open('./fixtures/asyn-tjmp', "rb") as f:
        data = f.read()
        BufPacket = AsynTjmpPacket.from_bytes(data)
        print(BufPacket)

