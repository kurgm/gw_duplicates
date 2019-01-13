#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import unicode_literals

import codecs
import collections
import functools
import itertools
import json
import logging
import os
import re

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

try:
    cmp
except NameError:
    def cmp(a, b):
        return (a > b) - (a < b)


logging.basicConfig(level=logging.DEBUG)


def memoize_to(attr_name):
    def _memoize_to(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            try:
                return getattr(self, attr_name)
            except AttributeError:
                pass
            result = f(self, *args, **kwargs)
            setattr(self, attr_name, result)
            return result

        return wrapper

    return _memoize_to


def print_arg0_on_error(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            logging.error("An error occurred in %s(%r, ...)",
                          f.__name__, args[0])
            raise

    return wrapper


class CircularCallError(ValueError):
    pass


def check_circular_call_arg0(f):
    callstack = []

    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        if self in callstack:
            raise CircularCallError(
                "circularly called in '{0}'".format(self))
        callstack.append(self)
        try:
            return f(self, *args, **kwargs)
        finally:
            callstack.pop()

    return wrapper


def coord_mapper(bp0, bp1):
    scale = (bp1 - bp0) / 200.0
    return lambda p: bp0 + p * scale


def stretch(dp, sp, p, pmin=12.0, pmax=188.0):
    if p < sp + 100.0:
        p1 = pmin
        p3 = pmin
        p2 = sp + 100.0
        p4 = dp + 100.0
    else:
        p1 = sp + 100.0
        p3 = dp + 100.0
        p2 = pmax
        p4 = pmax
    return ((p - p1) / (p2 - p1)) * (p4 - p3) + p3


def stretch_mapper(dp, sp, coords=[]):
    if coords:
        pmin = min(coords)
        pmax = max(coords)
    else:
        pmin = 12.0
        pmax = 188.0
    return lambda p: stretch(dp, sp, p, pmin, pmax)


def compose(f, g):
    return lambda *args: f(g(*args))


def dist_from_line(x0, y0, x1, y1, x, y):
    if abs(y0 - y1) > abs(x0 - x1):
        return abs(x0 + (x1 - x0) * (y - y0) / (y1 - y0) - x)
    return abs(y0 + (y1 - y0) * (x - x0) / (x1 - x0) - y)


def get_kaku_info(line_data):
    strokeType = line_data[0]
    sttType = int(line_data[1])
    endType = int(line_data[2])
    if strokeType == "1":
        x0, y0, x1, y1 = [float(x) for x in line_data[3:7]]
        if (sttType == endType == 32 and y0 > y1 and y0 - y1 >= x1 - x0) or \
                (y0 == y1 and x0 > x1):
            x0, y0, x1, y1 = x1, y1, x0, y0
        return 1, (sttType if sttType != 2 else 0, endType), (x0, y0, x1, y1)
    if strokeType == "2":
        x0, y0, x1, y1, x2, y2 = [float(x) for x in line_data[3:9]]
        if sttType == 32 and endType == 0 and \
                ((y0 == y2 and x0 > x2) or y0 > y2):
            x0, y0, x2, y2 = x2, y2, x0, y0
        if endType == 0 and sttType in (0, 12, 22, 32) and \
                0 != abs(y0 - y2) >= x2 - x0 and \
                dist_from_line(x0, y0, x2, y2, x1, y1) <= 5.0:
            return 1, (sttType, 32), (x0, y0, x2, y2)
        return 2, (sttType, endType), (x0, y0, x1, y1, x2, y2)
    if strokeType in ("6", "7"):
        x0, y0, x1, y1, x2, y2, x3, y3 = [float(x) for x in line_data[3:11]]
        if sttType == 32 and endType == 0 and \
                ((y0 == y3 and x0 > x3) or y0 > y3):
            x0, y0, x1, y1, x2, y2, x3, y3 = x3, y3, x2, y2, x1, y1, x0, y0
        if endType == 0 and sttType in (0, 12, 22, 32) and \
                0 != abs(y0 - y3) >= x3 - x0 and \
                dist_from_line(x0, y0, x3, y3, x1, y1) <= 5.0 and \
                dist_from_line(x0, y0, x3, y3, x2, y2) <= 5.0:
            return 1, (sttType, 32), (x0, y0, x3, y3)
        return 2, (sttType, endType), (x0, y0, x1, y1, x2, y2, x3, y3)
    if strokeType in ("3", "4"):
        x0, y0, x1, y1, x2, y2 = [float(x) for x in line_data[3:9]]
        return 3, (sttType, endType), (x0, y0, x1, y1, x2, y2)

    if strokeType == "0" and sttType in (97, 98, 99):
        x0, y0, x1, y1 = [float(x) for x in line_data[3:7]]
        return 0, (sttType, endType), (x0, y0, x1, y1)

    return None


class Glyph(object):

    def __init__(self, name, rel, data):
        self.name = name
        self.rel = rel if rel != "u3013" else None
        self.data = data.split("$")

    def __repr__(self):
        return "Glyph({0.name!r}, {0.rel!r}, {0.data!r})".format(self)

    @memoize_to("buhin")
    @print_arg0_on_error
    @check_circular_call_arg0
    def getBuhin(self, dump):
        buhin = []
        for row in self.data:
            splitrow = row.split(":")
            if splitrow[0] == "0" and splitrow[1] not in ("97", "98", "99"):
                continue
            if splitrow[0] != "99":
                buhin = []
                break
            buhinname = splitrow[7].split("@")[0]
            b_buhins = dump[buhinname].getBuhin(dump)
            x0, y0, x1, y1 = [float(x) for x in splitrow[3:7]]
            if not b_buhins:
                buhin.append((x0, y0, x1, y1, buhinname))
                continue
            x_map = coord_mapper(x0, x1)
            y_map = coord_mapper(y0, y1)
            for b_x0, b_y0, b_x1, b_y1, b_name in b_buhins:
                buhin.append((
                    x_map(b_x0), y_map(b_y0), x_map(b_x1), y_map(b_y1),
                    b_name))
        buhin.sort(key=lambda x: x[4])
        return tuple(buhin)

    def getBuhinHash(self, dump):
        return tuple(b[4] for b in self.getBuhin(dump))

    @memoize_to("kaku")
    @print_arg0_on_error
    @check_circular_call_arg0
    def getKaku(self, dump):
        k = []
        for row in self.data:
            line_data = row.split(":")
            if line_data[0] != "99":
                kaku_info = get_kaku_info(line_data)
                if kaku_info is None:
                    continue
                kaku_type, shapes, points = kaku_info
                dir1 = cmp(points[0], points[2]) * 3 + \
                    cmp(points[1], points[3])
                dir2 = cmp(points[-4], points[-2]) * 3 + \
                    cmp(points[-3], points[-1])
                dirs = (dir1,) if len(points) == 4 else (dir1, dir2)
                kaku_sig = (kaku_type, dirs + shapes) + points
                k.append(kaku_sig)
                continue

            buhinname = line_data[7].split("@")[0]
            b_kakus = dump[buhinname].getKaku(dump)
            x0, y0, x1, y1 = [float(x) for x in line_data[3:7]]
            dpx = float(line_data[1])
            dpy = float(line_data[2])
            if len(line_data) < 9:
                spx = spy = 0.0
            else:
                spx = float(line_data[9])
                spy = float(line_data[10])
            x_map = coord_mapper(x0, x1)
            y_map = coord_mapper(y0, y1)
            if not dpx == dpy == 0.0:
                if dpx > 100.0:
                    dpx -= 200.0  # 任意点モード
                else:
                    spx = spy = 0.0  # 中心点モード
                stretch_x = stretch_mapper(
                    dpx, spx,
                    [x for b_kaku in b_kakus for x in b_kaku[2::2]])
                stretch_y = stretch_mapper(
                    dpy, spy,
                    [y for b_kaku in b_kakus for y in b_kaku[3::2]])
                x_map = compose(x_map, stretch_x)
                y_map = compose(y_map, stretch_y)
            for b_kaku in b_kakus:
                points = list(b_kaku[2:])
                points[0::2] = [x_map(x) for x in points[0::2]]
                points[1::2] = [y_map(y) for y in points[1::2]]
                k.append(b_kaku[0:2] + tuple(points))
        k.sort()
        return tuple(k)

    def getKakuHash(self, dump):
        return tuple(k[0:2] for k in self.getKaku(dump))

    def isAlias(self):
        return len(self.data) == 1 and \
            self.data[0].startswith("99:0:0:0:0:200:200:")

    xorMaskType = 0


def getDump():
    glyphlist = []
    dump = {}
    DUMP_PATH = "dump_newest_only.txt"
    with codecs.open(DUMP_PATH, "r", encoding="utf-8") as dumpfile:
        dumpfile.readline()  # header
        dumpfile.readline()  # ------
        timestamp = os.path.getmtime(DUMP_PATH)

        for line in dumpfile:
            split_line = line[:-1].split("|")
            if len(split_line) != 3:
                continue
            split_line = [x.strip() for x in split_line]
            glyph = Glyph(*split_line)
            glyphlist.append(glyph)
            dump[split_line[0]] = glyph
    return glyphlist, dump, timestamp


def setXorMaskType(dump):
    neg_url = "http://glyphwiki.org/wiki/Group:NegativeCharacters?action=edit"
    neg_data = urlopen(neg_url, timeout=60).read().decode("utf-8")

    neg_src = re.split(r"</?textarea(?: [^>]*)?>", neg_data)[1]
    neg_masktype = 0
    for m in re.finditer(
            r"\[\[(?:[^]]+\s)?([0-9a-z_-]+)(?:@\d+)?\]\]|^\*([^\*].*)$",
            neg_src, re.M):
        gn = m.group(1)
        if gn:
            if gn in dump:
                dump[gn].xorMaskType = neg_masktype
        else:
            neg_masktype += 1


henka_re = re.compile(
    r"-(?:[gtv]v?|[hmi]|k[pv]?|us?|j[asv]?)?(\d{2})(?:-(?:var|itaiji)-\d{3})?$"
)


def main():
    glyphlist, dump, timestamp = getDump()
    setXorMaskType(dump)

    glyphsByBuhin = collections.defaultdict(list)
    glyphsByKaku = collections.defaultdict(list)

    for glyph in glyphlist:
        if "_" in glyph.name or glyph.isAlias():
            continue
        try:
            bh = glyph.getBuhinHash(dump)
            if bh:
                glyphsByBuhin[bh].append(glyph)
            kh = glyph.getKakuHash(dump)
            if kh:
                glyphsByKaku[kh].append(glyph)
        except Exception:
            logging.exception('Error in "%s"', glyph.name)

    result = {"buhin": [], "kaku": [], "timestamp": timestamp}

    for glyphs in glyphsByBuhin.values():
        for g1, g2 in itertools.combinations(glyphs, 2):
            if g1.xorMaskType != g2.xorMaskType:
                continue
            b1 = g1.getBuhin(dump)
            b2 = g2.getBuhin(dump)
            for (B1, B2) in zip(b1, b2):
                if cmp(B1[0], B1[2]) != cmp(B2[0], B2[2]):
                    break
                if cmp(B1[1], B1[3]) != cmp(B2[1], B2[3]):
                    break
                diflim = [15.0, 15.0, 15.0, 15.0]
                m = henka_re.search(B1[4])
                if m:
                    suffix = m.group(1)
                    if suffix == "01":
                        diflim[2] = 40.0
                    elif suffix == "02":
                        diflim[0] = 40.0
                    elif suffix == "03":
                        diflim[3] = 40.0
                    elif suffix in ("04", "14", "24"):
                        diflim[1] = 40.0
                    elif suffix == "08":
                        diflim[1] = 25.0
                        diflim[3] = 25.0
                    elif suffix == "09":
                        diflim[0] = 25.0
                        diflim[2] = 25.0
                if all(abs(p1 - p2) <= lim
                       for (p1, p2, lim) in zip(B1[0:4], B2[0:4], diflim)):
                    continue
                if abs((B1[0] + B1[2]) - (B2[0] + B2[2])) <= 20.0 and \
                        abs((B1[1] + B1[3]) - (B2[1] + B2[3])) <= 20.0:
                    continue
                break
            else:
                result["buhin"].append((g1.name, g2.name, g1.rel, g2.rel))

    for glyphs in glyphsByKaku.values():
        for g1, g2 in itertools.combinations(glyphs, 2):
            if g1.xorMaskType != g2.xorMaskType:
                continue
            k1 = g1.getKaku(dump)
            k2 = g2.getKaku(dump)
            for (K1, K2) in zip(k1, k2):
                if all(abs(p1 - p2) <= 20.0
                       for (p1, p2) in zip(K1[2:4] + K1[-2:],
                                           K2[2:4] + K2[-2:])):
                    continue
                break
            else:
                r = (g1.name, g2.name, g1.rel, g2.rel)
                if r not in result["buhin"]:
                    result["kaku"].append(r)

    json.dump(result, open("duplicates.json", "w"), separators=(",", ":"))


if __name__ == '__main__':
    main()
