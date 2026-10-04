"""The renderer shows repository text on a public page, so safety is the first thing tested.

Each hostile case asserts on the output as a whole: a tag that is merely escaped is fine,
a live one is not, and no `href` may carry anything but an allowed scheme or a fragment.
"""

from __future__ import annotations

import re
import time

import pytest

from tests.conftest import load_script

md = load_script("site_markdown.py")

BLOB = "https://github.com/greenblacked/AI/blob/main"


def hrefs(markup: str) -> list[str]:
    return re.findall(r'href="([^"]*)"', markup)


def test_headings_take_slug_ids_and_a_level_offset():
    out = md.render("# Top\n\n## Second `code` heading\n\n###### Deep", offset=1)
    assert '<h2 id="top">Top</h2>' in out
    assert '<h3 id="second-code-heading">Second <code>code</code> heading</h3>' in out
    # Offsets stop at h6 rather than inventing h7.
    assert '<h6 id="deep">Deep</h6>' in out
    assert md.render("#hashtag") == "<p>#hashtag</p>"
    assert md.render("# Closed ##") == '<h1 id="closed">Closed</h1>'
    assert md.render("#") == '<h1 id="section"></h1>'


def test_duplicate_slugs_are_numbered_and_reserved_ids_are_never_taken():
    out = md.render("## Same\n\n## Same\n\n## Same\n\n## Home\n\n## Find")
    assert 'id="same"' in out and 'id="same-1"' in out and 'id="same-2"' in out
    assert 'id="home"' not in out and 'id="home-1"' in out
    assert 'id="find"' not in out
    # One Slugs shared across calls keeps ids unique across a whole page.
    slugs = md.Slugs()
    first = md.render("## Part", slugs=slugs)
    second = md.render("## Part", slugs=slugs)
    assert 'id="part"' in first and 'id="part-1"' in second
    assert md.slugify("What a real week looks like") == "what-a-real-week-looks-like"


def test_paragraphs_join_lines_and_keep_a_two_space_break():
    out = md.render("one\ntwo  \nthree\n\nnext")
    assert out == "<p>one\ntwo<br>\nthree</p>\n<p>next</p>"


def test_fenced_code_is_escaped_and_the_language_is_sanitised():
    out = md.render("```Py{1} extra\n<b>x</b>\n  indented\n```\n\n~~~\ntilde\n~~~")
    assert '<code class="language-py1">&lt;b&gt;x&lt;/b&gt;\n  indented\n</code>' in out
    assert "<code>tilde\n</code>" in out
    assert "<b>" not in out
    hostile = md.render('```"><script>alert(1)</script>\nx\n```')
    assert "<script" not in hostile
    assert '<code class="language-scriptalert1script">' in hostile
    # A fence is closed only by a run at least as long, of the same character.
    assert "a\n```\nb" in md.render("````\na\n```\nb\n````")
    assert "x" in md.render("```\nunclosed fence\n")
    # An indented opener removes that much indentation from the body.
    assert "<code>code\n</code>" in md.render("  ```\n  code\n  ```")
    # A backtick fence cannot carry a backtick in its info string: that is inline code.
    assert "<pre" not in md.render("``` a`b")


def test_indented_code_blocks_are_literal():
    out = md.render("para\n\n    <i>code</i>\n\n    more\n\nafter")
    assert "<pre" in out and "&lt;i&gt;code&lt;/i&gt;\n\nmore" in out
    assert "<p>after</p>" in out


def test_lists_nest_and_distinguish_tight_from_loose():
    out = md.render("- a\n- b\n  - c\n  - d\n- e")
    assert out.count("<ul>") == 2
    assert "<li>a</li>" in out and "<p>" not in out
    loose = md.render("- a\n\n- b")
    assert "<li><p>a</p></li>" in loose
    ordered = md.render("3. x\n4. y")
    assert ordered.startswith('<ol start="3">') and "<li>x</li>" in ordered
    assert md.render("1) x\n2) y").startswith("<ol>")
    # A different marker starts a different list.
    assert md.render("- a\n* b").count("<ul>") == 2
    assert md.render("- a\n1. b").count("<ol>") == 1
    # A continuation paragraph and a code block belong to their item.
    item = md.render("- first\n\n  second\n\n  ```\n  code\n  ```\n- next")
    assert item.count("<li>") == 2 and "<p>second</p>" in item and "<pre" in item
    # A lazy continuation joins the item's paragraph; a fence does not get one.
    assert "a\nb" in md.render("- a\nb")
    assert md.render("-\n  x").count("<li>") == 1
    assert md.render("-     code in item").count("<li>") == 1


