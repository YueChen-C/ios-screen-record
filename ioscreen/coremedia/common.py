import struct


class NSNumber:
    def __init__(self, typeSpecifier, value):
        """
        :param typeSpecifier: 3 uint32, 4: uint64, 6:float64
        :param value:
        """
        self.typeSpecifier = typeSpecifier
        self.value = value

    @classmethod
    def from_bytes(self, buf):
        typeSpecifier = buf[0]
        if typeSpecifier == 3:
            value = struct.unpack('<I', buf[1:])[0]
        elif typeSpecifier == 4:
            value = struct.unpack('<Q', buf[1:])[0]
        elif typeSpecifier == 5:
            value = struct.unpack('<I', buf[1:])[0]
        elif typeSpecifier == 6:
            value = struct.unpack('<d', buf[1:])[0]
        else:
            raise Exception('not find value')
        return self(typeSpecifier, value)

    def to_bytes(self):
        buf = b''
        if self.typeSpecifier == 3:
            buf += b'\x03'
            buf += struct.pack('<I', self.value)
        elif self.typeSpecifier == 4:
            buf += b'\x04'
            buf += struct.pack('<Q', self.value)
        elif self.typeSpecifier == 6:
            buf += b'\x06'
            buf += struct.pack('<d', self.value)
        return buf

    def __str__(self):
        return f'NSNumber >>> typeSpecifier:{self.typeSpecifier},value:{self.value}'
