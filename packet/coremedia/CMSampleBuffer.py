# iOS Frameworks
## https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.9.sdk/System/Library/Frameworks/CoreMedia.framework/Versions/A/Headers/CMSampleBuffer.h
import enum
import struct

from .CMFormatDescription import DescriptorConst, FormatDescriptor
from .CMTime import CMTimeConst, CMTime
from .serialize import parse_length_magic, new_dictionary_from_bytes, DictConst


class CMSampleConst(enum.IntEnum):
    sbuf = 0x73627566
    opts = 0x6F707473
    stia = 0x73746961
    sdat = 0x73646174
    satt = 0x73617474
    sary = 0x73617279
    ssiz = 0x7373697A
    nsmp = 0x6E736D70
    cmSampleTimingInfoLength = 3 * CMTimeConst.CMTimeLengthInBytes


class SampleTimingInfo:
    def __init__(self, Duration, PresentationTimeStamp, DecodeTimeStamp):
        self.Duration = Duration  # 创建时间
        self.PresentationTimeStamp = PresentationTimeStamp  # 提交时间
        self.DecodeTimeStamp = DecodeTimeStamp  # 解码时间

    def __str__(self):
        return f'SampleTimingInfo >>> Duration:{self.Duration},PresentationTimeStamp:{self.PresentationTimeStamp},' \
               f'DecodeTimeStamp:{self.DecodeTimeStamp}'


class CMSampleBuffer:
    def __init__(self, OutputPresentationTimestamp=None, FormatDescription=None, HasFormatDescription=None,
                 NumSamples=None, SampleTimingInfoArray=None, SampleData=None, SampleSizes=None, Attachments=None,
                 CreateIfNecessary=None, MediaType=None):
        self.OutputPresentationTimestamp: CMTime = OutputPresentationTimestamp
        self.FormatDescription: FormatDescriptor = FormatDescription
        self.HasFormatDescription = HasFormatDescription
        self.NumSamples = NumSamples
        self.SampleTimingInfoArray = SampleTimingInfoArray
        self.SampleData = SampleData
        self.SampleSizes = SampleSizes
        self.Attachments = Attachments
        self.CreateIfNecessary = CreateIfNecessary
        self.MediaType = MediaType

    @classmethod
    def from_bytesAudio(self, buffer):
        return self.from_bytes(buffer, DescriptorConst.MediaTypeSound)

    @classmethod
    def from_bytesVideo(self, buffer):
        return self.from_bytes(buffer, DescriptorConst.MediaTypeVideo)

    @classmethod
    def from_bytes(self, buffer, mediaType):
        sampleBuffer = CMSampleBuffer()
        sampleBuffer.MediaType = mediaType
        sampleBuffer.HasFormatDescription = False
        length, remainingBytes = parse_length_magic(buffer, CMSampleConst.sbuf)
        if length > len(buffer):
            raise Exception("CMSampleBuffer >> from_bytes length error")

        while len(remainingBytes) > 0:
            code = struct.unpack('<I', remainingBytes[4:8])[0]
            if code == CMSampleConst.opts:
                sampleBuffer.OutputPresentationTimestamp = CMTime.from_buffer_copy(remainingBytes[8:])
                remainingBytes = remainingBytes[32:]

            elif code == CMSampleConst.stia:
                sampleBuffer.SampleTimingInfoArray, remainingBytes = parse_stia(remainingBytes)

            elif code == CMSampleConst.sdat:
                length, remainingBytes = parse_length_magic(remainingBytes, CMSampleConst.sdat)
                sampleBuffer.SampleData = remainingBytes[:length - 8]
                remainingBytes = remainingBytes[length - 8:]

            elif code == CMSampleConst.nsmp:
                length, remainingBytes = parse_length_magic(remainingBytes, CMSampleConst.nsmp)
                sampleBuffer.NumSamples = struct.unpack('<I', remainingBytes[:4])[0]
                remainingBytes = remainingBytes[4:]

            elif code == CMSampleConst.ssiz:
                sampleBuffer.SampleSizes, remainingBytes = parse_samples_list(remainingBytes)

            elif code == DescriptorConst.FormatDescriptorMagic:
                sampleBuffer.HasFormatDescription = True
                fdscLength = struct.unpack('<I', remainingBytes[:4])[0]
                sampleBuffer.FormatDescription = FormatDescriptor.from_bytes(remainingBytes[:fdscLength])
                remainingBytes = remainingBytes[fdscLength:]

            elif code == CMSampleConst.satt:
                attachmentsLength = struct.unpack('<I', remainingBytes[:4])[0]
                sampleBuffer.Attachments = new_dictionary_from_bytes(remainingBytes[:attachmentsLength],
                                                                     CMSampleConst.satt)
                remainingBytes = remainingBytes[attachmentsLength:]

            elif code == CMSampleConst.sary:
                saryLength = struct.unpack('<I', remainingBytes[:4])[0]
                sampleBuffer.CreateIfNecessary = new_dictionary_from_bytes(remainingBytes[8:saryLength],
                                                                           DictConst.DictionaryMagic)
                remainingBytes = remainingBytes[saryLength:]
            else:
                unknownMagic = str(remainingBytes[4:8])
                raise Exception(f"unknown magic type {unknownMagic}, cannot parse value {remainingBytes[4:8]}")
        return sampleBuffer

    def __str__(self):

        if self.MediaType == DescriptorConst.MediaTypeVideo:
            return f"OutputPresentationTS:{self.OutputPresentationTimestamp}, NumSamples:{self.NumSamples}, " \
                   f"SampleData-len:{get_nalu_details(self.SampleData)}, FormatDescription:{self.FormatDescription}, attach:{self.Attachments}, sary:{self.CreateIfNecessary}, " \
                   f"SampleTimingInfoArray:{self.SampleTimingInfoArray[0]}"

        return f"OutputPresentationTS:{self.OutputPresentationTimestamp}, NumSamples:{self.NumSamples}" \
               f", SampleSize:{self.SampleSizes[0]},'FormatDescription:{self.FormatDescription}'"


def parse_stia(data):
    stiaLength, _, = parse_length_magic(data, CMSampleConst.stia)
    stiaLength -= 8
    numEntries, modulus = stiaLength / CMSampleConst.cmSampleTimingInfoLength, stiaLength % CMSampleConst.cmSampleTimingInfoLength
    result = []
    data = data[8:]
    for i in range(int(numEntries)):
        index = i * CMSampleConst.cmSampleTimingInfoLength
        duration = CMTime.from_buffer_copy(data[index:])
        presentationTimeStamp = CMTime.from_buffer_copy(data[CMTimeConst.CMTimeLengthInBytes + index:])
        decodeTimeStamp = CMTime.from_buffer_copy(data[2 * CMTimeConst.CMTimeLengthInBytes + index:])
        result.append(SampleTimingInfo(duration, presentationTimeStamp, decodeTimeStamp))
    return result, data[stiaLength:]


def parse_samples_list(data):
    ssizLength, _, = parse_length_magic(data, CMSampleConst.ssiz)
    ssizLength -= 8
    numEntries, modulus = ssizLength / 4, ssizLength % 4
    result = []
    data = data[8:]
    for i in range(int(numEntries)):
        index = 4 * i
        result.append(int(struct.unpack('<I', data[index + i * 4:index + i * 4 + 4])[0]))
    return result, data[ssizLength:]


def get_nalu_details(data):
    if data:
        _str = ''
        while len(data):
            _length = struct.unpack('<I', data[:4])[0]
            _str += f'[len:{_length},type：{0x1f & int(data[4])}]'
            data = data[_length + 4:]
        return
    return ''