def test_a_list_may_interrupt_a_paragraph_only_as_commonmark_allows():
    assert "<ul>" in md.render("text\n- item")
    assert "<ol>" in md.render("text\n1. item")
    assert "<ol>" not in md.render("text\n2. item")


def test_block_quotes_nest_and_continue_lazily():
    out = md.render("> a\n> > b\ncontinued\n\n> - c")
    assert out.count("<blockquote>") == 3
    assert "b\ncontinued" in out
    assert "<li>c</li>" in out


def test_tables_align_pad_and_split_on_unescaped_pipes_only():
    out = md.render("| A | B | C |\n|:--|:-:|--:|\n| 1 | `x\\|y` | z \\| w |\n| only |")
    assert out.count("<tr>") == 3
    assert "<th>A</th>" in out and '<th class="al-c">B</th>' in out
    assert '<th class="al-r">C</th>' in out
    assert "<code>x|y</code>" in out and "z | w" in out
    assert '<td>only</td><td class="al-c"></td>' in out
    # Rows stop at a blank line; a header without a matching delimiter is a paragraph.
    assert "<p>after</p>" in md.render("a | b\n--|--\n1 | 2\n\nafter".replace("after", "after"))
    assert "<table>" not in md.render("a | b\n--|--|--\n1 | 2")
    assert "<table>" not in md.render("a | b\nnot a delimiter")
    cells = md._split_cells("| a | `p|q` | |")
    assert cells == ["a", "`p|q`", ""]
    assert md._split_cells("`open | x") == ["`open", "x"]
    assert md.render("x | y\n--|--\n1 | 2").count("<table>") == 1


def test_a_table_interrupts_a_paragraph_and_a_thematic_break_is_a_rule():
    out = md.render("intro\n| a | b |\n| - | - |\n| 1 | 2 |\n\n---\n\n***\n\n___")
    assert "<table>" in out and out.count("<hr>") == 3


def test_inline_code_emphasis_and_escapes():
    out = md.render("`a<b>` ``x ` y`` **bold** *em* _em_ ***both*** snake_case_name 2*3*4")
    assert "<code>a&lt;b&gt;</code>" in out and "<code>x ` y</code>" in out
    assert "<strong>bold</strong>" in out and out.count("<em>em</em>") == 2
    assert "<strong><em>both</em></strong>" in out
    assert "snake_case_name" in out and "<em>3</em>" in out
    assert md.render(r"\*not\* \`x\` \q") == "<p>*not* `x` \\q</p>"
    assert md.render("**a *b***") == "<p><strong>a <em>b</em></strong></p>"
    assert md.render("` x `") == "<p><code>x</code></p>"
    assert md.render("`unclosed") == "<p>`unclosed</p>"
    assert md.render("** nope **") == "<p>** nope **</p>"
    assert md.render("****x****") == "<p>****x****</p>"
    assert md.render("*a `*` b*") == "<p><em>a <code>*</code> b</em></p>"
    assert md.render("*a \\* b*") == "<p><em>a * b</em></p>"
    assert md.render("_a_b c_") == "<p><em>a_b c</em></p>"
    assert md.render("trailing *") == "<p>trailing *</p>"


def test_unmatched_delimiters_do_not_cost_a_scan_each():
    started = time.monotonic()
    out = md.render("* " * 20000)
    assert out.count("<em>") == 0
    assert time.monotonic() - started < 5
    huge = md.render("x" * (md.MAX_INLINE + 1) + " <b>")
    assert "<b>" not in huge and "&lt;b&gt;" in huge


def test_links_images_and_autolinks():
    out = md.render(
        "[a](https://e.com/x?y=1&z=2) [b](<http://e.com/a b>) [c](#frag) [d](mailto:x@y.z) "
        '[t](https://e.com "title") ![alt](https://e.com/i.png) ![](https://e.com/j.png) '
        "<https://auto.example/x> [nested [brackets]](https://e.com) [`code`](https://e.com)"
    )
    assert "https://e.com/x?y=1&amp;z=2" in out
    assert "#frag" in out and "mailto:x@y.z" in out
    assert '<a href="https://e.com/i.png" rel="noopener noreferrer">alt</a>' in out
    assert ">https://e.com/j.png</a>" in out
    assert "<img" not in out
    assert ">https://auto.example/x</a>" in out
    assert "nested [brackets]" in out and "<code>code</code></a>" in out
    assert md.render("[unfinished](https://e.com") == "<p>[unfinished](https://e.com</p>"
    assert md.render("[only text]") == "<p>[only text]</p>"
    assert md.render("[a](<b") == "<p>[a](&lt;b</p>"
    assert md.render("[a](b 'c") == "<p>[a](b &#x27;c</p>"
    assert md.render("!x ![y") == "<p>!x ![y</p>"
    assert md.render("[a](x (y))").count("<a ") == 1


