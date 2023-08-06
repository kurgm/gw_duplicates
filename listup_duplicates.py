#!/usr/bin/env python

from __future__ import annotations

from abc import ABCMeta, abstractmethod
import argparse
import collections
from collections.abc import Callable, Iterator, Mapping, Sequence
import copy
import itertools
import json
import logging
import os
import re
from typing import Generic, NamedTuple, Optional, TypeVar, Union
from urllib.request import urlopen


logging.basicConfig(level=logging.DEBUG)


class CircularCallError(ValueError):
    pass


T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")
Either = Union[tuple[T, None], tuple[None, U]]


class Glyph(NamedTuple):

    name: str
    rel: Optional[str]
    data: Sequence[str]
    xorMaskType: int = 0

    def isAlias(self):
        return len(self.data) == 1 and \
            self.data[0].startswith("99:0:0:0:0:200:200:")


class Dump(dict[str, Glyph]):
    timestamp: float

    def __init__(self, timestamp: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timestamp = timestamp


class GlyphSummaryManagerMixin(Generic[T], metaclass=ABCMeta):
    __getsummary_stack: list[str]
    __summary_cache: dict[str, Either[T, Exception]]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__getsummary_stack = []
        self.__summary_cache = {}

    @abstractmethod
    def _get_summary_impl(self, name: str) -> T:
        raise NotImplementedError

    def get_summary(self, name: str) -> T:
        if name in self.__summary_cache:
            entry = self.__summary_cache[name]
            if entry[1] is not None:
                # Copy the exception to prevent the traceback of original exc
                # getting extended
                raise copy.copy(entry[1])
            return entry[0]

        needs_pop = False
        try:
            if name in self.__getsummary_stack:
                raise CircularCallError(f"Circularly called in {name}")
            self.__getsummary_stack.append(name)
            needs_pop = True
            result = self._get_summary_impl(name)
        except Exception as exc:
            self.__summary_cache[name] = (None, exc)
            logging.error(
                "An error occurred in %r.get_summary(%r)", self, name)
            raise
        else:
            self.__summary_cache[name] = (result, None)
            return result
        finally:
            if needs_pop:
                self.__getsummary_stack.pop()


class SimilarGlyphFinderBase(Generic[T, U], metaclass=ABCMeta):
    dump: Dump

    def __init__(self, dump: Dump) -> None:
        self.dump = dump

    @abstractmethod
    def get_summary(self, name: str) -> T:
        raise NotImplementedError

    @abstractmethod
    def get_hash(self, name: str) -> U:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def is_similar_summary(cls, summary1: T, summay2: T) -> bool:
        raise NotImplementedError

    def find_similar_glyph_pairs(self) -> Iterator[tuple[Glyph, Glyph]]:
        hash_dict: Mapping[U, list[Glyph]] = collections.defaultdict(list)
        for name, glyph in self.dump.items():
            if "_" in name or glyph.isAlias():
                continue
            try:
                ghash = self.get_hash(name)
                if ghash:
                    hash_dict[ghash].append(glyph)
            except Exception:
                logging.exception("Error in %r", name)

        for glyphs in hash_dict.values():
            for g1, g2 in itertools.combinations(glyphs, 2):
                if g1.xorMaskType != g2.xorMaskType:
                    continue
                summary1 = self.get_summary(g1.name)
                summary2 = self.get_summary(g2.name)
                if self.is_similar_summary(summary1, summary2):
                    yield g1, g2


FloatMapper = Callable[[float], float]


def coord_mapper(bp0: float, bp1: float) -> FloatMapper:
    scale = (bp1 - bp0) / 200.0
    return lambda p: bp0 + p * scale


def stretch(
        dp: float, sp: float, p: float,
        pmin: float = 12.0, pmax: float = 188.0):
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


def stretch_mapper(dp: float, sp: float, coords: list[float] = []) -> \
        FloatMapper:
    if coords:
        pmin = min(coords)
        pmax = max(coords)
    else:
        pmin = 12.0
        pmax = 188.0
    return lambda p: stretch(dp, sp, p, pmin, pmax)


def compose(f: Callable[[U], R], g: Callable[[T], U]) -> Callable[[T], R]:
    return lambda *args: f(g(*args))


Point = tuple[float, float]
PointMapper = Callable[[Point], Point]


def point_mapper(x_mapper: FloatMapper, y_mapper: FloatMapper) -> PointMapper:
    return lambda p: (x_mapper(p[0]), y_mapper(p[1]))


def cmp(a: float, b: float) -> int:
    return (a > b) - (a < b)


def cmp2(a: Point, b: Point) -> int:
    return cmp(a[0], b[0]) * 3 + cmp(a[1], b[1])


def parse_pointarr(values: Sequence[str]):
    it = (float(value) for value in values)
    return list(zip(it, it))


henka_re = re.compile(
    r"""
        -(?:[gtv]v?|[hmis]|j[asv]?|k[pv]?|u[ks]?)?(\d{2})
        (?:-(?:var|itaiji)-\d{3})?
        $
    """,
    re.X
)


def get_buhin_diflim(name: str):
    x1 = y1 = x2 = y2 = 15.0
    if m := henka_re.search(name):
        suffix = m.group(1)
        if suffix == "01":
            x2 = 40.0
        elif suffix == "02":
            x1 = 40.0
        elif suffix == "03":
            y2 = 40.0
        elif suffix in ("04", "14", "24"):
            y1 = 40.0
        elif suffix == "08":
            y1 = 25.0
            y2 = 25.0
        elif suffix == "09":
            x1 = 25.0
            x2 = 25.0
    return ((x1, y1), (x2, y2))


class BuhinElem(NamedTuple):
    name: str
    coords: tuple[Point, Point]


BuhinSummary = tuple[BuhinElem, ...]
BuhinHash = tuple[str, ...]


class BuhinSimilarGlyphFinder(
        GlyphSummaryManagerMixin[BuhinSummary],
        SimilarGlyphFinderBase[BuhinSummary, BuhinHash]):

    def _get_summary_impl(self, name: str) -> BuhinSummary:
        buhin: list[BuhinElem] = []
        for row in self.dump[name].data:
            splitrow = row.split(":")
            if splitrow[0] == "0" and splitrow[1] not in ("97", "98", "99"):
                continue
            if splitrow[0] != "99":
                return ()
            x0, y0, x1, y1 = [float(x) for x in splitrow[3:7]]
            buhinname = splitrow[7].split("@")[0]
            b_buhins = self.get_summary(buhinname)
            if not b_buhins:
                buhin.append(BuhinElem(buhinname, ((x0, y0), (x1, y1))))
                continue
            x_map = coord_mapper(x0, x1)
            y_map = coord_mapper(y0, y1)
            p_map = point_mapper(x_map, y_map)
            buhin.extend(
                BuhinElem(b_name, (p_map(p1), p_map(p2)))
                for b_name, (p1, p2) in b_buhins)
        buhin.sort()
        return tuple(buhin)

    def get_hash(self, name: str) -> BuhinHash:
        return tuple(b.name for b in self.get_summary(name))

    @classmethod
    def is_similar_summary(
            cls, summary1: BuhinSummary, summary2: BuhinSummary) -> bool:
        for b1, b2 in zip(summary1, summary2):
            if cmp2(*b1.coords) != cmp2(*b2.coords):
                return False
            diflim = get_buhin_diflim(b1.name)
            if all(abs(x1 - x2) <= limx and abs(y1 - y2) <= limy
                    for (x1, y1), (x2, y2), (limx, limy) in
                    zip(b1.coords, b2.coords, diflim)):
                continue
            b1p1, b1p2 = b1.coords
            b2p1, b2p2 = b2.coords
            if abs((b1p1[0] + b1p2[0]) - (b2p1[0] + b2p2[0])) <= 20.0 and \
                    abs((b1p1[1] + b1p2[1]) - (b2p1[1] + b2p2[1])) <= 20.0:
                continue
            return False
        return True


class KakuElem(NamedTuple):
    stype: int
    dirshape: tuple[int, ...]
    coords: tuple[Point, Point]


KakuSummary = tuple[KakuElem, ...]
KakuHash0 = tuple[int, tuple[int, ...]]
KakuHash = tuple[KakuHash0, ...]


def dist_from_line(
        x0: float, y0: float, x1: float, y1: float, x: float, y: float):
    if abs(y0 - y1) > abs(x0 - x1):
        return abs(x0 + (x1 - x0) * (y - y0) / (y1 - y0) - x)
    return abs(y0 + (y1 - y0) * (x - x0) / (x1 - x0) - y)


def is_almost_straight(points: Sequence[Point]):
    p1 = points[0]
    p2 = points[-1]
    return all(dist_from_line(*p1, *p2, *p) <= 5.0 for p in points[1:-1])


_stype_data_endpos: dict[str, tuple[int, int]] = {
    "1": (1, 7),
    "2": (2, 9),
    "6": (2, 11),
    "7": (2, 11),
    "3": (3, 9),
    "4": (3, 9),
    "0": (0, 7),
}


def get_kaku_info(line_data: list[str]) -> \
        Optional[tuple[int, tuple[int, int], tuple[Point, ...]]]:
    strokeType = line_data[0]
    sttType = int(line_data[1])
    endType = int(line_data[2])
    if strokeType not in _stype_data_endpos:
        return None
    if strokeType == "0" and sttType not in (97, 98, 99):
        return None
    stype, data_endpos = _stype_data_endpos[strokeType]
    coords = parse_pointarr(line_data[3:data_endpos])

    if stype == 1:
        (x0, y0), (x1, y1) = coords
        if (sttType == endType == 32 and y0 > y1 and y0 - y1 >= x1 - x0) or \
                (y0 == y1 and x0 > x1):
            coords.reverse()
        if sttType == 2:
            sttType = 0
    elif stype == 2:
        x0, y0 = coords[0]
        x2, y2 = coords[-1]
        if sttType == 32 and endType == 0 and \
                ((y0 == y2 and x0 > x2) or y0 > y2):
            coords.reverse()
            x0, x2 = x2, x0
        if endType == 0 and sttType in (0, 12, 22, 32) and \
                0 != abs(y0 - y2) >= x2 - x0 and is_almost_straight(coords):
            return 1, (sttType, 32), (coords[0], coords[-1])

    return stype, (sttType, endType), tuple(coords)


class KakuSimilarGlyphFinder(
        GlyphSummaryManagerMixin[KakuSummary],
        SimilarGlyphFinderBase[KakuSummary, KakuHash]):

    def _get_summary_impl(self, name: str) -> KakuSummary:
        k: list[KakuElem] = []
        for row in self.dump[name].data:
            line_data = row.split(":")
            if line_data[0] != "99":
                kaku_info = get_kaku_info(line_data)
                if kaku_info is None:
                    continue
                kaku_type, shapes, points = kaku_info
                dir1 = cmp2(points[0], points[1])
                dir2 = cmp2(points[-2], points[-1])
                dirs = (dir1,) if len(points) == 2 else (dir1, dir2)
                kaku_sig = KakuElem(
                    kaku_type, dirs + shapes, (points[0], points[-1]))
                k.append(kaku_sig)
                continue

            buhinname = line_data[7].split("@")[0]
            b_kakus = self.get_summary(buhinname)
            x0, y0, x1, y1 = [float(x) for x in line_data[3:7]]
            dpx = float(line_data[1])
            dpy = float(line_data[2])
            spx = float(line_data[9]) if len(line_data) > 9 else 0.0
            spy = float(line_data[10]) if len(line_data) > 10 else 0.0
            x_map = coord_mapper(x0, x1)
            y_map = coord_mapper(y0, y1)
            if not dpx == dpy == 0.0:
                if dpx > 100.0:
                    dpx -= 200.0  # 任意点モード
                else:
                    spx = spy = 0.0  # 中心点モード
                stretch_x = stretch_mapper(
                    dpx, spx,
                    [x for b_kaku in b_kakus for (x, y) in b_kaku.coords]
                )
                stretch_y = stretch_mapper(
                    dpy, spy,
                    [y for b_kaku in b_kakus for (x, y) in b_kaku.coords]
                )
                x_map = compose(x_map, stretch_x)
                y_map = compose(y_map, stretch_y)
            p_map = point_mapper(x_map, y_map)
            k.extend(
                KakuElem(b_stype, b_dirshape, (p_map(b_stt), p_map(b_end)))
                for b_stype, b_dirshape, (b_stt, b_end) in b_kakus)
        k.sort()
        return tuple(k)

    def get_hash(self, name: str) -> KakuHash:
        return tuple(k[0:2] for k in self.get_summary(name))

    @classmethod
    def is_similar_summary(
            cls, summary1: KakuSummary, summary2: KakuSummary) -> bool:
        for k1, k2 in zip(summary1, summary2):
            if any(abs(x1 - x2) > 20.0 or abs(y1 - y2) > 20.0
                    for (x1, y1), (x2, y2) in zip(k1.coords, k2.coords)):
                return False
        return True


def get_xor_mask_type_map():
    neg_url = "https://glyphwiki.org/wiki/Group:NegativeCharacters?action=edit"
    neg_data = urlopen(neg_url, timeout=60).read().decode("utf-8")

    neg_src = re.split(r"</?textarea(?: [^>]*)?>", neg_data)[1]
    neg_masktype = 0
    result: dict[str, int] = {}
    for m in re.finditer(
            r"\[\[(?:[^]]+\s)?([0-9a-z_-]+)(?:@\d+)?\]\]|^\*([^\*].*)$",
            neg_src, re.M):
        gn = m.group(1)
        if gn:
            result[gn] = neg_masktype
        else:
            neg_masktype += 1
    return result


def getDump(path: str):
    masktype_map = get_xor_mask_type_map()
    timestamp = os.path.getmtime(path)
    dump = Dump(timestamp)
    with open(path, "r", encoding="utf-8") as dumpfile:
        dumpfile.readline()  # header
        dumpfile.readline()  # ------

        for line in dumpfile:
            split_line = line[:-1].split("|")
            if len(split_line) != 3:
                continue
            name, rel, gdata = [x.strip() for x in split_line]
            if rel == "u3013":
                rel = None
            glyph = Glyph(
                name, rel, gdata.split("$"), masktype_map.get(name, 0))
            dump[name] = glyph
    return dump


DEFAULT_DUMP_PATH = "dump_newest_only.txt"
DEFAULT_OUT_PATH = "duplicates.json"


def main(dump_path: str = DEFAULT_DUMP_PATH, out_path: str = DEFAULT_OUT_PATH):
    sgfinders: list[tuple[str, type[SimilarGlyphFinderBase]]] = [
        ("buhin", BuhinSimilarGlyphFinder),
        ("kaku", KakuSimilarGlyphFinder),
    ]

    dump = getDump(dump_path)

    result = {}
    visited_pairs: set[tuple[str, str]] = set()

    for key, sgfindercls in sgfinders:
        entries: list[tuple[str, str, Optional[str], Optional[str]]] = []
        finder = sgfindercls(dump)
        for g1, g2 in finder.find_similar_glyph_pairs():
            name_pair = (g1.name, g2.name)
            if name_pair in visited_pairs:
                continue
            visited_pairs.add(name_pair)
            entries.append((g1.name, g2.name, g1.rel, g2.rel))

        result[key] = entries

    result["timestamp"] = dump.timestamp

    with open(out_path, "w") as outfile:
        json.dump(result, outfile, separators=(",", ":"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_path", "-o", default=DEFAULT_OUT_PATH)
    parser.add_argument("dump_path", nargs="?", default=DEFAULT_DUMP_PATH)
    args = parser.parse_args()
    main(args.dump_path, args.out_path)
