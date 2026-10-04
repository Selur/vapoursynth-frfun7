#!/usr/bin/env python3
"""Functional tests for the Frfun7 VapourSynth plugin.

Usage: python3 test/test_frfun7.py [path/to/libfrfun7.so]

Without arguments the plugin is expected to be autoloaded (e.g. from the
installed wheel).

Requires the vapoursynth Python module and numpy.
"""
import sys

import numpy as np
import vapoursynth as vs

core = vs.core

WIDTH, HEIGHT, FRAMES = 96, 64, 8
SEED = 1234


def noise_clip(fmt, sigma=3.0):
    """A deterministic 8 bit noise pattern on top of a smooth gradient."""
    rng = np.random.default_rng(SEED)
    base = core.std.BlankClip(width=WIDTH, height=HEIGHT, length=FRAMES, format=fmt)
    planes = []
    for p in range(base.format.num_planes):
        w = WIDTH >> (base.format.subsampling_w if p else 0)
        h = HEIGHT >> (base.format.subsampling_h if p else 0)
        yy, xx = np.mgrid[0:h, 0:w]
        gradient = (xx * 255 / max(w - 1, 1) + yy * 255 / max(h - 1, 1)) / 2
        frames = []
        for n in range(FRAMES):
            img = gradient + rng.normal(0, sigma, size=(h, w)) + 3 * np.sin(n / 2.0)
            frames.append(np.clip(np.rint(img), 0, 255).astype(np.uint8))
        planes.append(frames)

    def fill(n, f):
        f = f.copy()
        for p in range(f.format.num_planes):
            np.asarray(f[p])[:] = planes[p][n]
        return f

    return core.std.ModifyFrame(base, base, fill)


def to_arrays(clip):
    out = []
    for n in range(clip.num_frames):
        f = clip.get_frame(n)
        out.append([np.array(f[p], dtype=np.int64) for p in range(f.format.num_planes)])
    return out


def same(a, b):
    return all(np.array_equal(x, y) for fa, fb in zip(a, b) for x, y in zip(fa, fb))


def noise_level(frames, plane=0):
    """Residual high frequency energy of a frame: std of the horizontal differences."""
    return float(np.std(np.diff(frames[-1][plane].astype(np.float64), axis=1)))


