import logging

import gi
from gi.repository import Gst, GObject, GLib


def setup_live_playAudio(pipe):
    autoaudiosink = Gst.ElementFactory.make("autoaudiosink", "autoaudiosink_01")
    autoaudiosink.set_property("sync", False)
    pipe.add(autoaudiosink)
    pipe.get_by_name("queue2").link(autoaudiosink)


def setup_video_pipeline(pipe):
    src = Gst.ElementFactory.make("appsrc", "my-video_src")
    src.set_property("is-live", True)
    queue1 = Gst.ElementFactory.make("queue", "queue_11")
    h264parse = Gst.ElementFactory.make("h264parse", "h264parse_01")
    avdecH264 = Gst.ElementFactory.make("vtdec", "vtdec_01")

    queue2 = Gst.ElementFactory.make("queue", "queue_12")
    videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert_01")

    queue3 = Gst.ElementFactory.make("queue", "queue_13")
    sink = Gst.ElementFactory.make("autovideosink", "autovideosink_01")
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

    queue1 = Gst.ElementFactory.make("queue", "queue1")
    wavparse = Gst.ElementFactory.make("wavparse", "wavparse_01")
    wavparse.set_property("ignore-length", True)

    queue2 = Gst.ElementFactory.make("queue", "queue2")
    audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert_01")

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


def run_main_loop(pipeline):
    def bus_call(bus, message, loop):
        t = message.type
        Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "test")
        if t == Gst.MessageType.EOS:
            logging.info("End-of-stream\n")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.info("Error: %s: %s\n" % (err, debug))
            loop.quit()
        return True
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)
    return loop
