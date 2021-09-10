import _thread
import argparse
import os

from ioscreen.util import *

def cmd_record_wav(args: argparse.Namespace):
    device = find_ios_device(args.udid)
    consumer = AVFileWriter(h264FilePath=args.h264File, wavFilePath=args.wavFile)
    stopSignal = threading.Event()
    register_signal(stopSignal)
    start_reading(consumer, device, stopSignal)


def cmd_record_udp(args: argparse.Namespace):
    device = find_ios_device(args.udid)
    consumer = SocketUDP()
    stopSignal = threading.Event()
    register_signal(stopSignal)
    start_reading(consumer, device, stopSignal)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')
    parser.add_argument("-u", "--udid", help="specify unique device identifier")

    udp_parser = subparsers.add_parser("udp",
                                       help="forward H264 data to UDP broadcast. You can use VLC to play the URL")
    udp_parser.set_defaults(func=cmd_record_udp)

    parser_foo = subparsers.add_parser('record', help="will start video&audio recording. Video will be saved in a raw "
                                                      "h264 file playable by VLC")
    parser_foo.add_argument('-h264File', type=str, required=True,
                            help='lease specify a valid path like /home/test/out.h264')
    parser_foo.add_argument('-wavFile', type=str, required=True,
                            help='lease specify a valid path like /home/test/out.wav')
    parser_foo.set_defaults(func=cmd_record_wav)
    args = parser.parse_args()
    if not args.subparser:
        parser.print_help()
        return
    args.func(args)


if __name__ == '__main__':
    main()
