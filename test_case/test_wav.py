import io
import os

from ioscreen.coremedia.wav import set_wav_header


def test_wav():
    expectedBytes = "524946461802000057415645666d7420100000000100020080bb000000ee02000400100064617461f401000044616e69656c"
    print(bytes.fromhex(expectedBytes))
    headerPlaceholder = b'\x00' * 44
    name = './test.wav'
    with open(name, 'wb+') as file:
        file.write(headerPlaceholder)
        file.write(b'Daniel')
        set_wav_header(500, file)
    with open(name, 'rb') as f:
        assert f.read() == bytes.fromhex(expectedBytes)
    os.remove(name)
