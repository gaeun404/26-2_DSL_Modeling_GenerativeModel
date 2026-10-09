#!/usr/bin/env bash
# GitHub 데이터셋/코드 일괄 클론 (이미 zip에 포함돼 있으면 실행 안 해도 됨).
# 실행: bash scripts/fetch_github.sh
set -e
cd "$(dirname "$0")/../data"

clone() { # url  dir
  if [ -d "$2" ]; then echo "skip $2 (이미 있음)"; else
    echo "clone $2"; git clone --depth 1 "$1" "$2"; rm -rf "$2/.git";
  fi
}

clone https://github.com/uci-soe/FairytaleQAData.git      02_fairytaleqa
clone https://github.com/Zayne-sprague/MuSR.git           03_musr
clone https://github.com/TartuNLP/true-detective.git      04_true_detective
clone https://github.com/alickzhu/PLAYER.git              05_player
# 아래는 데이터가 gated(폼 신청) — 코드/README만 받아짐
clone https://github.com/jackwu502/ThinkThrice.git        11_thinkthrice

echo "완료."