def test_links_inside_link_text_are_not_nested():
    out = md.render("[outer [inner](https://a.example)](https://b.example)")
    assert out.count("<a ") == 1 and "https://b.example" in out


@pytest.mark.parametrize(
    "target",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        " javascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "\x01javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "ftp://example.com/x",
        "//evil.example/x",
        "../../../../../x",
        "../../../../../../etc/passwd",
        "/../../etc/passwd",
        "a/../../../../../../x",
        "%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/x",
        "",
        "c:\\windows",
    ],
)
def test_dangerous_or_escaping_targets_render_as_text_only(target):
    out = md.render(f"[label](<{target}>)", source_dir="plugins/p/skills/s")
    assert "<a " not in out and "href" not in out, out
    assert md.rewrite_href(target, "plugins/p/skills/s") is None


@pytest.mark.parametrize(
    "target",
    [
        "jav&#x61;script:alert(1)",
        "\\\\evil.example\\x",
        "javascript%3Aalert(1)",
        "a/../../../x",
        "..\\..\\..\\..\\x",
        "%2e%2e/%2e%2e/%2e%2e/%2e%2e/x",
    ],
)
def test_odd_targets_that_stay_inside_the_repository_become_github_links(target):
    out = md.render(f"[label](<{target}>)", source_dir="plugins/p/skills/s")
    assert hrefs(out) and all(h.startswith(BLOB + "/") for h in hrefs(out)), out
    assert "javascript:" not in out.lower()


def test_unsafe_autolinks_and_raw_html_are_text():
    out = md.render("<javascript:alert(1)> <script>alert(1)</script> <img src=x onerror=y>")
    assert "<script" not in out and "<img" not in out and "<a " not in out
    assert "&lt;script&gt;" in out and "&lt;img src=x onerror=y&gt;" in out
    block = md.render("<div onclick=x>\nhello\n</div>\n\n<!-- hidden -->")
    assert "<div" not in block and "&lt;div" in block and "&lt;!-- hidden --&gt;" in block
    # Quotes in a label or title cannot break out of an attribute.
    quoted = md.render('[x" onmouseover="alert(1)](https://e.com/"onfocus="y)')
    assert 'onmouseover="' not in quoted
    for href in hrefs(quoted):
        assert '"' not in href


def test_relative_paths_resolve_against_the_source_directory():
    where = "plugins/p/skills/s"
    assert md.rewrite_href("references/a.md", where) == f"{BLOB}/{where}/references/a.md"
    assert md.rewrite_href("./references/a.md#sec", where) == f"{BLOB}/{where}/references/a.md#sec"
    assert md.rewrite_href("../t/SKILL.md", where) == f"{BLOB}/plugins/p/skills/t/SKILL.md"
    assert md.rewrite_href("../../../../README.md", where) == f"{BLOB}/README.md"
    assert md.rewrite_href("/docs/ci.md", where) == f"{BLOB}/docs/ci.md"
    assert md.rewrite_href("docs/", "") == f"{BLOB}/docs/"
    assert md.rewrite_href("a b/c d.md?x=1", "") == f"{BLOB}/a%20b/c%20d.md"
    assert md.rewrite_href(" https://e.com/a b ") == "https://e.com/a%20b"
    assert md.rewrite_href("../../../../../x", where) is None
    assert md.rewrite_href("../x", "") is None
    assert md.rewrite_href("#only", where) == "#only"
    assert md.rewrite_href("x.md#", where) == f"{BLOB}/{where}/x.md"
    assert md.rewrite_href("HTTPS://E.com/x", where) == "HTTPS://E.com/x"
    assert md.rewrite_href("#", where) == "#"
    assert md.rewrite_href(".", where) == f"{BLOB}/{where}"
    assert md.rewrite_href("..", "") is None
    # A backslash is a separator to a browser, so it cannot be used to climb out.
    assert md.rewrite_href("..\\..\\..\\..\\..\\x", where) is None


def test_deep_nesting_is_bounded():
    out = md.render(">" * 5000 + " deep")
    assert "deep" in out
    assert out.count("<blockquote>") == md.MAX_DEPTH
    items = md.render("".join("  " * n + "- x\n" for n in range(40)))
    assert items.count("<ul>") <= md.MAX_DEPTH + 1


def test_tabs_and_carriage_returns_are_normalised():
    out = md.render("- a\r\n\t- b\r\n")
    assert out.count("<ul>") == 2


def test_plain_text_strips_tags_and_unescapes():
    assert md.plain_text("a <code>&lt;b&gt;</code> c") == "a <b> c"
