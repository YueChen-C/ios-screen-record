# iOS Frameworks
# https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.9.sdk/System/Library/Frameworks/CoreMedia.framework/Versions/A/Headers/CMFormatDescription.h
import enum
import struct

from .AudioStream import AudioStreamBasicDescription
from .serialize import parse_length_magic, new_dictionary_from_bytes


class DescriptorConst(enum.IntEnum):
    FormatDescriptorMagic = 0x66647363  # fdsc - csdf
    MediaTypeVideo = 0x76696465  # vide - ediv
    MediaTypeSound = 0x736F756E  # nuos - soun
    MediaTypeMagic = 0x6D646961  # mdia - aidm
    VideoDimensionMagic = 0x7664696D  # vdim - midv
    CodecMagic = 0x636F6463  # codc - cdoc
    CodecAvc1 = 0x61766331  # avc1 - 1cva
    ExtensionMagic = 0x6578746E  # extn - ntxe
    AudioStreamBasicDescriptionMagic = 0x61736264  # asdb - dbsa


class FormatDescriptor:

    def __init__(self, MediaType=None, VideoDimensionWidth=None, VideoDimensionHeight=None, Codec=None, Extensions=None,
                 PPS=None, SPS=None, AudioStream=None):
        self.MediaType = MediaType
        self.VideoDimensionWidth = VideoDimensionWidth
        self.VideoDimensionHeight = VideoDimensionHeight
        self.Codec = Codec
        self.Extensions = Extensions
        self.PPS = PPS
        self.SPS = SPS
        self.AudioStreamBasicDescription: AudioStreamBasicDescription = AudioStream

    @classmethod
    def from_bytes(cls, buf):
        _, remainingBytes = parse_length_magic(buf, DescriptorConst.FormatDescriptorMagic)
        mediaType, remainingBytes = parse_media_type(remainingBytes)
        if mediaType == DescriptorConst.MediaTypeSound:
            length, _, = parse_length_magic(remainingBytes, DescriptorConst.AudioStreamBasicDescriptionMagic)
            AudioStream = AudioStreamBasicDescription.from_buffer_copy(remainingBytes[8:length])
            return cls(MediaType=DescriptorConst.MediaTypeSound, AudioStream=AudioStream)
        else:
            videoDimensionWidth, videoDimensionHeight, remainingBytes = parse_video_dimension(remainingBytes)
            codec, remainingBytes = parse_codec(remainingBytes)
            Extensions = new_dictionary_from_bytes(remainingBytes, DescriptorConst.ExtensionMagic)
            pps, sps = extract_pps(Extensions)
            return cls(MediaType=DescriptorConst.MediaTypeVideo, Extensions=Extensions, PPS=pps, SPS=sps, Codec=codec,
                       VideoDimensionHeight=videoDimensionHeight, VideoDimensionWidth=videoDimensionWidth)

    def __str__(self):
        if self.MediaType == DescriptorConst.MediaTypeVideo:
            return f'FormatDescriptor >>MediaType:{self.MediaType}, VideoDimension:({self.VideoDimensionWidth}x{self.VideoDimensionHeight}),' \
                   f'Codec:{self.Codec}, PPS:{self.PPS}, SPS:{self.SPS}, Extensions:{self.Extensions}'
        return f'FormatDescriptor >> MediaType:{self.MediaType}, AudioStreamBasicDescription: {self.AudioStreamBasicDescription} '


def parse_media_type(buf):
    length, _, = parse_length_magic(buf, DescriptorConst.MediaTypeMagic)
    mediaType = struct.unpack('<I', buf[8:12])[0]
    return mediaType, buf[length:]


def parse_codec(buf):
    length, _ = parse_length_magic(buf, DescriptorConst.CodecMagic)
    codec = struct.unpack('<I', buf[8:12])[0]
    return codec, buf[length:]


def parse_video_dimension(buf):
    length, _ = parse_length_magic(buf, DescriptorConst.VideoDimensionMagic)
    width = struct.unpack('<I', buf[8:12])[0]
    height = struct.unpack('<I', buf[12:16])[0]
    return width, height, buf[length:]


def extract_pps(data):
    val = None
    for i in data:
        if i == 49:
            val = data[i]
    if val:
        for i in val:
            if i == 105:
                val = val[i]
    if val:
        ppsLength = val[7]
        pps = val[8: 8 + ppsLength]
        spsLength = val[10 + ppsLength]
        sps = val[11 + ppsLength: 11 + ppsLength + spsLength]
        return pps, sps
    else:
        raise Exception("not contain PPS/SPS")
