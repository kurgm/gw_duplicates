#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import json
import logging
import os
import re
import urllib2

logging.basicConfig(level=logging.DEBUG)

buhin_stack = []


def stretch(dp, sp, p, min=12.0, max=188.0):
    if p < sp + 100.0:
        p1 = min
        p3 = min
        p2 = sp + 100.0
        p4 = dp + 100.0
    else:
        p1 = sp + 100.0
        p3 = dp + 100.0
        p2 = max
        p4 = max
    return ((p - p1) / (p2 - p1)) * (p4 - p3) + p3


class Glyph(object):

    def __init__(self, name, rel, data):
        self.name = name
        self.rel = rel if rel != "u3013" else None
        self.data = data.split("$")
        self.buhin = None
        self.kaku = None

    def getBuhin(self, dump):
        if self.buhin is not None:
            return self.buhin
        buhin = []
        for row in self.data:
            if row[0:2] == "0:":
                continue
            if row[0:2] != "99":
                break
            splitrow = row.split(":")
            buhinname = splitrow[7].split("@")[0]
            buhinglyph = dump.get(buhinname)
            if not buhinglyph or self is buhinglyph or buhinglyph in buhin_stack:
                buhin = []
                logging.error(
                    "'{}' was not found or has a quotation loop".format(buhinname))
                break
            buhin_stack.append(buhinglyph)
            b_buhins = buhinglyph.getBuhin(dump)
            buhin_stack.pop()
            buhinx0, buhiny0, buhinx1, buhiny1 = [
                float(x) for x in splitrow[3:7]]
            if b_buhins:
                scale_x = (buhinx1 - buhinx0) / 200.0
                scale_y = (buhiny1 - buhiny0) / 200.0
                for b_buhinx0, b_buhiny0, b_buhinx1, b_buhiny1, b_buhinname in b_buhins:
                    buhin.append((
                        buhinx0 + b_buhinx0 * scale_x,
                        buhiny0 + b_buhiny0 * scale_y,
                        buhinx0 + b_buhinx1 * scale_x,
                        buhiny0 + b_buhiny1 * scale_y,
                        b_buhinname
                    ))
            else:
                buhin.append((buhinx0, buhiny0, buhinx1, buhiny1, buhinname))
        buhin.sort(key=lambda x: x[4])
        self.buhin = tuple(buhin)
        return self.buhin

    def getBuhinHash(self, dump):
        return tuple(b[4] for b in self.getBuhin(dump))

    def getKaku(self, dump):
        if self.kaku is not None:
            return self.kaku
        k = []
        for row in self.data:
            r = row.split(":")
            strokeType = r[0]
            if strokeType == "99":
                buhinname = r[7].split("@")[0]
                buhinglyph = dump.get(buhinname)
                if not buhinglyph or self is buhinglyph or buhinglyph in buhin_stack:
                    k = []
                    logging.error(
                        "'{}' was not found or has a quotation loop".format(buhinname))
                    break
                buhin_stack.append(buhinglyph)
                b_kakus = buhinglyph.getKaku(dump)
                buhin_stack.pop()
                buhinx0, buhiny0, buhinx1, buhiny1 = [float(x) for x in r[3:7]]
                dpx = float(r[1])
                dpy = float(r[2])
                if len(r) < 9:
                    spx = spy = 0.0
                else:
                    spx = float(r[9])
                    spy = float(r[10])
                isStretched = False
                if not (dpx == dpy == 0.0):
                    isStretched = True
                    if dpx > 100.0:
                        dpx -= 200.0  # 任意点モード
                    else:
                        spx = spy = 0.0  # 中心点モード
                scale_x = (buhinx1 - buhinx0) / 200.0
                scale_y = (buhiny1 - buhiny0) / 200.0
                for b_kaku in b_kakus:
                    points = list(b_kaku[2:])
                    if isStretched:
                        points[0::2] = [stretch(dpx, spx, x)
                                        for x in points[0::2]]
                        points[1::2] = [stretch(dpy, spy, x)
                                        for y in points[1::2]]
                    points[0::2] = [buhinx0 + x * scale_x
                                    for x in points[0::2]]
                    points[1::2] = [buhiny0 + x * scale_y
                                    for y in points[1::2]]
                    k.append(b_kaku[0:2] + tuple(points))
                continue
            sttType = int(r[1])
            endType = int(r[2])
            if strokeType == "1":
                x0, y0, x1, y1 = [float(x) for x in r[3:7]]
                if (sttType == endType == 32 and y0 > y1 and y0 - y1 >= x1 - x0) or \
                        (y0 == y1 and x0 > x1):
                    x0, y0, x1, y1 = x1, y1, x0, y0
                dir1 = cmp(x0, x1) * 2 + cmp(y0, y1) + 3
                k.append((
                    1,
                    dir1 + 7 * (sttType // 10) +
                    28 * (endType * 2 if 0 < endType < 10 else endType // 10),
                    x0, y0, x1, y1
                ))
            elif strokeType == "2":
                x0, y0, x1, y1, x2, y2 = [float(x) for x in r[3:9]]
                if sttType == 32 and endType == 0 and ((y0 == y2 and x0 > x2) or y0 > y2):
                    x0, y0, x2, y2 = x2, y2, x0, y0
                if endType == 0 and sttType in (0, 12, 22, 32) and 0 != abs(y0 - y2) >= x2 - x0 and \
                   abs(x0 + (x2 - x0) * (y1 - y0) / (y2 - y0) - x1
                       if abs(y0 - y2) > abs(x0 - x2) else
                       y0 + (y2 - y0) * (x1 - x0) / (x2 - x0) - y1
                       ) <= 5.0:
                    dir1 = cmp(x0, x2) * 2 + cmp(y0, y2) + 3
                    k.append((
                        1,
                        dir1 + 7 * (sttType // 10) + 84,
                        x0, y0, x2, y2
                    ))
                    continue
                dir1 = cmp(x0, x1) * 2 + cmp(y0, y1) + 3
                dir2 = cmp(x1, x2) * 2 + cmp(y1, y2) + 3
                k.append((
                    2,
                    dir1 + 7 * dir2 + 49 *
                        (sttType // 5) + 392 * (endType // 5),
                    x0, y0, x1, y1, x2, y2
                ))
            elif strokeType == "6" or strokeType == "7":
                x0, y0, x1, y1, x2, y2, x3, y3 = [float(x) for x in r[3:11]]
                if sttType == 32 and endType == 0 and ((y0 == y3 and x0 > x3) or y0 > y3):
                    x0, y0, x1, y1, x2, y2, x3, y3 = x3, y3, x2, y2, x1, y1, x0, y0
                if endType == 0 and sttType in (0, 12, 22, 32) and 0 != abs(y0 - y3) >= x3 - x0 and max(
                        (
                            abs(x0 + (x3 - x0) * (y1 - y0) / (y3 - y0) - x1),
                            abs(x0 + (x3 - x0) * (y2 - y0) / (y3 - y0) - x2)
                        ) if abs(y0 - y3) > abs(x0 - x3) else (
                            abs(y0 + (y3 - y0) * (x1 - x0) / (x3 - x0) - y1),
                            abs(y0 + (y3 - y0) * (x2 - x0) / (x3 - x0) - y2)
                        )
                ) <= 5.0:
                    dir1 = cmp(x0, x3) * 2 + cmp(y0, y3) + 3
                    k.append((
                        1,
                        dir1 + 7 * (sttType // 10) + 84,
                        x0, y0, x3, y3
                    ))
                    continue
                dir1 = cmp(x0, x1) * 2 + cmp(y0, y1) + 3
                dir2 = cmp(x2, x3) * 2 + cmp(y2, y3) + 3
                k.append((
                    2,
                    dir1 + 7 * dir2 + 49 *
                        (sttType // 5) + 392 * (endType // 5),
                    x0, y0, x1, y1, x2, y2, x3, y3
                ))
            elif strokeType == "3" or strokeType == "4":
                x0, y0, x1, y1, x2, y2 = [float(x) for x in r[3:9]]
                k.append((
                    3,
                    (sttType // 10) + 4 * (endType // 5),
                    x0, y0, x1, y1, x2, y2
                ))
        k.sort()
        self.kaku = tuple(k)
        return self.kaku

    def getKakuHash(self, dump):
        return tuple(k[0:2] for k in self.getKaku(dump))

    def isAlias(self):
        return len(self.data) == 1 and self.data[0][:19] == "99:0:0:0:0:200:200:"

    xorMaskType = 0


def getDump():
    glyphlist = []
    dump = {}
    DUMP_PATH = "dump_newest_only.txt"
    with open(DUMP_PATH, "r") as dumpfile:
        dumpfile.readline()  # header
        dumpfile.readline()  # ------
        timestamp = os.path.getmtime(DUMP_PATH)

        for line in dumpfile:
            l = line[:-1].split("|")
            if len(l) != 3:
                continue
            l = [x.strip() for x in l]
            glyph = Glyph(*l)
            glyphlist.append(glyph)
            dump[l[0]] = glyph
    return glyphlist, dump, timestamp


def setXorMaskType(dump):
    neg_url = "http://glyphwiki.org/wiki/Group:NegativeCharacters?action=edit"
    neg_data = urllib2.urlopen(neg_url, timeout=60).read()

    neg_src = re.split(r"</?textarea(?: [^>]*)?>", neg_data)[1]
    neg_masktype = 0
    for m in re.finditer(r"\[\[(?:[^]]+\s)?([0-9a-z_-]+)(?:@\d+)?\]\]|^\*([^\*].*)$", neg_src, re.M):
        gn = m.group(1)
        if gn:
            if gn in dump:
                dump[gn].xorMaskType = neg_masktype
        else:
            neg_masktype += 1


def main():
    glyphlist, dump, timestamp = getDump()
    setXorMaskType(dump)

    glyphsByBuhin = {}
    glyphsByKaku = {}

    for glyph in glyphlist:
        if "_" in glyph.name or glyph.isAlias():
            continue
        try:
            bh = glyph.getBuhinHash(dump)
            if bh:
                glyphsByBuhin.setdefault(bh, []).append(glyph)
            kh = glyph.getKakuHash(dump)
            if kh:
                glyphsByKaku.setdefault(kh, []).append(glyph)
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
                suffix = B1[4][-3:]
                if suffix[0] != "-":
                    pass
                elif suffix == "-01":
                    diflim[2] = 40.0
                elif suffix == "-02":
                    diflim[0] = 40.0
                elif suffix == "-03":
                    diflim[3] = 40.0
                elif suffix == "-04" or suffix == "-14":
                    diflim[1] = 40.0
                elif suffix == "-08":
                    diflim[1] = 25.0
                    diflim[3] = 25.0
                elif suffix == "-09":
                    diflim[0] = 25.0
                    diflim[2] = 25.0
                if all(abs(p1 - p2) <= lim for (p1, p2, lim) in zip(B1[0:4], B2[0:4], diflim)):
                    continue
                if abs((B1[0] + B1[2]) - (B2[0] + B2[2])) <= 20.0 and abs((B1[1] + B1[3]) - (B2[1] + B2[3])) <= 20.0:
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
                if all(abs(p1 - p2) <= 20.0 for (p1, p2) in zip(K1[2:4] + K1[-2:], K2[2:4] + K2[-2:])):
                    continue
                break
            else:
                r = (g1.name, g2.name, g1.rel, g2.rel)
                if r not in result["buhin"]:
                    result["kaku"].append(r)

    json.dump(result, open("duplicates.json", "w"), separators=(",", ":"))


if __name__ == '__main__':
    main()
