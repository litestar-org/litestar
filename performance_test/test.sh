#!/bin/bash

TEST_ITERATIONS=${1:4}

set -e
[ -d "./node_modules" ] && npm install
[ -d "./results" ] && rm -rf results
mkdir -p results

[ ! -d "./.venv" ] && python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt

for TYPE in json plaintext; do
  for TARGET in starlite starlette fastapi; do
    (cd "$TARGET"_app && gunicorn main:app -k uvicorn.workers.UvicornWorker -c gunicorn.py) &
    printf "\n\nwaiting for 10 seconds before initiating test sequence\n\n"
    sleep 5
    endpoints=(
      "async-${TYPE}-no-params"
      "sync-${TYPE}-no-params"
      "async-${TYPE}/abc"
      "sync-${TYPE}/abc"
      "async-${TYPE}-query-param?first=abc"
      "sync-${TYPE}-query-param?first=abc"
      "async-${TYPE}-mixed-params/def?first=abc"
      "sync-${TYPE}-mixed-params/def?first=abc"
    )
    for i in $(seq 1 "$TEST_ITERATIONS"); do
      for ENDPOINT in "${endpoints[@]}"; do
        name=$(echo "${TYPE}-${TARGET}-${ENDPOINT}-${i}.json" | sed 's/^\///;s/\//-/g')
        npx autocannon -d 5 -c 25 -w 4 -j "http://0.0.0.0:8001/$ENDPOINT" >>"./results/$name"
      done
    done
    printf "\n\ntest sequence finished\n\nterminating all running python instances\n\n"
    pkill python
  done
done
[ -f "./result-json.png" ] && rm "./result-json.png"
[ -f "./result-plaintext.png" ] && rm "./result-plaintext.png"
python analysis/analyzer.py
printf "\n\nTests Finished Successfully!"
