gw_duplicates
=============

GlyphWiki 上のグリフで重複するものを探す

1. [dump](http://glyphwiki.org/dump.tar.gz) をダウンロード・展開して `dump_newest_only.txt` をこのフォルダに置く

2.  
    ```sh
python ./listup_duplicates.py
```
    で `duplicates.json` ができる

3. `index.html` をウェブブラウザで開く
