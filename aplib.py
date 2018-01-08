# -*- coding: utf-8 -*-
"""Module for decompressing aPLib compressed data.

Adapted from the original C source code from http://ibsensoftware.com/files/aPLib-1.1.1.zip

Approximately ~20 times faster than the other Python implementations.
"""
from io import BytesIO

__all__ = ['decompress']
__version__ = '0.2'
__author__ = 'Sandor Nemes'


class APDSTATE(object):
    """internal data structure"""

    def __init__(self, source):
        self.source = BytesIO(source)
        self.destination = bytearray()
        self.tag = 0
        self.bitcount = 0


def ap_getbit(ud):
    # check if tag is empty
    ud.bitcount -= 1
    if ud.bitcount < 0:
        # load next tag
        ud.tag = ord(ud.source.read(1))
        ud.bitcount = 7

    # shift bit out of tag
    bit = ud.tag >> 7 & 0x01
    ud.tag <<= 1

    return bit


def ap_getgamma(ud):
    result = 1

    # input gamma2-encoded bits
    while True:
        result = (result << 1) + ap_getbit(ud)
        if not ap_getbit(ud):
            break

    return result


def ap_depack(source):
    ud = APDSTATE(source)

    r0 = -1
    lwm = 0
    done = False

    # first byte verbatim
    ud.destination += ud.source.read(1)

    # main decompression loop
    while not done:
        if ap_getbit(ud):
            if ap_getbit(ud):
                if ap_getbit(ud):
                    offs = 0

                    for _ in xrange(4):
                        offs = (offs << 1) + ap_getbit(ud)

                    if offs:
                        ud.destination.append(ud.destination[-offs])
                    else:
                        ud.destination.append(0x00)

                    lwm = 0
                else:
                    offs = ord(ud.source.read(1))

                    length = 2 + (offs & 0x0001)

                    offs >>= 1

                    if offs:
                        for _ in xrange(length):
                            ud.destination.append(ud.destination[-offs])
                    else:
                        done = True

                    r0 = offs
                    lwm = 1
            else:
                offs = ap_getgamma(ud)

                if lwm == 0 and offs == 2:
                    offs = r0

                    length = ap_getgamma(ud)

                    for _ in xrange(length):
                        ud.destination.append(ud.destination[-offs])
                else:
                    if lwm == 0:
                        offs -= 3
                    else:
                        offs -= 2

                    offs <<= 8
                    offs += ord(ud.source.read(1))

                    length = ap_getgamma(ud)

                    if offs >= 32000:
                        length += 1
                    if offs >= 1280:
                        length += 1
                    if offs < 128:
                        length += 2

                    for _ in xrange(length):
                        ud.destination.append(ud.destination[-offs])

                    r0 = offs

                lwm = 1
        else:
            ud.destination += ud.source.read(1)
            lwm = 0

    return ud.destination


def decompress(data):
    try:
        return str(ap_depack(data))
    except Exception:
        raise Exception('aPLib decompression error')


if __name__ == '__main__':
    # self-test
    data = 'T\x00he quick\xecb\x0erown\xcef\xaex\x80jumps\xed\xe4veur`t?lazy\xead\xfeg\xc0\x00'
    assert decompress(data) == 'The quick brown fox jumps over the lazy dog'
