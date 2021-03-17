"""
最终流输出，需要继承 Consumer 类
"""

import io
import logging
import os
import socket
import struct
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst

from .CMFormatDescription import DescriptorConst
from .CMSampleBuffer import CMSampleBuffer
from .gstreamer import setup_video_pipeline, setup_audio_pipeline, setup_live_playAudio, run_main_loop
from .wav import set_wav_header, get_wav_header

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


class GstAdapter(Consumer):
    audioAppSrcTargetElementName = "audio_target"
    videoAppSrcTargetElementName = "video_target"
    MP3 = "mp3"
    OGG = "ogg"

    def __init__(self, videoAppSrc, audioAppSrc, firstAudioSample, loop=None, pipeline=None,stopSignal=None):
        self.videoAppSrc = videoAppSrc
        self.audioAppSrc = audioAppSrc
        self.firstAudioSample = firstAudioSample
        self.pipeline = pipeline
        self.loop = loop
        self.stopSignal = stopSignal

    @classmethod
    def new(cls, stopSignal):
        Gst.init(None)
        logging.info("Starting Gstreamer..")
        pipe = Gst.Pipeline.new("QT_Hack_Pipeline")
        videoAppSrc = setup_video_pipeline(pipe)
        audioAppSrc = setup_audio_pipeline(pipe)
        setup_live_playAudio(pipe)
        pipe.set_state(Gst.State.PLAYING)
        loop = run_main_loop(pipe,stopSignal)
        # _thread.start_new_thread(run_main_loop, (pipe,))
        logging.info("Gstreamer is running!")
        return cls(videoAppSrc, audioAppSrc, True, loop)

    def consume(self, data: CMSampleBuffer):
        if data.MediaType == DescriptorConst.MediaTypeSound:
            if self.firstAudioSample:
                self.firstAudioSample = False
                self.send_wav_header()
            return self.send_audio_sample(data)

        if data.OutputPresentationTimestamp.CMTimeValue > 17446044073700192000:
            data.OutputPresentationTimestamp.CMTimeValue = 0

        if data.HasFormatDescription:
            data.OutputPresentationTimestamp.CMTimeValue = 0
            self.write_app_src(startCode + data.FormatDescription.PPS, data)
            self.write_app_src(startCode + data.FormatDescription.SPS, data)
        self.write_buffers(data)

    def write_buffers(self, data: CMSampleBuffer):
        buf = data.SampleData
        if buf:
            while len(buf) > 0:
                _length = struct.unpack('>I', buf[:4])[0]
                self.write_app_src(startCode + buf[4:_length + 4], data)
                buf = buf[_length + 4:]
        return True

    def write_app_src(self, buf, data: CMSampleBuffer):
        gstBuf = Gst.Buffer.new_allocate(None, len(buf), None)
        gstBuf.pts = data.OutputPresentationTimestamp.CMTimeValue
        gstBuf.dts = 0
        gstBuf.fill(0, buf)
        self.videoAppSrc.emit('push-buffer', gstBuf)

    def send_wav_header(self):
        wav_header = get_wav_header(100)
        gstBuf = Gst.Buffer.new_allocate(None, len(wav_header), None)
        gstBuf.pts = 0
        gstBuf.dts = 0
        gstBuf.fill(0, wav_header)
        self.audioAppSrc.emit('push-buffer', gstBuf)

    def send_audio_sample(self, data: CMSampleBuffer):
        gstBuf = Gst.Buffer.new_allocate(None, len(data.SampleData), None)
        gstBuf.pts = data.OutputPresentationTimestamp.CMTimeValue
        gstBuf.dts = 0
        gstBuf.fill(0, data.SampleData)
        self.audioAppSrc.emit('push-buffer', gstBuf)

    def stop(self):
        if self.audioAppSrc:
            self.audioAppSrc.send_event(Gst.Event.new_eos())
        if self.videoAppSrc:
            self.videoAppSrc.send_event(Gst.Event.new_eos())
        if not self.pipeline:
            return
