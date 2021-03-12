# iOS Frameworks
# https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.8.sdk/System/Library/Frameworks/CoreMedia.framework/Versions/A/Headers/CMTime.h

import enum
import struct
from _ctypes import Structure
from ctypes import c_uint32, c_uint64

NanoSecondScale = 1000000000


class CMTimeConst(enum.IntEnum):
    KCMTimeFlagsValid = 0x0
    KCMTimeFlagsHasBeenRounded = 0x1
    KCMTimeFlagsPositiveInfinity = 0x2
    KCMTimeFlagsNegativeInfinity = 0x4
    KCMTimeFlagsIndefinite = 0x8
    KCMTimeFlagsImpliedValueFlagsMask = KCMTimeFlagsPositiveInfinity | KCMTimeFlagsNegativeInfinity | KCMTimeFlagsIndefinite
    CMTimeLengthInBytes = 24


class CMTime(Structure):
    _fields_ = [
        ('CMTimeValue', c_uint64),
        ('CMTimeScale', c_uint32),
        ('CMTimeFlags', c_uint32),
        ('CMTimeEpoch', c_uint64),
    ]

    def get_time_scale(self, newScaleToUse):
        scalingFactor = float(newScaleToUse.CMTimeScale) / float(self.CMTimeScale)
        return float(self.CMTimeValue) * scalingFactor

    def seconds(self):
        if self.CMTimeValue == 0:
            return 0
        return int(self.CMTimeValue / self.CMTimeScale)

    def __str__(self):
        return f"CMTime:{self.CMTimeValue}/{self.CMTimeScale}, flags:{self.CMTimeFlags}, epoch:{self.CMTimeEpoch}"
