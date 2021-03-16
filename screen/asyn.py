import enum
import struct

from .coremedia.AudioStream import AudioStreamBasicDescription, AudioFormatIDLMagic
from .coremedia.CMSampleBuffer import CMSampleBuffer
from .coremedia.CMTime import CMTime
from .coremedia.common import NSNumber
from .coremedia.serialize import SerializeStringKeyDict, parse_key_value_dict, parse_header


def parse_asyn_header(buffer, message_magic):
    return parse_header(buffer, AyncConst.AsyncPacketMagic, message_magic)


class AyncConst(enum.IntEnum):
    AsyncPacketMagic = 0x6173796E
    FEED = 0x66656564  # These contain CMSampleBufs which contain raw h264 Nalus
    TJMP = 0x746A6D70
    SRAT = 0x73726174
    SPRP = 0x73707270
    TBAS = 0x74626173
    RELS = 0x72656C73
    HPD1 = 0x68706431
    HPA1 = 0x68706131
    NEED = 0x6E656564
    EAT = 0x65617421
    HPD0 = 0x68706430
    HPA0 = 0x68706130


def create_hpd1_device():
    resultDict = {
        'Valeria': True,
        'HEVCDecoderSupports444': True
    }
    displaySizeDict = {
        'Width': NSNumber(6, 1920),
        'Height': NSNumber(6, 1200),
    }
    resultDict['DisplaySize'] = displaySizeDict
    return resultDict


def create_hpa1_device():
    AudioBytes = AudioStreamBasicDescription(FormatFlags=12,
                                             BytesPerPacket=4, FramesPerPacket=1, BytesPerFrame=4, ChannelsPerFrame=2,
                                             BitsPerChannel=16, Reserved=0,
                                             SampleRate=48000, FormatID=AudioFormatIDLMagic).to_bytes()

    resultDict = {
        'BufferAheadInterval': NSNumber(6, 0.07300000000000001),
        'deviceUID': 'Valeria',
        'ScreenLatency': NSNumber(6, 0.04),
        'formats': AudioBytes,
        'EDIDAC3Support': NSNumber(3, 0),
        'deviceName': 'Valeria',

    }
    return resultDict


def new_asyn_dict_packet(stringKeyDict, subtypeMarker, asynTypeHeader):
    serialize = SerializeStringKeyDict(stringKeyDict).to_bytes()
    _length = len(serialize) + 20
    packet_bytes = b''
    packet_bytes += struct.pack('<I', _length)
    packet_bytes += struct.pack('<I', AyncConst.AsyncPacketMagic)
    packet_bytes += struct.pack('<Q', asynTypeHeader)
    packet_bytes += struct.pack('<I', subtypeMarker)
    packet_bytes += serialize
    return packet_bytes


def asyn_need_packet_bytes(clockRef):
    packet_bytes = b''
    packet_bytes += struct.pack('<I', 20)
    packet_bytes += struct.pack('<I', AyncConst.AsyncPacketMagic)
    packet_bytes += struct.pack('<Q', clockRef)
    packet_bytes += struct.pack('<I', AyncConst.NEED)
    return packet_bytes


def asyn_hpa0(clockRef):
    packet_bytes = b''
    packet_bytes += struct.pack('<I', 20)
    packet_bytes += struct.pack('<I', AyncConst.AsyncPacketMagic)
    packet_bytes += struct.pack('<Q', clockRef)
    packet_bytes += struct.pack('<I', AyncConst.HPA0)
    return packet_bytes


def asyn_hpd0():
    packet_bytes = b''
    packet_bytes += struct.pack('<I', 20)
    packet_bytes += struct.pack('<I', AyncConst.AsyncPacketMagic)
    packet_bytes += struct.pack('<Q', 1)
    packet_bytes += struct.pack('<I', AyncConst.HPD0)
    return packet_bytes


# ------------------- AyncPacket ——————————————————————

