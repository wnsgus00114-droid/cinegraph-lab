#!/usr/bin/env bash
set -euo pipefail
mkdir -p data
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL https://files.grouplens.org/datasets/movielens/ml-latest-small.zip -o "$tmp/ml.zip"
unzip -q "$tmp/ml.zip" -d "$tmp"
cp "$tmp/ml-latest-small/movies.csv" "$tmp/ml-latest-small/ratings.csv" data/
printf 'MovieLens latest-small ready: data/movies.csv, data/ratings.csv\n'

