"""The catalogue site, driven in a real browser the way a person uses it.

The other site tests read the built HTML and the stylesheet as text, which can say that
a rule or a line of script exists but not that the page behaves: that Back returns to
the page you came from, that the bar and To top appear when they should and get out of
the way when they should not, that a jump to a heading is not hidden under them, that
the theme you chose survives a reload, or that the finder finds. These load the real
catalogue, built once from this repository, in Chromium, act on it and assert what a
person would see: URLs, computed visibility, boxes on screen, focus and storage.

They need the `playwright` package and a browser. CI's `site-browser` job installs the
package and uses the runner's own Chrome (`BROWSER_CHANNEL=chrome`), so nothing is
downloaded; locally, point `BROWSER_EXECUTABLE` at any Chromium. Without the package the
module is skipped, unless `REQUIRE_BROWSER=1`, which the CI job sets so these can never
pass by not running.
"""

from __future__ import annotations

import functools
import http.server
import os
import re
import threading
from pathlib import Path

import pytest

from tests.conftest import REPO, load_script

pytestmark = pytest.mark.browser

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    if os.environ.get("REQUIRE_BROWSER") == "1":
        raise
    pytest.skip(
        "playwright is not installed; CI's site-browser job runs these",
        allow_module_level=True,
    )

site = load_script("build_catalogue_site.py")

# The longest skill page in the catalogue, so there is room to scroll in both directions.
LONG = max(REPO.glob("plugins/*/skills/*/SKILL.md"), key=lambda p: p.stat().st_size)
PLUGIN_PATH = f"/plugins/{LONG.parents[2].name}/"
SKILL_PATH = f"{PLUGIN_PATH}{LONG.parent.name}/"
# The size the site promises for its own controls: Material's and Apple's 44px floor.
TARGET = 44


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # the suite's output is the assertions, not a log
        pass


@pytest.fixture(scope="session")
def built(tmp_path_factory) -> Path:
    output = tmp_path_factory.mktemp("browser") / "site"
    site.build(REPO, output, "v0")
    return output


@pytest.fixture(scope="session")
def base_url(built):
    handler = functools.partial(_Quiet, directory=str(built))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def browser():
    options = {}
    if os.environ.get("BROWSER_CHANNEL"):
        options["channel"] = os.environ["BROWSER_CHANNEL"]
    if os.environ.get("BROWSER_EXECUTABLE"):
        options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
    with sync_playwright() as playwright:
        launched = playwright.chromium.launch(**options)
        yield launched
        launched.close()


def new_context(browser, base_url: str, width: int = 1280):
    """A fresh profile: no history, no storage, nothing fetched from outside.

    Reduced motion turns the page's own transitions and smooth scrolling off, so what a
    test reads is the settled state rather than a frame of an animation. Requests that
    leave the local server, the web fonts, are refused, so no test waits on the network
    or changes with it; the fallback font is what is measured.
    """
    made = browser.new_context(viewport={"width": width, "height": 800}, reduced_motion="reduce")
    # Anchored on the server's own origin and a slash, so neither another local port
    # nor a userinfo trick such as http://127.0.0.1:1@elsewhere/ gets through.
    made.route(re.compile("^(?!" + re.escape(base_url) + "/)"), lambda route: route.abort())
    return made


@pytest.fixture
def context(browser, base_url):
    made = new_context(browser, base_url)
    yield made
    made.close()


@pytest.fixture
def page(context):
    return context.new_page()


def settle(page):
    """Wait two frames, so scroll handlers have run and styles have been recomputed."""
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def scroll_to(page, y: int) -> None:
    page.evaluate("y => window.scrollTo(0, y)", y)
    page.wait_for_function(
        "y => Math.abs(window.scrollY - Math.min(y, document.documentElement.scrollHeight"
        " - innerHeight)) < 2",
        arg=y,
    )
    settle(page)


