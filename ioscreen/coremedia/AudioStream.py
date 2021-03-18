## iOS AudioStreamBasicDescription
import struct
from _ctypes import Structure
from ctypes import c_uint32, c_double

AudioFormatIDLMagic = 0x6C70636D


class AudioStreamBasicDescription(Structure):
    _fields_ = [
        ('SampleRate', c_double),
        ('FormatID', c_uint32),
        ('FormatFlags', c_uint32),
        ('BytesPerPacket', c_uint32),
        ('FramesPerPacket', c_uint32),
        ('BytesPerFrame', c_uint32),
        ('ChannelsPerFrame', c_uint32),
        ('BitsPerChannel', c_uint32),
        ('Reserved', c_uint32),

    ]

    def __str__(self):
        return f"AudioStreamBasicDescription >> SampleRate:{self.SampleRate},FormatFlags:{self.FormatFlags}" \
               f",BytesPerPacket:{self.BytesPerPacket},FramesPerPacket:{self.FramesPerPacket}," \
               f"BytesPerFrame:{self.BytesPerFrame},ChannelsPerFrame:{self.ChannelsPerFrame}," \
               f"BitsPerChannel:{self.BitsPerChannel},Reserved:{self.Reserved}"

    def to_bytes(self):
        buf = bytes(self) + struct.pack('<dd', self.SampleRate, self.SampleRate)
        return buf

    @classmethod
    def new(cls):
        return cls(FormatFlags=12,
                   BytesPerPacket=4, FramesPerPacket=1, BytesPerFrame=4, ChannelsPerFrame=2,
                   BitsPerChannel=16, Reserved=0,
                   SampleRate=48000.0, FormatID=AudioFormatIDLMagic)

