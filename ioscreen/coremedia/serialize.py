"""
bytes 流序列化
"""
import enum
import struct

from .common import NSNumber


class DictConst(enum.IntEnum):
    KeyValuePairMagic = 0x6B657976  # keyv - vyek
    StringKey = 0x7374726B  # strk - krts
    IntKey = 0x6964786B  # idxk - kxdi
    BooleanValueMagic = 0x62756C76  # bulv - vlub
    DictionaryMagic = 0x64696374  # dict - tcid
    DataValueMagic = 0x64617476  # datv - vtad
    StringValueMagic = 0x73747276  # strv - vrts
    NumberValueMagic = 0x6E6D6276


def write_length_magic(length, magic):
    buf = b''
    buf += struct.pack('<I', length)
    buf += struct.pack('<I', magic)
    return buf


def serialize_key(key):
    buf = b''
    keyLength = len(key) + 8
    buf += write_length_magic(keyLength, DictConst.StringKey)
    buf += bytes(key, encoding='utf8')
    return buf, keyLength


def serialize_value(Value):
    buf = b''
    if isinstance(Value, bool):
        buf += write_length_magic(9, DictConst.BooleanValueMagic)
        boolValue = 0
        if Value:
            boolValue = 1
        buf += struct.pack('?', boolValue)
        return buf, 9
    elif isinstance(Value, NSNumber):
        numberBytes = Value.to_bytes()
        _length = len(numberBytes) + 8
        buf += write_length_magic(_length, DictConst.NumberValueMagic)
        buf += numberBytes
        return buf, _length
    elif isinstance(Value, str):
        _length = len(Value) + 8
        buf += write_length_magic(_length, DictConst.StringValueMagic)
        buf += bytes(Value, encoding='utf8')
        return buf, _length
    elif isinstance(Value, (bytes, bytearray)):
        _length = len(Value) + 8
        buf += write_length_magic(_length, DictConst.DataValueMagic)
        buf += bytes(Value)
        return buf, _length
    elif isinstance(Value, dict):
        dictValue = SerializeStringKeyDict(Value).to_bytes()
        buf += dictValue
        return buf, len(buf)


class SerializeStringKeyDict:
    def __init__(self, data):
        self.buf = bytes()
        self.data = data

    def to_bytes(self):
        index = 0
        for key, value in self.data.items():
            key_buf, keyLength = serialize_key(key)
            value_buf, valueLength = serialize_value(value)
            self.buf += write_length_magic(keyLength + valueLength + 8, DictConst.KeyValuePairMagic)
            self.buf += key_buf
            self.buf += value_buf
            index += 8 + valueLength + keyLength
        dictSizePlusHeaderAndLength = index + 4 + 4
        buf = write_length_magic(dictSizePlusHeaderAndLength, DictConst.DictionaryMagic) + self.buf
        return buf


def parse_length_magic(buf, exptectMagic):
    _length = struct.unpack('<I', buf[:4])[0]
    magic = struct.unpack('<I', buf[4:8])[0]
    if int(_length) > len(buf):
        raise Exception()
    if magic != exptectMagic:
        raise Exception()
    return int(_length), buf[8:]


def parse_int_dict(buf):
    key, remainingBytes = parse_int_key(buf)
    value = parse_value(remainingBytes)
    return {key: value}


def parse_int_key(buf):
    keyLength, _, = parse_length_magic(buf, DictConst.IntKey)
    key = struct.unpack('<H', buf[8:10])[0]
    return key, buf[keyLength:]


def parse_key(buf):
    keyLength, _ = parse_length_magic(buf, DictConst.StringKey)
    key = buf[8:keyLength].decode()
    return key, buf[keyLength:]


def parse_dict(buf):
    key, remainingBytes = parse_key(buf)
    value = parse_value(remainingBytes)
    return {key: value}


def parse_key_value_dict(data):
    keyValuePairLength, _, = parse_length_magic(data, DictConst.KeyValuePairMagic)
    keyValuePairData = data[8:keyValuePairLength]
    return parse_dict(keyValuePairData)


def parse_value(buf):
    from ioscreen.coremedia.CMFormatDescription import DescriptorConst, FormatDescriptor

    valueLength = struct.unpack('<I', buf[:4])[0]
    magic = struct.unpack('<I', buf[4:8])[0]
    if magic == DictConst.StringValueMagic:
        return buf[8:valueLength].decode()
    elif magic == DictConst.DataValueMagic:
        return buf[8:valueLength]
    elif magic == DictConst.BooleanValueMagic:
        return buf[8] == 1
    elif magic == DictConst.NumberValueMagic:
        return NSNumber.from_bytes(buf[8:])
    elif magic == DictConst.DictionaryMagic:
        try:
            _dict = new_string_dict_from_bytes(buf)
        except Exception:
            _dict = new_dictionary_from_bytes(buf, DictConst.DictionaryMagic)
        return _dict
    elif magic == DescriptorConst.FormatDescriptorMagic:
        _dict = FormatDescriptor.from_bytes(buf)
        return _dict


def parse_header(buffer, packet_magic, message_magic):
    magic = struct.unpack('<I', buffer[:4])[0]
    if magic != packet_magic:
        return False
    clockRef = struct.unpack('<Q', buffer[4:12])[0]
    messageType = struct.unpack('<I', buffer[12:16])[0]
    if messageType != message_magic:
        return False
    return buffer[16:], clockRef


def new_string_dict_from_bytes(buf):
    _, remainingBytes, = parse_length_magic(buf, DictConst.DictionaryMagic)
    _dict = {}
    while 0 != len(remainingBytes):
        keyValuePairLength, _, = parse_length_magic(remainingBytes, DictConst.KeyValuePairMagic)
        keyValuePair = remainingBytes[8:keyValuePairLength]
        parseDictEntry = parse_dict(keyValuePair)
        remainingBytes = remainingBytes[keyValuePairLength:]
        _dict.update(parseDictEntry)
    return _dict


def new_dictionary_from_bytes(buf, magic):
    _, remainingBytes, = parse_length_magic(buf, magic)
    _dict = {}
    while 0 != len(remainingBytes):
        keyValuePairLength, _, = parse_length_magic(remainingBytes, DictConst.KeyValuePairMagic)
        keyValuePair = remainingBytes[8:keyValuePairLength]
        intDictEntry = parse_int_dict(keyValuePair)
        _dict.update(intDictEntry)
        remainingBytes = remainingBytes[keyValuePairLength:]
    return _dict
