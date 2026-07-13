#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

cd "$ROOT"

echo "Running v39 final evidence / memory-accounting report generation"

python3 experiments/layer3-v39-final-evidence/v39_final_evidence_report.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v39_evidence_summary.csv \
  layer3-results/v39_final_evidence_report.md

echo
cat layer3-results/v39_final_evidence_report.md
