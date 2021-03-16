
### 介绍
本应用程序使用 python 实现,可以通过 USB  连接 iOS 设备进行屏幕共享

- 高帧率（30〜60fps）
- 高画质
- 低延迟（<200ms）
- 非侵入性
- 支持多设备并行



####  Mac OSX 安装
1. `brew install libusb pkg-config`
2. 如需使用 gstreamer 则需要安装 `brew install gstreamer gst-plugins-bad gst-plugins-good gst-plugins-base gst-plugins-ugly`
2. `python install -r requirements.txt`



#### 使用 
```bash
# vlc 工具播放udp地址： udp/h264://@:8880
# 转发 h264 udp 广播  
$ main.py --udid=xxxx udp

# 录制 h264/wav 文件
$ main.py --udid=xxxx record -h264File=/home/out.h264  -wavFile=/home/out.wav

# gstadapter 渲染显示画面
$ main.py --udid=xxxx gstadapter
```

