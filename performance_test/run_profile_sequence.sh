#!/bin/bash
set -e

endpoints=(
  #"async-json-no-params"
  #"sync-json-no-params"
  #"async-json/abc"
  #"sync-json/abc"
  #"async-json-query-param?first=abc"
  #"sync-json-query-param?first=abc"
  "async-json-mixed-params/def?first=abc"
  #"sync-json-mixed-params/def?first=abc"
)
for ENDPOINT in "${endpoints[@]}"; do
  npx autocannon "http://0.0.0.0:8001/$ENDPOINT"
done
