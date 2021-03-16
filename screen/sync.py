""" 需要同步并进行数据回调的包
"""

import enum
import struct

from .coremedia import CMTime
from .coremedia.AudioStream import AudioStreamBasicDescription
from .coremedia.common import NSNumber
from .coremedia.serialize import SerializeStringKeyDict, new_string_dict_from_bytes, parse_header


def parse_sync_header(buffer, message_magic):
    remainingBytes, clockRef = parse_header(buffer, SyncConst.SyncPacketMagic, message_magic)
    correlationID = struct.unpack('<Q', remainingBytes[:8])[0]
    return remainingBytes[8:], clockRef, correlationID


class SyncConst(enum.IntEnum):
    SyncPacketMagic = 0x73796E63
    ReplyPacketMagic = 0x72706C79
    TIME = 0x74696D65
    CWPA = 0x63777061
    AFMT = 0x61666D74
    CVRP = 0x63767270
    CLOK = 0x636C6F6B
    OG = 0x676F2120
    SKEW = 0x736B6577
    STOP = 0x73746F70


class SyncPacket:
    messageMagic = None

    def __init__(self, ClockRef, CorrelationID):
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, self.messageMagic)
        return self(ClockRef,CorrelationID)

    def __str__(self):
        return f"SyncSkewPacket >> ClockRef:{self.ClockRef}, CorrelationID:{self.CorrelationID}"


def clock_ref_reply(clockRef, CorrelationID):
    packet_bytes = b''
    packet_bytes += struct.pack('<I', 28)
    packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
    packet_bytes += struct.pack('<Q', CorrelationID)
    packet_bytes += struct.pack('<I', 0)
    packet_bytes += struct.pack('<Q', clockRef)
    return packet_bytes


# ------------------- SyncPacket ——————————————————————


class SyncAfmtPacket(SyncPacket):
    messageMagic = SyncConst.AFMT

    def __init__(self, ClockRef, CorrelationID, AudioStreamBasicDescription=None):
        super().__init__(ClockRef, CorrelationID)
        self.AudioStreamBasicDescription = AudioStreamBasicDescription

    def __str__(self):
        return f'SYNC_AFMT >> ClockRef:{self.ClockRef} CorrelationID:{self.CorrelationID} AudioStreamBasicDescription:{self.AudioStreamBasicDescription}'

    def to_bytes(self):
        _data = {'Error': NSNumber(3, 0)}
        dictBytes = SerializeStringKeyDict(_data).to_bytes()
        dictLength = len(dictBytes)
        _length = dictLength + 20
        packet_bytes = b''
        packet_bytes += struct.pack('<I', _length)
        packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
        packet_bytes += struct.pack('<Q', self.CorrelationID)
        packet_bytes += struct.pack('<I', 0)
        packet_bytes += dictBytes
        return packet_bytes

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, self.messageMagic)
        AudioStream = AudioStreamBasicDescription.from_buffer_copy(remainingBytes)
        return self(ClockRef, CorrelationID,AudioStream)


class SyncClockPacket(SyncPacket):
    messageMagic = SyncConst.CLOK

    def __init__(self, ClockRef, CorrelationID):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID

    def to_bytes(self, clockRef):
        return clock_ref_reply(clockRef, self.CorrelationID)

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, SyncConst.CLOK)
        return self(ClockRef,CorrelationID)

    def __str__(self):
        return f"SYNC_CLOK >> ClockRef:{self.ClockRef}, CorrelationID:{self.CorrelationID}"


class SyncCvrpPacket(SyncPacket):
    messageMagic = SyncConst.CVRP

    def __init__(self, ClockRef, CorrelationID, DeviceClockRef=None, Payload=None):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID
        self.DeviceClockRef = DeviceClockRef
        self.Payload = Payload

    def to_bytes(self, clockRef):
        return clock_ref_reply(clockRef, self.CorrelationID)

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, SyncConst.CVRP)
        Payload = new_string_dict_from_bytes(remainingBytes[8:])
        DeviceClockRef = struct.unpack('<Q', remainingBytes[:8])[0]
        return self(ClockRef, CorrelationID,DeviceClockRef,Payload)

    def __str__(self):
        return f"SyncCvrpPacket >> ClockRef:{self.ClockRef}, CorrelationID:{self.CorrelationID}, DeviceClockRef:{self.DeviceClockRef}, Payload:{self.Payload}"


class SyncCwpaPacket(SyncPacket):
    messageMagic = SyncConst.CWPA

    def __init__(self, ClockRef, CorrelationID, DeviceClockRef=None):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID
        self.DeviceClockRef = DeviceClockRef

    def to_bytes(self, clockRef):
        return clock_ref_reply(clockRef, self.CorrelationID)

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, SyncConst.CWPA)
        DeviceClockRef = struct.unpack('<Q', remainingBytes[:8])[0]
        return self(ClockRef, CorrelationID,DeviceClockRef)

    def __str__(self):
        return f"SyncCvrpPacket >> ClockRef:{self.ClockRef}, CorrelationID:{self.CorrelationID}, DeviceClockRef:{self.DeviceClockRef}"


class SyncOGPacket(SyncPacket):
    messageMagic = SyncConst.OG

    def __init__(self, ClockRef, CorrelationID, Unknown=None):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID
        self.Unknown = Unknown

    def to_bytes(self):
        packet_bytes = b''
        packet_bytes += struct.pack('<I', 24)
        packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
        packet_bytes += struct.pack('<Q', self.CorrelationID)
        packet_bytes += struct.pack('<Q', 0)
        return packet_bytes

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef, CorrelationID, = parse_sync_header(buffer, SyncConst.OG)
        Unknown = struct.unpack('<I', remainingBytes[:4])[0]
        return self(ClockRef, CorrelationID,Unknown)

    def __str__(self):
        return f"SyncOGPacket >> ClockRef:{self.ClockRef}, CorrelationID:{self.CorrelationID}, DeviceClockRef:{self.Unknown}"


class SyncSkewPacket(SyncPacket):
    messageMagic = SyncConst.SKEW

    def __init__(self, ClockRef, CorrelationID):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID

    def to_bytes(self, skew):
        packet_bytes = b''
        packet_bytes += struct.pack('<I', 28)
        packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
        packet_bytes += struct.pack('<Q', self.CorrelationID)
        packet_bytes += struct.pack('<I', 0)
        packet_bytes += struct.pack('<d', skew)
        return packet_bytes


class SyncStopPacket(SyncPacket):
    messageMagic = SyncConst.STOP

    def __init__(self, ClockRef, CorrelationID):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID

    def to_bytes(self):
        packet_bytes = b''
        packet_bytes += struct.pack('<I', 24)
        packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
        packet_bytes += struct.pack('<Q', self.CorrelationID)
        packet_bytes += struct.pack('<I', 0)
        packet_bytes += struct.pack('<I', 0)
        return packet_bytes


class SyncTimePacket(SyncPacket):
    messageMagic = SyncConst.TIME

    def __init__(self, ClockRef, CorrelationID):
        super().__init__(ClockRef, CorrelationID)
        self.ClockRef = ClockRef
        self.CorrelationID = CorrelationID

    def to_bytes(self, time:CMTime):
        packet_bytes = b''
        packet_bytes += struct.pack('<I', 44)
        packet_bytes += struct.pack('<I', SyncConst.ReplyPacketMagic)
        packet_bytes += struct.pack('<Q', self.CorrelationID)
        packet_bytes += struct.pack('<I', 0)
        packet_bytes += bytes(time)
        return packet_bytes
