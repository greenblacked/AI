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
import io
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
    """Serves the build the way the Worker does under `auto-trailing-slash` html_handling.

    A flat page is served at its extensionless path, and asking for `name.html` redirects
    there, so a test that loaded `/errors/503.html` would be testing a URL production
    never answers with the page.
    """

    def log_message(self, *args):  # the suite's output is the assertions, not a log
        pass

    def _flat_page(self) -> Path | None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path.endswith("/") or "." in path.rsplit("/", 1)[-1]:
            return None
        candidate = Path(self.translate_path(path) + ".html")
        return candidate if candidate.is_file() else None

    def _redirects(self) -> dict[str, str]:
        """Each flat page's `.html` address mapped to its extensionless one.

        Built from the files on disk, so the Location sent back is always a value this
        table holds and never text taken from the request.
        """
        root = Path(self.directory)
        table = {}
        for page in root.rglob("*.html"):
            if page.name in ("index.html", "404.html"):
                continue
            served = "/" + page.relative_to(root).as_posix()
            table[served] = served[: -len(".html")]
        return table

    def send_head(self):
        target = self._redirects().get(self.path.split("?", 1)[0])
        if target is not None:
            self.send_response(307)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        flat = self._flat_page()
        if flat is not None:
            self.path = self.path.split("?", 1)[0] + ".html"
        return super().send_head()


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


class _NotFound(_Quiet):
    """What the production host does for a path with no asset: the root 404.html, with 404."""

    def send_head(self):
        try:
            found = Path(self.translate_path(self.path)).exists() or self._flat_page() is not None
        except OSError:  # a name too long for the file system is just a path with no page
            found = False
        if found:
            return super().send_head()
        body = (Path(self.directory) / "404.html").read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)


@pytest.fixture(scope="session")
def missing_url(built):
    handler = functools.partial(_NotFound, directory=str(built))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
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
    leave the local server are refused, so no test waits on the network or changes with it.
    The two typefaces are the site's own files, so they load here and are what is measured.
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


# --- Fonts ------------------------------------------------------------------------------


def _loaded_faces(page) -> set[str]:
    page.evaluate("() => document.fonts.ready")
    return set(
        page.evaluate(
            "() => Array.from(document.fonts)"
            ".filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, ''))"
        )
    )


def test_both_typefaces_load_from_the_site_with_every_outside_request_refused(
    browser, built, base_url
):
    context = new_context(browser, base_url)
    page = context.new_page()
    served, refused = [], []
    page.on("response", lambda r: served.append(r.url) if "/fonts/" in r.url else None)
    page.on("requestfailed", lambda r: refused.append(r.url))
    page.goto(base_url + "/")
    assert _loaded_faces(page) == {"Instrument Sans", "Newsreader"}
    # Served by this host, from the hashed names, and nothing went out for one: a refused
    # request here would be a request to a font host, which the build no longer makes.
    assert sorted(served) == sorted(
        {base_url + site.site_style.SANS_URL, base_url + site.site_style.SERIF_URL}
    )
    assert refused == []
    # The weights the page asks for come out of the one variable file each.
    for weight, family in ((400, "Instrument Sans"), (500, "Instrument Sans"), (400, "Newsreader")):
        assert page.evaluate(
            '([w, f]) => document.fonts.check(`${w} 16px "${f}"`)', [weight, family]
        )
    used = page.evaluate(
        "() => getComputedStyle(document.querySelector('.card p')).fontFamily.split(',')[0]"
    )
    assert used.strip('"') == "Newsreader"
    context.close()


