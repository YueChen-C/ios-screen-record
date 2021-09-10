
### 介绍
本应用程序使用 python 实现,可以通过 USB  连接 iOS 设备进行屏幕共享

- 高帧率（30〜60fps）
- 高画质
- 低延迟（<200ms）
- 非侵入性
- 支持多设备并行





#### windows 开发交流方式
该方式并不是很稳定仅供交流学习使用，这里讲解使用 libusb-win32驱动用法

1. 下载 [zadig](https://zadig.akeo.ie/) 这一步主要是用来替换驱动
2. 打开 zadig 勾选 list all devices，并取消勾选 lgnore hubs，可以看到 iphone(Composite Parent) 别选成了 apple usb 了选择替换成 libusb-win32 驱动
3. 如果 曾经使用 zadig 替换驱动，那么可以省略第二步。
   - 直接打开设备管理列表-> 选择 Apple Mobile Device USB Composite Device（有相似的别选错了）
   - 更新驱动设备选择从本地计算机驱动选择 -> 列表中选择 libusb-win32 驱动即可j
   - 驱动更换完毕之后将设备重新插入，即可使用心得驱动了
4. 将 pyusb 的驱动变更成 libusb-win32 驱动，下载地址 [libusb-win32](https://nchc.dl.sourceforge.net/project/libusb-win32/libusb-win32-releases/1.2.6.0/libusb-win32-bin-1.2.6.0.zip) 示例
   ```python
   from usb.backend import libusb0
   import usb,os
   backend0 = libusb0.get_backend(lambda x:os.getcwd()+'/libusb0.dll')
   devices = usb.core.find(find_all=True,backend=backend0)
   ```
5. 测试隐藏配置是否能成功激活运行 get_config.py 看到有  bInterfaceSubClass :   0x2a 的配置代表音视频隐藏配置已激活

6. 运行代码录制音视频的代码,可成功接收到 ping 等数据
>2021-09-10 16:44:19,632 - util.py[line:176] - INFO: USB connection ready, waiting for ping..
接收： array('B', [16, 0, 0, 0, 103, 110, 105, 112, 0, 0, 0, 0, 1, 0, 0, 0])
写入: b'\x10\x00\x00\x00gnip\x00\x00\x00\x00\x01\x00\x00\x00'
2021-09-10 16:44:19,647 - meaasge.py[line:148] - INFO: 接收到 PING
2021-09-10 16:44:19,647 - meaasge.py[line:149] - INFO: AudioVideo-Stream has start success