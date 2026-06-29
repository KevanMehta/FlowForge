#!/usr/bin/env sh
set -e
cd backend && pytest
cd ../frontend && npm test
