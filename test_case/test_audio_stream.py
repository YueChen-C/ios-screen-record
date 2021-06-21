from ioscreen.coremedia.AudioStream import AudioStreamBasicDescription


def test_audio_stream_serializer():
    with open('./fixtures/adsb-from-hpa-dict.bin', "rb") as f:
        data = f.read()

    adsb = AudioStreamBasicDescription.new()
    buf = adsb.to_bytes()
    assert data == buf
    parsedAdsb = AudioStreamBasicDescription.from_buffer_copy(buf)
    assert str(adsb) == str(parsedAdsb)
