# Reference environment

The versioned release was built and checked with:

- Python 3.12.2
- NumPy 2.2.6
- Matplotlib 3.9.2
- SymPy 1.13.1
- mpmath 1.3.0
- Poppler 26.06.0 for PDF inspection
- GNU Make 3.81
- macOS 26.5.1 on Apple silicon

The Makefile fixes the timezone, locale, Python hash seed, Matplotlib backend,
and source-date epoch. It disables user-site packages and bytecode caches. The
scientific acceptance criterion on another supported system is exact agreement
of the rational quantities, classifications, counts, file sets, and manifest
hashes generated there. Byte identity of raster or PDF files also depends on
the listed graphics and font toolchain.
