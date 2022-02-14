#!/usr/bin/env python

from abc import ABCMeta, abstractmethod
import argparse
import collections
import copy
import itertools
import json
import logging
import os
import re
from typing import Callable, Dict, Generic, Iterator, List, Mapping, \
    NamedTuple, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, cast
from urllib.request import urlopen


logging.basicConfig(level=logging.DEBUG)


class CircularCallError(ValueError):
    pass


T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")
Either = Union[Tuple[T, None], Tuple[None, U]]


class Glyph(NamedTuple):

    name: str
    rel: Optional[str]
    data: Sequence[str]
    xorMaskType: int = 0

    def isAlias(self):
        return len(self.data) == 1 and \
            self.data[0].startswith("99:0:0:0:0:200:200:")


class Dump(Dict[str, Glyph]):
    timestamp: float

    def __init__(self, timestamp: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timestamp = timestamp


class GlyphSummaryManagerMixin(Generic[T], metaclass=ABCMeta):
    __getsummary_stack: List[str]
    __summary_cache: Dict[str, Either[T, Exception]]

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
    _hash_dict: Mapping[U, List[Glyph]]

    def __init__(self, dump: Dump) -> None:
        self.dump = dump
        self._hash_dict = collections.defaultdict(list)

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

    def find_similar_glyph_pairs(self) -> Iterator[Tuple[Glyph, Glyph]]:
        for name, glyph in self.dump.items():
            if "_" in name or glyph.isAlias():
                continue
            try:
                ghash = self.get_hash(name)
                if ghash:
                    self._hash_dict[ghash].append(glyph)
            except Exception:
                logging.exception("Error in %r", name)

        for glyphs in self._hash_dict.values():
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


def stretch_mapper(dp: float, sp: float, coords: List[float] = []) -> \
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


def cmp(a: float, b: float):
    return (a > b) - (a < b)


henka_re = re.compile(
    r"""
        -(?:[gtv]v?|[hmis]|j[asv]?|k[pv]?|u[ks]?)?(\d{2})
        (?:-(?:var|itaiji)-\d{3})?
        $
    """,
    re.X
)

BuhinElem = Tuple[float, float, float, float, str]
BuhinSummary = Tuple[BuhinElem, ...]
BuhinHash = Tuple[str, ...]


class BuhinSimilarGlyphFinder(
        GlyphSummaryManagerMixin[BuhinSummary],
        SimilarGlyphFinderBase[BuhinSummary, BuhinHash]):

    def _get_summary_impl(self, name: str) -> BuhinSummary:
        buhin: List[BuhinElem] = []
        for row in self.dump[name].data:
            splitrow = row.split(":")
            if splitrow[0] == "0" and splitrow[1] not in ("97", "98", "99"):
                continue
            if splitrow[0] != "99":
                buhin = []
                break
            buhinname = splitrow[7].split("@")[0]
            b_buhins = self.get_summary(buhinname)
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

    def get_hash(self, name: str) -> BuhinHash:
        return tuple(b[4] for b in self.get_summary(name))

    @classmethod
    def is_similar_summary(
            cls, summary1: BuhinSummary, summary2: BuhinSummary) -> bool:
        for B1, B2 in zip(summary1, summary2):
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
            return True
        return False


KakuElem = Tuple[Union[int, Tuple[int, ...], float], ...]
KakuSummary = Tuple[KakuElem, ...]
KakuHash0 = Tuple[int, Tuple[int, ...]]
KakuHash = Tuple[KakuHash0, ...]


def dist_from_line(
        x0: float, y0: float, x1: float, y1: float, x: float, y: float):
    if abs(y0 - y1) > abs(x0 - x1):
        return abs(x0 + (x1 - x0) * (y - y0) / (y1 - y0) - x)
    return abs(y0 + (y1 - y0) * (x - x0) / (x1 - x0) - y)


def get_kaku_info(line_data: List[str]) -> \
        Optional[Tuple[int, Tuple[int, int], Tuple[float, ...]]]:
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


class KakuSimilarGlyphFinder(
        GlyphSummaryManagerMixin[KakuSummary],
        SimilarGlyphFinderBase[KakuSummary, KakuHash]):

    def _get_summary_impl(self, name: str) -> KakuSummary:
        k: List[KakuElem] = []
        for row in self.dump[name].data:
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
            b_kakus = self.get_summary(buhinname)
            x0, y0, x1, y1 = [float(x) for x in line_data[3:7]]
            dpx = float(line_data[1])
            dpy = float(line_data[2])
            spx = spy = 0.0
            try:
                spx = float(line_data[9])
                spy = float(line_data[10])
            except IndexError:
                pass
            x_map = coord_mapper(x0, x1)
            y_map = coord_mapper(y0, y1)
            if not dpx == dpy == 0.0:
                if dpx > 100.0:
                    dpx -= 200.0  # 任意点モード
                else:
                    spx = spy = 0.0  # 中心点モード
                stretch_x = stretch_mapper(
                    dpx, spx,
                    [x for b_kaku in b_kakus for x in cast(
                        Tuple[float, ...], b_kaku[2::2])]
                )
                stretch_y = stretch_mapper(
                    dpy, spy,
                    [y for b_kaku in b_kakus for y in cast(
                        Tuple[float, ...], b_kaku[3::2])]
                )
                x_map = compose(x_map, stretch_x)
                y_map = compose(y_map, stretch_y)
            for b_kaku in b_kakus:
                points = list(cast(Tuple[float], b_kaku[2:]))
                points[0::2] = [x_map(x) for x in points[0::2]]
                points[1::2] = [y_map(y) for y in points[1::2]]
                k.append(b_kaku[0:2] + tuple(points))
        k.sort()
        return tuple(k)

    def get_hash(self, name: str) -> KakuHash:
        return tuple(cast(KakuHash0, k[0:2]) for k in self.get_summary(name))

    @classmethod
    def is_similar_summary(
            cls, summary1: KakuSummary, summary2: KakuSummary) -> bool:
        for (K1, K2) in zip(summary1, summary2):
            if all(abs(p1 - p2) <= 20.0 for (p1, p2) in zip(
                    cast(Tuple[float, ...], K1[2:4] + K1[-2:]),
                    cast(Tuple[float, ...], K2[2:4] + K2[-2:]))):
                continue
            break
        else:
            return True
        return False


def get_xor_mask_type_map():
    neg_url = "https://glyphwiki.org/wiki/Group:NegativeCharacters?action=edit"
    neg_data = urlopen(neg_url, timeout=60).read().decode("utf-8")

    neg_src = re.split(r"</?textarea(?: [^>]*)?>", neg_data)[1]
    neg_masktype = 0
    result: Dict[str, int] = {}
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
    sgfinders: List[Tuple[str, Type[SimilarGlyphFinderBase]]] = [
        ("buhin", BuhinSimilarGlyphFinder),
        ("kaku", KakuSimilarGlyphFinder),
    ]

    dump = getDump(dump_path)

    result = {}
    visited_pairs: Set[Tuple[str, str]] = set()

    for key, sgfindercls in sgfinders:
        entries: List[Tuple[str, str, Optional[str], Optional[str]]] = []
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
