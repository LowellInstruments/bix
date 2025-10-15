#!/usr/bin/env bash


FOL=/home/kaz/PycharmProjects/bix


clear
echo
echo "activating python venv for BIX"
cd $FOL || (echo "BIX error, cannot switch folder"; exit 1)
source .venv/bin/activate

echo "running main_bix.py"
python3 main_bix.py
