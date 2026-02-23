#!/bin/bash

bunx openapi-generator-cli generate -g typescript-fetch -i http://127.0.0.1:8000/openapi.json -o ./src/lib/api
bun --bun run dev --open
