Description
===========

Frfun7 is a spatial fractal denoising plugin by Copyright (C) 2002-2006, 2013 Marc Fauconneau (prunedtree), (C)2021 Ferenc Pintér.


Usage
=====
::

    frfun7.Frfun7(clip clip[, float l=1.1, float t=6.0, float tuv=2.0, int p=0, int tp1=0, int r1=3, int opt=1])


Parameters:
    *clip*
        A clip to process. It must be 8 bit Gray or YUV.

        Clips with a variable format are accepted, each frame is then
        checked individually.

    *l*
        It should be called "lambda" but that word is reserved by Python.

        Adjusts the power of the local denoising.
        
        It must not be negative.

        Default: 1.1.

    *t*
        Limits the maximum luma denoising power for edges.

        0 disables processing of the luma plane.

        It must not be negative.

        Default: 6.0.

    *tuv*
        Limits the maximum chroma denoising power for edges.

        0 disables processing of the chroma planes.

        It must not be negative.

        Default: 2.0.

    *p*
        Selects the type of filtering.

        0 - the basic algorithm

        1 - adaptive overlapping

        2 - temporal

        4 - adaptive radius

        Default: 0.

    *tp1*
        A threshold which affects p=1. Values greater than 0 will make it skip processing some pixels.

        Default: 0.

    *r1*
        Radius for first pass of the internal algorithm.

        It can be 2 or 3. 2 is faster.

        Default: 3.

    *opt*
        Selects the implementation.

        0 - scalar C++ code

        1 - SSE2 code (x86 only, falls back to the scalar code elsewhere)

        Both produce identical output.

        Default: 1.


Installation
============

Prebuilt wheels for Windows x64, Linux x86_64 and macOS arm64 are
attached to each `GitHub release
<https://github.com/Selur/vapoursynth-frfun7/releases>`_::

    pip install vapoursynth_frfun7-*.whl

The plugin uses the VapourSynth API 4 (VapourSynth R55 or newer).


Testing
=======

``test/test_frfun7.py`` runs the plugin on synthetic clips: it checks
that the SIMD and the scalar code produce identical output in every
mode, that the planes are denoised, that ``t=0``/``tuv=0`` leave the
respective planes untouched and that unsupported formats and
parameters are rejected. It needs the ``vapoursynth`` Python module
and ``numpy``::

    python3 test/test_frfun7.py build/libfrfun7.so


Compilation
===========

Meson and Ninja are required. The VapourSynth API 4 headers are
bundled, a system installation of VapourSynth is optional.

::

    meson setup build
    ninja -C build

On macOS the plugin is built as ``libfrfun7.dylib``, which is the only
extension VapourSynth autoloads there.


License
=======

GPLv2.
