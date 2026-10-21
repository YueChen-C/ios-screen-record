from time import sleep
import logging
import struct
import sys
from .CMFormatDescription import DescriptorConst
from .CMSampleBuffer import CMSampleBuffer
from .wav import get_wav_header
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstVideo', '1.0')

from .consumer import startCode, Consumer
from gi.repository import Gst, GObject, GLib

GST_PLUGIN_PATH = '/usr/local/lib/gstreamer-1.0'


def ensure_macos_nsapplication():
    """GStreamer video sinks (glimagesink/osxvideosink) can only create their
    window when [NSApplication sharedApplication] exists on the main thread;
    otherwise the pipeline plays silently with no window. See the warning:
    "An NSApplication needs to be running on the main thread ...".

    The process also runs as a background (non-bundle) app by default, so
    macOS may place the video window on another display or behind other apps;
    activate it so the window shows up front on the current display.
    """
    if sys.platform != 'darwin':
        return
    try:
        import objc
        objc.loadBundle('AppKit', {}, bundle_path='/System/Library/Frameworks/AppKit.framework')
        app = objc.lookUpClass('NSApplication').sharedApplication()
        # NSApplicationActivationPolicyAccessory = 1 (activatable, no Dock icon)
        app.setActivationPolicy_(1)
        app.activateIgnoringOtherApps_(True)
    except Exception as e:
        logging.warning("Unable to initialize NSApplication, video window may not show: %s", e)


def focus_macos_video_window():
    """Bring the GStreamer video window to front and center it on its display.
    Called repeatedly on the GLib main loop until the window exists and is
    focused (the window is created lazily when the first video frame arrives)."""
    focus_macos_video_window.tries += 1
    try:
        import objc
        app = objc.lookUpClass('NSApplication').sharedApplication()
        visible = [w for w in app.windows() if w.isVisible()]
        if not visible:
            logging.info("video window not created yet (try %d), waiting for first frame..",
                         focus_macos_video_window.tries)
            return focus_macos_video_window.tries < 15
        for window in visible:
            window.center()
            window.makeKeyAndOrderFront_(None)
        app.activateIgnoringOtherApps_(True)
        logging.info("video window is now visible and focused")
        return False
    except Exception as e:
        logging.warning("Unable to focus video window: %s", e)
        return False


focus_macos_video_window.tries = 0


def run_consumer_loop(consumer):
    """Run the GStreamer GLib main loop.

    On macOS the Cocoa run loop must be serviced on the main thread, or the
    GStreamer video window is created unreliably (sometimes never, sometimes
    on the wrong display). At the same time the main thread must keep
    executing Python code for signal handlers (Ctrl-C) to run, so we cannot
    hand the thread over to a pure Cocoa loop (gst_macos_main). Iterating
    both loops alternately satisfies the two requirements.
    """
    stopSignal = consumer.stopSignal
    if sys.platform != 'darwin' or stopSignal is None:
        consumer.loop.run()
        return

    try:
        import objc
        objc.loadBundle('AppKit', {}, bundle_path='/System/Library/Frameworks/AppKit.framework')
        NSRunLoop = objc.lookUpClass('NSRunLoop')
        NSDate = objc.lookUpClass('NSDate')
        cocoa_run_loop = NSRunLoop.mainRunLoop()
    except Exception as e:
        logging.warning("Unable to use NSRunLoop (%s); falling back to plain GLib loop", e)
        consumer.loop.run()
        return

    context = consumer.loop.get_context()
    while not stopSignal.isSet():
        # run pending GLib sources (bus watch, timers) -> Python runs -> signals handled
        context.iteration(may_block=False)
        # service the Cocoa run loop on the main thread (needed by the GL video sink)
        cocoa_run_loop.runMode_beforeDate_('NSDefaultRunLoopMode',
                                            NSDate.dateWithTimeIntervalSinceNow_(0.01))



def setup_live_playAudio(pipe):
    autoaudiosink = Gst.ElementFactory.make("autoaudiosink", "auto_audio_sink")
    autoaudiosink.set_property("sync", False)
    pipe.add(autoaudiosink)
    pipe.get_by_name("queue_audio_convert").link(autoaudiosink)


