import logging
import struct
import threading

from .coremedia.consumer import Consumer
from packet.asyn import AyncConst, CreateHpd1DeviceInfoDict, newAsynDictPacket, CreateHpa1DeviceInfoDict, \
    AsynNeedPacketBytes, AsynCmSampleBufPacket, AsynSprpPacket, AsynTjmpPacket, AsynSratPacket, AsynTbasPacket, \
    AsynRelsPacket, AsynHPA0, AsynHPD0
from packet.coremedia.CMclock import CMClock, calculate_skew
from packet.ping import PingConst, new_ping_packet_bytes
from .sync import SyncConst, SyncOGPacket, SyncCwpaPacket, clockRefReply, SyncCvrpPacket, SyncClockPacket, \
    SyncTimePacket, SyncAfmtPacket, SyncSkewPacket, SyncStopPacket


class MessageProcessor:
    stopSignal = None
    clock = None
    needClockRef = None
    needMessage = None
    audioSamplesReceived = 0
    videoSamplesReceived = 0
    clockBuilder = None
    releaseWaiter = threading.Event()
    firstAudioTimeTaken = None
    startTimeDeviceAudioClock = None
    startTimeLocalAudioClock = None
    lastEatFrameReceivedDeviceAudioClockTime = None
    lastEatFrameReceivedLocalAudioClockTime = None

    def __init__(self, device, inEndpoint, outEndpoint, stopSignal, cmSampleBufConsumer):
        self.device = device
        self.inEndpoint = inEndpoint
        self.outEndpoint = outEndpoint
        self.stopSignal = stopSignal
        self.localAudioClock = None
        self.deviceAudioClockRef = None
        self.cmSampleBufConsumer: Consumer = cmSampleBufConsumer

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
            self.localAudioClock = CMClock.new_clock(clockRef)
            self.deviceAudioClockRef = cwpaPacket.DeviceClockRef
            deviceInfo = newAsynDictPacket(CreateHpd1DeviceInfoDict(), AyncConst.HPD1, 1)
            logging.debug("Sending ASYN HPD1")
            self.usbWrite(deviceInfo)

            logging.debug("Send CWPA-RPLY {correlation:%x, clockRef:%x}", cwpaPacket.CorrelationID, clockRef)
            self.usbWrite(clockRefReply(clockRef, cwpaPacket.CorrelationID))
            logging.debug("Sending ASYN HPD1")
            self.usbWrite(deviceInfo)
            deviceInfo1 = newAsynDictPacket(CreateHpa1DeviceInfoDict(), AyncConst.HPA1, cwpaPacket.DeviceClockRef)
            logging.debug("Sending ASYN HPA1")
            self.usbWrite(deviceInfo1)

        elif code == SyncConst.CVRP:
            cvrpPacket = SyncCvrpPacket.from_bytes(buffer)
            self.needClockRef = cvrpPacket.DeviceClockRef
            self.needMessage = AsynNeedPacketBytes(cvrpPacket.DeviceClockRef)
            self.usbWrite(self.needMessage)
            clockRef2 = cvrpPacket.DeviceClockRef + 0x1000AF
            self.usbWrite(clockRefReply(clockRef2, cvrpPacket.CorrelationID))

        elif code == SyncConst.CLOK:
            clockPacket = SyncClockPacket.from_bytes(buffer)
            clockRef = clockPacket.ClockRef + 0x10000
            self.clock = CMClock.new_clock(clockRef)
            replyBytes = clockRefReply(clockRef, clockPacket.CorrelationID)
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
            logging.warning("received unknown sync packet type: %x", buffer)

    def handleAsyncPacket(self, buffer: bytes):
        code = struct.unpack('<I', buffer[12:16])[0]
        if code == AyncConst.EAT:
            self.audioSamplesReceived += 1
            eatPacket = AsynCmSampleBufPacket.from_bytes(buffer)
            if self.firstAudioTimeTaken:
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
            self.videoSamplesReceived += 1
            self.cmSampleBufConsumer.consume(feedPacket.CMSampleBuf)
            if self.videoSamplesReceived % 500 == 0:
                self.videoSamplesReceived = 0
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

    def ReceiveData(self, buffer):
        code = struct.unpack('<I', buffer[:4])[0]
        if code == PingConst.PingPacketMagic:
            logging.info("AudioVideo-Stream has start success")
            self.usbWrite(new_ping_packet_bytes())
        elif code == SyncConst.SyncPacketMagic:
            self.handleSyncPacket(buffer)
        elif code == AyncConst.AsyncPacketMagic:
            self.handleAsyncPacket(buffer)
        else:
            logging.warning(f'received unknown packet {buffer}')

    def CloseSession(self):
        logging.info("Telling device to stop streaming..")
        self.usbWrite(AsynHPA0(self.deviceAudioClockRef))
        self.usbWrite(AsynHPD0())
        while not self.releaseWaiter.wait(5):
            logging.warning("Timed out waiting for device closing")
            break
        logging.info("Waiting for device to tell us to stop..")
        self.usbWrite(AsynHPD0())
        logging.info("Ready to release USB Device.")

    def stop(self):
        self.stopSignal.set()