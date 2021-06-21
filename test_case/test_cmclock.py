from ioscreen.coremedia.CMclock import CMClock, NanoSecondScale


def test_clock_get_time():
    cm_clock = CMClock.new(5)
    assert NanoSecondScale == cm_clock.timeScale
    time1 = cm_clock.getTime()
    time2 = cm_clock.getTime()
    assert cm_clock.timeScale == time1.CMTimeScale
    assert time2.CMTimeValue > time1.CMTimeValue
    cm_clock = CMClock.new_scale(0, 1)
    assert 0 == cm_clock.getTime().CMTimeValue
