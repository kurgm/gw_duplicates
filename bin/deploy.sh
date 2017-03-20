#!/bin/bash

set -ev

if [ "$TRAVIS_SECURE_ENV_VARS" != "true" ] || [ "$TRAVIS_BRANCH" != "master" ] || [ "$TRAVIS_PULL_REQUEST" != "false" ]; then
	exit 0
fi

git add --all
git commit -m "Update build - $TRAVIS_COMMIT"
git push "https://${GH_TOKEN}@github.com/kurgm/gw_duplicates.git" gh-pages:gh-pages --follow-tags > /dev/null 2>&1
