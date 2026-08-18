PYTHON ?= python3
override MPLCONFIGDIR := .mplconfig
export SOURCE_DATE_EPOCH := 1786968000
export FORCE_SOURCE_DATE := 1
export TZ := UTC
export LANG := C
export LC_ALL := C
export PYTHONHASHSEED := 0
export PYTHONNOUSERSITE := 1
export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPATH :=
export MPLBACKEND := Agg

.NOTPARALLEL:
.PHONY: all rebuild theory analysis assets manifest verify release clean

all: theory analysis assets manifest verify

rebuild:
	$(MAKE) clean
	$(MAKE) all

theory:
	$(PYTHON) replication/check_theory.py

analysis:
	$(PYTHON) replication/run_analysis.py

assets: analysis
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) replication/render_assets.py

manifest: assets
	$(PYTHON) replication/build_release.py --manifest-only

verify: theory assets manifest
	$(PYTHON) replication/verify_reproduction.py

release: rebuild
	$(PYTHON) replication/build_release.py
	$(PYTHON) replication/verify_release.py

clean:
	$(PYTHON) replication/clean_generated.py
