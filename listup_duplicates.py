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

    def getBuhin(self, dbn):
        if self.buhin is not None:
            return self.buhin
        b = []
        tb = ()
        for row in self.data:
            if row[0:2] == "0:":
                continue
            if row[0:2] != "99":
                break
            r = row.split(":")
            bn = r[7].split("@")[0]
            g = dbn.get(bn)
            if not g or self is g or g in buhin_stack:
                b = []
                logging.error(
                    "'{}' was not found or has a quotation loop".format(bn))
                break
            buhin_stack.append(g)
            area = [float(x) for x in r[3:7]]
            bbs = g.getBuhin(dbn)
            buhin_stack[-1:] = []
            if bbs:
                scale = [(area[2] - area[0]) / 200.0,
                         (area[3] - area[1]) / 200.0]
                for bb in bbs:
                    b.append((
                        area[0] + bb[0] * scale[0],
                        area[1] + bb[1] * scale[1],
                        area[0] + bb[2] * scale[0],
                        area[1] + bb[3] * scale[1],
                        bb[4]
                    ))
            else:
                b.append(tuple(area + [bn]))
        else:
            b.sort(key=lambda x: x[4])
            tb = tuple(b)
        self.buhin = tb
        return tb

    def getBuhinHash(self, dbn):
        if len(self.data) == 1 and self.data[0][0:19] == "99:0:0:0:0:200:200:":
            return ()
        if "_" in self.name:
            return ()
        return tuple(b[4] for b in self.getBuhin(dbn))

    def getKaku(self, dbn):
        if self.kaku is not None:
            return self.kaku
        k = []
        for row in self.data:
            r = row.split(":")
            if r[0] == "1":
                r = [float(x) for x in r]
                if (r[1] == r[2] == 32.0 and r[4] > r[6] and r[4] - r[6] > r[5] - r[3]) or (r[4] == r[6] and r[3] > r[5]):
                    r[3:7] = r[5:7] + r[3:5]
                dir1 = cmp(r[3], r[5]) * 2 + cmp(r[4], r[6]) + 3
                k.append((1, int(dir1 + 7 * (r[1] // 10) + 28 * (r[2] * 2 if 0.0 < r[
                         2] < 10.0 else r[2] // 10)), r[3], r[4], r[5], r[6]))
            elif r[0] == "2":
                r = [float(x) for x in r]
                if r[1] == 32.0 and r[2] == 0.0:
                    if (r[4] == r[8] and r[3] < r[7]) or r[4] > r[8]:
                        r[3:9] = r[7:9] + r[5:7] + r[3:5]
                if r[2] == 0.0 and r[1] in (0.0, 12.0, 22.0, 32.0) and 0 != abs(r[4] - r[8]) > r[7] - r[3] and \
                   abs(r[3] + (r[7] - r[3]) * (r[6] - r[4]) / (r[8] - r[4]) - r[5]
                       if abs(r[4] - r[8]) > abs(r[3] - r[7]) else
                       r[4] + (r[8] - r[4]) * (r[5] - r[3]) /
                       (r[7] - r[3]) - r[6]
                       ) <= 5.0:
                    dir1 = cmp(r[3], r[7]) * 2 + cmp(r[4], r[8]) + 3
                    k.append(
                        (1, int(dir1 + 7 * (r[1] // 10) + 84), r[3], r[4], r[7], r[8]))
                    continue
                dir1 = cmp(r[3], r[5]) * 2 + cmp(r[4], r[6]) + 3
                dir2 = cmp(r[5], r[7]) * 2 + cmp(r[6], r[8]) + 3
                k.append((2, int(dir1 + 7 * dir2 + 49 * (r[1] // 5) + 392 * (
                    r[2] // 5)), r[3], r[4], r[5], r[6], r[7], r[8]))
            elif r[0] == "6" or r[0] == "7":
                r = [float(x) for x in r]
                if r[1] == 32.0 and r[2] == 0.0:
                    if (r[4] == r[10] and r[3] < r[9]) or r[4] > r[10]:
                        r[3:11] = r[9:11] + r[7:9] + r[5:7] + r[3:5]
                if r[2] == 0.0 and r[1] in (0.0, 12.0, 22.0, 32.0) and 0 != abs(r[4] - r[10]) > r[9] - r[3] and max(
                        (
                            abs(r[3] + (r[9] - r[3]) *
                                (r[6] - r[4]) / (r[10] - r[4]) - r[5]),
                            abs(r[3] + (r[9] - r[3]) *
                                (r[8] - r[4]) / (r[10] - r[4]) - r[7])
                        ) if abs(r[4] - r[10]) > abs(r[3] - r[9]) else (
                            abs(r[4] + (r[10] - r[4]) *
                                (r[5] - r[3]) / (r[9] - r[3]) - r[6]),
                            abs(r[4] + (r[10] - r[4]) *
                                (r[7] - r[3]) / (r[9] - r[3]) - r[8])
                        )
                ) <= 5.0:
                    dir1 = cmp(r[3], r[9]) * 2 + cmp(r[4], r[10]) + 3
                    k.append(
                        (1, int(dir1 + 7 * (r[1] // 10) + 84), r[3], r[4], r[9], r[10]))
                    continue
                dir1 = cmp(r[3], r[5]) * 2 + cmp(r[4], r[6]) + 3
                dir2 = cmp(r[7], r[9]) * 2 + cmp(r[8], r[10]) + 3
                k.append((2, int(dir1 + 7 * dir2 + 49 * (r[1] // 5) + 392 * (r[2] // 5)), r[
                         3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]))
            elif r[0] == "3" or r[0] == "4":
                r = [float(x) for x in r]
                k.append(
                    (3, int((r[1] // 10) + 4 * (r[2] // 5)), r[3], r[4], r[5], r[6], r[7], r[8]))
            elif r[0] == "99":
                bn = r[7].split("@")[0]
                g = dbn.get(bn)
                if not g or self is g or g in buhin_stack:
                    k = []
                    logging.error(
                        "'{}' was not found or has a quotation loop".format(bn))
                    break
                buhin_stack.append(g)
                bk = g.getKaku(dbn)
                buhin_stack[-1:] = []
                area = [float(x) for x in r[3:7]]
                params = [float(x) for x in r[1:3] + r[9:11]]
                if len(params) < 4:
                    params = (params + [0.0, 0.0])[0:4]
                isStretched = False
                if params[0:2] != [0.0, 0.0]:
                    isStretched = True
                    if params[0] > 100.0:
                        params[0] -= 200.0  # 任意点モード
                    else:
                        params[2:4] = [0.0, 0.0]  # 中心点モード
                scale = [(area[2] - area[0]) / 200.0,
                         (area[3] - area[1]) / 200.0]
                for bkaku in bk:
                    points = list(bkaku[2:])
                    l = len(points)
                    if isStretched:
                        for i in range(0, l, 2):
                            points[i] = stretch(
                                params[0], params[2], points[i])
                            points[
                                i + 1] = stretch(params[1], params[3], points[i + 1])
                    for i in range(0, l, 2):
                        points[i] = area[0] + points[i] * scale[0]
                        points[i + 1] = area[1] + points[i + 1] * scale[1]
                    k.append(bkaku[0:2] + tuple(points))
        k.sort()
        self.kaku = tuple(k)
        return self.kaku

    def getKakuHash(self, dbn):
        if len(self.data) == 1 and self.data[0][0:19] == "99:0:0:0:0:200:200:":
            return ()
        if "_" in self.name:
            return ()
        return tuple(k[0:2] for k in self.getKaku(dbn))
    xorMaskType = 0


def main():

    db = []
    dbn = {}

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
            db.append(glyph)
            dbn[l[0]] = glyph

    neg_url = "http://glyphwiki.org/wiki/Group:NegativeCharacters?action=edit"
    neg_data = urllib2.urlopen(neg_url, timeout=60).read()

    neg_src = re.split(r"</?textarea(?: [^>]*)?>", neg_data)[1]
    neg_masktype = 0
    for m in re.finditer(r"\[\[(?:[^]]+\s)?([0-9a-z_-]+)(?:@\d+)?\]\]|^\*([^\*].*)$", neg_src, re.M):
        gn = m.group(1)
        if gn and gn in dbn:
            dbn[gn].xorMaskType = neg_masktype
        else:
            neg_masktype += 1

    buhin = {}
    kaku = {}

    for glyph in db:
        try:
            bh = glyph.getBuhinHash(dbn)
            if bh:
                buhin.setdefault(bh, []).append(glyph)
            kh = glyph.getKakuHash(dbn)
            if kh:
                kaku.setdefault(kh, []).append(glyph)
        except Exception:
            logging.exception('Error in "%s"', glyph.name)

    result = {"buhin": [], "kaku": [], "timestamp": timestamp}

    for b in buhin:
        for g1, g2 in itertools.combinations(buhin[b], 2):
            if g1.xorMaskType != g2.xorMaskType:
                continue
            b1 = g1.getBuhin(dbn)
            b2 = g2.getBuhin(dbn)
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

    for k in kaku:
        for g1, g2 in itertools.combinations(kaku[k], 2):
            if g1.xorMaskType != g2.xorMaskType:
                continue
            k1 = g1.getKaku(dbn)
            k2 = g2.getKaku(dbn)
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
