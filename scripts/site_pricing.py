"""Static, client-only AI subscription comparison for the catalogue.

Monthly USD list prices are an editorial snapshot, not live billing quotes, and each
card links the vendor's own page so a reader can check it before buying. The options
are deliberately a single table: a new plan must update the table and its source.
"""

from __future__ import annotations

import html

RECORDED_ON = "20 October 2026"
BASELINE = 120  # ChatGPT Plus ($20) + Claude Max 5x ($100).

# (key, provider, description, official URL, (plan label, USD/month)...)
PLANS = (
    (
        "chatgpt",
        "ChatGPT",
        "General AI, deep research and Codex",
        "https://help.openai.com/en/articles/9793128-about-chatgpt-pro-tiers",
        (("None", 0), ("Plus", 20), ("Pro 100", 100), ("Pro 200", 200), ("Pro 500", 500)),
    ),
    (
        "claude",
        "Claude",
        "Claude Code and long-running engineering work",
        "https://claude.com/pricing",
        (("None", 0), ("Pro", 20), ("Max 5x", 100), ("Max 20x", 200)),
    ),
    (
        "x",
        "The X Subscription",
        "Grok on X",
        "https://docs.x.ai/x-subscription/pricing",
        (("None", 0), ("Plus", 8), ("Premium", 30), ("Super", 100), ("Ultra", 200)),
    ),
    (
        "copilot",
        "GitHub Copilot",
        "IDE completions, code review and agents",
        "https://github.com/features/copilot/plans",
        (("None", 0), ("Pro", 10), ("Pro+", 39), ("Max", 100)),
    ),
    (
        "gemini",
        "Google Gemini",
        "Research, multimodal tools and Google apps",
        "https://gemini.google/us/subscriptions/",
        (("None", 0), ("AI Pro (US price)", 19.99)),
    ),
)

# The plan each card starts on; the totals in the static markup assume these.
DEFAULT = {"chatgpt": 100, "claude": 100, "x": 0, "copilot": 0, "gemini": 0}

STYLE = """
/* Self-contained pricing view, following the site's existing theme tokens. */
.pricing-page { max-width: 68rem; }
.pricing-head { margin: 2.25rem 0 2rem; max-width: 49rem; }
.pricing-eyebrow {
  color: var(--muted); text-transform: uppercase; font-size: .75rem;
  font-weight: 700; letter-spacing: .13em; margin-bottom: .75rem;
}
.pricing-head h1 { font-size: clamp(2.3rem, 6vw, 4.8rem); line-height: 1.04;
  font-weight: 650; letter-spacing: -.055em; }
.pricing-head .lede { margin-top: 1.1rem; }
.pricing-layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(16rem, 1fr);
  gap: 1.25rem; align-items: start; }
.pricing-options { display: grid; gap: .75rem; }
.pricing-plan {
  padding: 1.2rem; border: 1px solid var(--line); border-radius: 1.2rem;
  background: var(--glass-tint);
  box-shadow: inset 0 1px 0 var(--glass-edge);
}
.pricing-plan-head { display: flex; align-items: baseline; gap: .75rem; }
.pricing-number { color: var(--muted); font-family: var(--font-mono); font-size: .7rem; }
.pricing-plan h2 { font-size: 1.15rem; font-weight: 650; letter-spacing: -.02em; }
.pricing-plan p { color: var(--muted); font-size: .9rem; margin: .35rem 0 .9rem; }
.pricing-plan fieldset { border: 0; margin: 0; padding: 0; display: flex;
  flex-wrap: wrap; gap: .4rem; }
.pricing-plan legend { font-size: .78rem; font-weight: 600; margin-bottom: .45rem;
  padding: 0; }
.pricing-choice { display: inline-flex; align-items: center; gap: .4rem;
  min-height: 2.65rem; padding: .45rem .8rem; border: 1px solid var(--line);
  border-radius: 999px; background: var(--bg); font-size: .85rem; cursor: pointer; }
.pricing-choice:has(input:checked) { box-shadow: inset 0 0 0 1px var(--ink); }
.pricing-choice input:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.pricing-source { display: inline-block; margin-top: .65rem; font-size: .8rem;
  color: var(--muted); text-decoration: underline; text-underline-offset: .15rem; }
.pricing-summary { position: sticky; top: 5.5rem; padding: 1.4rem;
  border-radius: 1.2rem; background: var(--card); border: 1px solid var(--line); }
.pricing-summary h2 { font-size: 1.1rem; font-weight: 650; }
.pricing-totals { display: grid; grid-template-columns: 1fr 1fr; gap: 1.1rem; margin: 1.5rem 0; }
.pricing-totals dt { color: var(--muted); font-size: .8rem; }
.pricing-totals dd { font-size: clamp(1.4rem, 3vw, 2rem); font-weight: 650;
  letter-spacing: -.045em; font-variant-numeric: tabular-nums; }
.pricing-difference { color: var(--muted); font-size: .84rem; line-height: 1.5;
  border-top: 1px solid var(--line); padding-top: 1rem; }
.pricing-presets { margin-top: 1.4rem; display: flex; flex-wrap: wrap; gap: .4rem; }
.pricing-presets button { border: 1px solid var(--line); min-height: 2.65rem;
  border-radius: 999px; padding: .5rem .8rem; font-size: .82rem;
  background: var(--glass-tint); }
.pricing-presets button:hover, .pricing-presets button:focus-visible {
  box-shadow: inset 0 0 0 1px var(--ink); }
.pricing-notes { margin-top: 1.6rem; padding-top: 1rem; border-top: 1px solid var(--line);
  color: var(--muted); font-size: .85rem; max-width: 62rem; }
.pricing-notes p + p { margin-top: .75rem; }
.pricing-notes a { text-decoration: underline; }
@media (max-width: 48rem) {
  .pricing-layout { grid-template-columns: 1fr; }
  .pricing-summary { position: static; }
  .pricing-totals dd { font-size: 1.7rem; }
}
@media (prefers-reduced-motion: no-preference) {
  .pricing-plan, .pricing-summary { transition: box-shadow 180ms ease; }
}
"""

