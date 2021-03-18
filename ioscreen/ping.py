import enum
import struct


class PingConst(enum.IntEnum):
    PingPacketMagic = 0x70696E67
    PingLength = 16
    PingHeader = 0x0000000100000000


def new_ping_packet_bytes():
    """default Ping ioscreen
    :return:
    """
    packet_bytes = b''
    packet_bytes += struct.pack('<I', PingConst.PingLength)
    packet_bytes += struct.pack('<I', PingConst.PingPacketMagic)
    packet_bytes += struct.pack('<Q', PingConst.PingHeader)
    return packet_bytes