def test_the_text_is_drawn_in_the_real_faces_and_not_the_fallback(page, base_url):
    page.goto(base_url + "/family/")
    # A face loads when text first needs it; ask for each so the measure below is not early.
    page.evaluate(
        "() => Promise.all(['400 40px \"Instrument Sans\"', '400 40px \"Newsreader\"']"
        ".map(f => document.fonts.load(f, 'Hamburgefontsiv')))"
    )
    widths = page.evaluate(
        """() => {
            const measure = (family, weight) => {
                const span = document.createElement('span');
                span.textContent = 'Hamburgefontsiv quick brown fox 0123456789';
                span.style.cssText = `position:absolute;visibility:hidden;white-space:nowrap;`
                    + `font-size:40px;font-weight:${weight};font-family:${family}`;
                document.body.append(span);
                const width = span.getBoundingClientRect().width;
                span.remove();
                return width;
            };
            return {
                sans: measure('"Instrument Sans", monospace', 400),
                sansBare: measure('monospace', 400),
                serif: measure('"Newsreader", monospace', 400),
                serifBare: measure('monospace', 400),
            };
        }"""
    )
    # A face that did not apply would measure as the monospace it falls back to.
    assert abs(widths["sans"] - widths["sansBare"]) > 20
    assert abs(widths["serif"] - widths["serifBare"]) > 20
    assert widths["sans"] != widths["serif"]


def test_the_404_page_loads_the_fonts_from_any_depth(browser, missing_url):
    context = new_context(browser, missing_url)
    page = context.new_page()
    page.goto(missing_url + "/a/b/c/d/missing/")
    assert _loaded_faces(page) >= {"Instrument Sans"}
    context.close()


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


FAMILY_KEYS = (
    "() => [...document.querySelectorAll('.family-word .fk, .family-word .fd')]"
    ".map(e => ({text: e.textContent, opacity: getComputedStyle(e).opacity,"
    " width: e.getBoundingClientRect().width, color: getComputedStyle(e).color}))"
)


def test_the_family_heading_is_whole_and_named_when_motion_is_reduced(page, base_url):
    page.goto(base_url + "/family/")
    # Screen readers hear the workflow's name, not twelve letters and dots.
    assert page.get_by_role("heading", level=1, name="The FAMILY workflow").count() == 1
    keys = page.evaluate(FAMILY_KEYS)
    assert "".join(k["text"] for k in keys) == "F.A.M.I.L.Y."
    # Nothing waits on an animation the visitor asked not to see.
    assert all(k["opacity"] == "1" and k["width"] > 0 for k in keys)
    assert page.evaluate("() => document.getAnimations().length") == 0
    # Each stage letter has its own colour; the dots share the text colour.
    letters = keys[0::2]
    assert len({k["color"] for k in letters}) == 6
    assert len({k["color"] for k in keys[1::2]}) == 1


def test_the_family_heading_types_itself_in_when_motion_is_allowed(browser, base_url):
    made = browser.new_context(viewport={"width": 1280, "height": 800})
    made.route(re.compile("^(?!" + re.escape(base_url) + "/)"), lambda route: route.abort())
    try:
        page = made.new_page()
        page.emulate_media(reduced_motion="no-preference")
        page.goto(base_url + "/family/")
        names = page.evaluate(
            "() => document.getAnimations().filter(a => a.effect.target.closest('.family-word'))"
            ".map(a => a.animationName)"
        )
        assert names.count("family-key") == 12 and "family-caret" in names
        page.wait_for_function(
            "() => document.getAnimations().every(a => a.playState === 'finished')",
            timeout=10_000,
        )
        assert all(k["opacity"] == "1" and k["width"] > 0 for k in page.evaluate(FAMILY_KEYS))
    finally:
        made.close()


def test_a_stage_focused_during_the_entrance_is_visible(browser, base_url):
    # The rows rise in seconds after load, but their summaries can take focus at once.
    made = browser.new_context(viewport={"width": 1280, "height": 800})
    made.route(re.compile("^(?!" + re.escape(base_url) + "/)"), lambda route: route.abort())
    try:
        page = made.new_page()
        page.emulate_media(reduced_motion="no-preference")
        page.goto(base_url + "/family/")
        summary = page.locator(".family-stages > li:nth-child(6) summary")
        summary.focus()
        row = "el => getComputedStyle(el.closest('li')).opacity"
        assert summary.evaluate(row) == "1"
    finally:
        made.close()


