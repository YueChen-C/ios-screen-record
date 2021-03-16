from packet.util import find_ios_device, record_gstAdapter

if __name__ == '__main__':
    # # devices = usb.core.find(find_all=True)
    # # devices = usb.core.find(find_all=True)
    # # devices.get_active_configuration()
    device = find_ios_device()
    # record_wav(device, './test.h264', './test.wav', False)
    # send_udp(device,False)
    record_gstAdapter(device)