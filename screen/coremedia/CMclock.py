import time

from .CMTime import CMTimeConst, CMTime

NanoSecondScale = 1000000000


class CMClock:
    def __init__(self, id, timeScale, startTime, factor):
        self.id: int = id
        self.timeScale = timeScale
        self.startTime = startTime
        self.factor = factor

    def calcValue(self, val):
        if NanoSecondScale == self.timeScale:
            return int(val)
        return int(self.factor * val)

    def getTime(self):
        return CMTime(
            CMTimeValue=self.calcValue((time.time_ns()-self.startTime)),
            CMTimeScale=self.timeScale,
            CMTimeFlags=CMTimeConst.KCMTimeFlagsHasBeenRounded,
            CMTimeEpoch=0)

    @classmethod
    def new(cls, id):
        return cls(id, NanoSecondScale, time.time_ns(), 1)

    @classmethod
    def new_scale(cls, id, timeScale):
        factor = float(timeScale) / float(NanoSecondScale)
        return cls(id, timeScale, time.time_ns(), factor)


def calculate_skew(startTimeClock1, endTimeClock1, startTimeClock2, endTimeClock2):
    timeDiffClock1 = endTimeClock1.CMTimeValue - startTimeClock1.CMTimeValue
    timeDiffClock2 = endTimeClock2.CMTimeValue - startTimeClock2.CMTimeValue
    diffTime = CMTime(CMTimeValue=timeDiffClock1, CMTimeScale=startTimeClock1.CMTimeScale)
    scaledDiff = diffTime.get_time_scale(startTimeClock2)
    return float(startTimeClock2.CMTimeScale) * scaledDiff / float(timeDiffClock2)
