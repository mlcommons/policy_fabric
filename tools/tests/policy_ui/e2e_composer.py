#!/usr/bin/env python3
"""Drive the Policy Composer of the built docs site like a person, and check what it must do.

It serves the built site over HTTP (a page opened from file:// cannot fetch catalog.json), then checks:
  - the library lists the catalog's components: Shared 3, Cards 23;
  - Load opens each of the 23 cards with no check errors, and draws its capability;
  - building the IRB card from the library, choosing its operation and requiring its card component, with
    accept presented on at the two outputs a wallet may also present, gives JSON equal to
    policy_cards/ethics-approval-required/graph.json, and Download saves that file;
  - Load followed by Download gives back each card's graph.json byte for byte, even after values are typed on
    the Simulate tab, whose values never reach the JSON;
  - the canvas carries no text it does not need: no subtitle under a credential's type, a wired input drawn as
    an empty lane the wire runs through into its component, no blurbs or notes, and the side panel only on the
    Simulate tab;
and the interactions: the details popup, wiring, accept presented, the capability's operation and required
components, Simulate, Arrange, two cards the capability requires, a local graph.json, the draft kept on reload,
the docs page that frames the app and its theme, and phone width. It takes light and dark screenshots.

usage: python3 e2e_composer.py <built site dir> <screenshots dir>
Build the site first (mkdocs build --strict -f docs/mkdocs.yml writes it to docs/site). Needs Playwright for
Python with Chromium. Prints a PASS or FAIL line per check and exits 1 on any failure.
"""
import argparse
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]   # tools/tests/policy_ui/ -> the repo root
IRB = "ethics-approval-required"
IRB_ORDER = ["project_membership", "institutional_irb_approval", "irb_clearance", "ethics_approval_required"]
IRB_SHORTCUTS = [("irb_clearance", "membership"), ("ethics_approval_required", "clearance")]   # input, read from:
IRB_ACCEPTED = ["irb_clearance", "project_membership"]                                          # these outputs
IRB_LANES = ["ethics_approval_required.clearance", "irb_clearance.approval", "irb_clearance.membership"]
DS = "disease-specific-research"
GROUPS = [["Shared", 3], ["Cards", 23]]                  # the library: policy_components/README.md
AMBER = "rgb(148, 88, 10)"                               # --pf-grant, light
DARK_SUNK = "rgb(17, 26, 39)"                            # --pf-sunk, dark
JARGON = re.compile(r"\b(facts?|slots?|bindings?|planners?|parity|AccessCondition)\b", re.I)

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("site", type=Path, help="the built docs site (docs/site)")
ap.add_argument("shots", type=Path, help="where to write the screenshots")
args = ap.parse_args()
SHOTS = args.shots
SHOTS.mkdir(parents=True, exist_ok=True)
CATALOG = json.loads((args.site / "composer" / "app" / "catalog.json").read_text())
COMMITTED = {f: (REPO / "policy_cards" / f / "graph.json").read_bytes() for f in CATALOG["cards"]}

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""), flush=True)


def serve(site):
    """python3 -m http.server on a free port, in the site folder; returns the process and the base URL"""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(site)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            urllib.request.urlopen(base + "/composer/app/catalog.json", timeout=1).read()
            return proc, base
        except OSError:
            time.sleep(0.05)
    proc.terminate()
    sys.exit(f"the site server on {base} did not answer")


def drag(page, x1, y1, x2, y2, steps=16):
    page.mouse.move(x1, y1)
    page.mouse.down()
    for i in range(1, steps + 1):
        page.mouse.move(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
    page.mouse.up()


def center(page, selector):
    box = page.locator(selector).bounding_box()
    assert box, f"not found: {selector}"
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def grab_point(page, nid):
    """a point on the node's Policy Component shape that no other component covers"""
    pt = page.evaluate("""nid => {
        const el = document.querySelector(`.node[data-node="${nid}"] [data-comp]`), r = el.getBoundingClientRect();
        for (const fy of [0.5, 0.3, 0.7, 0.15, 0.85]) for (const fx of [0.5, 0.25, 0.75, 0.1, 0.9]) {
            const x = r.left + r.width * fx, y = r.top + r.height * fy, top = document.elementFromPoint(x, y);
            if (top && top.closest('[data-comp]') === el) return [x, y];
        }
        return null; }""", nid)
    assert pt, f"every point of {nid}'s Policy Component is covered"
    return pt


def ready(page):
    page.wait_for_selector("html[data-ready=true]", state="attached")


def node_ids(page):
    return page.evaluate("Object.keys(S.nodes)")


def graph_text(page):
    page.locator("#tab-json").click()
    return page.evaluate("document.getElementById('json-out').textContent") + "\n"


def graph_json(page):
    return json.loads(graph_text(page))


def download(page, selector="#download"):
    with page.expect_download() as d:
        page.locator(selector).click()
    return d.value.suggested_filename, Path(d.value.path()).read_bytes()


def load_card(page, folder):
    page.select_option("#load-select", "card:" + folder)
    page.wait_for_timeout(60)


def verdict(page):
    page.locator("#tab-sim").click()
    return page.locator(".verdict").inner_text().replace("\n", " ")


def chips(page, sel):
    return page.locator(f"{sel} .chip").all_inner_texts()


def toast(page):
    return page.locator("#toast").inner_text()


def wire_by_clicks(page, src, dst, inp):
    """Click the source's output, then the header of the credential presented to the input."""
    page.locator(f'.n-out[data-node="{src}"] .vc-h').click()
    page.locator(f'.n-in[data-node="{dst}"][data-input="{inp}"] .vc-h').click()
    page.wait_for_timeout(60)


def choose_operation(page, op):
    """pick the capability's operation on its card"""
    page.select_option("#cap-operation", op)
    page.wait_for_timeout(60)


def require(page, nid):
    """switch required on, or off, at the node's output on the canvas"""
    page.locator(f'label[for="rqc-{nid}"]').click()
    page.wait_for_timeout(60)


def click_wire(page, src, dst, inp):
    """click the middle of the wire from src into dst.inp, on the curve itself"""
    x, y = page.evaluate("""([src, dst, inp]) => {
        const w = S.wires.find(w => w.from === src && w.to === dst && w.input === inp);
        const path = document.querySelector(`.wire-hit[data-wire="${w.id}"]`);
        const p = path.getPointAtLength(path.getTotalLength() / 2).matrixTransform(path.getScreenCTM());
        return [p.x, p.y]; }""", [src, dst, inp])
    page.mouse.click(x, y)
    page.wait_for_timeout(60)


def ui_text(page):
    """visible text plus the labels people see on hover or hear from a screen reader"""
    return page.evaluate("""document.body.innerText + ' ' + [...document.querySelectorAll('[title],[aria-label],[placeholder]')]
        .filter(e => e.offsetParent !== null || e === document.body)
        .map(e => [e.getAttribute('title'), e.getAttribute('aria-label'), e.getAttribute('placeholder')].join(' ')).join(' ')""")


jargon_seen = set()


def scan_jargon(page, where):
    for m in JARGON.finditer(ui_text(page)):
        jargon_seen.add(f"{m.group(0)} ({where})")


def track_errors(page, base, errors):
    """page errors, and console errors from this site (the docs theme also asks api.github.com, which the test ignores)"""
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(f"{m.text} ({m.location['url']})")
            if m.type == "error" and m.location["url"].startswith(base) else None)