def test_opening_and_leaving_a_stage_does_not_replay_its_entrance(browser, base_url):
    # Toggling the row's animation on focus restarted it on blur: the row went back to
    # invisible and rose again, a one-second flicker every time a stage was opened.
    made = browser.new_context(viewport={"width": 390, "height": 800})
    made.route(re.compile("^(?!" + re.escape(base_url) + "/)"), lambda route: route.abort())
    try:
        page = made.new_page()
        page.emulate_media(reduced_motion="no-preference")
        page.goto(base_url + "/family/")
        page.wait_for_function(
            "() => document.getAnimations().every(a => a.playState === 'finished')",
            timeout=10_000,
        )
        row = page.locator(".family-stages > li.stage-a")
        row.locator("summary").click()
        page.locator("h1").click()
        page.locator(".family-stages > li.stage-f summary").click()
        for _ in range(5):
            assert row.evaluate("el => getComputedStyle(el).opacity") == "1"
            states = row.evaluate("el => el.getAnimations().map(a => a.playState)")
            assert "running" not in states
            page.wait_for_timeout(100)
    finally:
        made.close()


def test_the_family_page_is_the_plugin_page_with_its_install_line_and_skills(page, built, base_url):
    page.goto(base_url + "/family/")
    assert page.get_by_role("heading", level=1, name="The FAMILY workflow").count() == 1
    assert page.get_by_text("/plugin install family@", exact=False).first.is_visible()
    skills = page.evaluate("() => [...document.querySelectorAll('#list [data-name]')].length")
    assert skills == len(list(REPO.glob("plugins/family/skills/*/SKILL.md")))
    assert page.locator(".family-agents li").count() == 6
    # The retired plugin page is not built; its address redirects in production.
    assert not (built / "plugins" / "family" / "index.html").exists()
    assert (
        (built / "_redirects")
        .read_text(encoding="utf-8")
        .startswith("/plugins/family/ /family/ 301")
    )
    page.get_by_role("link", name="See one slice end to end").click()
    page.wait_for_url(base_url + "/family/example/")
    page.get_by_role("link", name="Back").first.click()
    page.wait_for_url(base_url + "/family/")


def _stage_look(page, letter: str) -> dict:
    return page.evaluate(
        "l => { const li = document.querySelector('.stage-' + l + '.family-stages > li,"
        " .family-stages > li.stage-' + l);"
        " return {letter: getComputedStyle(li.querySelector('.letter')).color,"
        " name: getComputedStyle(li.querySelector('h3')).color,"
        " tint: getComputedStyle(li.querySelector('details')).backgroundColor,"
        " bar: getComputedStyle(li, '::before').backgroundColor,"
        " width: getComputedStyle(li, '::before').width}; }",
        letter,
    )


def test_picking_a_profile_highlights_its_stages_and_mutes_the_rest(page, base_url):
    page.goto(base_url + "/family/")
    plain = {letter: _stage_look(page, letter) for letter in "fami"}
    # No profile is picked, so every stage looks the same way: tinted by none.
    assert {look["tint"] for look in plain.values()} == {"rgba(0, 0, 0, 0)"}
    assert not page.locator(".start").evaluate_all("els => els.some(e => e.offsetParent)")
    page.get_by_label("Developer").check()
    owned, handed_off = _stage_look(page, "m"), _stage_look(page, "i")
    # Owned: the stage's own colour kept and a tint added. Handed off: muted.
    assert owned["letter"] == plain["m"]["letter"] and owned["tint"] != plain["m"]["tint"]
    assert handed_off["letter"] != plain["i"]["letter"]
    assert handed_off["name"] != plain["i"]["name"] and handed_off["bar"] != plain["i"]["bar"]
    assert owned["width"] != handed_off["width"] or owned["bar"] != handed_off["bar"]
    assert page.locator('.start[data-for="developer"]').is_visible()
    assert not page.locator('.start[data-for="qa"]').is_visible()
    assert page.locator('.stage-i .note[data-for="developer"]').is_visible()
    # QA owns Inspect and only pushes into Frame: Frame is neither tinted nor muted.
    page.get_by_label("QA").check()
    assert _stage_look(page, "i")["tint"] != "rgba(0, 0, 0, 0)"
    assert _stage_look(page, "f")["tint"] == "rgba(0, 0, 0, 0)"
    assert _stage_look(page, "f")["letter"] == plain["f"]["letter"]
    assert _stage_look(page, "m")["letter"] != plain["m"]["letter"]
    # Solo and Team own all six.
    for label in ("Solo", "Team"):
        page.get_by_label(label).check()
        assert all(_stage_look(page, x)["tint"] != "rgba(0, 0, 0, 0)" for x in "fami")
    # Clear returns to the neutral page.
    page.get_by_role("button", name="Clear").click()
    assert {_stage_look(page, x)["tint"] for x in "fami"} == {"rgba(0, 0, 0, 0)"}


