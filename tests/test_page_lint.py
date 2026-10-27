"""The distinctive-page-design lint: each rule kind, the waiver path and the exit codes."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/design/skills/distinctive-page-design"
SCRIPT = SKILL / "scripts/page_lint.py"

spec = importlib.util.spec_from_file_location("page_lint", SCRIPT)
assert spec is not None
assert spec.loader is not None
page_lint = importlib.util.module_from_spec(spec)
sys.modules["page_lint"] = page_lint
spec.loader.exec_module(page_lint)

CHECK_KIND = {
    "declaration": "css",
    "css-requires": "css",
    "number-below": "css",
    "required-element": "html",
    "heading-order": "html",
    "phrase-list": "copy",
    "gradient-stops": "css",
}


def rule(rule_id, check, params, tier="taste", message="a message", stricter=None):
    entry = {
        "id": rule_id,
        "tier": tier,
        "kind": CHECK_KIND[check],
        "check": check,
        "params": params,
        "message": message,
    }
    if stricter:
        entry["stricter"] = stricter
    return entry


def judged(rule_id, tier="floor", message="check this by hand"):
    return {"id": rule_id, "tier": tier, "kind": "judged", "message": message}


def write_rules(tmp_path, *rules, shared=None, name="rules.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"version": 1, "shared": shared or {}, "rules": list(rules)}))
    return path


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def lint(capsys, *argv):
    code = page_lint.main([str(a) for a in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- css rules ----------------------------------------------------------------------

TRANSITION_ALL = rule(
    "taste-transition-all",
    "declaration",
    {"property": "transition", "value": r"\ball\b"},
    message="transition: all animates properties nobody chose",
)


def test_a_css_declaration_rule_reports_file_line_rule_tier_and_message(tmp_path, capsys):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    css = write(tmp_path, "site.css", "a {\n  color: red;\n  transition: all 0.2s;\n}\n")
    code, out, _ = lint(capsys, css, "--rules", rules)
    assert code == 1
    assert (
        f"{css}:3 taste-transition-all taste transition: all animates properties nobody chose"
        in out
    )


def test_a_css_file_with_no_match_exits_zero(tmp_path, capsys):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    css = write(tmp_path, "site.css", "a { transition: color 0.2s; }\n")
    code, out, _ = lint(capsys, css, "--rules", rules)
    assert code == 0
    assert "0 findings" in out


def test_a_style_block_in_html_reports_the_line_in_the_html_file(tmp_path, capsys):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    page = write(
        tmp_path,
        "index.html",
        "<!doctype html>\n<html lang=en>\n<style>\n  a { transition: all 1s; }\n</style>\n",
    )
    code, out, _ = lint(capsys, page, "--rules", rules)
    assert code == 1
    assert f"{page}:4 taste-transition-all" in out


def test_a_selector_filter_limits_a_declaration_rule(tmp_path, capsys):
    only_body = rule(
        "floor-hidden-overflow",
        "declaration",
        {"property": "overflow-x", "value": "hidden", "selector": "^(html|body)$"},
        tier="floor",
    )
    rules = write_rules(tmp_path, only_body)
    ok = write(tmp_path, "ok.css", ".carousel { overflow-x: hidden; }\n")
    bad = write(tmp_path, "bad.css", "html, body { overflow-x: hidden; }\n")
    assert lint(capsys, ok, "--rules", rules)[0] == 0
    assert lint(capsys, bad, "--rules", rules)[0] == 1


def test_comments_and_font_face_blocks_are_not_read_as_declarations(tmp_path, capsys):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    css = write(
        tmp_path,
        "site.css",
        "/* transition: all 1s; */\n@font-face { font-family: X; src: url(a.woff2); }\n",
    )
    assert lint(capsys, css, "--rules", rules)[0] == 0


def test_a_rule_that_needs_a_companion_fails_until_the_companion_exists(tmp_path, capsys):
    needs_query = rule(
        "floor-reduced-motion",
        "css-requires",
        {"when": r"@keyframes|animation\s*:", "require": "prefers-reduced-motion"},
        tier="floor",
    )
    rules = write_rules(tmp_path, needs_query)
    bad = write(tmp_path, "bad.css", "a { animation: spin 1s; }\n")
    good = write(
        tmp_path,
        "good.css",
        "a { animation: spin 1s; }\n"
        "@media (prefers-reduced-motion: reduce) { a { animation: none; } }\n",
    )
    untouched = write(tmp_path, "static.css", "a { color: red; }\n")
    assert lint(capsys, bad, "--rules", rules)[0] == 1
    assert lint(capsys, good, "--rules", rules)[0] == 0
    assert lint(capsys, untouched, "--rules", rules)[0] == 0


# --- html rules ---------------------------------------------------------------------

NEEDS_LANG = rule(
    "floor-lang",
    "required-element",
    {"tag": "html", "need_attr": "lang"},
    tier="floor",
    message="the page declares no language",
)
NEEDS_TITLE = rule(
    "floor-title",
    "required-element",
    {"tag": "title", "need_text": True},
    tier="floor",
    message="the page has no title",
)
HEADING_ORDER = rule(
    "floor-heading-order",
    "heading-order",
    {},
    tier="floor",
    message="a heading level is skipped",
)


def test_a_document_without_lang_fails_and_one_with_it_passes(tmp_path, capsys):
    rules = write_rules(tmp_path, NEEDS_LANG)
    bad = write(tmp_path, "bad.html", "<!doctype html>\n<html>\n<body></body>\n</html>\n")
    good = write(tmp_path, "good.html", "<!doctype html>\n<html lang=en>\n<body></body>\n</html>\n")
    code, out, _ = lint(capsys, bad, "--rules", rules)
    assert code == 1
    assert f"{bad}:2 floor-lang floor the page declares no language" in out
    assert lint(capsys, good, "--rules", rules)[0] == 0


def test_an_empty_title_is_a_missing_title(tmp_path, capsys):
    rules = write_rules(tmp_path, NEEDS_TITLE)
    empty = write(tmp_path, "empty.html", "<!doctype html><html lang=en><title> </title>")
    absent = write(tmp_path, "absent.html", "<!doctype html><html lang=en><body>x</body>")
    present = write(tmp_path, "present.html", "<!doctype html><html lang=en><title>Hello</title>")
    assert lint(capsys, empty, "--rules", rules)[0] == 1
    assert lint(capsys, absent, "--rules", rules)[0] == 1
    assert lint(capsys, present, "--rules", rules)[0] == 0


def test_a_fragment_is_not_asked_for_document_level_elements(tmp_path, capsys):
    rules = write_rules(tmp_path, NEEDS_LANG, NEEDS_TITLE)
    fragment = write(tmp_path, "part.html", "<section><h2>Part</h2></section>\n")
    assert lint(capsys, fragment, "--rules", rules)[0] == 0


def test_a_skipped_heading_level_is_reported_at_the_heading(tmp_path, capsys):
    rules = write_rules(tmp_path, HEADING_ORDER)
    bad = write(tmp_path, "bad.html", "<h1>A</h1>\n<h3>C</h3>\n")
    good = write(tmp_path, "good.html", "<h1>A</h1>\n<h2>B</h2>\n<h3>C</h3>\n<h2>D</h2>\n")
    code, out, _ = lint(capsys, bad, "--rules", rules)
    assert code == 1
    assert f"{bad}:2 floor-heading-order" in out
    assert "[h1 is followed by h3]" in out
    assert lint(capsys, good, "--rules", rules)[0] == 0


def test_a_document_that_opens_below_h1_says_so_in_plain_words(tmp_path, capsys):
    rules = write_rules(tmp_path, HEADING_ORDER)
    page = write(tmp_path, "index.html", "<!doctype html><html><body><h2>A</h2></body></html>")
    _, out, _ = lint(capsys, page, "--rules", rules)
    assert "[the document opens on h2]" in out
    assert "none" not in out


# --- copy rules ---------------------------------------------------------------------

VAGUE = rule(
    "taste-vague-copy",
    "phrase-list",
    {"phrases": ["seamless", "next level", "cutting-edge"]},
    message="vague superlative copy",
)


def test_a_listed_phrase_in_visible_text_is_reported_with_its_line(tmp_path, capsys):
    rules = write_rules(tmp_path, VAGUE)
    page = write(
        tmp_path,
        "index.html",
        "<p>Plain words.</p>\n<p>A <b>Seamless</b>\n experience that is cutting-edge.</p>\n",
    )
    code, out, _ = lint(capsys, page, "--rules", rules)
    assert code == 1
    assert f"{page}:2 taste-vague-copy" in out
    assert f"{page}:3 taste-vague-copy" in out


def test_a_listed_phrase_inside_markup_or_a_longer_word_is_not_copy(tmp_path, capsys):
    rules = write_rules(tmp_path, VAGUE)
    page = write(
        tmp_path,
        "index.html",
        '<p class="seamless" data-x="next level">Unseamlessly plain.</p>\n'
        "<script>var seamless = 1;</script>\n",
    )
    assert lint(capsys, page, "--rules", rules)[0] == 0


# --- waivers, judged rules, overrides, json and exit codes --------------------------

BODY_SIZE = rule(
    "floor-body-size",
    "number-below",
    {"property": "font-size", "selector": "^(html|body|p)$", "unit": "px", "minimum": 16},
    tier="floor",
    message="body text under the minimum size",
    stricter={"minimum": "higher"},
)
STOPS = rule(
    "taste-gradient-stops",
    "gradient-stops",
    {"max": 3},
    message="too many stops",
)
FIVE_STOPS = ".h { background: linear-gradient(to right, red, orange, yellow, green, teal); }\n"


def trio_project(tmp_path, decisions):
    rules = write_rules(tmp_path, TRANSITION_ALL, judged("floor-invented-proof"))
    css = write(tmp_path, "site.css", "a { transition: all 1s; }\n")
    record = write(tmp_path, "design-decisions.md", decisions)
    return rules, css, record


def test_a_taste_finding_with_a_reasoned_waiver_passes(tmp_path, capsys):
    rules, css, record = trio_project(
        tmp_path, "# Decisions\nwaive: taste-transition-all — one tiny control, reviewed\n"
    )
    code, out, _ = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 0
    assert "waived taste-transition-all: one tiny control, reviewed" in out
    assert "0 findings" in out


def test_a_waiver_without_a_reason_does_not_count(tmp_path, capsys):
    rules, css, record = trio_project(tmp_path, "waive: taste-transition-all\n")
    code, out, err = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 1
    assert "taste-transition-all" in out
    assert "gives no reason" in err


def test_a_floor_rule_cannot_be_waived(tmp_path, capsys):
    rules = write_rules(tmp_path, BODY_SIZE)
    css = write(tmp_path, "site.css", "p { font-size: 12px; }\n")
    record = write(tmp_path, "design-decisions.md", "waive: floor-body-size - it is a footnote\n")
    code, out, err = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 1
    assert f"{css}:1 floor-body-size floor" in out
    assert "floor-body-size is a floor rule and cannot be waived" in err


def test_an_unknown_rule_in_a_waiver_is_named_not_ignored_silently(tmp_path, capsys):
    rules, css, record = trio_project(tmp_path, "waive: taste-typo-id — because\n")
    code, _, err = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 1
    assert "taste-typo-id is not a rule in the table" in err


def test_judged_rules_are_listed_as_a_manual_checklist_and_never_fail(tmp_path, capsys):
    rules = write_rules(tmp_path, judged("floor-invented-proof", message="no invented proof"))
    css = write(tmp_path, "site.css", "a { color: red; }\n")
    code, out, _ = lint(capsys, css, "--rules", rules)
    assert code == 0
    assert "Manual checks" in out
    assert "floor-invented-proof floor no invented proof" in out


def body_override(tmp_path, capsys, line, size="17px", *extra):
    rules = write_rules(tmp_path, BODY_SIZE)
    css = write(tmp_path, "site.css", f"p {{ font-size: {size}; }}\n")
    record = write(tmp_path, "design-decisions.md", line + "\n")
    return lint(capsys, css, "--rules", rules, "--waivers", record, *extra)


def test_a_floor_override_may_make_the_rule_stricter(tmp_path, capsys):
    code, out, err = body_override(tmp_path, capsys, "override: floor-body-size minimum=18")
    assert code == 1
    assert "floor-body-size floor" in out
    assert "override floor-body-size minimum: 16 -> 18" in out
    assert err == ""


def test_a_floor_override_that_loosens_the_rule_is_refused_and_reported(tmp_path, capsys):
    code, out, err = body_override(tmp_path, capsys, "override: floor-body-size minimum=0", "10px")
    assert code == 1
    assert "floor-body-size floor" in out
    assert "override refused: floor-body-size minimum=0 would loosen a floor rule" in err
    assert "override floor-body-size" not in out


def test_a_refused_floor_override_is_in_the_json_refusals(tmp_path, capsys):
    code, out, _ = body_override(
        tmp_path, capsys, "override: floor-body-size minimum=14", "13px", "--json"
    )
    report = json.loads(out)
    assert code == 1
    assert report["overrides"] == []
    assert any("would loosen a floor rule" in note for note in report["refused"])


def test_a_floor_parameter_with_no_declared_direction_cannot_be_overridden(tmp_path, capsys):
    undeclared = rule(
        "floor-body-size",
        "number-below",
        {"property": "font-size", "selector": "^p$", "unit": "px", "minimum": 16},
        tier="floor",
    )
    rules = write_rules(tmp_path, undeclared)
    css = write(tmp_path, "site.css", "p { font-size: 17px; }\n")
    record = write(tmp_path, "design-decisions.md", "override: floor-body-size minimum=18\n")
    code, _, err = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 0
    assert "floor-body-size minimum=18 has no declared stricter direction" in err


def test_a_taste_override_may_go_either_way(tmp_path, capsys):
    rules = write_rules(tmp_path, STOPS)
    css = write(tmp_path, "site.css", FIVE_STOPS)
    looser = write(tmp_path, "looser.md", "override: taste-gradient-stops max=5\n")
    tighter = write(tmp_path, "tighter.md", "override: taste-gradient-stops max=2\n")
    assert lint(capsys, css, "--rules", rules)[0] == 1
    code, out, _ = lint(capsys, css, "--rules", rules, "--waivers", looser)
    assert code == 0
    assert "override taste-gradient-stops max: 3 -> 5" in out
    code, out, _ = lint(capsys, css, "--rules", rules, "--waivers", tighter)
    assert code == 1
    assert "override taste-gradient-stops max: 3 -> 2" in out


def test_every_applied_override_is_in_the_json_report(tmp_path, capsys):
    rules = write_rules(tmp_path, STOPS, BODY_SIZE)
    css = write(tmp_path, "site.css", FIVE_STOPS)
    record = write(
        tmp_path,
        "design-decisions.md",
        "override: taste-gradient-stops max=5\noverride: floor-body-size minimum=18\n",
    )
    _, out, _ = lint(capsys, css, "--rules", rules, "--waivers", record, "--json")
    assert json.loads(out)["overrides"] == [
        {"rule": "taste-gradient-stops", "parameter": "max", "old": 3, "new": 5},
        {"rule": "floor-body-size", "parameter": "minimum", "old": 16, "new": 18},
    ]


def test_a_chain_of_overrides_cannot_loosen_a_floor_rule_past_its_default(tmp_path, capsys):
    record = "override: floor-body-size minimum=20\noverride: floor-body-size minimum=12\n"
    code, _, err = body_override(tmp_path, capsys, record.strip(), "14px")
    assert code == 1
    assert "floor-body-size minimum=12 would loosen a floor rule" in err


@pytest.mark.parametrize(
    "value", ["nan", "inf", "-inf", "1e999", "-1", "abc", "2.5"], ids=lambda v: f"max={v}"
)
def test_an_override_value_that_is_not_usable_is_a_reported_refusal(tmp_path, capsys, value):
    rules = write_rules(tmp_path, STOPS)
    css = write(tmp_path, "site.css", FIVE_STOPS)
    record = write(tmp_path, "design-decisions.md", f"override: taste-gradient-stops max={value}\n")
    code, out, err = lint(capsys, css, "--rules", rules, "--waivers", record, "--json")
    assert code == 1
    assert "taste-gradient-stops" in out
    assert "override refused" in err
    assert json.loads(out)["overrides"] == []


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "1e999"])
def test_a_floor_override_with_a_bad_number_is_refused_and_the_default_stands(
    tmp_path, capsys, value
):
    code, out, err = body_override(
        tmp_path, capsys, f"override: floor-body-size minimum={value}", "14px"
    )
    assert code == 1
    assert "floor-body-size floor" in out
    assert "override refused" in err


def test_a_zero_count_override_never_divides_by_zero(tmp_path, capsys):
    record = write(tmp_path, "design-decisions.md", "override: taste-eyebrow-heading min_count=0\n")
    html = write(tmp_path, "index.html", "<p class='eyebrow'>x</p><p>No headings here.</p>")
    code, out, _ = lint(capsys, html, "--waivers", record)
    assert "taste-eyebrow-heading taste" not in out
    assert "0 findings" in out
    assert code in (0, 1)


def test_an_override_of_an_unknown_parameter_is_reported(tmp_path, capsys):
    rules = write_rules(tmp_path, BODY_SIZE)
    css = write(tmp_path, "site.css", "p { font-size: 14px; }\n")
    record = write(tmp_path, "design-decisions.md", "override: floor-body-size colour=14\n")
    code, _, err = lint(capsys, css, "--rules", rules, "--waivers", record)
    assert code == 1
    assert "floor-body-size has no parameter colour" in err


def test_json_output_has_a_stable_shape(tmp_path, capsys):
    rules, css, record = trio_project(tmp_path, "waive: taste-transition-all — checked\n")
    code, out, _ = lint(capsys, css, "--rules", rules, "--waivers", record, "--json")
    report = json.loads(out)
    assert code == 0
    assert set(report) == {"findings", "manual", "overrides", "refused", "summary"}
    finding = report["findings"][0]
    assert set(finding) == {"file", "line", "rule", "tier", "message", "detail", "waived", "reason"}
    assert (finding["rule"], finding["waived"], finding["reason"]) == (
        "taste-transition-all",
        True,
        "checked",
    )
    assert report["manual"] == [
        {"rule": "floor-invented-proof", "tier": "floor", "message": "check this by hand"}
    ]
    assert report["summary"] == {"floor": 0, "taste": 0, "waived": 1}


@pytest.mark.parametrize(
    "case",
    [
        "no-such-file",
        "wrong-suffix",
        "bad-rules",
        "unknown-check",
        "bad-waiver-file",
        "empty-dir",
        "missing-param",
        "bad-regex",
        "bad-optional-regex",
    ],
)
def test_unusable_input_exits_two_and_says_why(tmp_path, capsys, case):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    css = write(tmp_path, "site.css", "a { color: red; }\n")
    args = {
        "no-such-file": [tmp_path / "missing.css", "--rules", rules],
        "wrong-suffix": [write(tmp_path, "notes.txt", "x"), "--rules", rules],
        "bad-rules": [css, "--rules", write(tmp_path, "broken.json", "{not json")],
        "unknown-check": [
            css,
            "--rules",
            write_rules(
                tmp_path, {**TRANSITION_ALL, "check": "no-such-check"}, name="unknown.json"
            ),
        ],
        "bad-waiver-file": [css, "--rules", rules, "--waivers", tmp_path / "gone.md"],
        "missing-param": [
            css,
            "--rules",
            write_rules(
                tmp_path, {**TRANSITION_ALL, "params": {"value": "x"}}, name="missing.json"
            ),
        ],
        "bad-regex": [
            css,
            "--rules",
            write_rules(
                tmp_path, {**TRANSITION_ALL, "params": {"property": "(unclosed"}}, name="regex.json"
            ),
        ],
        "bad-optional-regex": [
            css,
            "--rules",
            write_rules(
                tmp_path,
                {**TRANSITION_ALL, "params": {"property": "transition", "selector": "[a"}},
                name="optional.json",
            ),
        ],
        "empty-dir": [tmp_path / "empty", "--rules", rules],
    }[case]
    (tmp_path / "empty").mkdir()
    code, out, err = lint(capsys, *args)
    assert code == 2
    assert out == ""
    assert err.startswith("unusable input: ")


def test_a_directory_is_read_for_every_page_file_in_it(tmp_path, capsys):
    rules = write_rules(tmp_path, TRANSITION_ALL)
    site = tmp_path / "site"
    (site / "css").mkdir(parents=True)
    (site / "css" / "a.css").write_text("a { transition: all 1s; }\n")
    (site / "readme.txt").write_text("transition: all")
    code, out, _ = lint(capsys, site, "--rules", rules)
    assert code == 1
    assert "a.css:1 taste-transition-all" in out


# --- the shipped rule table: a failing and a passing example for every mechanical rule -


def doc(body="", head="", lang='lang="en"'):
    return (
        f"<!doctype html>\n<html {lang}>\n<head><title>Studio</title>"
        f'<meta name="description" content="A studio.">{head}</head>\n'
        f"<body>{body}</body>\n</html>\n"
    )


def css(text):
    return {"site.css": text}


def page(**kw):
    return {"index.html": doc(**kw)}


FEATURE = '<div class="f">{}<h3>A</h3><p>Words.</p></div>'
SECTION = "<section><div><h2>A</h2><p>x</p><a href='#'>y</a></div></section>"

CASES = {
    "floor-lang": (page(lang=""), page()),
    "floor-title": (
        {"index.html": '<!doctype html><html lang="en"><head></head><body></body></html>'},
        page(),
    ),
    "floor-meta-description": (
        {"index.html": '<!doctype html><html lang="en"><head><title>t</title></head></html>'},
        page(),
    ),
    "floor-heading-order": (page(body="<h1>a</h1><h3>b</h3>"), page(body="<h1>a</h1><h2>b</h2>")),
    "floor-body-size": (css("p { font-size: 14px; }"), css("p { font-size: 1rem; }")),
    "floor-body-leading": (css("body { line-height: 1.1; }"), css("body { line-height: 1.5; }")),
    "floor-focus-visible": (
        page(body='<a href="/">x</a>', head="<style>a { color: red; }</style>"),
        page(
            body='<a href="/">x</a>',
            head="<style>a { color: red; } a:focus-visible { outline: 2px solid; }</style>",
        ),
    ),
    "floor-focus-border-width": (
        css("a:focus-visible { border: 4px solid red; }"),
        css("a:focus-visible { outline: 3px solid red; outline-offset: 2px; }"),
    ),
    "floor-reveal-hidden": (css(".reveal { opacity: 0; }"), css(".js .reveal { opacity: 0; }")),
    "floor-reduced-motion": (
        css("a { transition: color 0.2s; }"),
        css(
            "a { transition: color 0.2s; }\n"
            "@media (prefers-reduced-motion: reduce) { a { transition: none; } }"
        ),
    ),
    "floor-autoplay-muted": (
        page(body='<video autoplay loop src="a.mp4"></video>'),
        page(body='<video autoplay muted loop src="a.mp4"></video>'),
    ),
    "floor-lazy-largest": (
        page(
            body='<img src="a.jpg" width="1600" height="900" loading="lazy" alt="">'
            '<img src="b.jpg" width="100" height="100" alt="">'
        ),
        page(
            body='<img src="a.jpg" width="1600" height="900" alt="">'
            '<img src="b.jpg" width="100" height="100" loading="lazy" alt="">'
        ),
    ),
    "floor-hidden-overflow": (
        css("body { overflow-x: hidden; }"),
        css(".rail { overflow-x: auto; }"),
    ),
    "floor-viewport-width": (css(".band { width: 100vw; }"), css(".band { width: 100%; }")),
    "floor-placeholder-block": (
        page(body='<div class="placeholder"></div>'),
        page(body='<div class="photo"><img src="a.jpg" alt="A room"></div>'),
    ),
    "floor-placeholder-copy": (
        page(body="<p>Lorem ipsum dolor sit amet</p>"),
        page(body="<p>Rooms from May.</p>"),
    ),
    "taste-gradient-hue": (
        css(".h { background: linear-gradient(135deg, #7c3aed, #2563eb); }"),
        css(".h { background: linear-gradient(#f4efe6, #e9e1d3); }"),
    ),
    "taste-gradient-clip-text": (
        css("h1 { -webkit-background-clip: text; }"),
        css("h1 { color: var(--ink); }"),
    ),
    "taste-gradient-stops": (
        css(".h { background: linear-gradient(to right, red, orange, yellow, green); }"),
        css(".h { background: linear-gradient(to right, red, orange, yellow); }"),
    ),
    "taste-glow-halo": (css(".blob { filter: blur(80px); }"), css(".thumb { filter: blur(2px); }")),
    "taste-pure-black-white": (
        css("p { color: #000; }"),
        css(":root { --ink: #000; }\np { color: var(--ink); }"),
    ),
    "taste-literal-colours": (css("p { color: #3a5; }"), css("p { color: var(--ink); }")),
    "taste-literal-fonts": (
        css("p { font-family: Georgia, serif; }"),
        css("p { font-family: var(--body); }"),
    ),
    "taste-system-display-face": (
        css("h1 { font-family: system-ui, sans-serif; }"),
        css('h1 { font-family: "Display Serif", serif; }'),
    ),
    "taste-family-count": (
        css(
            "h1 { font-family: A; } h2 { font-family: B; } p { font-family: C; }"
            " b { font-family: D; }"
        ),
        css("h1 { font-family: A; } h2 { font-family: B; } p { font-family: C; }"),
    ),
    "taste-weight-count": (
        css(
            "h1 { font-weight: 300; } h2 { font-weight: 400; }"
            " h3 { font-weight: 600; } b { font-weight: 800; }"
        ),
        css("h1 { font-weight: 400; } b { font-weight: 700; }"),
    ),
    "taste-transition-all": (
        css("a { transition: all 0.2s; }"),
        css("a { transition: color 0.2s; }"),
    ),
    "taste-transition-layout": (
        css(".panel { transition: width 0.3s; }"),
        css(".panel { transition: opacity 0.3s; }"),
    ),
    "taste-bounce-easing": (
        css(".btn { transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1); }"),
        css(".btn { transition-timing-function: ease-out; }"),
    ),
    "taste-hover-lift": (
        css(".card:hover { transform: translateY(-6px); }"),
        css(".card:hover { background: var(--step-2); }"),
    ),
    "taste-hero-vh": (css(".hero { min-height: 100vh; }"), css(".hero { min-height: 100svh; }")),
    "taste-nested-card": (
        page(body='<div class="card"><div class="card">x</div></div>'),
        page(body='<div class="card">x</div><div class="card">y</div>'),
    ),
    "taste-card-trio": (
        page(body='<div class="row">' + FEATURE.format("<svg></svg>") * 3 + "</div>"),
        page(body='<div class="row">' + FEATURE.format("") * 3 + "</div>"),
    ),
    "taste-eyebrow-heading": (
        page(body='<p class="eyebrow">A</p><h2>X</h2>' * 3),
        page(body='<p class="eyebrow">A</p><h2>X</h2><h2>Y</h2><h2>Z</h2>'),
    ),
    "taste-emoji-icon": (
        page(body="<ul><li>🚀 Fast</li></ul>"),
        page(body="<ul><li>Fast</li></ul>"),
    ),
    "taste-icon-sets": (
        page(
            head='<link rel="stylesheet" href="/v/outline-icons.css">'
            '<link rel="stylesheet" href="/v/solid-icons.css">'
        ),
        page(
            head='<link rel="icon" href="/favicon.svg">'
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            '<link rel="stylesheet" href="/v/outline-icons.css">'
        ),
    ),
    "taste-repeated-sections": (
        page(body=SECTION * 2),
        page(body=SECTION + "<section><blockquote>q</blockquote></section>"),
    ),
    "taste-email-close": (
        page(body='<section><h2>A</h2></section><section><input type="email"></section>'),
        page(body='<section><input type="email"></section><section><h2>A</h2></section>'),
    ),
    "taste-vague-copy": (
        page(body="<p>A seamless platform</p>"),
        page(body="<p>Rooms from May.</p>"),
    ),
}


def found_ids(tmp_path, capsys, files):
    paths = []
    for name, text in files.items():
        paths.append(write(tmp_path, name, text))
    _, out, _ = lint(capsys, *paths, "--json")
    return {f["rule"] for f in json.loads(out)["findings"]}


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_the_shipped_rule_fires_on_its_bad_example_and_not_its_good_one(rule_id, tmp_path, capsys):
    bad, good = CASES[rule_id]
    (tmp_path / "bad").mkdir()
    (tmp_path / "good").mkdir()
    assert rule_id in found_ids(tmp_path / "bad", capsys, bad)
    assert rule_id not in found_ids(tmp_path / "good", capsys, good)


EXTRA_GOOD = {
    "floor-reveal-hidden": [
        css("@media (scripting: enabled) { .reveal { opacity: 0; } }"),
        css(".reveal { @media (scripting: enabled) { opacity: 0; } }"),
        css("@media screen and (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@media only screen and (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@media (scripting: enabled) and (min-width: 600px) { .reveal { opacity: 0; } }"),
        css("@media (min-width: 600px) and (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@MEDIA  (  SCRIPTING :  ENABLED  ) { .reveal { opacity: 0; } }"),
        css("@supports (display: grid) { @media (scripting: enabled) { .reveal { opacity: 0 } } }"),
        css("@media (scripting: enabled) { @media (min-width: 40em) { .reveal { opacity: 0 } } }"),
        css(".js .reveal, html.js .fade-in { opacity: 0 }"),
        css(".js .reveal { opacity: 0 !important }"),
        css(".reveal { opacity: 0.5 }"),
        css(".reveal { opacity: 1 }"),
    ],
    "floor-body-size": [
        css("body { font-size: 16px !important }"),
        css("body { font-size: 1rem }"),
    ],
    "floor-hidden-overflow": [
        css("body { overflow: auto hidden }"),
        css("body { overflow-y: hidden }"),
        css(".x { overflow-x: hidden }"),
    ],
    "taste-icon-sets": [
        page(
            head='<link rel="icon" href="/favicon.svg">'
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
        ),
    ],
    "taste-pure-black-white": [css(".p { background-image: url(white-paper.png); }")],
    "taste-emoji-icon": [
        page(body="<ul><li>\u2713 Included</li><li>\u2717 Not included</li></ul>")
    ],
    "taste-hero-vh": [css(".hero { min-height: 100vh; min-height: 100svh; }")],
}
EXTRA_BAD = {
    "floor-reveal-hidden": [
        css("@media (scripting: none) { .reveal { opacity: 0; } }"),
        css("@media not (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@media not all and (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@media print, (scripting: enabled) { .fade-in { opacity: 0; } }"),
        css("@media (scripting: enabled), print { .fade-in { opacity: 0; } }"),
        css("@media print and (scripting: enabled) { .reveal { opacity: 0; } }"),
        css("@media (scripting: enabled) or (min-width: 1px) { .reveal { opacity: 0; } }"),
        css("@media (scripting: initial-only) { .reveal { opacity: 0; } }"),
        css("@media (not (scripting: enabled)) { .reveal { opacity: 0; } }"),
        css("@media (scripting: enabledx) { .reveal { opacity: 0; } }"),
        css("@supports (scripting: enabled) { .reveal { opacity: 0; } }"),
        css(
            "@media not (scripting: enabled) { @media (min-width: 1px) { .reveal { opacity: 0 } } }"
        ),
        css(".reveal { opacity: 0 !important; }"),
        css(".reveal { opacity: 0!important; }"),
        css(".reveal { opacity: 0 ! IMPORTANT ; }"),
        css(".reveal { opacity: 0% }"),
        css(".reveal { opacity: .0 }"),
        css(".reveal { opacity: 00 }"),
        css(".reveal { opacity: +0 }"),
        css(".reveal { opacity: 0.0% }"),
        css(".reveal { OPACITY: 0 }"),
        css(".reveal { opacity: /* x */ 0 }"),
        css("html:not(.js) .reveal { opacity: 0 }"),
        css(".reveal:not(.js) { opacity: 0 }"),
        css(".reveal, .js .x { opacity: 0 }"),
        css(".reveal,.js { opacity: 0 }"),
        css(".reveal:not(.js), .js .other { opacity: 0 }"),
    ],
    "floor-reduced-motion": [
        css("a { -webkit-transition: color 1s }"),
        css("a { -webkit-animation: x 1s }"),
        css("a { color: red } /* prefers-reduced-motion */ a { transition: color 1s }"),
    ],
    "floor-body-size": [
        css("body { font-size: 12px !important }"),
        css("body { font-size: 12px!important }"),
        css("html, .x { font-size: 12px }"),
        css("BODY { FONT-SIZE: 12PX }"),
        css("body { font-size: /* c */ 0.5rem }"),
    ],
    "floor-body-leading": [
        css("body { line-height: 1.1 !important }"),
        css("p { line-height: 1 ! important }"),
    ],
    "floor-hidden-overflow": [
        css("body { overflow-x: hidden !important }"),
        css("body { overflow: hidden auto }"),
        css("body { overflow: clip hidden }"),
        css("html { overflow-x: clip }"),
        css("body { overflow: hidden !important }"),
        css("html, .a { overflow-x: hidden }"),
    ],
    "taste-hover-lift": [css(".card { &:hover { transform: translateY(-4px); } }")],
    "taste-gradient-hue": [
        css(".h { background: linear-gradient(135deg, rgb(124, 58, 237), rgb(37, 99, 235)); }"),
        css(".h { background: linear-gradient(rgba(124 58 237 / 0.9), rgb(80% 20% 90%)); }"),
    ],
    "taste-icon-sets": [
        page(
            head='<link rel="stylesheet" href="/v/outline-icons.css">'
            '<script src="/v/solid-icons.js"></script>'
        ),
    ],
    "taste-emoji-icon": [
        page(body="<ul><li>\u2705 Done</li></ul>"),
        page(body="<ul><li>\u2764\ufe0f Loved</li></ul>"),
        page(body="<ul><li>\U0001f1fa\U0001f1f8 United States</li></ul>"),
    ],
    "taste-hero-vh": [css(".hero { min-height: 100vh; }\n.hero { max-height: 100svh; }")],
}


@pytest.mark.parametrize("rule_id", sorted(EXTRA_GOOD))
def test_the_shipped_rule_stays_quiet_on_its_extra_good_examples(rule_id, tmp_path, capsys):
    for index, files in enumerate(EXTRA_GOOD[rule_id]):
        folder = tmp_path / str(index)
        folder.mkdir()
        assert rule_id not in found_ids(folder, capsys, files)


@pytest.mark.parametrize("rule_id", sorted(EXTRA_BAD))
def test_the_shipped_rule_fires_on_its_extra_bad_examples(rule_id, tmp_path, capsys):
    for index, files in enumerate(EXTRA_BAD[rule_id]):
        folder = tmp_path / str(index)
        folder.mkdir()
        assert rule_id in found_ids(folder, capsys, files)


def test_a_nested_rule_is_read_under_the_selector_it_applies_to(tmp_path, capsys):
    sheet = write(tmp_path, "site.css", ".card { color: red; &:hover { color: blue; } }")
    decls = page_lint.parse_css(sheet.read_text(), "site.css")
    assert [(d.selector, d.prop) for d in decls] == [(".card", "color"), (".card:hover", "color")]


@pytest.mark.parametrize("bad", ["x", None, True, [16], {"a": 1}])
def test_a_numeric_parameter_that_is_not_a_number_is_an_unusable_table(tmp_path, capsys, bad):
    broken = rule(
        "floor-body-size",
        "number-below",
        {"property": "font-size", "selector": "^p$", "unit": "px", "minimum": bad},
        tier="floor",
    )
    rules = write_rules(tmp_path, broken)
    css_file = write(tmp_path, "site.css", "p { font-size: 12px; }\n")
    code, _, err = lint(capsys, css_file, "--rules", rules)
    assert code == 2
    assert "minimum" in err


def test_a_declaration_value_loses_its_important_flag_once_at_parse(tmp_path):
    decls = page_lint.parse_css("p { a: 1 !important; b: 2!IMPORTANT; c: 3 ! important ; }", "s")
    assert [d.value for d in decls] == ["1", "2", "3"]


def test_every_numeric_floor_parameter_declares_which_way_is_stricter():
    for entry in shipped_rules():
        if entry["tier"] != "floor" or entry["kind"] == "judged":
            continue
        numeric = {
            k for k, v in entry["params"].items() if isinstance(v, (int, float)) and v is not True
        }
        assert numeric <= set(entry.get("stricter", {})), entry["id"]


def shipped_rules():
    return json.loads((SKILL / "assets/rules.json").read_text())["rules"]


def test_every_mechanical_rule_in_the_table_has_an_example():
    mechanical = {r["id"] for r in shipped_rules() if r["kind"] != "judged"}
    assert mechanical == set(CASES)


def test_the_table_covers_all_three_mechanical_kinds_and_both_tiers():
    rules = shipped_rules()
    assert {r["kind"] for r in rules} == {"css", "html", "copy", "judged"}
    assert {r["tier"] for r in rules} == {"floor", "taste"}


CLEAN_CSS = """
:root {
  --paper: oklch(96% 0.01 85);
  --ink: oklch(22% 0.02 60);
  --accent: oklch(55% 0.17 40);
  --display: "Display Serif", Georgia, serif;
  --body: "Body Sans", system-ui, sans-serif;
}
body { background: var(--paper); color: var(--ink); font: 1.0625rem/1.6 var(--body); }
h1, h2 { font-family: var(--display); font-weight: 700; }
.hero { min-height: 100svh; }
a { color: var(--accent); transition: color 0.2s ease-out; }
a:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { a { transition: none; } }
"""
CLEAN_HTML = doc(
    body='<header class="hero"><h1>Tide tables for the north shore</h1></header>'
    "<main><section><h2>Printed each spring</h2><p>Four pages, folded once.</p>"
    '<a href="/order">Order the 2027 table</a></section></main>'
)


def test_a_clean_page_has_no_finding_from_the_shipped_table(tmp_path, capsys):
    html = write(tmp_path, "index.html", CLEAN_HTML)
    sheet = write(tmp_path, "site.css", CLEAN_CSS)
    code, out, _ = lint(capsys, html, sheet)
    assert code == 0
    assert "0 findings" in out
    assert "Manual checks" in out


# --- the human-readable list and the table cannot drift -----------------------------


def rules_md_sections():
    text = (SKILL / "references/rules.md").read_text()
    floor, _, taste = text.partition("\n## Taste rules")
    return floor, taste


def test_every_rule_id_in_the_table_is_in_rules_md_under_its_own_tier():
    floor_part, taste_part = rules_md_sections()
    for entry in shipped_rules():
        part = floor_part if entry["tier"] == "floor" else taste_part
        assert f"`{entry['id']}`" in part, f"{entry['id']} is not listed under {entry['tier']}"


def test_rules_md_lists_no_rule_the_table_lacks():
    listed = set(
        re.findall(r"^### `((?:floor|taste)-[a-z0-9-]+)`", "".join(rules_md_sections()), re.M)
    )
    assert listed == {r["id"] for r in shipped_rules()}


def test_the_default_run_uses_the_shipped_table_and_lists_its_manual_checks(tmp_path, capsys):
    sheet = write(tmp_path, "site.css", "p { font-size: 12px; }\n")
    code, out, _ = lint(capsys, sheet)
    assert code == 1
    assert "floor-body-size" in out
    assert "floor-invented-proof floor" in out


def test_the_unfilled_decision_template_declares_no_waiver_or_override():
    decisions = page_lint.parse_decisions((SKILL / "assets/decisions-template.md").read_text())
    assert decisions.waivers == {}
    assert decisions.overrides == []


# --- review fixes: :root, viewport units, pt, :not(.no-js), icon kits ------------------


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        ("floor-body-size", ":root { font-size: 12px }"),
        ("floor-body-size", "p { font-size: 11pt }"),
        ("floor-body-leading", ":root { line-height: 1.1 }"),
        ("floor-hidden-overflow", ":root { overflow-x: hidden }"),
        ("floor-viewport-width", ".a { width: 100dvw }"),
        ("floor-viewport-width", ".a { min-width: 100SVW }"),
        ("floor-viewport-width", ".a { max-width: 100lvw }"),
    ],
)
def test_review_fixes_fire(rule_id, text, tmp_path, capsys):
    assert rule_id in found_ids(tmp_path, capsys, css(text))


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        ("floor-body-size", "p { font-size: 12pt }"),
        ("floor-body-size", ":root { font-size: 16px }"),
        ("floor-viewport-width", ".a { width: 100dvh }"),
        ("floor-reveal-hidden", "html:not(.no-js) [data-aos] { opacity: 0 }"),
        ("floor-reveal-hidden", "html:not( .no-js ) .reveal { opacity: 0 }"),
        ("floor-reveal-hidden", ":root:not(.no-js) .reveal { opacity: 0 }"),
    ],
)
def test_review_fixes_stay_quiet(rule_id, text, tmp_path, capsys):
    assert rule_id not in found_ids(tmp_path, capsys, css(text))


def test_other_not_markers_still_do_not_excuse_a_reveal(tmp_path, capsys):
    text = ".reveal:not(.js) { opacity: 0 } html:not(.other) .reveal { opacity: 0 }"
    assert "floor-reveal-hidden" in found_ids(tmp_path, capsys, css(text))


@pytest.mark.parametrize(
    "head",
    [
        '<script src="https://kit.fontawesome.com/abc123.js"></script>'
        '<link rel="stylesheet" href="/v/outline-icons.css">',
        '<script src="https://unpkg.com/lucide@latest"></script>'
        '<link rel="stylesheet" href="/v/outline-icons.css">',
        '<script src="/node_modules/lucide-static/font/lucide.js"></script>'
        '<link rel="stylesheet" href="/v/outline-icons.css">',
    ],
)
def test_icon_kits_count_as_icon_sets(head, tmp_path, capsys):
    assert "taste-icon-sets" in found_ids(tmp_path, capsys, page(head=head))


def test_no_js_under_not_counts_only_on_the_root_element(tmp_path, capsys):
    # .no-js sits on <html>; on the revealed element itself it says nothing about scripts
    text = ".reveal:not(.no-js) { opacity: 0 }"
    assert "floor-reveal-hidden" in found_ids(tmp_path, capsys, css(text))
