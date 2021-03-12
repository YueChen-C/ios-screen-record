import _thread
import array
import logging
import signal
import struct
import threading
from time import sleep, time

import usb
from usb.core import Configuration

from .coremedia.consumer import AVFileWriter, SocketUDP
from packet.meaasge import MessageProcessor

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


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
        _device = next(devices)
    else:
        for device in devices:
            if udid in device.serial_number:
                _device = device
    if not _device:
        raise Exception(f'not find {udid}')

    return _device


def enable_qt_config(device):
    """ 开启 qt 配置选项
    :param device:
    :return:
    """
    val = device.ctrl_transfer(0x40, 0x52, 0, 2, b'')
    if val:
        raise Exception(f'Enable QTConfig Error {val} ')
    while 5:
        try:
            device = find_ios_device(device.serial_number)
            break
        except:
            pass
    return device


def disable_qt_config(device):
    """ 关闭 qt 配置选项
    :param device:
    :return:
    """
    val = device.ctrl_transfer(0x40, 0x52, 0, 0, b'')
    if val:
        logging.warning('Failed sending control transfer for enabling hidden QT config')


class ByteStream:
    # mutex = threading.Lock()

    def __init__(self):
        self._byte = bytearray()

    def put(self, _byte: array):
        # self.mutex.acquire()
        self._byte.extend(_byte)
        # self.mutex.release()
        return True

    def get(self, num: int, timeout=5):
        t1 = time()
        while num > len(self._byte):
            if timeout < t1 - time():
                break
        # self.mutex.acquire()
        _byte = self._byte[:num]
        self._byte = self._byte[num:]
        # self.mutex.release()
        return _byte


def record_wav(device, h264FilePath, wavFilePath, audioOnly):
    consumer = AVFileWriter(h264FilePath=h264FilePath, wavFilePath=wavFilePath, audioOnly=audioOnly)
    stopSignal = threading.Event()
    start_reading(consumer, device, stopSignal)


def send_udp(device, audioOnly):
    consumer = SocketUDP(audioOnly=audioOnly)
    stopSignal = threading.Event()
    start_reading(consumer, device, stopSignal)


def start_reading(consumer, device, stopSignal: threading.Event = None):
    stopSignal = stopSignal or threading.Event()

    def shutdown(num, frame):
        stopSignal.set()

    for sig in [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]:
        signal.signal(sig, shutdown)

    disable_qt_config(device)
    device.set_configuration()
    logging.info("enable_qt_config..")
    device = enable_qt_config(device)
    QTConfigIndex = 0
    QTConfig = None
    for i in range(device.bNumConfigurations):
        _config = Configuration(device, i)
        QTConfig = usb.util.find_descriptor(_config, bInterfaceSubClass=0x2A)
        if QTConfig:
            QTConfigIndex = i + 1
            break
    device.set_configuration(QTConfigIndex)
    device.ctrl_transfer(0x02, 0x01, 0, 0x86, b'')
    device.ctrl_transfer(0x02, 0x01, 0, 0x05, b'')
    if not QTConfig:
        raise Exception('Find QTConfig Error')
    inEndpoint = outEndpoint = None
    for i in QTConfig:
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
                data = device.read(inEndpoint, 1024 * 1024, 5000)
                byteStream.put(data)
            except Exception as E:
                logging.error(E)
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
            message.ReceiveData(buffer)

    _thread.start_new_thread(writeStream, ())
    _thread.start_new_thread(readStream, ())

    while not stopSignal.wait(1):
        pass
    message.CloseSession()
    consumer.stop()
    disable_qt_config(device)




if __name__ == '__main__':
    # # devices = usb.core.find(find_all=True)
    # # devices = usb.core.find(find_all=True)
    # # devices.get_active_configuration()
    device = find_ios_device('9a4597f837b52349346008e14fd081a1e2e3840d')
    # send_udp(device,False)
    record_wav(device, './test2.h264', './test2.wav', False)
    # disable_qt_config(device)
    # device.set_configuration()
    # device = enable_qt_config(device)
    # device.set_configuration(6)
    # device.ctrl_transfer(0x02, 0x01, 0, 0x86, b'')
    # device.ctrl_transfer(0x02, 0x01, 0, 0x05, b'')
    # # print(device)
    # # cfg = device.get_active_configuration()
    # # intf = cfg[(0,0)]
    # # print(intf)
    # # 获取配置 CONFIGURATION 6 的具体数据
    # config = Configuration(device, 5)
    # # 获取 QuickTime Interface 节点内容
    #
    # qt_interface = usb.util.find_descriptor(config, bInterfaceSubClass=0x2A)
    # # print(qt_interface)
    # inEndpoint = outEndpoint = None
    # for i in qt_interface:
    #     if usb.util.endpoint_direction(i.bEndpointAddress) == usb.util.ENDPOINT_IN:
    #         # 入口端点
    #         inEndpoint = i
    #     if usb.util.endpoint_direction(i.bEndpointAddress) == usb.util.ENDPOINT_OUT:
    #         # 出口端点
    #         outEndpoint = i
    # if not inEndpoint or not outEndpoint:
    #     raise Exception('could not get InEndpoint or outEndpoint')
    #
    # logging.info("Device '%s' USB connection ready, waiting for ping..")
    # print(inEndpoint,outEndpoint)
    # while True:
    #     ret = device.read(inEndpoint, 4096, 10000)
    #     # _length = struct.unpack('<I', ret)[0]
    #     # data = device.read(inEndpoint, _length - 1, 1000)
    #     print(ret)