def check(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok  ", msg)


def main():
    args = sys.argv[1:]
    if args:
        core.std.LoadPlugin(args[0])
    frfun7 = core.frfun7.Frfun7

    src420 = noise_clip(vs.YUV420P8)
    src_gray = noise_clip(vs.GRAY8)
    inp420 = to_arrays(src420)
    inp_gray = to_arrays(src_gray)

    # The thresholds limit the denoising to areas whose block deviation is below
    # them, so the strength must suit the noise level: with t=6 the luma noise
    # (sigma 3) is filtered, the chroma planes need tuv=4 to be filtered as well.
    params = dict(t=6.0, tuv=4.0)

    # 1. Luma and chroma of YUV and gray clips are denoised.
    out = to_arrays(frfun7(src420, **params))
    check(all(a.shape == b.shape for fa, fb in zip(out, inp420) for a, b in zip(fa, fb)),
          "YUV420P8 output has the input dimensions")
    for p in range(3):
        r = noise_level(out, p) / noise_level(inp420, p)
        check(r < 0.8, "YUV420P8 plane %d is denoised (residual noise %.3f)" % (p, r))
    check(all(0 <= int(a.min()) and int(a.max()) <= 255 for fa in out for a in fa),
          "YUV420P8 output stays within range")

    out_gray = to_arrays(frfun7(src_gray, **params))
    r = noise_level(out_gray) / noise_level(inp_gray)
    check(r < 0.8, "GRAY8 clip is denoised (residual noise %.3f)" % r)

    # 2. The SIMD and the scalar code paths produce identical output in every mode.
    for p in range(8):
        for r1 in (2, 3):
            for tp1 in ((0, 1) if p & 1 else (0,)):
                simd = to_arrays(frfun7(src420, p=p, r1=r1, tp1=tp1, opt=1))
                scalar = to_arrays(frfun7(src420, p=p, r1=r1, tp1=tp1, opt=0))
                check(same(simd, scalar), "p=%d r1=%d tp1=%d: SIMD output is bit exact with the scalar code" % (p, r1, tp1))
                check(all(0 <= int(a.min()) and int(a.max()) <= 255 for fa in simd for a in fa),
                      "p=%d r1=%d tp1=%d: output stays within range" % (p, r1, tp1))

    # 3. A larger lambda removes more noise, a larger threshold lets more blocks be filtered.
    weak = noise_level(to_arrays(frfun7(src_gray, l=0.5)))
    strong = noise_level(to_arrays(frfun7(src_gray, l=2.0)))
    check(strong < weak, "a larger lambda denoises more (%.3f < %.3f)" % (strong, weak))
    weak = noise_level(to_arrays(frfun7(src_gray, t=4.0)))
    strong = noise_level(to_arrays(frfun7(src_gray, t=12.0)))
    check(strong < weak, "a larger threshold denoises more (%.3f < %.3f)" % (strong, weak))

    # 4. t=0 leaves luma untouched, tuv=0 leaves chroma untouched.
    out = to_arrays(frfun7(src420, t=0, tuv=4.0))
    check(all(np.array_equal(fa[0], fb[0]) for fa, fb in zip(out, inp420)), "t=0 passes the luma plane through unchanged")
    check(not same(out, inp420), "t=0 still processes the chroma planes")
    out = to_arrays(frfun7(src420, tuv=0))
    check(all(np.array_equal(fa[p], fb[p]) for fa, fb in zip(out, inp420) for p in (1, 2)),
          "tuv=0 passes the chroma planes through unchanged")
    check(not same(out, inp420), "tuv=0 still processes the luma plane")

    # 5. Constant clips are returned unchanged.
    for fmt in (vs.GRAY8, vs.YUV420P8, vs.YUV422P8, vs.YUV444P8):
        f = core.get_video_format(fmt)
        clip = core.std.BlankClip(width=WIDTH, height=HEIGHT, length=3, format=fmt, color=[128] * f.num_planes)
        out = to_arrays(frfun7(clip, p=7))
        check(all(np.all(a == 128) for fa in out for a in fa), "%s constant clip is unchanged" % f.name)

    # 6. The temporal mode takes the neighbouring frames into account, so its
    #    output differs from the input and from the purely spatial result.
    spatial = to_arrays(frfun7(src_gray, p=0))
    temporal = to_arrays(frfun7(src_gray, p=2))
    check(not same(temporal, inp_gray) and not same(temporal, spatial), "temporal mode produces its own result")
    check(all(0 <= int(a.min()) and int(a.max()) <= 255 for fa in temporal for a in fa), "temporal mode output stays within range")

    # 7. Seeking: requesting frames out of order works, also in the temporal mode.
    clip = frfun7(src420, p=3)
    ref = to_arrays(clip)
    for n in [5, 2, 7, 0, 4, 0, 7]:
        f = clip.get_frame(n)
        check(np.array_equal(np.array(f[0], dtype=np.int64), ref[n][0]), "frame %d is the same when requested out of order" % n)

    # 8. Frame properties are copied from the source frame.
    tagged = core.std.SetFrameProp(src420, prop="_Frfun7Test", intval=42)
    check(frfun7(tagged).get_frame(0).props["_Frfun7Test"] == 42, "frame properties are passed through")

    # 9. Unsupported formats are rejected.
    for fmt in [vs.RGB24, vs.GRAY10, vs.GRAY16, vs.YUV420P10, vs.YUV444P16, vs.GRAYS, vs.YUV444PS]:
        try:
            frfun7(core.std.BlankClip(width=WIDTH, height=HEIGHT, format=fmt)).get_frame(0)
        except vs.Error:
            check(True, "%s is rejected" % core.get_video_format(fmt).name)
        else:
            raise SystemExit("FAIL: %s was accepted" % core.get_video_format(fmt).name)

    # 10. Invalid parameters are rejected.
    for kwargs in [dict(l=-1), dict(t=-1), dict(tuv=-1), dict(r1=1), dict(r1=4)]:
        try:
            frfun7(src420, **kwargs)
        except vs.Error:
            check(True, "%r is rejected" % (kwargs,))
        else:
            raise SystemExit("FAIL: %r was accepted" % (kwargs,))

    print("all tests passed")


if __name__ == "__main__":
    main()