def test_the_profile_picker_works_from_the_keyboard_with_a_visible_focus(page, base_url):
    page.goto(base_url + "/family/")
    page.focus(".install pre")
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.value") == "solo"
    outline = page.evaluate(
        "() => getComputedStyle(document.activeElement.closest('.chip')).outlineStyle"
    )
    assert outline != "none"
    page.keyboard.press("ArrowRight")
    assert page.evaluate("() => document.activeElement.value") == "developer"
    assert page.get_by_label("Developer").is_checked()
    assert page.locator('.start[data-for="developer"]').is_visible()
    # Pressing Enter in the group does not submit the form and reload the page.
    page.keyboard.press("Enter")
    assert page.url == base_url + "/family/" and page.get_by_label("Developer").is_checked()


def test_a_stage_opens_on_click_and_shows_its_agent_and_verdicts(page, base_url):
    page.goto(base_url + "/family/")
    stage = page.locator(".family-stages > li.stage-i")
    assert not stage.get_by_text("inspector", exact=True).is_visible()
    stage.locator("summary").click()
    assert stage.locator("details").evaluate("el => el.open")
    assert stage.get_by_text("inspector", exact=True).is_visible()
    assert stage.get_by_text("PASS", exact=True).is_visible()
    assert stage.get_by_text("→ launcher").is_visible()
    # Keyboard: a focused summary opens with Enter, and the others stay closed.
    page.locator(".family-stages > li.stage-l summary").focus()
    page.keyboard.press("Enter")
    assert page.locator(".family-stages > li.stage-l details").evaluate("el => el.open")
    assert not page.locator(".family-stages > li.stage-f details").evaluate("el => el.open")


def ticked(page) -> list[str]:
    return page.evaluate(
        "() => [...document.querySelectorAll('[data-gate]')].filter(b => b.checked)"
        ".map(b => b.dataset.gate)"
    )


def test_the_slice_checklist_remembers_its_ticks_until_reset(page, base_url):
    page.goto(base_url + "/family/")
    assert page.locator("[data-gate]").count() == 6 and ticked(page) == []
    page.locator('[data-gate="f"]').check()
    page.locator('[data-gate="i"]').check()
    page.reload()
    assert ticked(page) == ["f", "i"]
    assert page.evaluate("() => JSON.parse(localStorage.getItem('family-slice'))") == ["f", "i"]
    page.get_by_role("button", name="Reset").click()
    assert ticked(page) == []
    assert page.evaluate("() => localStorage.getItem('family-slice')") is None
    page.reload()
    assert ticked(page) == []


def test_the_slice_checklist_still_works_when_storage_is_blocked(browser, base_url):
    made = new_context(browser, base_url)
    made.add_init_script(
        "Object.defineProperty(window, 'localStorage',"
        " {get() { throw new Error('blocked'); }, configurable: true});"
    )
    try:
        page = made.new_page()
        page.goto(base_url + "/family/")
        page.locator('[data-gate="a"]').check()
        assert ticked(page) == ["a"]
        page.get_by_role("button", name="Reset").click()
        assert ticked(page) == []
    finally:
        made.close()


def test_the_finder_filters_the_family_skills(page, base_url):
    page.goto(base_url + "/family/")
    names = page.evaluate("() => [...document.querySelectorAll('#list [data-name]')]"
                          ".map(e => e.dataset.name)")  # fmt: skip
    assert "qa-workflow" in names and len(names) > 3
    page.fill("#find", "qa-work")
    shown = page.evaluate(
        "() => [...document.querySelectorAll('#list [data-name]')]"
        ".filter(e => !e.hidden).map(e => e.dataset.name)"
    )
    assert shown == ["qa-workflow"]
    assert page.inner_text("#count") == f"1 of {len(names)}"
    page.fill("#find", "zz-none-zz")
    assert page.is_visible("#none")


