iOS Screen
### 基本概念
1. libimobiledevice: iTunes管理iPhone功能第三⽅开源替代品
2. libusbmuxd: libimobiledevice基于此库通过跟iTunes驱动提供的，AppleMobileDeviceService.exe，
实现跟iPhone USB通讯
3. usbmuxd: AppleMobileDeviceService.exe的第三⽅开源实现，基于libusb实现
4. libusb: 跨平台USB通讯⼯具，Windows下⾯的实现为libusb-win32
### Windows跟iPhone的通讯⽅式
1. iTunes -> AppleMobileDeviceService.exe（⾃带USB驱动） -> iPhone
2. libimobiledevice -> AppleMobileDeviceService.exe（⾃带USB驱动） -> iPhone
3. libimobiledevice -> libusbmuxd -> usbmuxd -> libusb-win32 -> iPhone


因为 iOS Screen协议⽆法通过 AppleMobileDeviceService.exe 跟iPhone通讯，所以需要用新的驱动
通讯⽅案
### 新方案
1. 可以使用编译 https://github.com/libimobiledevice-win32/usbmuxd 作为驱动
2. 也可以使用编译 https://github.com/YueChen-C/usbmuxd 作为驱动（修复了些 bug）

编译后得到：
usbmuxd.exe

你也可以用编译好的 https://github.com/iFred09/libimobiledevice-windows/archive/master.zip 来验证服务

#### 执行步骤:
1. 通过 [zadig](https://zadig.akeo.ie/) 安装libusb-win32驱动
2. 验证阶段 kill  AppleMobileDeviceService.exe 进程，避免⼲扰 usbmuxd.exe
3. 运⾏ usbmuxd.exe，运⾏成功后会⾃动监听会监听27015端
4. 执⾏ ideviceinfo.exe，如果有正常显示数据，则说明通讯⽅案跑通，如果提示 No device found
则说明通讯失败，需要排查下原因

#### 运⾏ioscreen
1. 按照上述验证步骤，libusb-win32驱 动已经安装成功
2. pip install pyusb==1.1.1
3. git clone https://github.com/YueChen-C/ios-screen-record.git && cd ios-screen_record && git checkout windows && python setup.py install
4. 通过 ideviceinfo.exe 获取 iPhone 设备的 udid，运⾏ idevicepair.exe -u 获取到的 iPhone 设备的 udid
pair 进⾏配对
5. 执⾏ ioscreen --udid=获取到的iPhone设备的udid record -h264File=out.h264 -
wavFile=out.wav ，正常情况下会在接收到 PING之后提示libusb写⼊相关的time out，是因为配对
问题
6. 修改安装的ioscreen的site-package，在代码执⾏到此处时暂停：https://github.com/YueChen-C/ios-screen-record/blob/06babe5a6452ae9918dbd653d9e6f003063c9489/ioscreen/util.py#L152
⼏秒后继续执⾏ioscreen 修改QT-Config会导致设备重连，所以这⾥要等待⼏秒
（经测试5秒⽐较稳定）等设备重连成功后继续执⾏，或者使⽤其它⽅式检测是否重连成功后再继续
执⾏），即可成功将视频流和⾳频流保存到out.h264和out.wav