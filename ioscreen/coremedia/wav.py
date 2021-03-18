import struct
from ctypes import c_uint32, c_uint16
from _ctypes import Structure


class RiffHeader(Structure):
    _fields_ = [
        ('ChunkID', c_uint32),
        ('ChunkSize', c_uint32),
        ('Format', c_uint32),
    ]

    @classmethod
    def new(cls, size):
        return cls(ChunkID=0x46464952, Format=0x45564157, ChunkSize=int(36 + size))


class FmtSubChunk(Structure):
    _fields_ = [
        ('SubChunkID', c_uint32),
        ('SubChunkSize', c_uint32),
        ('AudioFormat', c_uint16),
        ('NumChannels', c_uint16),
        ('SampleRate', c_uint32),
        ('ByteRate', c_uint32),
        ('BlockAlign', c_uint16),
        ('BitsPerSample', c_uint16),
    ]

    @classmethod
    def new(cls):
        result = cls()
        result.SubChunkID = 0x20746d66
        result.SubChunkSize = 16
        result.AudioFormat = 1
        result.NumChannels = 2
        result.SampleRate = 48000
        result.BitsPerSample = 16
        result.ByteRate = int(result.SampleRate * result.NumChannels * result.BitsPerSample / 8)
        result.BlockAlign = int(result.NumChannels * (result.BitsPerSample / 8))
        return result


def set_wav_header(_length, wavFile):
    buf = get_wav_header(_length)
    wavFile.seek(0)
    wavFile.write(buf)


def get_wav_header(_length):
    buf = b''
    riff = RiffHeader.new(_length)
    buf += bytes(riff)
    fmt = FmtSubChunk().new()
    buf += bytes(fmt)
    buf += struct.pack('>I', 0x64617461)
    buf += struct.pack('<I', _length)
    return buf