from ioscreen.coremedia.CMTime import CMTimeConst
from ioscreen.coremedia.CMTime import CMTime as CM
from ioscreen.sync import *


def test_afmt():
    with open('./fixtures/afmt-request', "rb") as f:
        data = f.read()
        BufPacket = SyncAfmtPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes()
    with open('./fixtures/afmt-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_clock():
    with open('./fixtures/clok-request', "rb") as f:
        data = f.read()
        BufPacket = SyncClockPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes(0x00007FA67CC17980)
    with open('./fixtures/clok-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_cvrp():
    with open('./fixtures/cvrp-request', "rb") as f:
        data = f.read()
        BufPacket = SyncCvrpPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes(0x00007FA66CD10250)
    with open('./fixtures/cvrp-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_cwpa():
    with open('./fixtures/cwpa-request1', "rb") as f:
        data = f.read()
        BufPacket = SyncCwpaPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes(0x00007FA66CE20CB0)
    with open('./fixtures/cwpa-reply1', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_og():
    with open('./fixtures/og-request', "rb") as f:
        data = f.read()
        BufPacket = SyncOGPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes()
    with open('./fixtures/og-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_skew():
    with open('./fixtures/skew-request', "rb") as f:
        data = f.read()
        BufPacket = SyncSkewPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes(48000)
    with open('./fixtures/skew-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_stop():
    with open('./fixtures/stop-request', "rb") as f:
        data = f.read()
        BufPacket = SyncStopPacket.from_bytes(data[4:])
        print(BufPacket)
    Bytes = BufPacket.to_bytes()
    with open('./fixtures/stop-reply', "rb") as f:
        data = f.read()
    assert data == Bytes


def test_time():
    with open('./fixtures/time-request1', "rb") as f:
        data = f.read()
        BufPacket = SyncTimePacket.from_bytes(data[4:])
        print(BufPacket)
    _time = CM(
        CMTimeValue=0x0000BA62C442E1E1,
        CMTimeScale=0x3B9ACA00,
        CMTimeFlags=CMTimeConst.KCMTimeFlagsHasBeenRounded,
        CMTimeEpoch=0)
    Bytes = BufPacket.to_bytes(_time)
    with open('./fixtures/time-reply1', "rb") as f:
        data = f.read()
    assert data == Bytes