@pytest.mark.parametrize("path", ["/family/", "/family/example/"])
def test_the_family_pages_do_not_scroll_sideways_on_a_phone(browser, base_url, path):
    context = new_context(browser, base_url, 390)
    try:
        page = context.new_page()
        page.goto(base_url + path)
        if path == "/family/":
            page.get_by_label("QA").check()
            page.locator(".family-stages > li").evaluate_all(
                "els => els.forEach(e => e.querySelector('details').open = true)"
            )
        assert page.evaluate("() => document.documentElement.scrollWidth") <= 390
    finally:
        context.close()


# --- The 404 and the pages under /errors/ -----------------------------------------------

ERROR_PAGES = {"403": False, "500": True, "502": True, "503": True}
LIGHT_BG, NIGHT_BG = "rgb(244, 241, 234)", "rgb(0, 0, 0)"


def lost(browser, base_url: str, *, width: int = 1280, reduced: str = "reduce", **options):
    """A context for pages served by the 404 handler, which is a different server."""
    made = browser.new_context(
        viewport={"width": width, "height": 800}, reduced_motion=reduced, **options
    )
    made.route(re.compile("^(?!" + re.escape(base_url) + "/)"), lambda route: route.abort())
    return made


def suggested(page) -> list[str]:
    return page.evaluate(
        "() => [...document.querySelectorAll('#lost-list a')].map(a => a.getAttribute('href'))"
    )


def test_a_near_miss_is_answered_with_a_404_and_the_page_it_was_close_to(browser, missing_url):
    made = lost(browser, missing_url)
    try:
        page = made.new_page()
        response = page.goto(missing_url + "/family-workflw/")
        assert response.status == 404
        assert page.get_by_role("heading", level=1, name="Error 404: page not found").count() == 1
        # The request is shown back, and the closest real page is offered first.
        assert page.locator("#lost-path").text_content() == "/family-workflw/"
        assert page.is_visible("#lost-suggest")
        links = suggested(page)
        assert links[0] == "/plugins/family/family-workflow/" and len(links) <= 3
        page.get_by_role("link", name="family-workflow").click()
        page.wait_for_url(missing_url + "/plugins/family/family-workflow/")
    finally:
        made.close()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/statr/", "/start/"),  # two letters swapped
        ("/plugins/coding/code-reveiw/", "/plugins/coding/code-review/"),
        ("/old/skills/code-rev", "/plugins/coding/code-review/"),  # the start of a name
        ("/Family_Workflow.html", "/plugins/family/family-workflow/"),
    ],
)
def test_the_suggestion_forgives_swaps_prefixes_case_and_an_extension(
    browser, missing_url, path, expected
):
    made = lost(browser, missing_url)
    try:
        page = made.new_page()
        page.goto(missing_url + path)
        assert expected in suggested(page)
    finally:
        made.close()


def test_a_path_that_matches_nothing_shows_itself_and_no_suggestions(browser, missing_url):
    made = lost(browser, missing_url)
    try:
        page = made.new_page()
        page.goto(missing_url + "/qqqqzzzz/")
        assert page.locator("#lost-path").text_content() == "/qqqqzzzz/"
        assert not page.is_visible("#lost-suggest") and suggested(page) == []
        # The four ways onward are always there.
        for name in ("Home", "Start", "Search the catalogue", "FAMILY"):
            assert page.get_by_role("link", name=name, exact=True).first.is_visible(), name
    finally:
        made.close()


def test_the_requested_path_is_text_and_never_markup(browser, missing_url):
    made = lost(browser, missing_url)
    try:
        page = made.new_page()
        dialogs = []
        page.on("dialog", lambda dialog: dialogs.append(dialog.message))
        hostile = "/<img src=x onerror=alert(1)>/<script>alert(2)</script>"
        page.goto(missing_url + hostile)
        assert page.locator("#lost-path").text_content() == hostile
        assert page.locator("#lost-path img, #lost-path script").count() == 0
        assert page.locator("main img").count() == 0 and dialogs == []
    finally:
        made.close()


