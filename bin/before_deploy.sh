#!/bin/bash

set -ev

# Deploy built files to gh-pages
cat << EOS >> .gitignore
!/duplicates.json
EOS
