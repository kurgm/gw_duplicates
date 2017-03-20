#!/bin/bash

set -ev

if [ "$TRAVIS_SECURE_ENV_VARS" != "true" ] || [ "$TRAVIS_BRANCH" != "master" ] || [ "$TRAVIS_PULL_REQUEST" != "false" ]; then
	exit 0
fi

git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch
git config user.name "Travis CI"
git config user.email "gogottt2009-hp@yahoo.co.jp"
git checkout gh-pages
git merge "$TRAVIS_BRANCH" --no-edit
