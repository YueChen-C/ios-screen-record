import struct

from ioscreen.coremedia.CMSampleBuffer import CMSampleBuffer
from ioscreen.coremedia.CMTime import CMTimeConst


def test_feed_data():
    with open('./fixtures/asyn-feed-ttas-only', "rb") as f:
        data = f.read()
    sbufPacket = CMSampleBuffer.from_bytesVideo(data[20:])
    assert False == sbufPacket.HasFormatDescription
    print(sbufPacket)


def test_CMSampleBuffer():
    with open('./fixtures/asyn-feed', "rb") as f:
        data = f.read()
    sbufPacket = CMSampleBuffer.from_bytesVideo(data[20:])
    assert True == sbufPacket.HasFormatDescription
    assert CMTimeConst.KCMTimeFlagsHasBeenRounded == sbufPacket.OutputPresentationTimestamp.CMTimeFlags
    assert 0x176a7 == sbufPacket.OutputPresentationTimestamp.seconds()
    assert 1 == len(sbufPacket.SampleTimingInfoArray)
    assert 0 == sbufPacket.SampleTimingInfoArray[0].Duration.seconds()
    assert 0x176a7 == sbufPacket.SampleTimingInfoArray[0].PresentationTimeStamp.seconds()
    assert 0 == sbufPacket.SampleTimingInfoArray[0].DecodeTimeStamp.seconds()
    assert 90750 == len(sbufPacket.SampleData)
    assert 1 == sbufPacket.NumSamples
    assert 1 == len(sbufPacket.SampleSizes)
    assert 90750 == sbufPacket.SampleSizes[0]
    assert 4 == len(sbufPacket.Attachments)
    assert 1 == len(sbufPacket.CreateIfNecessary)
    print(sbufPacket)


def test_CMSampleBufferNoFdsc():
    with open('./fixtures/asyn-feed-nofdsc', "rb") as f:
        data = f.read()
    sbufPacket = CMSampleBuffer.from_bytesVideo(data[16:])
    assert False == sbufPacket.HasFormatDescription
    assert CMTimeConst.KCMTimeFlagsHasBeenRounded == sbufPacket.OutputPresentationTimestamp.CMTimeFlags
    assert 0x44b82fa09 == sbufPacket.OutputPresentationTimestamp.seconds()
    assert 1 == len(sbufPacket.SampleTimingInfoArray)
    assert 0 == sbufPacket.SampleTimingInfoArray[0].Duration.seconds()
    assert 0x44b82fa09 == sbufPacket.SampleTimingInfoArray[0].PresentationTimeStamp.seconds()
    assert 0 == sbufPacket.SampleTimingInfoArray[0].DecodeTimeStamp.seconds()
    assert 56604 == len(sbufPacket.SampleData)
    assert 1 == sbufPacket.NumSamples
    assert 1 == len(sbufPacket.SampleSizes)
    assert 56604 == sbufPacket.SampleSizes[0]
    assert 4 == len(sbufPacket.Attachments)
    assert 2 == len(sbufPacket.CreateIfNecessary)

    print(sbufPacket)


def test_CMSampleBufferAudio():
    with open('./fixtures/asyn-eat', "rb") as f:
        data = f.read()

    sbufPacket = CMSampleBuffer.from_bytesAudio(data[16:])
    assert True == sbufPacket.HasFormatDescription
    assert 1024 == sbufPacket.NumSamples
    assert 1 == len(sbufPacket.SampleSizes)
    assert 4 == sbufPacket.SampleSizes[0]
    assert sbufPacket.NumSamples * sbufPacket.SampleSizes[0] == len(sbufPacket.SampleData)
    print(sbufPacket)


def test_CMSampleBufferAudioNoFdsc():
    with open('./fixtures/asyn-eat-nofdsc', "rb") as f:
        data = f.read()
    sbufPacket = CMSampleBuffer.from_bytesAudio(data[16:])
    assert False == sbufPacket.HasFormatDescription
    assert 1024 == sbufPacket.NumSamples
    assert 1 == len(sbufPacket.SampleSizes)
    assert 4 == sbufPacket.SampleSizes[0]
    assert sbufPacket.NumSamples * sbufPacket.SampleSizes[0] == len(sbufPacket.SampleData)
    print(sbufPacket)



