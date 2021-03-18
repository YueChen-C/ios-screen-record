import logging
from time import sleep

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GLib


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
