"""Phase 3: the translate.py post-edit hook (approved design).

Pins the contract:
  * translate_many() is a thin wrapper over _translate_many_raw() — with the
    hook OFF the output is byte-identical to the raw engine output.
  * With the hook ON every returned string is post-edited, including the
    all-natively-Persian early-return path and empty input ({}).
  * The cache keeps RAW values only — toggling POST_EDIT is instantly
    reversible, no invalidation needed.
  * to_persian() still validates the RAW candidate; only the returned text
    is edited.
  * post_edit() raising, or returning empty/None for a non-empty input, never
    breaks the news cycle (raw text is returned instead).
  * A missing data/fa/ dir degrades to the data-free rules — no crash.
  * is_persian() and its thresholds are untouched (pinned below).
No network: _translate_batch is always stubbed.
"""
import time

import translate
import fa_postedit
from fa_lexicon import Lexicon
from fa_postedit import post_edit

RAW = "Bitcoin today: می رود و کتاب ها فروش رفتند."


def _stub(monkeypatch, fake_out=RAW):
    """Offline engine: no network, no real cache file, deterministic output."""
    monkeypatch.setattr(translate, "_LOADED", True)
    monkeypatch.setattr(translate, "_CACHE", {})
    monkeypatch.setattr(translate, "_DIRTY", False)
    monkeypatch.setattr(translate, "_translate_batch",
                        lambda texts: [fake_out for _ in texts])
    monkeypatch.setattr(translate, "POST_EDIT", False)


def test_off_is_byte_identical_to_raw(monkeypatch):
    _stub(monkeypatch)
    off = translate.translate_many(["BTC headline"])
    raw = translate._translate_many_raw(["BTC headline"])
    assert off == raw
    assert off["BTC headline"] == RAW          # hook OFF: nothing touched


def test_on_covers_all_persian_batch_and_empty_input(monkeypatch):
    """The native-Persian early return (`if not todo: return out`) is covered."""
    _stub(monkeypatch)
    monkeypatch.setattr(translate, "POST_EDIT", True)
    fa_src = "بیت کوین امروز می رود و کتاب ها فروش رفتند"
    out = translate.translate_many([fa_src])
    assert "می‌رود" in out[fa_src] and "کتاب‌ها" in out[fa_src]
    # empty input walks the other early return (`if not wanted: return {}`)
    assert translate.translate_many([]) == {}
    assert translate.translate_many(["", " "]) == {}


def test_cache_keeps_raw_values_and_toggle_reverts(monkeypatch):
    _stub(monkeypatch)
    monkeypatch.setattr(translate, "POST_EDIT", True)
    out = translate.translate_many(["BTC headline"])
    assert "می‌رود" in out["BTC headline"]      # edited at the boundary
    assert list(translate._CACHE.values()) == [RAW]   # cache stores RAW
    monkeypatch.setattr(translate, "POST_EDIT", False)
    again = translate.translate_many(["BTC headline"])   # cache hit
    assert again["BTC headline"] == RAW         # instantly reverted


def test_to_persian_edits_only_the_returned_candidate(monkeypatch):
    src = "قیمت کتاب ها بالا رفت"
    want = "قیمت کتاب‌ها بالا رفت"
    monkeypatch.setattr(translate, "POST_EDIT", True)
    assert translate.to_persian(src) == want
    monkeypatch.setattr(translate, "POST_EDIT", False)
    assert translate.to_persian(src) == src     # OFF: byte-identical


def test_post_edit_failure_returns_raw(monkeypatch):
    """An exception or an erased result never raises / never loses text."""
    _stub(monkeypatch)
    monkeypatch.setattr(translate, "POST_EDIT", True)
    monkeypatch.setattr(translate, "post_edit",
                        lambda _t: (_ for _ in ()).throw(RuntimeError("boom")))
    out = translate.translate_many(["BTC headline"])
    assert out["BTC headline"] == RAW
    monkeypatch.setattr(translate, "post_edit", lambda _t: "")   # eraser
    out = translate.translate_many(["BTC headline"])
    assert out["BTC headline"] == RAW


def test_missing_data_dir_degrades_to_free_rules(monkeypatch, tmp_path):
    monkeypatch.setattr(fa_postedit, "lexicon",
                        lambda: Lexicon(data_dir=tmp_path / "nope"))
    assert post_edit("بازار می رود") == "بازار می‌رود"   # data-free rules live
    assert "Bitcoin" in post_edit("Bitcoin بالا رفت")    # lexicon rule skipped
    assert post_edit("سال 2026") == "سال ۲۰۲۶"


def test_is_persian_thresholds_untouched():
    assert translate._LATIN_RUN_MAX == 4
    assert translate._PERSIAN_MIN_SHARE == 0.45


def test_benchmark_post_edit_10k_mixed():
    """Report-only benchmark: no fragile time threshold."""
    samples = [
        "Bitcoin slides toward $77,000 ahead of the Senate vote",
        "بیت کوین ۸۴۰ هزار دلار است؟ وال استریت می تواند روند صعودی ایجاد کند",
        "قیمت طلا با وجود تورم افزایش یافت؛ کتاب ها هم فروش رفتند.",
        "Fed's Powell: inflation is under control (https://example.com/2026/a)",
        "فدرال رزرو نرخ بهره را تغییر نداد؛ Jerome Powell گفت تورم کنترل شده",
        "ICE سلطه نیویورک را با معاملات آتی روزانه فلزات گرانبها به چالش می کشد",
        "سهام MSTR افت کرد و به info@example.com ایمیل زدند 2 بار",
    ]
    corpus = [samples[i % len(samples)] for i in range(10000)]
    t0 = time.perf_counter()
    out = [post_edit(s) for s in corpus]
    dt = time.perf_counter() - t0
    assert len(out) == 10000 and all(isinstance(s, str) and s for s in out)
    print(f"\n[bench] post_edit x10,000 mixed: {dt:.2f}s "
          f"({10000 / dt:,.0f} strings/s)")