def test_the_404_reads_whole_without_script(browser, missing_url):
    made = lost(browser, missing_url, java_script_enabled=False)
    try:
        page = made.new_page()
        page.goto(missing_url + "/family-workflw/")
        assert page.get_by_role("heading", level=1, name="Error 404: page not found").count() == 1
        assert page.get_by_text("There is nothing at this address.").is_visible()
        assert not page.is_visible("#lost-path") and not page.is_visible("#lost-suggest")
        assert page.get_by_role("link", name="Search the catalogue").is_visible()
        page.get_by_role("link", name="Search the catalogue").click()
        page.wait_for_url(missing_url + "/#finder")
    finally:
        made.close()


def test_the_404_digits_are_whole_and_still_when_motion_is_reduced(browser, missing_url):
    made = lost(browser, missing_url)
    try:
        page = made.new_page()
        page.goto(missing_url + "/nothing-here/")
        digits = page.evaluate(
            "() => [...document.querySelectorAll('.lost-word .ld')].map(e => ({text: e.textContent,"
            " opacity: getComputedStyle(e).opacity, width: e.getBoundingClientRect().width}))"
        )
        assert "".join(d["text"] for d in digits) == "404"
        assert all(d["opacity"] == "1" and d["width"] > 0 for d in digits)
        assert page.evaluate("() => document.getAnimations().length") == 0
    finally:
        made.close()


def test_the_404_types_and_scans_when_motion_is_allowed(browser, missing_url):
    made = lost(browser, missing_url, reduced="no-preference")
    try:
        page = made.new_page()
        page.goto(missing_url + "/nothing-here/")
        names = page.evaluate("() => document.getAnimations().map(a => a.animationName)")
        assert names.count("lost-key") == 3 and "lost-scan" in names and "lost-caret" in names
        page.wait_for_function(
            "() => [...document.querySelectorAll('.lost-word .ld')]"
            ".every(e => getComputedStyle(e).opacity === '1')",
            timeout=10_000,
        )
    finally:
        made.close()


@pytest.mark.parametrize("path", ["/qqqqzzzz/", "/" + "a" * 300 + "/", "/family-workflw/"])
def test_the_404_does_not_scroll_sideways_on_a_phone(browser, missing_url, path):
    made = lost(browser, missing_url, width=390)
    try:
        page = made.new_page()
        page.goto(missing_url + path)
        assert page.evaluate("() => document.documentElement.scrollWidth") <= 390
    finally:
        made.close()


def test_an_error_page_is_answered_at_its_extensionless_address(browser, base_url):
    # The .html address redirects, as the Worker's html_handling does, so a consumer
    # pointed at it would get a redirect rather than the page.
    made = browser.new_context()
    try:
        page = made.new_page()
        response = page.goto(f"{base_url}/errors/503.html")
        assert page.url == f"{base_url}/errors/503"
        assert response.request.redirected_from is not None
        assert page.get_by_role("heading", level=1).count() == 1
    finally:
        made.close()


@pytest.mark.parametrize("code", ERROR_PAGES)
@pytest.mark.parametrize("width", [320, 390, 1280])
def test_each_error_page_fits_the_screen_and_makes_no_requests(browser, base_url, code, width):
    made = browser.new_context(viewport={"width": width, "height": 800}, reduced_motion="reduce")
    requested = []
    made.route("**/*", lambda route: (requested.append(route.request.url), route.continue_()))
    try:
        page = made.new_page()
        page.goto(f"{base_url}/errors/{code}")
        assert page.evaluate("() => document.documentElement.scrollWidth") <= width
        assert page.get_by_role("heading", level=1).count() == 1
        assert page.get_by_role("link", name="Home", exact=True).last.is_visible()
        # The page is the whole of what was fetched, bar the tab icon's own data URI.
        assert [url for url in requested if not url.startswith("data:")] == [
            f"{base_url}/errors/{code}"
        ]
    finally:
        made.close()


