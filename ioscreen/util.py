import _thread
import array
import logging
import signal
import struct
import sys
import threading
from time import sleep, time
import usb
from usb.core import Configuration

from .coremedia.consumer import AVFileWriter, SocketUDP, GstAdapter
from .meaasge import MessageProcessor

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class iOSDevice:
    def __init__(self, SerialNumber, ProductName, UsbMuxConfigInde, QTConfigIndex, VID, PID, UsbInfo):
        self.SerialNumber = SerialNumber
        self.ProductName = ProductName
        self.UsbMuxConfigInde = UsbMuxConfigInde
        self.QTConfigIndex = QTConfigIndex
        self.VID = VID
        self.PID = PID
        self.UsbInfo = UsbInfo


def find_ios_device(udid=None):
    class find_class(object):
        def __init__(self, class_):
            self._class = class_

        def __call__(self, device):
            if device.bDeviceClass == self._class:
                return True
            for cfg in device:
                intf = usb.util.find_descriptor(
                    cfg,
                    bInterfaceSubClass=self._class
                )
                if intf is not None:
                    return True
            return False

    devices = usb.core.find(find_all=True, custom_match=find_class(0xfe))
    _device = None
    if not udid:
        try:
            _device = next(devices)
        except StopIteration:
            logging.warning('未找到 iOS 连接设备')
            sys.exit()
    else:
        for device in devices:
            if udid in device.serial_number:
                logging.info(f'Find Device UDID: {device.serial_number}')
                _device = device
    if not _device:
        raise Exception(f'not find {udid}')

    return _device


def enable_qt_config(device,stopSignal):
    """ 开启 qt 配置选项
    :param device:
    :return:
    """
    logging.info('Enabling hidden QT config')
    val = device.ctrl_transfer(0x40, 0x52, 0, 2, b'')
    if val:
        raise Exception(f'Enable QTConfig Error {val} ')
    for _ in range(5):
        try:
            device = find_ios_device(device.serial_number)
            break
        except Exception as E:
            logging.error(E)
    else:
        stopSignal.set()
    return device


def disable_qt_config(device):
    """ 关闭 qt 配置选项
    :param device:
    :return:
    """
    logging.info('Disabling hidden QT config')
    val = device.ctrl_transfer(0x40, 0x52, 0, 0, b'')
    if val:
        logging.warning('Failed sending control transfer for enabling hidden QT config')


class ByteStream:
    # mutex = threading.Lock()

    def __init__(self):
        self._byte = bytearray()

    def put(self, _byte: array):
        self._byte.extend(_byte)
        return True

    def get(self, num: int, timeout=5):
        t1 = time()
        while num > len(self._byte):
            sleep(0.01)
            if timeout < t1 - time():
                break
        _byte = self._byte[:num]
        self._byte = self._byte[num:]
        return _byte


def register_signal(stopSignal):
    def shutdown(num, frame):
        stopSignal.set()

    for sig in [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]:
        signal.signal(sig, shutdown)


def record_wav(device, h264FilePath, wavFilePath, audio_only=False):
    consumer = AVFileWriter(h264FilePath=h264FilePath, wavFilePath=wavFilePath, audioOnly=audio_only)
    stopSignal = threading.Event()
    register_signal(stopSignal)
    start_reading(consumer, device, stopSignal)


def record_udp(device, audio_only=False):
    consumer = SocketUDP(audioOnly=audio_only)
    stopSignal = threading.Event()
    register_signal(stopSignal)
    start_reading(consumer, device, stopSignal)


def record_gstreamer(device):
    stopSignal = threading.Event()
    register_signal(stopSignal)
    consumer = GstAdapter.new(stopSignal)
    _thread.start_new_thread(start_reading, (consumer, device, stopSignal,))
    consumer.loop.run()


def start_reading(consumer, device, stopSignal: threading.Event = None):
    stopSignal = stopSignal or threading.Event()
    disable_qt_config(device)
    device.set_configuration()
    logging.info("enable_qt_config..")
    device = enable_qt_config(device,stopSignal)
    config_index = 0
    qt_config = None
    for i in range(device.bNumConfigurations):
        _config = Configuration(device, i)
        qt_config = usb.util.find_descriptor(_config, bInterfaceSubClass=0x2A)
        if qt_config:
            config_index = i + 1
            break
    device.set_configuration(config_index)
    device.ctrl_transfer(0x02, 0x01, 0, 0x86, b'')
    device.ctrl_transfer(0x02, 0x01, 0, 0x05, b'')
    if not qt_config:
        raise Exception('Find QTConfig Error')
    inEndpoint = outEndpoint = None
    for i in qt_config:
        if usb.util.endpoint_direction(i.bEndpointAddress) == usb.util.ENDPOINT_IN:
            inEndpoint = i  # 入口端点
        if usb.util.endpoint_direction(i.bEndpointAddress) == usb.util.ENDPOINT_OUT:
            outEndpoint = i  # 出口端点
    if not inEndpoint or not outEndpoint:
        raise Exception('could not get InEndpoint or outEndpoint')
    logging.info("USB connection ready, waiting for ping..")

    message = MessageProcessor(device, inEndpoint=inEndpoint, outEndpoint=outEndpoint, stopSignal=stopSignal,
                               cmSampleBufConsumer=consumer)
    byteStream = ByteStream()

    def writeStream():
        """ 异步写入线程
        :return:
        """
        while True:
            try:
                data = device.read(inEndpoint, 1024 * 1024, 3000)
                byteStream.put(data)
            except Exception as E:
                logging.warning(E)
                message.outEndpoint = None
                message.inEndpoint = None
                stopSignal.set()
                break

    def readStream():
        """ 异步读取流数据
        :return:
        """
        while True:
            lengthBuffer = byteStream.get(4)
            _length = struct.unpack('<I', lengthBuffer)[0] - 4
            buffer = byteStream.get(_length)
            message.receive_data(buffer)

    _thread.start_new_thread(writeStream, ())
    _thread.start_new_thread(readStream, ())

    while not stopSignal.wait(1):
        pass
    message.close_session()
    disable_qt_config(device)
    consumer.stop()
