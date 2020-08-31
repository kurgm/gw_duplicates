#!/bin/bash

set -ev

curl https://glyphwiki.org/dump.tar.gz | tar -zf - -x dump_newest_only.txt