@pytest.mark.parametrize("code", ERROR_PAGES)
def test_error_pages_stop_all_motion_when_it_is_reduced_and_move_when_it_is_not(
    browser, base_url, code
):
    still = browser.new_context(reduced_motion="reduce")
    moving = browser.new_context(reduced_motion="no-preference")
    try:
        quiet = still.new_page()
        quiet.goto(f"{base_url}/errors/{code}")
        assert quiet.evaluate("() => document.getAnimations().length") == 0
        digits = quiet.evaluate(
            "() => [...document.querySelectorAll('.digits .dg')].map(e =>"
            " [e.textContent, getComputedStyle(e).opacity])"
        )
        assert digits == [[c, "1"] for c in code]
        busy = moving.new_page()
        busy.goto(f"{base_url}/errors/{code}")
        names = busy.evaluate("() => document.getAnimations().map(a => a.animationName)")
        assert names.count("err-key") == 3 and "err-caret" in names
        # And each page has the effect that belongs to its code.
        effect = {"403": "err-lock", "500": "err-shake", "502": "err-dash", "503": "err-sweep"}
        assert effect[code] in names, names
    finally:
        still.close()
        moving.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_error_pages_follow_the_colour_scheme_and_a_choice_made_on_the_site(
    browser, base_url, scheme
):
    made = browser.new_context(color_scheme=scheme, reduced_motion="reduce")
    try:
        page = made.new_page()
        page.goto(f"{base_url}/errors/503")
        background = lambda: page.evaluate(  # noqa: E731
            "() => getComputedStyle(document.documentElement).backgroundColor"
        )
        assert background() == (NIGHT_BG if scheme == "dark" else LIGHT_BG)
        # The theme stored by the site's own switch wins over the system's.
        page.evaluate(
            "t => localStorage.setItem('theme', t)", "day" if scheme == "dark" else "night"
        )
        page.reload()
        assert background() == (LIGHT_BG if scheme == "dark" else NIGHT_BG)
    finally:
        made.close()


@pytest.mark.parametrize("code", ERROR_PAGES)
def test_error_page_text_has_enough_contrast_in_both_schemes(browser, base_url, code):
    for scheme in ("light", "dark"):
        made = browser.new_context(color_scheme=scheme, reduced_motion="reduce")
        try:
            page = made.new_page()
            page.goto(f"{base_url}/errors/{code}")
            ratios = page.evaluate(
                """() => {
                  const lin = x => { x /= 255;
                    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
                  const lum = c => { const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map(lin);
                    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
                  const bg = lum(getComputedStyle(document.documentElement).backgroundColor);
                  return ['.digits', '.err-title', '.err-msg', '.foot'].map(s => {
                    const l = lum(getComputedStyle(document.querySelector(s)).color);
                    return [s, (Math.max(l, bg) + 0.05) / (Math.min(l, bg) + 0.05)]; });
                }"""
            )
            for selector, ratio in ratios:
                assert ratio >= 4.5, (code, scheme, selector, ratio)
        finally:
            made.close()


def test_retry_reloads_the_page_and_shows_only_with_script(browser, base_url):
    made = browser.new_context(reduced_motion="reduce")
    try:
        page = made.new_page()
        page.goto(f"{base_url}/errors/503")
        page.evaluate("() => { window.stale = true; }")
        page.get_by_role("button", name="Retry").click()
        page.wait_for_function("() => window.stale === undefined")
        assert page.get_by_role("button", name="Retry").is_visible()
    finally:
        made.close()
    bare = browser.new_context(java_script_enabled=False)
    try:
        page = bare.new_page()
        page.goto(f"{base_url}/errors/503")
        assert page.get_by_role("heading", level=1, name="Error 503: Back shortly").count() == 1
        assert page.get_by_role("link", name="Retry").is_visible()
        assert (
            page.get_by_role("button", name="Retry").count() == 0
            or not page.get_by_role("button", name="Retry").is_visible()
        )
    finally:
        bare.close()


def test_403_offers_no_retry_and_a_way_home(browser, base_url):
    made = browser.new_context(reduced_motion="reduce")
    try:
        page = made.new_page()
        page.goto(f"{base_url}/errors/403")
        assert page.get_by_role("button", name="Retry").count() == 0
        page.get_by_role("link", name="Home", exact=True).last.click()
        page.wait_for_url(base_url + "/")
    finally:
        made.close()
