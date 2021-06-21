from ioscreen.coremedia.CMFormatDescription import FormatDescriptor, DescriptorConst

ppsHex = "27640033AC5680470133E69E6E04040404"
spsHex = "28EE3CB0"


def test_format_descriptor():
    with open('./fixtures/formatdescriptor.bin', "rb") as f:
        data = f.read()

    fdsc = FormatDescriptor.from_bytes(data)
    assert DescriptorConst.MediaTypeVideo == fdsc.MediaType
    assert bytes.fromhex(ppsHex) == fdsc.PPS
    assert bytes.fromhex(spsHex) == fdsc.SPS
    print(fdsc)


def test_format_descriptor_audio():
    with open('./fixtures/formatdescriptor-audio.bin', "rb") as f:
        data = f.read()
    fdsc = FormatDescriptor.from_bytes(data)
    assert DescriptorConst.MediaTypeSound == fdsc.MediaType
    print(fdsc)