def bottom(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight - innerHeight")


def shown(page, selector: str) -> bool:
    return page.evaluate(
        "s => { const e = document.querySelector(s);"
        " return !!e && getComputedStyle(e).visibility === 'visible'; }",
        selector,
    )


def box(page, selector: str) -> dict:
    return page.evaluate(
        "s => { const r = document.querySelector(s).getBoundingClientRect();"
        " return {top: r.top, bottom: r.bottom, left: r.left, right: r.right,"
        " width: r.width, height: r.height}; }",
        selector,
    )


def past_inline_back(page) -> int:
    """A scroll position just below the page's own Back, where the bar takes over."""
    return (
        int(
            page.evaluate(
                "() => document.querySelector('main .back').getBoundingClientRect()"
                ".bottom + scrollY"
            )
        )
        + 40
    )


# --- Back -------------------------------------------------------------------------------


def test_back_returns_to_the_page_you_came_from(page, built, base_url):
    # Arrive from a page that is not the skill's plugin, so going back through history
    # and following the link's own target land in different places.
    elsewhere = next(
        "/" + index.parent.relative_to(built).as_posix() + "/"
        for index in sorted(built.rglob("index.html"))
        if f'href="{SKILL_PATH}"' in index.read_text(encoding="utf-8")
        and index.parent != built / PLUGIN_PATH.strip("/")
        and index.parent != built / SKILL_PATH.strip("/")
    )
    page.goto(base_url + elsewhere)
    page.click(f'main a[href="{SKILL_PATH}"] >> nth=0')
    page.wait_for_url(base_url + SKILL_PATH)
    page.click("main .back")
    page.wait_for_url(base_url + elsewhere)


def test_back_opened_directly_goes_to_the_page_above(page, base_url):
    # No history on this site to return through, so the link's own target is used:
    # the plugin for a skill page, never a page on another site.
    page.goto(base_url + SKILL_PATH)
    page.click("main .back")
    page.wait_for_url(base_url + PLUGIN_PATH)


def test_back_never_leaves_for_the_site_you_arrived_from(page, base_url):
    # A visitor who followed a link from another site has history, but going back
    # through it would leave this one; Back goes to the page above instead.
    page.goto("about:blank")
    page.goto(base_url + SKILL_PATH, referer="https://example.com/somewhere")
    page.click("main .back")
    page.wait_for_url(base_url + PLUGIN_PATH)


def test_back_in_a_tab_opened_from_this_site_goes_to_the_page_above(context, page, base_url):
    # A skill opened in a new tab has a referrer on this site but no history to go back
    # through; Back has to follow its link rather than call history.back() on nothing.
    page.goto(base_url + PLUGIN_PATH)
    with context.expect_page() as opened:
        page.click(f'main a[href="{SKILL_PATH}"]', modifiers=["ControlOrMeta"])
    tab = opened.value
    tab.wait_for_load_state()
    assert tab.url == base_url + SKILL_PATH
    assert tab.evaluate("() => history.length") == 1
    tab.click("main .back")
    tab.wait_for_url(base_url + PLUGIN_PATH)


def test_a_modified_click_on_back_opens_the_page_above_in_a_new_tab(context, page, base_url):
    page.goto(base_url + PLUGIN_PATH)
    page.click(f'main a[href="{SKILL_PATH}"]')
    page.wait_for_url(base_url + SKILL_PATH)
    with context.expect_page() as opened:
        page.click("main .back", modifiers=["ControlOrMeta"])
    opened.value.wait_for_load_state()
    assert opened.value.url == base_url + PLUGIN_PATH
    assert page.url == base_url + SKILL_PATH


# --- The bar ----------------------------------------------------------------------------


def test_the_bar_takes_over_back_once_the_page_scrolls_past_it(page, base_url):
    page.goto(base_url + SKILL_PATH)
    assert not shown(page, "#dock")
    scroll_to(page, past_inline_back(page))
    assert shown(page, "#dock")
    # The bar's Back is the same link, and it works from there.
    assert page.get_attribute("#dock .back", "href") == PLUGIN_PATH
    scroll_to(page, 0)
    assert not shown(page, "#dock")


def test_the_bar_follows_back_when_the_window_changes_width(page, base_url):
    # The inline Back sits higher on a phone than on a wider screen, so the point past
    # which the bar takes over moves with the width. Between the two, a narrower window
    # has to bring the bar out without waiting for the next scroll.
    page.goto(base_url + SKILL_PATH)
    wide = past_inline_back(page) - 40
    page.set_viewport_size({"width": 360, "height": 800})
    settle(page)
    narrow = past_inline_back(page) - 40
    assert narrow < wide, "Back no longer moves with the width; pick another breakpoint"
    page.set_viewport_size({"width": 1280, "height": 800})
    scroll_to(page, (narrow + wide) // 2)
    assert not shown(page, "#dock")
    page.set_viewport_size({"width": 360, "height": 800})
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('dock')).visibility === 'visible'",
        timeout=2000,
    )


