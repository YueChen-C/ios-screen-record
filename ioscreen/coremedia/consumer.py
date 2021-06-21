"""
最终流输出，需要继承 Consumer 类
"""

import io
import logging
import os
import socket
import struct

from .CMFormatDescription import DescriptorConst
from .CMSampleBuffer import CMSampleBuffer
from .wav import set_wav_header

startCode = b'\x00\x00\x00\x01'


class Consumer:
    def consume(self, data: CMSampleBuffer):
        pass

    def stop(self):
        pass


class AVFileWriter(Consumer):
    """ 保存 h264/wav 文件
    """
    num = 0

    def __init__(self, h264FilePath=None, wavFilePath=None, outFilePath=None, audioOnly=False):
        self.h264FilePath = h264FilePath
        self.wavFilePath = wavFilePath
        self.h264FileWriter: io.open = io.open(h264FilePath, 'wb+')
        self.wavFileWriter: io.open = io.open(wavFilePath, 'wb+')
        self.outFilePath = outFilePath
        self.audioOnly = audioOnly

    def consume(self, data: CMSampleBuffer):
        if data.MediaType == DescriptorConst.MediaTypeSound:
            return self.consume_audio(data)
        if self.audioOnly:
            return
        return self.consume_video(data)

    def consume_video(self, data: CMSampleBuffer):
        if data.HasFormatDescription:
            self.write_h264(data.FormatDescription.PPS)
            self.write_h264(data.FormatDescription.SPS)
        if not data.SampleData:
            return True
        return self.write_h264s(data.SampleData)

    def consume_audio(self, data: CMSampleBuffer):
        if not data.SampleData:
            return True
        return self.wavFileWriter.write(data.SampleData)

    def write_h264s(self, buf):
        while len(buf) > 0:
            _length = struct.unpack('>I', buf[:4])[0]
            self.write_h264(buf[4:_length + 4])
            buf = buf[_length + 4:]
        return True

    def write_h264(self, naluBuf):
        self.h264FileWriter.write(startCode)
        self.h264FileWriter.write(naluBuf)
        return True

    def stop(self):
        self.h264FileWriter.close()
        self.wavFileWriter.close()
        size = os.stat(self.wavFilePath).st_size
        with open(self.wavFilePath, 'rb+') as file:
            set_wav_header(size, file)


class SocketUDP(Consumer):
    """
    发送 udp h264 裸流, 在 mac 有限制长度，需要 udp 长度切割，但是数据会积压延迟会变大，仅测试用
    :param naluBuf:
    :return:
    """

    def __init__(self, broadcast=None, audioOnly=False):

        self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast = broadcast or ('127.0.0.1', 8880)
        self.audioOnly = audioOnly
        logging.info(f'listen UDP: udp/h264://{self.broadcast[0]}:{self.broadcast[1]}')

    def consume(self, data: CMSampleBuffer):
        if data.MediaType == DescriptorConst.MediaTypeSound:
            return
        return self.consume_video(data)

    def consume_video(self, data: CMSampleBuffer):
        if data.HasFormatDescription:
            self.write_udp(data.FormatDescription.PPS)
            self.write_udp(data.FormatDescription.SPS)
        if not data.SampleData:
            return True
        return self.write_buf(data.SampleData)

    def write_buf(self, buf):
        while len(buf) > 0:
            _length = struct.unpack('>I', buf[:4])[0]
            self.write_udp(buf[4:_length + 4])
            buf = buf[_length + 4:]
        return True

    def write_udp(self, naluBuf):
        self.socket_udp.sendto(startCode, self.broadcast)
        index = 0
        ## vlc 接收长度过大会绿屏？？
        while len(naluBuf) >= index:
            self.socket_udp.sendto(naluBuf[index:index + 1024], self.broadcast)
            index += 1024
        return True

    def stop(self):
        self.socket_udp.close()

