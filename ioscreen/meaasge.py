import logging
import struct
import threading

from .coremedia.consumer import Consumer
from .asyn import AyncConst, create_hpd1_device, new_asyn_dict_packet, create_hpa1_device, \
    asyn_need_packet_bytes, AsynCmSampleBufPacket, AsynSprpPacket, AsynTjmpPacket, AsynSratPacket, AsynTbasPacket, \
    AsynRelsPacket, asyn_hpa0, asyn_hpd0
from .coremedia.CMclock import CMClock, calculate_skew
from .ping import PingConst, new_ping_packet_bytes
from .sync import SyncConst, SyncOGPacket, SyncCwpaPacket, clock_ref_reply, SyncCvrpPacket, SyncClockPacket, \
    SyncTimePacket, SyncAfmtPacket, SyncSkewPacket, SyncStopPacket


class MessageProcessor:
    stopSignal = None
    clock = None
    needClockRef = None
    needMessage = None
    clockBuilder = None
    firstAudioTimeTaken = None
    startTimeDeviceAudioClock = None
    startTimeLocalAudioClock = None
    lastEatFrameReceivedDeviceAudioClockTime = None
    lastEatFrameReceivedLocalAudioClockTime = None
    releaseWaiter = threading.Event()  # 主动结束回调

    def __init__(self, device, inEndpoint, outEndpoint, stopSignal, cmSampleBufConsumer: Consumer):
        self.device = device
        self.inEndpoint = inEndpoint  # 输出数据端口
        self.outEndpoint = outEndpoint  # 写入数据端口
        self.stopSignal = stopSignal  # 停止标识
        self.localAudioClock = None
        self.deviceAudioClockRef = None
        self.cmSampleBufConsumer: Consumer = cmSampleBufConsumer  # 处理输出数据

    def usbWrite(self, data):
        # print('写入:',data)
        self.device.write(self.outEndpoint, data, 100)

    def handleSyncPacket(self, buffer: bytes):

        code = struct.unpack('<I', buffer[12:16])[0]
        if code == SyncConst.OG:
            ogPacket = SyncOGPacket.from_bytes(buffer)
            self.usbWrite(ogPacket.to_bytes())

        elif code == SyncConst.CWPA:
            cwpaPacket = SyncCwpaPacket.from_bytes(buffer)
            clockRef = cwpaPacket.DeviceClockRef + 1000
            self.localAudioClock = CMClock.new(clockRef)
            self.deviceAudioClockRef = cwpaPacket.DeviceClockRef
            deviceInfo = new_asyn_dict_packet(create_hpd1_device(), AyncConst.HPD1, 1)
            logging.debug("Sending ASYN HPD1")
            self.usbWrite(deviceInfo)

            logging.debug("Send CWPA-RPLY {correlation:%x, clockRef:%x}", cwpaPacket.CorrelationID, clockRef)
            self.usbWrite(clock_ref_reply(clockRef, cwpaPacket.CorrelationID))
            logging.debug("Sending ASYN HPD1")
            self.usbWrite(deviceInfo)
            deviceInfo1 = new_asyn_dict_packet(create_hpa1_device(), AyncConst.HPA1, cwpaPacket.DeviceClockRef)
            logging.debug("Sending ASYN HPA1")
            self.usbWrite(deviceInfo1)

        elif code == SyncConst.CVRP:
            cvrpPacket = SyncCvrpPacket.from_bytes(buffer)
            self.needClockRef = cvrpPacket.DeviceClockRef
            self.needMessage = asyn_need_packet_bytes(cvrpPacket.DeviceClockRef)
            self.usbWrite(self.needMessage)
            clockRef2 = cvrpPacket.DeviceClockRef + 0x1000AF
            self.usbWrite(clock_ref_reply(clockRef2, cvrpPacket.CorrelationID))

        elif code == SyncConst.CLOK:
            clockPacket = SyncClockPacket.from_bytes(buffer)
            clockRef = clockPacket.ClockRef + 0x10000
            self.clock = CMClock.new(clockRef)  # 本地时钟用来同步时间差
            replyBytes = clock_ref_reply(clockRef, clockPacket.CorrelationID)
            self.usbWrite(replyBytes)

        elif code == SyncConst.TIME:
            timePacket = SyncTimePacket.from_bytes(buffer)
            timeToSend = self.clock.getTime()
            replyBytes = timePacket.to_bytes(timeToSend)
            self.usbWrite(replyBytes)

        elif code == SyncConst.AFMT:
            afmtPacket = SyncAfmtPacket.from_bytes(buffer)
            replyBytes = afmtPacket.to_bytes()
            self.usbWrite(replyBytes)

        elif code == SyncConst.SKEW:
            afmtPacket = SyncSkewPacket.from_bytes(buffer)
            skewValue = calculate_skew(self.startTimeLocalAudioClock, self.lastEatFrameReceivedLocalAudioClockTime,
                                       self.startTimeDeviceAudioClock, self.lastEatFrameReceivedDeviceAudioClockTime)
            replyBytes = afmtPacket.to_bytes(skewValue)
            self.usbWrite(replyBytes)

        elif code == SyncConst.STOP:
            stopPacket = SyncStopPacket.from_bytes(buffer)
            replyBytes = stopPacket.to_bytes()
            self.usbWrite(replyBytes)

        else:
            logging.warning("received unknown sync ioscreen type: %x", buffer)

    def handleAsyncPacket(self, buffer: bytes):
        code = struct.unpack('<I', buffer[12:16])[0]
        if code == AyncConst.EAT:
            eatPacket = AsynCmSampleBufPacket.from_bytes(buffer)
            if self.firstAudioTimeTaken:  # 第一次接入记录本地时间
                self.lastEatFrameReceivedDeviceAudioClockTime = eatPacket.CMSampleBuf.OutputPresentationTimestamp
                self.lastEatFrameReceivedLocalAudioClockTime = self.localAudioClock.getTime()
            else:
                self.startTimeDeviceAudioClock = eatPacket.CMSampleBuf.OutputPresentationTimestamp
                self.startTimeLocalAudioClock = self.localAudioClock.getTime()
                self.lastEatFrameReceivedDeviceAudioClockTime = eatPacket.CMSampleBuf.OutputPresentationTimestamp
                self.lastEatFrameReceivedLocalAudioClockTime = self.startTimeLocalAudioClock
                self.firstAudioTimeTaken = True
            self.cmSampleBufConsumer.consume(eatPacket.CMSampleBuf)
        elif code == AyncConst.FEED:
            feedPacket = AsynCmSampleBufPacket.from_bytes(buffer)
            self.cmSampleBufConsumer.consume(feedPacket.CMSampleBuf)
            self.usbWrite(self.needMessage)
        elif code == AyncConst.SPRP:
            Packet = AsynSprpPacket.from_bytes(buffer)
            logging.debug(Packet)

        elif code == AyncConst.TJMP:
            Packet = AsynTjmpPacket.from_bytes(buffer)
            logging.debug(Packet)

        elif code == AyncConst.SRAT:
            Packet = AsynSratPacket.from_bytes(buffer)
            logging.debug(Packet)

        elif code == AyncConst.TBAS:
            Packet = AsynTbasPacket.from_bytes(buffer)
            logging.debug(Packet)

        elif code == AyncConst.RELS:
            Packet = AsynRelsPacket.from_bytes(buffer)
            logging.debug(Packet)
            self.releaseWaiter.set()

    def receive_data(self, buffer):
        code = struct.unpack('<I', buffer[:4])[0]
        if code == PingConst.PingPacketMagic:
            logging.info("AudioVideo-Stream has start success")
            self.usbWrite(new_ping_packet_bytes())
        elif code == SyncConst.SyncPacketMagic:
            self.handleSyncPacket(buffer)
        elif code == AyncConst.AsyncPacketMagic:
            self.handleAsyncPacket(buffer)
        else:
            logging.warning(f'received unknown ioscreen {buffer}')

    def close_session(self):
        # 如非正常关闭有可能会造成设备无法访问，需要重插 usb 或重启设备
        logging.info("Telling device to stop streaming..")
        if self.outEndpoint:
            self.usbWrite(asyn_hpa0(self.deviceAudioClockRef))
            self.usbWrite(asyn_hpd0())
            while not self.releaseWaiter.wait(5):
                logging.warning("Timed out waiting for device closing")
                break
            logging.info("Waiting for device to tell us to stop..")
            self.usbWrite(asyn_hpd0())
            logging.info("Ready to release USB Device.")

    def stop(self):
        self.stopSignal.set()