SCRIPT = """
(function () {
  "use strict";
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-price-plan]"));
  var monthly = document.getElementById("price-monthly");
  var yearly = document.getElementById("price-yearly");
  var difference = document.getElementById("price-difference");
  if (!monthly || !yearly || !difference || !groups.length) return;
  function chosen(group) {
    var checked = group.querySelector('input[type="radio"]:checked');
    return checked ? Number(checked.value) : 0;
  }
  var baseline = 120;
  var presets = {
    lean: { chatgpt: 20, claude: 0, x: 0, copilot: 10, gemini: 0 },
    balanced: { chatgpt: 20, claude: 100, x: 0, copilot: 0, gemini: 0 },
    power: { chatgpt: 100, claude: 100, x: 0, copilot: 0, gemini: 0 }
  };
  var formatter = new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 2
  });
  function update() {
    var total = groups.reduce(function (sum, group) { return sum + chosen(group); }, 0);
    var delta = total - baseline;
    monthly.textContent = formatter.format(total);
    yearly.textContent = formatter.format(total * 12);
    difference.textContent = formatter.format(Math.abs(delta)) +
      (delta === 0 ? " difference" : (delta > 0 ? " more" : " less")) +
      " per month vs ChatGPT Plus + Claude Max 5x (" + formatter.format(baseline) + ").";
  }
  groups.forEach(function (group) { group.addEventListener("change", update); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-price-preset]"), function (button) {
    button.addEventListener("click", function () {
      var values = presets[button.getAttribute("data-price-preset")];
      if (!values) return;
      groups.forEach(function (group) {
        var value = String(values[group.getAttribute("data-price-plan")]);
        var radio = group.querySelector('input[type="radio"][value="' + value + '"]');
        if (radio) radio.checked = true;
      });
      update();
    });
  });
  update();
}());
"""


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def render_main(back_html: str) -> str:
    """Markup contains a useful default estimate even if scripting is disabled."""
    rows = []
    for i, (key, name, description, url, choices) in enumerate(PLANS, 1):
        k = _escape(key)
        options = "".join(
            f'<label class="pricing-choice"><input type="radio" name="plan-{k}" '
            f'value="{amount}"{" checked" if DEFAULT[key] == amount else ""}> '
            f"{_escape(label)} · {_escape('$' + format(amount, 'g')) if amount else '$0'}"
            "</label>"
            for label, amount in choices
        )
        rows.append(
            f'<section class="pricing-plan" aria-labelledby="plan-{k}-heading">'
            f'<div class="pricing-plan-head"><span class="pricing-number">{i:02d}</span>'
            f'<h2 id="plan-{k}-heading">{_escape(name)}</h2></div>'
            f"<p>{_escape(description)}</p>"
            f'<fieldset data-price-plan="{k}"><legend>Monthly subscription</legend>'
            f"{options}</fieldset>"
            f'<a class="pricing-source" href="{_escape(url)}" target="_blank" '
            'rel="noopener noreferrer">Official pricing and limits</a></section>'
        )
    return (
        '<div class="page pricing-page">\n'
        + back_html
        + '<div class="pricing-head"><p class="pricing-eyebrow">AI subscription explorer</p>'
        "<h1>Compare your AI stack.</h1>"
        '<p class="lede">Choose plans, compare combinations and see their total cost. '
        "No account connection, no tracking and no API fees hidden in the estimate.</p></div>"
        '<div class="pricing-layout"><div class="pricing-options">'
        + "\n".join(rows)
        + '</div><section class="pricing-summary" aria-labelledby="price-summary-heading">'
        '<h2 id="price-summary-heading">Your monthly stack</h2>'
        '<dl class="pricing-totals" aria-live="polite">'
        '<div><dt>Monthly</dt><dd id="price-monthly">$200</dd></div>'
        '<div><dt>Annual</dt><dd id="price-yearly">$2,400</dd></div></dl>'
        '<p class="pricing-difference" id="price-difference">'
        "$80 more per month vs ChatGPT Plus + Claude Max 5x ($120).</p>"
        '<div class="pricing-presets" aria-label="Example combinations">'
        '<button type="button" data-price-preset="lean">Lean · $30</button>'
        '<button type="button" data-price-preset="balanced">Balanced · $120</button>'
        '<button type="button" data-price-preset="power">Power · $200</button>'
        "</div></section></div>"
        '<div class="pricing-notes">'
        "<p><strong>Prices recorded "
        + _escape(RECORDED_ON)
        + ".</strong> Standard US monthly list prices in USD, before taxes. Check the "
        "vendor's page linked on each card before you buy. "
        "Annual totals multiply monthly prices by 12, not discounted annual contracts. "
        "Prices, plan names, availability and limits may change.</p>"
        "<p><strong>Gemini:</strong> US AI Pro price is shown; local and promotional "
        "prices can differ. API usage and credits are never included in these totals.</p>"
        "<p>Sources are linked on each plan card. This comparison is editorial and "
        "is not a live price feed.</p></div>"
        "</div>"
    )
