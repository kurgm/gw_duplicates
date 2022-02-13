gw_duplicates
=============

[![Update](https://github.com/kurgm/gw_duplicates/actions/workflows/update.yml/badge.svg)](https://github.com/kurgm/gw_duplicates/actions/workflows/update.yml)
[![Update viewer](https://github.com/kurgm/gw_duplicates/actions/workflows/update-viewer.yml/badge.svg)](https://github.com/kurgm/gw_duplicates/actions/workflows/update-viewer.yml)

GlyphWiki 上のグリフで重複するものを探す - https://kurgm.github.io/gw_duplicates/

```sh
bash getdump.sh  # あるいは dump_newest_only.txt を同じフォルダに置く
python ./listup_duplicates.py -o duplicates.json dump_newest_only.txt
```

を実行すると `duplicates.json` が生成される