server, BASE = serve(args.site)
APP = BASE + "/composer/app/"
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light",
                                  accept_downloads=True, permissions=["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        errors = []
        track_errors(page, BASE, errors)
        page.goto(APP)
        page.evaluate("localStorage.clear()")
        page.reload()
        ready(page)
        comps = CATALOG["components"]

        # ---------- the built site, first visit, library
        check("the built site holds this repository's cards (catalog.json graphs equal policy_cards/**/graph.json)",
              all(CATALOG["cards"][f]["graph"] == json.loads(COMMITTED[f]) for f in COMMITTED) and len(COMMITTED) == 23, len(COMMITTED))
        check("the composer reads its components from catalog.json, unchanged", page.evaluate("COMPONENTS") == comps)
        check("first visit opens an empty canvas with a hint, and Checks says the canvas is empty",
              node_ids(page) == [] and page.locator("#canvas-hint").is_visible() and page.locator("#count-checks").inner_text() == "1")
        groups = page.evaluate("[...document.querySelectorAll('.lib-group')].map(g => [g.getAttribute('aria-label'), g.querySelectorAll('.lib-item').length])")
        want = [[t, sum(1 for c in comps.values() if c["group"] == g)] for t, g in (("Shared", "shared"), ("Cards", "card"))]
        check("library groups: Shared 3, Cards 23, as the catalog has them", groups == GROUPS == want and len(comps) == 26, f"{groups} / catalog {want}")
        check("every library item has an Add button", page.locator(".lib-item").count() == page.locator(".lib-item .lib-add").count() == 26)
        rows = page.evaluate("Object.fromEntries([...document.querySelectorAll('.lib-group')].map(g => [g.getAttribute('aria-label'), [...g.querySelectorAll('.lib-item')].map(i => i.dataset.component)]))")
        check("each group lists the catalog's components of that group, in catalog order",
              rows == {t: [k for k, c in comps.items() if c["group"] == g] for t, g in (("Shared", "shared"), ("Cards", "card"))}, rows)
        abouts = {op["about"] for op in CATALOG["operations"].values()}
        outs = page.evaluate("Object.values(COMPONENTS).filter(c => c.group === 'card').map(c => [c.output.type, c.output.about])")
        check("every card component outputs a credential about the subject of an operation", outs and all(a in abouts for _, a in outs), outs)
        check("the library is its groups and components: no blurbs, no footer",
              page.locator(".lib-blurb, .lib-foot, .lib-group p").count() == 0)
        check("while building, the side panel is hidden and the canvas takes its place",
              page.locator("#side").is_hidden() and page.evaluate("document.querySelector('.workbench').classList.contains('no-side')"))
        load_values = page.evaluate("[...document.querySelectorAll('#load-select option')].map(o => o.value)")
        check("the Load menu lists every card of the catalog, an empty canvas and a local graph.json",
              sorted(v[5:] for v in load_values if v.startswith("card:")) == sorted(CATALOG["cards"]) and "empty" in load_values and "file" in load_values, load_values)
        issuers = page.evaluate("EXAMPLE_ISSUERS")
        signed = {t for i in issuers for t in i["types"]}
        presentable = {t for t, c in CATALOG["credentials"].items() if c["presentable"]}
        check("every type a wallet may present has an example issuer, and none signs a type only components produce",
              presentable <= signed and signed <= presentable, f"missing {sorted(presentable - signed)}, not presentable {sorted(signed - presentable)}")

        # ---------- details popup
        page.locator('.lib-item[data-component="irb_clearance"] .lib-open').click()
        page.wait_for_timeout(80)
        ins = page.locator("#modal-inputs .vc").all_inner_texts()
        out = page.locator("#modal-output .vc").inner_text()
        check("details: IRBClearance shows three input credentials and its output",
              page.locator("#modal").is_visible() and len(ins) == 3 and "IRBClearanceCredential" in out.replace("\n", "") and "purposes" in out, f"{len(ins)} / {out!r}")
        subj = page.evaluate("[...document.querySelectorAll('#modal-inputs .vw')].map(v => [...v.classList].find(c => c.startsWith('s-')))")
        check("details: input cards are coloured by who they are about",
              subj == ["s-" + i["about"] for i in comps["irb_clearance"]["inputs"].values()] == ["s-project", "s-requester", "s-requester"], subj)
        rego_hidden = page.locator("#modal-rego").is_hidden()
        page.locator('#modal [data-act="toggle-rego"]').click()
        check("details: the Rego source on request, as in the catalog",
              rego_hidden and page.evaluate("document.getElementById('modal-rego-code').textContent") == comps["irb_clearance"]["rego"]
              and comps["irb_clearance"]["rego"].startswith("package pf.components.irb_clearance"))
        scan_jargon(page, "details IRBClearance")
        page.keyboard.press("Escape")
        page.wait_for_timeout(60)
        check("Escape closes the details", page.locator("#modal").is_hidden())
        bad = []
        for cid, c in comps.items():
            page.locator(f'.lib-item[data-component="{cid}"] .lib-open').click()
            got = page.evaluate("""() => ({
                n: document.querySelectorAll('#modal-inputs .vw').length,
                out: document.querySelector('#modal-output').innerText,
                pd: [...document.querySelectorAll('#modal .pd-list dt')].map(d => d.firstChild.textContent),
                rego: !!document.querySelector('#modal [data-act="toggle-rego"]'),
                none: (document.querySelector('#modal-no-rego') || {textContent: ''}).textContent,
                desc: document.querySelector('#modal .modal-desc').textContent,
                paras: document.querySelectorAll('#modal .modal-body > p').length })""")
            ok = (got["n"] == len(c["inputs"]) and got["pd"] == list(c["policy_data"]) and got["desc"] == c["summary"]
                  and c["output"]["type"] in got["out"].replace("\n", "")
                  and (got["rego"] if c["rego"] is not None else "Not written yet" in got["none"])
                  and got["paras"] == 1 + (not c["policy_data"]) + (c["rego"] is None))
            if not ok:
                bad.append(cid)
            page.locator('#modal-box .modal-foot [data-act="close-modal"]').click()
        check("details of every component: its summary and nothing more, its inputs, output, policy data, and its Rego or that it is not written yet",
              not bad, bad)
        page.locator('.lib-item[data-component="disease_specific_research_for_inference"] .lib-open').click()
        out = page.evaluate("[document.querySelector('#modal-output').innerText.replace(/\\n/g, ''), document.querySelectorAll('#modal .vc.cap').length, [...document.querySelector('#modal-output .vw').classList]]")
        check("details: an FL card component outputs a DataUseConditionCredential about the script, not a capability",
              "DataUseConditionCredential" in out[0] and "subject: script" in out[0] and out[1] == 0 and "s-script" in out[2], out)
        page.locator('#modal-box .modal-foot [data-act="close-modal"]').click()

        # ---------- build the IRB card from an empty canvas
        page.select_option("#load-select", "empty")
        page.wait_for_timeout(120)
        check("Empty canvas loads with no components", node_ids(page) == [] and page.locator("#count-checks").inner_text() == "1")
        page.fill("#card-name", CATALOG["cards"][IRB]["name"])
        for cid in IRB_ORDER:
            if cid == "ethics_approval_required":
                page.fill("#lib-search", "ethics")
                found = page.evaluate("[...document.querySelectorAll('.lib-item')].map(i => i.dataset.component)")
                check("the library filter matches names and credential types",
                      found == ["institutional_irb_approval", "ethics_approval_required"], found)
                page.fill("#lib-search", "EthicsApproval")
                check("a narrower filter finds just the card", page.locator(".lib-item").count() == 1)
            page.locator(f'.lib-item[data-component="{cid}"] .lib-add').click()
            page.wait_for_timeout(80)
            if cid == "ethics_approval_required":
                page.fill("#lib-search", "")
        check("four components added with the Add buttons", node_ids(page) == IRB_ORDER, node_ids(page))
        boxes = page.evaluate("[...document.querySelectorAll('#nodes .node')].map(n => { const r = n.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
        overlap = sum(1 for i, a in enumerate(boxes) for b in boxes[i + 1:] if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
        check("added components and the capability do not overlap", overlap == 0 and len(boxes) == 5, f"{overlap} / {len(boxes)}")
        cap = page.evaluate("""(() => { const c = document.querySelector('#nodes .node.capability');
            return [c.querySelector('#cap-operation').value, [...c.querySelectorAll('#cap-operation option')].map(o => o.value), c.querySelectorAll('.n-in').length,
                    Math.min(...[...document.querySelectorAll('#nodes .node[data-node]')].map(n => c.getBoundingClientRect().left - n.getBoundingClientRect().right))]; })()""")
        check("with no operation chosen and no component required, the capability is drawn right of every component, with no inputs, "
              "and its card offers the catalog's operations",
              cap[0] == "" and cap[1] == ["", *CATALOG["operations"]] and cap[2] == 0 and cap[3] > 0, cap)
        page.screenshot(path=SHOTS / "composer-light-added.png")

        # drag them into columns by their Policy Component shapes
        for _ in range(12):
            if page.evaluate("ui.view.k") < 0.42:
                break
            page.locator("#zoom-out").click()
        k = page.evaluate("ui.view.k")
        ox, oy = page.evaluate("[(-ui.view.x + 40) / ui.view.k, (-ui.view.y + 70) / ui.view.k]")
        # added in the committed order, they sit in that order from the top left; each drop lands where a component
        # already moved away from
        layout = {"project_membership": (0, 0), "institutional_irb_approval": (0, 300), "irb_clearance": (500, 90),
                  "ethics_approval_required": (1000, 230)}
        for nid, (tx, ty) in layout.items():
            nx, ny = page.evaluate(f"[S.nodes['{nid}'].x, S.nodes['{nid}'].y]")
            x, y = grab_point(page, nid)
            drag(page, x, y, x + (ox + tx - nx) * k, y + (oy + ty - ny) * k)
            page.wait_for_timeout(40)
        moved = page.evaluate("Object.fromEntries(Object.values(S.nodes).map(n => [n.id, [n.x, n.y]]))")
        off = max(abs(moved[n][0] - (ox + tx)) + abs(moved[n][1] - (oy + ty)) for n, (tx, ty) in layout.items())
        check("components dragged by their shapes into columns", off < 6, off)
        card = page.evaluate("""(() => { const n = document.querySelector('.node[data-node="ethics_approval_required"]');
            return [!!n.querySelector('.pc'), n.querySelector('.pc-tab').textContent, n.querySelector('.pc').innerText.trim(),
                    getComputedStyle(n.querySelector('.pc')).borderTopWidth, n.querySelectorAll('[class*="hex"], [data-hex]').length]; })()""")
        check("the card component is a Policy Component with its tab; it takes no policy data, so it shows its name only",
              card == [True, "Policy Component", "EthicsApprovalRequired", "4px", 0], card)
        seals = page.evaluate("[...document.querySelectorAll('#nodes .vw')].every(w => { const s = w.querySelector(':scope > .seal').getBoundingClientRect(), c = w.querySelector('.vc').getBoundingClientRect(); return s.left < c.left && s.top < c.top && s.right > c.left && s.bottom > c.top; })")
        subj = page.evaluate("[...document.querySelectorAll('#nodes .vc .subj')].length === document.querySelectorAll('#nodes .vw').length")
        check("every credential has its seal on the top-left corner and a subject section", seals and subj, [seals, subj])
        page.locator("#zoom-fit").click()
        page.wait_for_timeout(80)

        # wire by clicking an output, then an input
        wire_by_clicks(page, "project_membership", "irb_clearance", "approval")
        text = toast(page)
        check("a wire between different credential types is refused with a toast",
              "takes InstitutionalIRBApprovalCredential" in text and page.evaluate("S.wires.length") == 0, text)
        page.locator('.n-out[data-node="project_membership"] .vc-h').click()
        hl = page.evaluate("[...document.querySelectorAll('.n-in.ok')].map(e => e.dataset.node + '.' + e.dataset.input)")
        check("while wiring, only inputs of the same credential type are highlighted", hl == ["irb_clearance.membership"], hl)
        check("while wiring, nothing but the highlight says so: no banner", page.locator("#banner, .banner").count() == 0)
        page.keyboard.press("Escape")
        page.locator("#toast").evaluate("t => { t.hidden = true; }")   # the refused wire's
        for src, dst, inp in [("project_membership", "irb_clearance", "membership"), ("institutional_irb_approval", "irb_clearance", "approval"),
                              ("irb_clearance", "ethics_approval_required", "clearance")]:
            wire_by_clicks(page, src, dst, inp)
        check("three wires made by clicking, with no toast for each", page.evaluate("S.wires.length") == 3 and page.locator("#toast").is_hidden())
        lanes = page.evaluate("""[...document.querySelectorAll('#nodes .n-in.lane[data-node]')].map(e => [e.dataset.node + '.' + e.dataset.input, e.children.length, e.innerText]).sort()""")
        check("a wired input is an empty lane, no card: the credential is drawn once, at the output it comes from",
              lanes == [[x, 0, ""] for x in IRB_LANES], lanes)
        ends = page.evaluate("""S.wires.map(w => {
            const path = document.querySelector(`.wire-hit[data-wire="${w.id}"]`), p = path.getPointAtLength(path.getTotalLength()).matrixTransform(path.getScreenCTM());
            const pc = document.querySelector(`.node[data-node="${w.to}"] .pc`).getBoundingClientRect();
            const out = document.querySelector(`.n-out[data-node="${w.from}"] .vc`).getBoundingClientRect();
            const q = path.getPointAtLength(0).matrixTransform(path.getScreenCTM());
            return [w.to, Math.round(pc.left - p.x), p.y > pc.top && p.y < pc.bottom, Math.round(q.x - out.right), Math.abs(q.y - (out.top + out.height / 2)) < 2]; })""")
        check("each wire runs from the output credential straight into the Policy Component that reads it",
              all(0 < dx < 12 and inside and -1 <= ox <= 8 and level for _, dx, inside, ox, level in ends) and len(ends) == 3, ends)
        issues = page.locator("#tray-body .issue .txt").all_inner_texts()
        check("before the capability is set, Checks says it has no operation and requires no component, and flags the card's unused output",
              page.locator("#count-checks").inner_text() == "3"
              and issues == ["The capability has no operation.", "The capability requires no component.",
                             "EthicsApprovalRequired's output is neither wired nor required."], issues)
        check("with no operation chosen, every component's output has a required switch",
              sorted(page.evaluate("[...document.querySelectorAll('#nodes .n-out [data-act=require]')].map(i => i.dataset.node)")) == sorted(IRB_ORDER))
        choose_operation(page, "do_download")
        rows = page.evaluate("[...document.querySelectorAll('#nodes .n-out [data-act=require]')].map(i => i.dataset.node)")
        check("choosing do_download on the capability's card leaves the required switch on the outputs about the requester",
              sorted(rows) == ["ethics_approval_required", "irb_clearance", "project_membership"] and page.locator("#toast").is_hidden(), rows)
        params = page.evaluate("[...document.querySelectorAll('#nodes .node.capability [data-parameter]')].map(e => [e.dataset.parameter, e.dataset.type, e.querySelector('.vc-t').innerText.replace(/\\n/g, '')])")
        check("the capability draws the operation's parameter as the credential it is read from, a publicKeyCredential, with no subtitle",
              params == [["channel_key", "publicKeyCredential", "publicKeyCredential"]]
              and "channel_key" in page.locator("#nodes .node.capability .vc.cap .cl").inner_text(), params)
        require(page, "ethics_approval_required")
        check("switching required on at the card component's output: the capability requires it, through an empty lane; Checks says OK",
              page.evaluate("S.requires") == ["ethics_approval_required"] and page.locator("#count-checks").inner_text() == "OK"
              and page.evaluate("[...document.querySelectorAll('#nodes .node.capability [data-requires]')].map(e => [e.dataset.requires, e.children.length])") == [["ethics_approval_required", 0]]
              and page.locator("#rqc-ethics_approval_required").is_checked(),
              page.locator("#tray-body").inner_text()[:300])
        choose_operation(page, "do_inference")
        issues = page.locator("#tray-body .issue .txt").all_inner_texts()
        check("do_inference while the capability requires a component about the requester: Checks says so, its switch stays on to turn off, "
              "and the capability reads script_digest instead",
              issues == ["do_inference is about the script, but EthicsApprovalRequired's output is about the requester."]
              and page.locator("#rqc-ethics_approval_required").is_checked()
              and page.evaluate("[...document.querySelectorAll('#nodes .node.capability [data-parameter]')].map(e => e.dataset.type)") == ["ScriptHashCredential"],
              issues)
        choose_operation(page, "do_download")
        accepting = page.evaluate("[...document.querySelectorAll('#nodes .n-out [data-act=accept]')].map(i => i.dataset.node).sort()")
        check("accept presented is a switch on an output wired to an input, when a wallet may present its credential",
              accepting == IRB_ACCEPTED and page.locator("#nodes .n-in [data-act=accept]").count() == 0, accepting)
        subtitles = page.evaluate("""[document.querySelectorAll('#nodes .vc-id, #nodes .vc-sub:not(.vc.cap .vc-sub)').length,
            [...document.querySelectorAll('#nodes .vw .vc-t')].filter(t => t.innerText.replace(/\\n/g, '') !== t.closest('.n-in, .n-out').dataset.type).length]""")
        check("no credential has a subtitle: its type, nothing under it (no input name, no 'presented')", subtitles == [0, 0], subtitles)
        legend = page.locator("#legend").inner_text().replace("\n", " | ")
        check("legend shows only what is on the canvas",
              all(t in legend for t in ("the requester", "the project", "the PI", "the ethics committee", "Policy Component", "capability"))
              and not any(t in legend for t in ("the script", "compute node", "terms document", "an institution", "wire")), legend)
        canvas_text = page.locator("#nodes").inner_text()
        claims = page.evaluate("[...document.querySelectorAll('#nodes .cl li')].map(l => l.textContent.trim())")
        check("claims are inside the cards; subject is never listed; outputs list claim names only",
              "subject" not in claims and "←" not in canvas_text and "<-" not in canvas_text and "purposes" in claims)
        shapes = page.evaluate("""(() => [[...document.querySelectorAll('#nodes .node[data-node]')].every(n => n.querySelector('.pc') && n.querySelector('.pc-tab').textContent === 'Policy Component'),
            getComputedStyle(document.querySelector('#nodes .node.capability .vc.cap .vc-h')).backgroundColor,
            document.querySelectorAll('#nodes .vc.cap').length, document.querySelectorAll('#nodes .node.capability .pc').length])()""")
        check("every component is a Policy Component; the capability, drawn once, is a solid amber card and no component",
              shapes[0] and shapes[1] == AMBER and shapes[2] == 1 and shapes[3] == 0, shapes)
        page.screenshot(path=SHOTS / "composer-light-built.png")

        irb = json.loads(COMMITTED[IRB])
        off_graph = json.loads(COMMITTED[IRB])
        for n, i in IRB_SHORTCUTS:
            off_graph["nodes"][n]["inputs"][i]["accept_presented"] = False
        for t in ("IRBClearanceCredential", "ProjectMembershipCredential"):
            del off_graph["trusted_issuers"][t]
        built = graph_json(page)
        check("with accept presented off, the JSON reads only the wired outputs there, and those types leave trusted_issuers", built == off_graph,
              json.dumps(built["trusted_issuers"]))
        scan_jargon(page, "JSON tab")

        # ---------- simulate
        v = verdict(page)
        titles = page.locator("#side .side-card h2").all_inner_texts()
        check("Simulate: the side panel opens beside the canvas with Policy data, Trusted issuers and Presented credentials, titles only",
              titles == ["Policy data", "Trusted issuers", "Presented credentials"] and page.locator("#side").is_visible()
              and page.locator("#side .side-card > header").all_inner_texts() == titles, titles)
        sep = page.evaluate("""(() => { const b = [...document.querySelectorAll('#side .side-card')].map(c => c.getBoundingClientRect());
            return b.every((r, i) => i === 0 || r.top >= b[i - 1].bottom + 4); })()""")
        check("the three sections do not overlap", sep)
        fits = page.evaluate("""(() => { const c = document.getElementById('canvas').getBoundingClientRect();
            return [...document.querySelectorAll('#nodes .node')].every(n => { const r = n.getBoundingClientRect(); return r.left >= c.left - 1 && r.right <= c.right + 1; }); })()""")
        check("opening the side panel refits the card to the narrower canvas", fits)
        check("Simulate is a tab name and a result, with no notes", page.locator("#tab-sim").inner_text() == "Simulate" and page.locator("#tray-body .note").count() == 0)
        presented = page.evaluate("[...document.querySelectorAll('[data-act=sim-present]')].filter(i => i.checked).map(i => i.dataset.type).sort()")
        check("every required credential ticked, from a trusted issuer", presented == sorted(off_graph["trusted_issuers"]), presented)
        check("allow: the capability is issued", v == "Capability issued", v)
        check("allow: the capability says it is issued, and its parameter's credential presented",
              page.locator("#nodes .node.capability .vc.cap .st.good").inner_text() == "✓ issued"
              and page.locator('#nodes .node.capability [data-parameter="channel_key"] .st.good').inner_text() == "✓")
        run = chips(page, "#sim-order")
        check("allow: components run producers first, the required card component last",
              run == ["1 InstitutionalIRBApproval", "2 ProjectMembership", "3 IRBClearance", "4 EthicsApprovalRequired"], run)
        badges = page.locator("#nodes .order").all_inner_texts()
        check("allow: run order shown on the canvas", sorted(badges) == ["1", "2", "3", "4"], badges)
        scan_jargon(page, "Simulate allow")
        page.locator("#pc-IRBApprovalCredential").uncheck()
        v = verdict(page)
        check("deny: IRBApprovalCredential dropped -> no capability, named as missing",
              v.startswith("No capability") and "IRBApprovalCredential (not presented)" in v, v)
        cannot = [c for c in chips(page, "#sim-order") if "cannot run" in c]
        check("deny: the components that depend on it cannot run", len(cannot) == 3 and cannot[0].startswith("1 InstitutionalIRBApproval"), cannot)
        check("deny: the input says it is missing",
              page.locator('.n-in[data-node="institutional_irb_approval"][data-input="irb"] .st.bad').inner_text() == "missing")
        page.screenshot(path=SHOTS / "composer-light-deny.png")
        page.locator("#pc-IRBApprovalCredential").check()
        page.locator("#pc-publicKeyCredential").uncheck()
        v = verdict(page)
        run = chips(page, "#sim-order")
        check("deny: without the credential its parameter is read from, every component runs but no capability is issued",
              v.startswith("No capability") and "publicKeyCredential (not presented)" in v and len(run) == 4
              and not any("cannot run" in c for c in run)
              and page.locator('#nodes .node.capability [data-parameter="channel_key"] .st.bad').inner_text() == "missing"
              and page.locator("#nodes .node.capability .vc.cap .st.bad").inner_text() == "not issued", f"{v} | {run}")
        page.locator("#pc-publicKeyCredential").check()
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:unknown")
        v = verdict(page)
        check("deny: IRBApprovalCredential from an unknown issuer does not count, and its input says untrusted",
              v.startswith("No capability") and "(signed by an unknown issuer, not trusted)" in v
              and page.locator('.n-in[data-node="institutional_irb_approval"][data-input="irb"] .st.bad').inner_text() == "untrusted", v)
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:hospital-irb")
        check("with none ticked, every example issuer that signs the type is trusted: City Hospital IRB counts; the panel says so once",
              verdict(page).startswith("Capability issued") and page.locator("#side-trust .hint").all_inner_texts() == ["None ticked: all trusted."])
        page.locator('[data-act="trust"][data-type="IRBApprovalCredential"][data-issuer="did:example:dac"]').check()
        v = verdict(page)
        check("deny: trusting only the Data Access Committee turns City Hospital IRB's credential away",
              v.startswith("No capability") and "(signed by City Hospital IRB, not trusted)" in v, v)
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:dac")
        check("allow again with the trusted issuer", verdict(page).startswith("Capability issued"))
        page.locator('[data-act="trust"][data-type="IRBApprovalCredential"][data-issuer="did:example:dac"]').uncheck()
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:hospital-irb")
        check("untrusting it empties the list, which trusts every example issuer again; Checks stays OK (no 'no issuer is trusted' error)",
              verdict(page).startswith("Capability issued") and page.locator("#count-checks").inner_text() == "OK")
        check("the Simulate values did not change the JSON", graph_json(page) == off_graph)

        # ---------- accept presented at the two outputs a wallet may also present
        page.locator("#tab-checks").click()
        check("back on Checks, the side panel closes and the capability still issues do_download",
              page.locator("#side").is_hidden() and page.evaluate("document.getElementById('cap-operation').value") == "do_download")
        page.locator('label[for="apc-irb_clearance"]').click()
        page.wait_for_timeout(60)
        g = graph_json(page)
        check("accept presented at IRBClearance's output: saved on the input it is wired to, with an empty trusted_issuers list for IRBClearanceCredential",
              g["nodes"]["ethics_approval_required"]["inputs"]["clearance"] == {"from": "node", "node": "irb_clearance", "accept_presented": True}
              and g["trusted_issuers"].get("IRBClearanceCredential") == [] and page.locator("#apc-irb_clearance").is_checked(), json.dumps(g["trusted_issuers"]))
        v = verdict(page)
        run = chips(page, "#sim-order")
        check("not presented yet: the components upstream still run", v.startswith("Capability issued") and len(run) == 4, f"{v} | {run}")
        page.locator('[data-act="sim-preset"][data-preset="none"]').click()
        for t in ("IRBClearanceCredential", "IntendedDataUseCredential", "publicKeyCredential"):
            page.locator(f"#pc-{t}").check()
        v = verdict(page)
        run, skipped = chips(page, "#sim-order"), chips(page, "#sim-skipped")
        check("presenting an IRBClearanceCredential skips the upstream components",
              v.startswith("Capability issued") and run == ["1 EthicsApprovalRequired"]
              and sorted(skipped) == ["IRBClearance", "InstitutionalIRBApproval", "ProjectMembership"], f"{v} | {run} | {skipped}")
        dim = page.evaluate("[...document.querySelectorAll('.node.dim')].map(n => n.dataset.node).sort()")
        check("skipped components are dimmed on the canvas", dim == ["institutional_irb_approval", "irb_clearance", "project_membership"], dim)
        check("the presented credential is listed as used instead",
              chips(page, "#sim-instead") == ["IRBClearanceCredential → EthicsApprovalRequired"], chips(page, "#sim-instead"))
        page.screenshot(path=SHOTS / "composer-light-accept-presented.png")
        page.locator('[data-act="trust"][data-type="IRBClearanceCredential"][data-issuer="did:example:research-office"]').check()
        page.select_option("#pc-IRBClearanceCredential-issuer", "did:example:hospital-irb")
        v = verdict(page)
        check("an IRBClearanceCredential from an untrusted issuer does not skip anything; without the other credentials: no capability",
              v.startswith("No capability") and len(chips(page, "#sim-order")) == 4, v)
        page.locator("#tab-checks").click()
        page.locator('label[for="apc-project_membership"]').click()
        page.wait_for_timeout(60)
        text = graph_text(page)
        check("the IRB card built from the library, accept presented on at its two outputs, equals policy_cards/ethics-approval-required/graph.json",
              json.loads(text) == irb and text.encode() == COMMITTED[IRB], text[:200])
        name, data = download(page)
        check("Download saves that file: graph.json, byte for byte", name == "graph.json" and data == COMMITTED[IRB], name)
        page.locator("#tab-json").click()
        name, data = download(page, '[data-act="download-json"]')
        page.locator('[data-act="copy-json"]').click()
        page.wait_for_timeout(100)
        clip = page.evaluate("navigator.clipboard.readText()")
        check("the Graph JSON tab's Download and Copy give the same file", data == COMMITTED[IRB] and clip.encode() == COMMITTED[IRB], toast(page))
        page.locator('.lib-item[data-component="project_membership"] .lib-add').click()
        page.wait_for_timeout(80)
        check("a component added twice gets the id _2, shown as (2)",
              "project_membership_2" in node_ids(page) and page.locator('.node[data-node="project_membership_2"] .pc-nm').inner_text().replace("\n", "") == "ProjectMembership (2)")
        page.locator("#zoom-fit").click()
        page.locator('.n-out[data-node="project_membership_2"] .vc-h').click()
        hl = page.evaluate("[...document.querySelectorAll('.n-in.ok')].map(e => e.dataset.node + '.' + e.dataset.input)")
        page.keyboard.press("Escape")
        check("while wiring, an input that already takes a wire is not highlighted", hl == [], hl)
        refused = page.evaluate("tryConnect('project_membership_2', 'irb_clearance', 'membership')")
        text = toast(page)
        check("a second wire into a wired input is refused, naming the output it takes",
              refused is False and text == "That input already takes the output of ProjectMembership."
              and len([w for w in page.evaluate("S.wires") if w["to"] == "irb_clearance" and w["input"] == "membership"]) == 1, text)
        check("an output wired to nothing has no accept presented switch", page.locator('#apc-project_membership_2').count() == 0)
        page.locator('.node[data-node="project_membership_2"] [data-act="node-remove"]').click(force=True)
        page.wait_for_timeout(60)
        check("removing it gives back the committed IRB graph", graph_text(page).encode() == COMMITTED[IRB])

        # ---------- arrange
        page.locator("#arrange").click()
        xs = page.evaluate("Object.fromEntries(Object.values(S.nodes).map(n => [n.id, n.x]))")
        cap_left = page.evaluate("CAPGEO.x - S.nodes.ethics_approval_required.x - GEO.ethics_approval_required.w")
        check("Arrange lays the components out from left to right, and the capability follows the component it requires",
              xs["institutional_irb_approval"] == xs["project_membership"] < xs["irb_clearance"] < xs["ethics_approval_required"] and cap_left == 64,
              f"{xs} / {cap_left}")

        # ---------- every card: Load, then Download, before and after typing on the Simulate tab
        errs, caps = {}, {}
        for folder in sorted(CATALOG["cards"]):
            want = COMMITTED[folder]
            load_card(page, folder)
            if node_ids(page) != list(json.loads(want)["nodes"]) or page.locator("#count-checks").inner_text() != "OK":
                errs[folder] = page.locator("#tray-body").inner_text()[:200]
            capability = json.loads(want)["capability"]
            drawn = page.evaluate("""(() => { const c = document.querySelector('#nodes .node.capability');
                return [c.querySelector('#cap-operation').value, [...c.querySelectorAll('.vc.cap .cl li')].map(l => l.textContent),
                        [...c.querySelectorAll('.n-in.lane[data-requires]')].map(e => e.dataset.requires), [...c.querySelectorAll('[data-parameter]')].map(e => e.dataset.type),
                        [...document.querySelectorAll('#nodes [data-act=require]:checked')].map(i => i.dataset.node),
                        [...document.querySelectorAll('#nodes [data-act=accept]:checked')].map(i => i.dataset.node).sort()]; })()""")
            graph = json.loads(want)
            accepted = sorted({s["node"] for n in graph["nodes"].values() for s in n["inputs"].values() if s["from"] == "node" and s["accept_presented"]})
            if drawn != [capability["operation"], list(capability["parameters"]), capability["requires"],
                         [p["type"] for p in capability["parameters"].values()], capability["requires"], accepted]:
                caps[folder] = drawn
            first = download(page)
            page.locator("#tab-sim").click()
            for field in page.locator('#side-pd input[data-act="pd"]').all():
                field.fill("example-1, example-2")
            for t in page.evaluate("[...new Set([...document.querySelectorAll('#side-trust [data-act=trust]')].map(i => i.dataset.type))]"):
                page.locator(f'#side-trust [data-act="trust"][data-type="{t}"]').first.check()
            page.locator('[data-act="sim-preset"][data-preset="none"]').click()
            page.locator('#side-presented [data-act="sim-present"]').first.check()
            typed = page.evaluate("[...document.querySelectorAll('#side-pd input')].every(i => i.value === 'example-1, example-2')")
            second = download(page)
            text = graph_text(page)
            check(f"Load then Download gives back policy_cards/{folder}/graph.json byte for byte, also after Simulate values",
                  first == second == ("graph.json", want) and text.encode() == want and typed, f"{len(first[1])} / {len(second[1])} / {len(want)} bytes")
            page.locator("#tab-checks").click()
        check("Load opens each of the 23 cards, in the file's node order, with no check errors", not errs and len(CATALOG["cards"]) == 23, errs)
        check("each loaded card draws its capability: the operation and its parameters, a lane for each node it requires and the "
              "credential each parameter is read from, required switched on at those nodes, and accept presented on at the outputs "
              "its inputs accept presented", not caps, caps)

        # ---------- the DS card: policy data stays out of the JSON
        load_card(page, DS)
        page.locator("#tab-sim").click()
        page.fill("#pd-disease_specific_research-allowedDiseases", "MONDO:0005148, MONDO:0005015")
        page.wait_for_timeout(60)
        text = graph_text(page)
        g = json.loads(text)
        check("DS: Disease Specific Research is ProjectMembership and its card component, which its do_download capability requires",
              list(g["nodes"]) == ["project_membership", "disease_specific_research"]
              and g["capability"]["operation"] == "do_download" and g["capability"]["requires"] == ["disease_specific_research"]
              and g["nodes"]["disease_specific_research"]["inputs"]["intendedDataUse"] == {"from": "presented"})
        check("DS: the policy data typed on the Simulate tab stays out of the JSON (no example codes in it)",
              g["nodes"]["disease_specific_research"]["policy_data"] == {} and "MONDO" not in text and text.encode() == COMMITTED[DS])
        check("DS checks OK and simulates allow", page.locator("#count-checks").inner_text() == "OK" and verdict(page).startswith("Capability issued"))
        page.screenshot(path=SHOTS / "composer-light-ds-simulate.png")
        legend = page.locator("#legend").inner_text()
        check("legend follows the canvas (no ethics committee on the DS card)", "ethics committee" not in legend and "the PI" in legend, legend)
        page.fill("#pd-disease_specific_research-allowedDiseases", "")
        page.wait_for_timeout(60)
        check("an empty policy data value raises no warning: values are the asset owner's", page.locator("#count-checks").inner_text() == "OK")
        page.locator("#tab-checks").click()
        page.evaluate("ui.view = { x: 30, y: 60, k: 1 }; applyView();")
        page.screenshot(path=SHOTS / "composer-ds-zoom.png")

        # ---------- two cards the capability requires
        page.select_option("#load-select", "empty")
        page.fill("#card-name", "Two cards on one dataset")
        both = ["geographical_restriction", "institution_specific_restriction"]
        for cid in both:
            page.locator(f'.lib-item[data-component="{cid}"] .lib-add').click()
            page.wait_for_timeout(80)
        page.locator("#arrange").click()
        page.wait_for_timeout(60)
        choose_operation(page, "do_download")
        for cid in both:
            require(page, cid)
        page.locator("#arrange").click()
        g = graph_json(page)
        check("required on at both cards: the capability requires both, in that order, with do_download's parameters, and draws a lane for each",
              g["capability"] == {"operation": "do_download", "requires": both, "parameters": CATALOG["operations"]["do_download"]["parameters"]}
              and page.evaluate("[...document.querySelectorAll('#nodes .node.capability [data-requires]')].map(e => e.dataset.requires)") == both
              and list(g["trusted_issuers"]) == ["AffiliationCredential", "LocationCredential", "publicKeyCredential"], json.dumps(g["capability"]))
        check("it checks OK, and every input is bound to one source",
              page.locator("#count-checks").inner_text() == "OK" and all(isinstance(s, dict) for n in g["nodes"].values() for s in n["inputs"].values()))
        check("Simulate: the capability is issued when both cards ran", verdict(page).startswith("Capability issued") and len(chips(page, "#sim-order")) == 2)
        page.locator("#pc-LocationCredential").uncheck()
        v = verdict(page)
        run = chips(page, "#sim-order")
        check("Simulate: without one card's credential no capability is issued, though the other card runs",
              v.startswith("No capability") and "LocationCredential (not presented)" in v and "GeographicalRestriction · cannot run" in " ".join(run)
              and any(c.endswith("InstitutionSpecificRestriction") for c in run), run)
        page.screenshot(path=SHOTS / "composer-light-two-required.png")
        name, two = download(page)
        with tempfile.TemporaryDirectory() as tmp:
            def open_file(file, change):
                broken = json.loads(two)
                change(broken)
                Path(tmp, file).write_text(json.dumps(broken))
                page.set_input_files("#load-file", str(Path(tmp, file)))
                page.wait_for_timeout(150)
                return toast(page)

            Path(tmp, "two.json").write_bytes(two)
            page.select_option("#load-select", "empty")
            page.set_input_files("#load-file", str(Path(tmp, "two.json")))
            page.wait_for_timeout(150)
            check("Load reads a local graph.json whose capability requires two nodes, with no toast",
                  node_ids(page) == both and page.evaluate("S.requires") == both and page.locator("#toast").is_hidden(), toast(page))
            check("Load then Download of that file gives it back byte for byte", download(page)[1] == two)
            kept = lambda: page.evaluate("S.requires") == both
            text = open_file("list.json", lambda b: b["nodes"]["geographical_restriction"]["inputs"].update(location=[{"from": "presented"}]))
            check("a list of sources is refused, saying what a source is, and the canvas is kept",
                  "Could not open list.json" in text and "a source is" in text and kept(), text)
            text = open_file("old.json", lambda b: b.update(version=2))
            check("a graph of another version is refused", "Could not open old.json" in text and "version 2" in text and kept(), text)
            text = open_file("unknown.json", lambda b: b["nodes"]["geographical_restriction"].update(component="grant_download"))
            check("a graph with a component the repository does not have (Grant download) is refused",
                  "grant_download, which is not in this repository" in text and kept(), text)
            text = open_file("operation.json", lambda b: b["capability"].update(operation="do_everything"))
            check("a capability whose operation is not the catalog's is refused, naming the operations",
                  '"do_everything", which is not an operation here: do_download or do_inference' in text and kept(), text)
            text = open_file("parameters.json", lambda b: b["capability"].update(parameters={}))
            check("a capability whose parameters are not its operation's is refused", "parameters are not those do_download reads" in text and kept(), text)
            text = open_file("requires.json", lambda b: b["capability"].update(requires=["grant_download"]))
            check("a capability that requires a node the graph does not have is refused",
                  '"grant_download", which the graph does not have' in text and kept(), text)
            open_file("draft.json", lambda b: b["capability"].update(requires=[]))
            page.locator("#tab-checks").click()
            check("a graph whose capability requires no node yet opens, as the composer writes a draft, and Checks says so",
                  page.evaluate("S.requires") == [] and page.locator("#count-checks").inner_text() == "3"
                  and "requires no component" in page.locator("#tray-body").inner_text())
            # the IRB card with a second EthicsApprovalRequired reading IRBClearance: the two inputs reading it must agree
            irb2 = json.loads(COMMITTED[IRB])
            irb2["nodes"]["ethics_approval_required_2"] = json.loads(json.dumps(irb2["nodes"]["ethics_approval_required"]))
            Path(tmp, "agree.json").write_text(json.dumps(irb2, indent=2) + "\n")
            page.set_input_files("#load-file", str(Path(tmp, "agree.json")))
            page.wait_for_timeout(150)
            check("an output read by two inputs that both accept it presented opens with its switch on, and Download gives the file back",
                  node_ids(page) == list(irb2["nodes"]) and page.locator("#apc-irb_clearance").is_checked()
                  and json.loads(download(page)[1]) == irb2)
            irb2["nodes"]["ethics_approval_required_2"]["inputs"]["clearance"]["accept_presented"] = False
            Path(tmp, "disagree.json").write_text(json.dumps(irb2))
            page.set_input_files("#load-file", str(Path(tmp, "disagree.json")))
            page.wait_for_timeout(150)
            text = toast(page)
            check("an output read by two inputs that disagree on accept_presented is refused: the composer sets it once per output",
                  "Could not open disagree.json" in text and "disagree on accept_presented" in text and "ethics_approval_required_2" in node_ids(page), text)
            page.set_input_files("#load-file", str(Path(tmp, "two.json")))
            page.wait_for_timeout(150)
        page.locator("#tab-checks").click()
        require(page, "geographical_restriction")
        issues = page.locator("#tray-body .issue .txt").all_inner_texts()
        g = graph_json(page)
        check("switching required off at one card leaves the other required, and Checks flags the card that now leads to nothing",
              g["capability"]["requires"] == ["institution_specific_restriction"] and page.locator("#count-checks").inner_text() == "1"
              and issues == ["GeographicalRestriction's output is neither wired nor required."], issues)

        # ---------- the draft survives a reload, without the Simulate values; drafts that do not read are refused
        load_card(page, DS)
        x, y = center(page, '.node[data-node="disease_specific_research"] [data-comp]')
        drag(page, x, y, x + 60, y + 40)
        page.locator("#tab-sim").click()
        page.fill("#pd-disease_specific_research-allowedDiseases", "MONDO:0005015")
        places = "[Object.values(S.nodes).map(n => [n.id, n.x, n.y]), [CAPGEO.x, CAPGEO.y]]"
        before = (graph_text(page), page.evaluate(places))
        page.wait_for_timeout(400)
        page.reload()
        ready(page)
        after = (graph_text(page), page.evaluate(places))
        page.locator("#tab-sim").click()
        check("reload keeps the draft (components, wires, accept presented, the capability, places) but not the Simulate values",
              after == before and page.locator("#pd-disease_specific_research-allowedDiseases").input_value() == "", f"{before[1]} / {after[1]}")
        page.wait_for_timeout(400)   # let the draft save the page does after loading run first; leaving the page flushes a pending one
        page.evaluate("""localStorage.setItem('pf-policy-composer-v5', JSON.stringify({v: 5, positions: {},
            graph: {version: 2, name: 'Old', root: null, nodes: {}, trusted_issuers: {}}}))""")
        page.reload()
        ready(page)
        text = toast(page)
        check("a saved draft that does not read (a version 2 graph) is not restored, and the page says why",
              node_ids(page) == [] and "Your saved draft was not restored" in text and "version 2" in text, text)
        page.wait_for_timeout(400)
        page.evaluate("""localStorage.clear(); localStorage.setItem('pf-policy-composer-v4', JSON.stringify({v: 4, name: 'Old draft',
            nodes: {project_membership: {id: 'project_membership', component: 'project_membership', x: 0, y: 0, data: {}, accept: {}}}, wires: [], trusted: {}, seq: 1}))""")
        page.reload()
        ready(page)
        check("the mock's drafts are not read", node_ids(page) == [] and page.locator("#toast").is_hidden())

        # ---------- theme on its own, screenshots
        load_card(page, IRB)
        page.locator("#toast").evaluate("t => { t.hidden = true; }")
        page.screenshot(path=SHOTS / "composer-irb.png")
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(150)
        bg = page.evaluate("[getComputedStyle(document.getElementById('canvas')).backgroundColor, document.documentElement.hasAttribute('data-theme')]")
        check("opened on its own, the composer follows prefers-color-scheme (dark)", bg == [DARK_SUNK, False], bg)
        page.screenshot(path=SHOTS / "composer-irb-dark.png")
        page.locator("#tab-sim").click()
        page.screenshot(path=SHOTS / "composer-irb-simulate-dark.png")
        page.locator("#tab-checks").click()
        page.emulate_media(color_scheme="light")
        page.wait_for_timeout(150)
        page.locator('.lib-item[data-component="irb_clearance"] .lib-open').click()
        page.locator('#modal [data-act="toggle-rego"]').click()
        page.wait_for_timeout(80)
        page.screenshot(path=SHOTS / "composer-details.png")
        page.keyboard.press("Escape")
        for tab in ("checks", "sim", "json"):
            page.locator(f"#tab-{tab}").click()
            scan_jargon(page, tab)
        check("no jargon in the UI text (fact, slot, binding, planner, parity, AccessCondition)", not jargon_seen, sorted(jargon_seen))

        # ---------- phone width
        page.locator("#tab-checks").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        check("phone width: no page-level horizontal scroll", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),
              page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"))
        fits = page.evaluate("""(() => { const c = document.getElementById('canvas').getBoundingClientRect();
            return [...document.querySelectorAll('.node')].every(n => { const r = n.getBoundingClientRect(); return r.left >= c.left - 1 && r.right <= c.right + 1; }); })()""")
        check("phone width: Fit shows the whole card on the canvas", fits)
        page.screenshot(path=SHOTS / "composer-phone-light.png", full_page=True)
        page.emulate_media(color_scheme="dark")
        page.locator("#tab-sim").click()
        page.wait_for_timeout(150)
        page.screenshot(path=SHOTS / "composer-phone-dark.png", full_page=True)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.emulate_media(color_scheme="light")
        check("no console errors in the composer", not errors, "; ".join(errors[:3]))

        # ---------- the docs page frames the app, and the app follows the docs site's theme
        docs = ctx.new_page()
        docs_errors = []
        track_errors(docs, BASE, docs_errors)
        docs.goto(BASE + "/composer/")
        docs.frame_locator("iframe.pf-composer-frame").locator("html[data-ready=true]").wait_for(state="attached")
        frame = next(f for f in docs.frames if f.url == APP)
        link = docs.locator("a.md-button")
        href = docs.evaluate("document.querySelector('a.md-button').href")
        check("the docs page at composer/ frames the app at composer/app/, and links to it on a page of its own",
              docs.evaluate("document.querySelector('iframe.pf-composer-frame').src") == APP and href == APP
              and urllib.request.urlopen(href).status == 200 and "own" in link.inner_text())
        frame.locator("#tab-sim").click()
        layout_ok = frame.evaluate("""(() => { const s = document.querySelector('.stage').getBoundingClientRect(), d = document.querySelector('.side').getBoundingClientRect();
            return d.left >= s.right && document.documentElement.scrollWidth <= window.innerWidth; })()""")
        frame.locator("#tab-checks").click()
        check("at 1440px the framed composer has its full layout, on Simulate the side panel beside the canvas", layout_ok)
        frame.select_option("#load-select", "card:" + IRB)
        frame.wait_for_timeout(100)
        docs.locator("iframe.pf-composer-frame").scroll_into_view_if_needed()
        docs.wait_for_timeout(500)   # the docs header swaps its title for the page's on scroll
        scheme = lambda: [docs.evaluate("document.body.getAttribute('data-md-color-scheme')"), frame.evaluate("document.documentElement.getAttribute('data-theme')")]
        check("framed, the composer follows the docs site's light scheme", scheme() == ["default", "light"], scheme())
        docs.screenshot(path=SHOTS / "composer-docs-page.png")
        docs.locator('label[title="Switch to dark mode"]').click()
        docs.wait_for_timeout(200)
        bg = frame.evaluate("getComputedStyle(document.getElementById('canvas')).backgroundColor")
        check("switching the docs site to dark switches the framed composer too", scheme() == ["slate", "dark"] and bg == DARK_SUNK, f"{scheme()} {bg}")
        docs.locator("iframe.pf-composer-frame").scroll_into_view_if_needed()
        docs.wait_for_timeout(500)
        docs.screenshot(path=SHOTS / "composer-docs-page-dark.png")
        docs.locator('label[title="Switch to light mode"]').click()
        docs.wait_for_timeout(200)
        check("and back to light", scheme() == ["default", "light"], scheme())
        docs.evaluate("localStorage.clear()")
        docs.close()
        dark = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        docs = dark.new_page()
        track_errors(docs, BASE, docs_errors)
        docs.goto(BASE + "/composer/")
        docs.frame_locator("iframe.pf-composer-frame").locator("html[data-ready=true]").wait_for(state="attached")
        frame = next(f for f in docs.frames if f.url == APP)
        check("with a dark system theme the docs site is slate, and the framed composer dark", scheme() == ["slate", "dark"], scheme())
        dark.close()
        check("no console errors on the docs page", not docs_errors, "; ".join(docs_errors[:3]))
        browser.close()
finally:
    server.terminate()
    server.wait()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(1 if failed else 0)
