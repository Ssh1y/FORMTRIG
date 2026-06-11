#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m py_compile \
  tools/formtrig_algorithm_core.py \
  tools/formtrig_modes.py \
  tools/run_formtrig_preflight_v3.py \
  tests/test_formtrig_algorithm_core.py \
  tests/test_tcir_semantics.py \
  tests/test_atom_truth_semantics.py

python3 tests/test_formtrig_algorithm_core.py
python3 tests/test_tcir_semantics.py
python3 tests/test_atom_truth_semantics.py
python3 tools/run_formtrig_preflight_v3.py