def test_the_front_page_has_no_bar(page, base_url):
    page.goto(base_url + "/")
    assert page.query_selector("#dock") is None


# --- To top -----------------------------------------------------------------------------


def test_to_top_stays_away_while_reading_down_and_comes_back_on_the_way_up(page, base_url):
    page.goto(base_url + SKILL_PATH)
    assert not shown(page, "#to-top")
    start = past_inline_back(page) + 600
    scroll_to(page, start)
    assert not shown(page, "#to-top"), "shown while reading down"
    scroll_to(page, start - 200)
    assert shown(page, "#to-top"), "not shown on the way up"
    scroll_to(page, start + 400)
    assert not shown(page, "#to-top"), "not hidden again on the next scroll down"
    scroll_to(page, bottom(page))
    assert shown(page, "#to-top"), "not shown at the end of the page"


def test_to_top_returns_to_the_top_and_hands_focus_to_home(page, base_url):
    page.goto(base_url + SKILL_PATH)
    scroll_to(page, bottom(page))
    page.click("#to-top")
    page.wait_for_function("() => window.scrollY === 0")
    settle(page)
    assert page.evaluate("() => document.activeElement.id") == "home"
    assert not shown(page, "#to-top")


def test_to_top_is_not_hidden_while_it_has_focus(page, base_url):
    page.goto(base_url + SKILL_PATH)
    start = past_inline_back(page) + 600
    scroll_to(page, start)
    scroll_to(page, start - 200)
    page.focus("#to-top")
    scroll_to(page, start + 400)
    assert shown(page, "#to-top")


# --- Anchors ----------------------------------------------------------------------------


def test_a_jump_up_to_a_heading_lands_below_the_header_and_the_bar(page, base_url):
    page.goto(base_url + SKILL_PATH)
    limit = past_inline_back(page)
    target = page.evaluate(
        "limit => [...document.querySelectorAll('main h2[id], main h3[id]')]"
        ".map(h => ({id: h.id, y: h.getBoundingClientRect().top + scrollY}))"
        ".find(h => h.y > limit + 400).id",
        limit,
    )
    scroll_to(page, bottom(page))
    page.evaluate("id => { location.hash = id; }", target)
    settle(page)
    heading = box(page, f"#{target}")
    covered = box(page, "#banner")["bottom"]
    if shown(page, "#dock"):
        covered = max(covered, box(page, "#dock")["bottom"])
    assert heading["top"] >= covered, (heading, covered)


# --- Theme ------------------------------------------------------------------------------


def theme(page) -> str:
    return page.get_attribute("html", "data-theme")


@pytest.mark.parametrize(
    ("hour", "expected"), [(21, "night"), (5, "night"), (6, "day"), (19, "day")]
)
def test_without_a_choice_the_theme_follows_the_clock(page, base_url, hour, expected):
    page.clock.install(time=f"2026-10-06T{hour:02d}:30:00")
    page.goto(base_url + "/")
    assert theme(page) == expected


def test_the_dark_switch_flips_the_theme_and_the_choice_survives_a_reload(page, base_url):
    page.goto(base_url + "/")
    before = theme(page)
    page.click("#dark-switch")
    after = theme(page)
    assert after == ("day" if before == "night" else "night")
    assert page.get_attribute("#dark-switch", "aria-checked") == str(after == "night").lower()
    page.reload()
    assert theme(page) == after


def test_the_console_theme_toggles_and_forgets_itself_when_turned_off(page, base_url):
    page.goto(base_url + "/")
    page.click("#console-theme")
    assert theme(page) == "reactor"
    assert page.get_attribute("#console-theme", "aria-pressed") == "true"
    page.reload()
    assert theme(page) == "reactor"
    page.click("#console-theme")
    assert theme(page) in {"day", "night"}
    assert page.evaluate("() => localStorage.getItem('theme')") is None