class AyncPacket:
    messageMagic = None

    def __init__(self, ClockRef):
        self.ClockRef = ClockRef

    @classmethod
    def from_bytes(self, buffer):
        _, clockRef = parse_asyn_header(buffer, self.messageMagic)
        return self(clockRef)

    def __str__(self):
        return f"SyncSkewPacket >> ClockRef:{self.ClockRef}"


class AsynCmSampleBufPacket(AyncPacket):

    def __init__(self, ClockRef, CMSampleBuf):
        super().__init__(ClockRef)
        self.CMSampleBuf: CMSampleBuffer = CMSampleBuf

    @classmethod
    def from_bytes(self, buffer):
        magic = struct.unpack('<I', buffer[12:16])[0]
        _, clockRef = parse_asyn_header(buffer, magic)

        if magic == AyncConst.FEED:
            CMSampleBuf = CMSampleBuffer.from_bytesVideo(buffer[16:])
        else:
            CMSampleBuf = CMSampleBuffer.from_bytesAudio(buffer[16:])
        return self(clockRef, CMSampleBuf)

    def __str__(self):
        return f'AsynCmSampleBufPacket >> ClockRef:{self.ClockRef},CMSampleBuf:{self.CMSampleBuf} '


class AsynRelsPacket(AyncPacket):
    messageMagic = AyncConst.RELS

    def __init__(self, ClockRef):
        super().__init__(ClockRef)
        self.ClockRef = ClockRef

    def __str__(self):
        return f"AsynRelsPacket >> ClockRef: {self.ClockRef}"


class AsynSprpPacket(AyncPacket):
    messageMagic = AyncConst.SPRP

    def __init__(self, ClockRef, Property):
        super().__init__(ClockRef)
        self.ClockRef = ClockRef
        self.Property = Property

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef = parse_asyn_header(buffer, self.messageMagic)
        Property = parse_key_value_dict(remainingBytes)
        return self(ClockRef, Property)

    def __str__(self):
        return f"AsynRelsPacket >> ClockRef: {self.ClockRef} ,Property: {self.Property}"


class AsynSratPacket(AyncPacket):
    messageMagic = AyncConst.SRAT

    def __init__(self, ClockRef, Rate1, Rate2, Time):
        super().__init__(ClockRef)
        self.ClockRef = ClockRef
        self.Rate1 = Rate1
        self.Rate2 = Rate2
        self.Time: CMTime = Time

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef = parse_asyn_header(buffer, self.messageMagic)
        Rate1 = struct.unpack('f', remainingBytes[:4])[0]
        Rate2 = struct.unpack('f', remainingBytes[4:8])[0]
        Time = CMTime.from_buffer_copy(remainingBytes[8:])
        return self(ClockRef, Rate1, Rate2, Time)

    def __str__(self):
        return f"AsynSratPacket >> ClockRef: {self.ClockRef}, Rate1:{self.Rate1}, Rate2:{self.Rate1}, Time:{self.Time}"


class AsynTbasPacket(AyncPacket):
    messageMagic = AyncConst.TBAS

    def __init__(self, ClockRef, SomeOtherRef):
        super().__init__(ClockRef)
        self.ClockRef = ClockRef
        self.SomeOtherRef = SomeOtherRef

    @classmethod
    def from_bytes(self, buffer):
        remainingBytes, ClockRef = parse_asyn_header(buffer, self.messageMagic)
        SomeOtherRef = struct.unpack('<Q', buffer[:8])[0]
        return self(ClockRef, SomeOtherRef)

    def __str__(self):
        return f"AsynSratPacket >> ClockRef: {self.ClockRef},SomeOtherRef{self.SomeOtherRef}"


class AsynTjmpPacket(AyncPacket):
    messageMagic = AyncConst.TJMP

    def __init__(self, ClockRef, Unknown):
        super().__init__(ClockRef)
        self.ClockRef = ClockRef
        self.Unknown = Unknown

    @classmethod
    def from_bytes(self, buffer):
        Unknown, ClockRef = parse_asyn_header(buffer, self.messageMagic)

        return self(ClockRef, Unknown)

    def __str__(self):
        return f"AsynSratPacket >> ClockRef: {self.ClockRef},Unknown:{self.Unknown}"