def setup_video_pipeline(pipe):
    src = Gst.ElementFactory.make("appsrc", "my-video_src")
    src.set_property("is-live", True)
    queue1 = Gst.ElementFactory.make("queue", "queue_h264parse")
    h264parse = Gst.ElementFactory.make("h264parse", "h264_parse")
    avdecH264 = Gst.ElementFactory.make("vtdec", "vt_dec")

    queue2 = Gst.ElementFactory.make("queue", "queue_video_convert")
    videoconvert = Gst.ElementFactory.make("videoconvert", "video_convert")

    queue3 = Gst.ElementFactory.make("queue", "queue_av")
    sink = Gst.ElementFactory.make("autovideosink", "av_sink")
    sink.set_property("sync", False)

    pipe.add(src)
    pipe.add(queue1)
    pipe.add(h264parse)
    pipe.add(avdecH264)
    pipe.add(queue2)
    pipe.add(videoconvert)
    pipe.add(queue3)
    pipe.add(sink)


    src.link(queue1)
    queue1.link(h264parse)
    h264parse.link(avdecH264)
    avdecH264.link(queue2)
    queue2.link(videoconvert)
    videoconvert.link(queue3)
    queue3.link(sink)
    return src


def setup_audio_pipeline(pipe):
    src = Gst.ElementFactory.make("appsrc", "my-audio-src")
    src.set_property("is-live", True)

    queue1 = Gst.ElementFactory.make("queue", "queue_wav_parse")
    wavparse = Gst.ElementFactory.make("wavparse", "wav_parse")
    wavparse.set_property("ignore-length", True)

    queue2 = Gst.ElementFactory.make("queue", "queue_audio_convert")
    audioconvert = Gst.ElementFactory.make("audioconvert", "audio_convert")

    pipe.add(src)
    pipe.add(queue1)
    pipe.add(wavparse)
    pipe.add(queue2)
    pipe.add(audioconvert)

    src.link(queue1)
    queue1.link(wavparse)
    wavparse.link(audioconvert)
    audioconvert.link(queue2)
    return src


def run_main_loop(pipeline,stopSignal):
    def bus_call(bus, message, loop):
        if stopSignal.isSet():
            loop.quit()
        t = message.type
        Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "test")
        if t == Gst.MessageType.EOS:
            logging.info("End-of-stream")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.error(f" {err}: {debug}")
            stopSignal.set()
            sleep(2)
            loop.quit()
        return True
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)
    return loop



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
        self.firstVideoSample = True
        self.videoSampleCount = 0
        self.audioSampleCount = 0
        if loop is not None:
            GLib.timeout_add_seconds(5, self._log_stream_stats)

    def _log_stream_stats(self):
        logging.info("stream stats: %d video samples, %d audio samples",
                     self.videoSampleCount, self.audioSampleCount)
        return True

    @classmethod
    def new(cls, stopSignal):
        ensure_macos_nsapplication()
        Gst.init([])
        logging.info("Starting Gstreamer..")

        # fix Gst plugin path issue in brew:
        # https://gstreamer.freedesktop.org/documentation/gstreamer/gstregistry.html?gi-language=python#GstRegistry
        # default locations are: $XDG_DATA_HOME/gstreamer-$GST_API_VERSION/plugins/ and $prefix/libs
        # brew gstream installation $prefix=/usr/local/Cellar/gstreamer/1.20.3/lib
        # and installed plugins in /usr/local/lib/gstreamer-1.0
        registry = Gst.Registry.get()
        if not registry.find_plugin('app'):
            logging.warning("Gstreamer plugin not loaded... scan for %s", GST_PLUGIN_PATH)
            registry.scan_path(GST_PLUGIN_PATH)

        pipe = Gst.Pipeline.new("QT_Hack_Pipeline")
        videoAppSrc = setup_video_pipeline(pipe)
        audioAppSrc = setup_audio_pipeline(pipe)
        setup_live_playAudio(pipe)
        pipe.set_state(Gst.State.PLAYING)
        loop = run_main_loop(pipe,stopSignal)
        if sys.platform == 'darwin':
            # the video window is created lazily on first frame; keep focusing until it shows up
            GLib.timeout_add_seconds(1, focus_macos_video_window)
        # _thread.start_new_thread(run_main_loop, (pipe,))
        logging.info("Gstreamer is running!")
        return cls(videoAppSrc, audioAppSrc, True, loop, pipe, stopSignal)

    def consume(self, data: CMSampleBuffer):
        if data.MediaType == DescriptorConst.MediaTypeSound:
            self.audioSampleCount += 1
            if self.firstAudioSample:
                self.firstAudioSample = False
                self.send_wav_header()
            return self.send_audio_sample(data)

        self.videoSampleCount += 1

        if data.OutputPresentationTimestamp.CMTimeValue > 17446044073700192000:
            data.OutputPresentationTimestamp.CMTimeValue = 0

        if self.firstVideoSample:
            self.firstVideoSample = False
            logging.info("first video sample received")

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