# --- Finder -----------------------------------------------------------------------------


def visible_plugins(page) -> list[str]:
    return page.evaluate(
        "() => [...document.querySelectorAll('#list [data-plugin]')]"
        ".filter(s => !s.hidden).map(s => s.dataset.plugin)"
    )


def test_the_finder_narrows_the_plugins_and_says_how_many(page, base_url):
    page.goto(base_url + "/")
    every = visible_plugins(page)
    assert len(every) > 1
    page.fill("#find", LONG.parents[2].name)
    assert visible_plugins(page) == [LONG.parents[2].name]
    assert page.inner_text("#count") == f"1 of {len(every)}"
    # A skill's name finds the plugin it belongs to and names the skill under it.
    page.fill("#find", LONG.parent.name)
    assert LONG.parents[2].name in visible_plugins(page)
    hits = f'[data-plugin="{LONG.parents[2].name}"] .hits'
    assert LONG.parent.name in page.inner_text(hits)


def test_the_finder_says_so_when_nothing_matches_and_restores_everything(page, base_url):
    page.goto(base_url + "/")
    every = visible_plugins(page)
    page.fill("#find", "zz-no-such-skill-zz")
    assert visible_plugins(page) == []
    assert page.is_visible("#none")
    assert page.inner_text("#count") == f"0 of {len(every)}"
    page.fill("#find", "")
    assert visible_plugins(page) == every
    assert not page.is_visible("#none")
    assert re.fullmatch(rf"{len(every)} plugins", page.inner_text("#count"))


# --- Layout -----------------------------------------------------------------------------


@pytest.mark.parametrize("width", [360, 1440])
def test_nothing_scrolls_sideways_and_every_control_is_big_enough(browser, base_url, width):
    context = new_context(browser, base_url, width)
    try:
        page = context.new_page()
        page.goto(base_url + SKILL_PATH)
        controls = ["main .back", "#dark-switch", "#console-theme"]
        for selector in controls:
            size = box(page, selector)
            assert size["width"] >= TARGET and size["height"] >= TARGET, (selector, size)
        # Bring the bar and To top out together: past Back, down, then a little back up.
        start = past_inline_back(page) + 600
        scroll_to(page, start)
        scroll_to(page, start - 200)
        for selector in ("#dock .back", "#to-top"):
            assert shown(page, selector), selector
            size = box(page, selector)
            assert size["width"] >= TARGET and size["height"] >= TARGET, (selector, size)
            assert size["left"] >= 0 and size["right"] <= width, (selector, size)
        # The bar spans the header's width, so its Back lines up under the header's edge.
        assert box(page, "#dock .dock-in")["left"] == box(page, "#banner .bar")["left"]
        # To top carries its label only where the margin beside the column can hold it.
        assert page.is_visible("#to-top span") == (width >= 1440)
        assert page.evaluate("() => document.documentElement.scrollWidth") <= width
        # At the end of the page the footer has room to scroll clear of To top.
        scroll_to(page, bottom(page))
        fab = box(page, "#to-top")
        covered = page.evaluate(
            "f => [...document.querySelectorAll('footer a')].filter(a => {"
            " const r = a.getBoundingClientRect();"
            " return r.right > f.left && r.left < f.right && r.bottom > f.top && r.top < f.bottom;"
            " }).map(a => a.textContent)",
            fab,
        )
        assert covered == []
    finally:
        context.close()


def test_no_page_scrolls_sideways_on_a_phone(browser, built, base_url):
    # Every page, because the one that overflows is the one with the long path in its
    # prose: seven skill pages did, through a single unbreakable identifier each.
    paths = sorted(
        "/" + "".join(f"{part}/" for part in index.parent.relative_to(built).parts)
        for index in built.rglob("index.html")
    )
    context = new_context(browser, base_url, 360)
    try:
        page = context.new_page()
        wide = {}
        for path in paths:
            page.goto(base_url + path, wait_until="domcontentloaded")
            width = page.evaluate("() => document.documentElement.scrollWidth")
            if width > 360:
                wide[path] = width
        assert not wide, wide
        # The walk found the real pages, not an empty or partial build.
        assert {"/", PLUGIN_PATH, SKILL_PATH} <= set(paths)
    finally:
        context.close()
