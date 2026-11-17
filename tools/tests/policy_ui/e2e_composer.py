#!/usr/bin/env python3
"""Drive the Policy Composer of the built docs site like a person, and check what it must do.

It serves the built site over HTTP (a page opened from file:// cannot fetch catalog.json), then checks:
  - the library lists the catalog's components: Shared 3, Cards 23, Grants 2;
  - Load opens each of the 23 cards with no check errors;
  - building the IRB card from the library, with accept presented on for its two shortcut inputs, gives JSON
    equal to policy_cards/ethics-approval-required/graph.json, and Download saves that file;
  - Load followed by Download gives back each card's graph.json byte for byte, even after values are typed on
    the Simulate tab, whose values never reach the JSON;
and the interactions: the details popup, wiring, accept presented, Simulate, Arrange, several outputs into one
input, a local graph.json, the draft kept on reload, the docs page that frames the app and its theme, and phone
width. It takes light and dark screenshots.

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
IRB_ORDER = ["project_membership", "institutional_irb_approval", "irb_clearance", "ethics_approval_required", "grant_download"]
IRB_SHORTCUTS = [("irb_clearance", "membership"), ("ethics_approval_required", "clearance")]
DS = "disease-specific-research"
GROUPS = [["Shared", 3], ["Cards", 23], ["Grants", 2]]   # the library: policy_components/README.md
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
    """Click the source's output, then the input's header: a wired input is a short socket whose middle is
    its accept presented switch."""
    page.locator(f'.n-out[data-node="{src}"] .vc').click()
    page.locator(f'.n-in[data-node="{dst}"][data-input="{inp}"] .vc-h').click()
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
        want = [[t, sum(1 for c in comps.values() if c["group"] == g)] for t, g in (("Shared", "shared"), ("Cards", "card"), ("Grants", "grant"))]
        check("library groups: Shared 3, Cards 23, Grants 2, as the catalog has them", groups == GROUPS == want, f"{groups} / catalog {want}")
        check("every library item has an Add button", page.locator(".lib-item").count() == page.locator(".lib-item .lib-add").count() == 28)
        rows = page.evaluate("Object.fromEntries([...document.querySelectorAll('.lib-group')].map(g => [g.getAttribute('aria-label'), [...g.querySelectorAll('.lib-item')].map(i => i.dataset.component)]))")
        check("each group lists the catalog's components of that group, in catalog order",
              rows == {t: [k for k, c in comps.items() if c["group"] == g] for t, g in (("Shared", "shared"), ("Cards", "card"), ("Grants", "grant"))}, rows)
        grant_inputs = {i["type"] for c in comps.values() if c["group"] == "grant" for i in c["inputs"].values()}
        outs = page.evaluate("Object.values(COMPONENTS).filter(c => c.group === 'card').map(c => c.output.type)")
        blurb = page.locator('.lib-group[aria-label="Cards"] .lib-blurb').inner_text()
        check("every card component outputs a credential a grant takes, and the Cards blurb names each",
              outs and all(o in grant_inputs for o in outs) and all(o in blurb for o in set(outs)), f"{set(outs)} / {blurb}")
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
                changes: [...document.querySelectorAll('#modal .changed')].map(p => p.textContent),
                rego: !!document.querySelector('#modal [data-act="toggle-rego"]'),
                none: (document.querySelector('#modal-no-rego') || {textContent: ''}).textContent,
                desc: document.querySelector('#modal .modal-desc').textContent })""")
            ok = (got["n"] == len(c["inputs"]) and got["pd"] == list(c["policy_data"]) and got["changes"] == c["changes_from_today"]
                  and got["desc"].startswith(c["summary"])
                  and (c["output"]["capability"] if c["group"] == "grant" else c["output"]["type"]) in got["out"].replace("\n", "")
                  and (got["rego"] if c["rego"] is not None else "not written yet" in got["none"]))
            if not ok:
                bad.append(cid)
            page.locator('#modal-box .modal-foot [data-act="close-modal"]').click()
        check("details of every component: its inputs, output, policy data, changes from today, and its Rego or that it is not written yet",
              not bad, bad)
        page.locator('.lib-item[data-component="grant_download"] .lib-open').click()
        cap = page.locator("#modal-output .vc.cap")
        check("details: Grant download outputs the capability card", cap.count() == 1 and "do_download" in cap.inner_text() and "CAPABILITY" in cap.inner_text().upper())
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
        check("five components added with the Add buttons", node_ids(page) == IRB_ORDER, node_ids(page))
        boxes = page.evaluate("[...document.querySelectorAll('.node')].map(n => { const r = n.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
        overlap = sum(1 for i, a in enumerate(boxes) for b in boxes[i + 1:] if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
        check("added components do not overlap", overlap == 0, overlap)
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
                  "ethics_approval_required": (1000, 230), "grant_download": (1500, 250)}
        for nid, (tx, ty) in layout.items():
            nx, ny = page.evaluate(f"[S.nodes['{nid}'].x, S.nodes['{nid}'].y]")
            x, y = grab_point(page, nid)
            drag(page, x, y, x + (ox + tx - nx) * k, y + (oy + ty - ny) * k)
            page.wait_for_timeout(40)
        moved = page.evaluate("Object.fromEntries(Object.values(S.nodes).map(n => [n.id, [n.x, n.y]]))")
        off = max(abs(moved[n][0] - (ox + tx)) + abs(moved[n][1] - (oy + ty)) for n, (tx, ty) in layout.items())
        check("components dragged by their shapes into columns", off < 6, off)
        card = page.evaluate("""(() => { const n = document.querySelector('.node[data-node="ethics_approval_required"]');
            return [!!n.querySelector('.pc'), n.querySelector('.pc-tab').textContent, (n.querySelector('.pc .lbl')).textContent,
                    getComputedStyle(n.querySelector('.pc')).borderTopWidth, n.querySelectorAll('[class*="hex"], [data-hex]').length]; })()""")
        check("the card component is a Policy Component with its tab and no policy data", card == [True, "Policy Component", "no policy data", "4px", 0], card)
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
        page.locator('.n-out[data-node="project_membership"] .vc').click()
        hl = page.evaluate("[...document.querySelectorAll('.n-in.ok')].map(e => e.dataset.node + '.' + e.dataset.input)")
        check("while wiring, only inputs of the same credential type are highlighted", hl == ["irb_clearance.membership"], hl)
        page.keyboard.press("Escape")
        for src, dst, inp in [("project_membership", "irb_clearance", "membership"), ("institutional_irb_approval", "irb_clearance", "approval"),
                              ("irb_clearance", "ethics_approval_required", "clearance"), ("ethics_approval_required", "grant_download", "grant")]:
            wire_by_clicks(page, src, dst, inp)
        check("four wires made by clicking", page.evaluate("S.wires.length") == 4)
        check("Checks says OK", page.locator("#count-checks").inner_text() == "OK", page.locator("#count-checks").inner_text())
        wired = page.evaluate("[...document.querySelectorAll('.n-in')].filter(e => e.querySelector('.ap')).map(e => e.dataset.node + '.' + e.dataset.input).sort()")
        check("only a wired input whose credential a wallet may present shows the accept presented switch",
              wired == sorted(f"{n}.{i}" for n, i in IRB_SHORTCUTS), wired)
        fixed = page.locator("#accept-fixed").inner_text()
        check("the side panel says which wired inputs take only their wired output, and why",
              "IRBClearance · approval" in fixed and "Grant download · grant" in fixed and "only components produce DownloadGrantCredential" in fixed, fixed)
        check("unwired inputs read as presented credentials",
              page.locator('.n-in[data-node="irb_clearance"][data-input="affiliation"] .vc-id').inner_text().endswith("presented"))
        legend = page.locator("#legend").inner_text().replace("\n", " | ")
        check("legend shows only what is on the canvas",
              all(t in legend for t in ("the requester", "the project", "the PI", "the ethics committee", "Policy Component", "capability", "wire"))
              and not any(t in legend for t in ("the script", "compute node", "terms document", "an institution")), legend)
        canvas_text = page.locator("#nodes").inner_text()
        claims = page.evaluate("[...document.querySelectorAll('#nodes .cl li')].map(l => l.textContent.trim())")
        check("claims are inside the cards; subject is never listed; outputs list claim names only",
              "subject" not in claims and "←" not in canvas_text and "<-" not in canvas_text and "purposes" in claims)
        shapes = page.evaluate("""(() => [[...document.querySelectorAll('#nodes .node')].every(n => n.querySelector('.pc') && n.querySelector('.pc-tab').textContent === 'Policy Component'),
            getComputedStyle(document.querySelector('.n-out[data-node="grant_download"] .vc.cap .vc-h')).backgroundColor])()""")
        check("every component is a Policy Component; the capability is a solid amber card", shapes[0] and shapes[1] == AMBER, shapes)
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
        check("Simulate: Policy data, Trusted issuers and Presented credentials as separate sections",
              titles == ["Policy data", "Trusted issuers", "Presented credentials"], titles)
        sep = page.evaluate("""(() => { const b = [...document.querySelectorAll('#side .side-card')].map(c => c.getBoundingClientRect());
            return b.every((r, i) => i === 0 || r.top >= b[i - 1].bottom + 4); })()""")
        check("the three sections do not overlap", sep)
        check("Simulate says it is a preview that runs no Rego",
              "preview" in page.locator("#tab-sim").inner_text() and "runs no Rego" in page.locator("#tray-body").inner_text())
        presented = page.evaluate("[...document.querySelectorAll('[data-act=sim-present]')].filter(i => i.checked).map(i => i.dataset.type).sort()")
        check("every required credential ticked, from a trusted issuer",
              presented == sorted(off_graph["trusted_issuers"]) and page.locator("#side-presented .why").count() == 0, presented)
        check("allow: the capability is issued", v.startswith("Capability issued") and "do_download" in v, v)
        run = chips(page, "#sim-order")
        check("allow: components run producers first, the grant last",
              run == ["1 InstitutionalIRBApproval", "2 ProjectMembership", "3 IRBClearance", "4 EthicsApprovalRequired", "5 Grant download"], run)
        badges = page.locator("#nodes .order").all_inner_texts()
        check("allow: run order shown on the canvas", sorted(badges) == ["1", "2", "3", "4", "5"], badges)
        scan_jargon(page, "Simulate allow")
        page.locator("#pc-IRBApprovalCredential").uncheck()
        v = verdict(page)
        check("deny: IRBApprovalCredential dropped -> no capability, named as missing",
              v.startswith("No capability") and "IRBApprovalCredential, not presented" in v, v)
        cannot = [c for c in chips(page, "#sim-order") if "cannot run" in c]
        check("deny: the components that depend on it cannot run", len(cannot) == 4 and cannot[0].startswith("1 InstitutionalIRBApproval"), cannot)
        check("deny: the input says it is not presented",
              page.locator('.n-in[data-node="institutional_irb_approval"][data-input="irb"] .st.bad').inner_text() == "not presented")
        page.screenshot(path=SHOTS / "composer-light-deny.png")
        page.locator("#pc-IRBApprovalCredential").check()
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:unknown")
        v = verdict(page)
        check("deny: IRBApprovalCredential from an unknown issuer does not count",
              v.startswith("No capability") and "signed by an unknown issuer, which this policy does not trust" in v, v)
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:hospital-irb")
        check("with none ticked, every example issuer that signs the type is trusted: City Hospital IRB counts",
              verdict(page).startswith("Capability issued") and page.locator("#tr-state-IRBApprovalCredential").inner_text() == "None ticked, so every one is trusted.")
        page.locator('[data-act="trust"][data-type="IRBApprovalCredential"][data-issuer="did:example:dac"]').check()
        v = verdict(page)
        check("deny: trusting only the Data Access Committee turns City Hospital IRB's credential away",
              v.startswith("No capability") and "City Hospital IRB, which this policy does not trust" in v, v)
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:dac")
        check("allow again with the trusted issuer", verdict(page).startswith("Capability issued"))
        page.locator('[data-act="trust"][data-type="IRBApprovalCredential"][data-issuer="did:example:dac"]').uncheck()
        page.select_option("#pc-IRBApprovalCredential-issuer", "did:example:hospital-irb")
        check("untrusting it empties the list, which trusts every example issuer again; Checks stays OK (no 'no issuer is trusted' error)",
              verdict(page).startswith("Capability issued") and page.locator("#count-checks").inner_text() == "OK")
        check("the Simulate values did not change the JSON", graph_json(page) == off_graph)

        # ---------- accept presented on the two shortcut inputs
        page.locator("#tab-checks").click()
        side = page.locator("#side .side-card h2").all_inner_texts()
        check("side panel while building: the accept presented switches of the two shortcut inputs",
              side == ["Accept presented"] and page.locator('#side [data-act="accept"]').count() == 2, side)
        page.locator('label[for="ap-ethics_approval_required-clearance"]').click()
        page.wait_for_timeout(60)
        g = graph_json(page)
        check("accept presented saved in the JSON, with an empty trusted_issuers list for IRBClearanceCredential",
              g["nodes"]["ethics_approval_required"]["inputs"]["clearance"] == {"from": "node", "node": "irb_clearance", "accept_presented": True}
              and g["trusted_issuers"].get("IRBClearanceCredential") == [], json.dumps(g["trusted_issuers"]))
        check("the canvas switch follows", page.locator("#apc-ethics_approval_required-clearance").is_checked())
        v = verdict(page)
        run = chips(page, "#sim-order")
        check("not presented yet: the components upstream still run", v.startswith("Capability issued") and len(run) == 5, f"{v} | {run}")
        page.locator('[data-act="sim-preset"][data-preset="none"]').click()
        for t in ("IRBClearanceCredential", "IntendedDataUseCredential", "publicKeyCredential"):
            page.locator(f"#pc-{t}").check()
        v = verdict(page)
        run, skipped = chips(page, "#sim-order"), chips(page, "#sim-skipped")
        check("presenting an IRBClearanceCredential skips the upstream components",
              v.startswith("Capability issued") and run == ["1 EthicsApprovalRequired", "2 Grant download"]
              and sorted(skipped) == ["IRBClearance", "InstitutionalIRBApproval", "ProjectMembership"], f"{v} | {run} | {skipped}")
        dim = page.evaluate("[...document.querySelectorAll('.node.dim')].map(n => n.dataset.node).sort()")
        check("skipped components are dimmed on the canvas", dim == ["institutional_irb_approval", "irb_clearance", "project_membership"], dim)
        check("the presented credential is listed as used instead",
              chips(page, "#sim-instead") == ["IRBClearanceCredential → EthicsApprovalRequired · clearance"], chips(page, "#sim-instead"))
        page.screenshot(path=SHOTS / "composer-light-accept-presented.png")
        page.locator('[data-act="trust"][data-type="IRBClearanceCredential"][data-issuer="did:example:research-office"]').check()
        page.select_option("#pc-IRBClearanceCredential-issuer", "did:example:hospital-irb")
        v = verdict(page)
        check("an IRBClearanceCredential from an untrusted issuer does not skip anything; without the other credentials: no capability",
              v.startswith("No capability") and len(chips(page, "#sim-order")) == 5, v)
        page.locator('label[for="apc-irb_clearance-membership"]').click()
        page.wait_for_timeout(60)
        text = graph_text(page)
        check("the IRB card built from the library, accept presented on for its two shortcut inputs, equals policy_cards/ethics-approval-required/graph.json",
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
        wire_by_clicks(page, "project_membership_2", "irb_clearance", "membership")
        text = toast(page)
        check("a second wire into an input that accepts presented is refused, saying why",
              "Switch that off" in text and len([w for w in page.evaluate("S.wires") if w["to"] == "irb_clearance" and w["input"] == "membership"]) == 1, text)
        page.locator('.node[data-node="project_membership_2"] [data-act="node-remove"]').click(force=True)
        page.wait_for_timeout(60)
        check("removing it gives back the committed IRB graph", graph_text(page).encode() == COMMITTED[IRB])

        # ---------- arrange
        page.locator("#arrange").click()
        xs = page.evaluate("Object.fromEntries(Object.values(S.nodes).map(n => [n.id, n.x]))")
        check("Arrange lays the components out from left to right",
              xs["institutional_irb_approval"] == xs["project_membership"] < xs["irb_clearance"] < xs["ethics_approval_required"] < xs["grant_download"], xs)

        # ---------- every card: Load, then Download, before and after typing on the Simulate tab
        errs = {}
        for folder in sorted(CATALOG["cards"]):
            want = COMMITTED[folder]
            load_card(page, folder)
            if node_ids(page) != list(json.loads(want)["nodes"]) or page.locator("#count-checks").inner_text() != "OK":
                errs[folder] = page.locator("#tray-body").inner_text()[:200]
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

        # ---------- the DS card: policy data stays out of the JSON
        load_card(page, DS)
        page.locator("#tab-sim").click()
        page.fill("#pd-disease_specific_research-allowedDiseases", "MONDO:0005148, MONDO:0005015")
        page.wait_for_timeout(60)
        text = graph_text(page)
        g = json.loads(text)
        check("DS: Disease Specific Research is ProjectMembership, its card component and Grant download",
              list(g["nodes"]) == ["project_membership", "disease_specific_research", "grant_download"] and g["root"] == "grant_download"
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

        # ---------- several outputs into one input
        page.select_option("#load-select", "empty")
        page.fill("#card-name", "Two cards on one dataset")
        for cid in ("geographical_restriction", "institution_specific_restriction", "grant_download"):
            page.locator(f'.lib-item[data-component="{cid}"] .lib-add').click()
            page.wait_for_timeout(80)
        page.locator("#arrange").click()
        page.wait_for_timeout(60)
        wire_by_clicks(page, "geographical_restriction", "grant_download", "grant")
        wire_by_clicks(page, "institution_specific_restriction", "grant_download", "grant")
        text = toast(page)
        page.locator("#arrange").click()
        g = graph_json(page)
        check("a second output wired into an input adds to it; the toast says so", "2 components" in text and len(page.evaluate("S.wires")) == 2, text)
        check("an input with several wires is written as the list of its node sources, none accepting presented",
              g["nodes"]["grant_download"]["inputs"]["grant"] == [{"from": "node", "node": "geographical_restriction", "accept_presented": False},
                                                                   {"from": "node", "node": "institution_specific_restriction", "accept_presented": False}]
              and list(g["trusted_issuers"]) == ["AffiliationCredential", "LocationCredential", "publicKeyCredential"], json.dumps(g["nodes"]["grant_download"]))
        check("it checks OK, and has no accept presented switch",
              page.locator("#count-checks").inner_text() == "OK" and page.locator('.n-in[data-node="grant_download"][data-input="grant"] .ap').count() == 0
              and page.locator('.n-in[data-node="grant_download"][data-input="grant"] .vc-id').inner_text() == "grant · 2 wires")
        check("Simulate: the grant runs when both cards ran", verdict(page).startswith("Capability issued") and len(chips(page, "#sim-order")) == 3)
        page.locator("#pc-LocationCredential").uncheck()
        v = verdict(page)
        run = chips(page, "#sim-order")
        check("Simulate: without one card's credential the grant cannot run, though the other card does",
              v.startswith("No capability") and "LocationCredential, not presented" in v and "Grant download · cannot run" in " ".join(run)
              and any(c.endswith("InstitutionSpecificRestriction") for c in run), run)
        page.screenshot(path=SHOTS / "composer-light-several-sources.png")
        name, several = download(page)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "several.json").write_bytes(several)
            page.select_option("#load-select", "empty")
            page.set_input_files("#load-file", str(Path(tmp, "several.json")))
            page.wait_for_timeout(150)
            check("Load reads a local graph.json with the list form: two wires into the grant",
                  node_ids(page) == ["geographical_restriction", "institution_specific_restriction", "grant_download"]
                  and len(page.evaluate("S.wires")) == 2 and "Opened several.json" in toast(page), toast(page))
            check("Load then Download of that file gives it back byte for byte", download(page)[1] == several)
            broken = json.loads(several)
            broken["nodes"]["grant_download"]["inputs"]["grant"] = broken["nodes"]["grant_download"]["inputs"]["grant"][:1]
            Path(tmp, "one.json").write_text(json.dumps(broken))
            page.set_input_files("#load-file", str(Path(tmp, "one.json")))
            page.wait_for_timeout(150)
            text = toast(page)
            check("a list of one source is refused, saying why, and the canvas is kept",
                  "Could not open one.json" in text and "two or more different nodes" in text and len(page.evaluate("S.wires")) == 2, text)
            broken = json.loads(several)
            broken["version"] = 1
            Path(tmp, "old.json").write_text(json.dumps(broken))
            page.set_input_files("#load-file", str(Path(tmp, "old.json")))
            page.wait_for_timeout(150)
            text = toast(page)
            check("a graph of another version is refused", "Could not open old.json" in text and "version 1" in text, text)
            broken = json.loads(several)
            broken["nodes"]["grant_download"]["component"] = "grant_everything"
            Path(tmp, "unknown.json").write_text(json.dumps(broken))
            page.set_input_files("#load-file", str(Path(tmp, "unknown.json")))
            page.wait_for_timeout(150)
            text = toast(page)
            check("a graph with a component the repository does not have is refused", "grant_everything, which is not in this repository" in text, text)
        page.locator("#tab-checks").click()
        click_wire(page, "geographical_restriction", "grant_download", "grant")
        page.locator(".wire-tool").click()
        page.wait_for_timeout(60)
        g = graph_json(page)
        check("disconnecting one of the two wires gives back a single source, and an unwired card the checks flag",
              g["nodes"]["grant_download"]["inputs"]["grant"] == {"from": "node", "node": "institution_specific_restriction", "accept_presented": False}
              and page.locator("#count-checks").inner_text() == "1", json.dumps(g["nodes"]["grant_download"]))

        # ---------- the draft survives a reload, without the Simulate values; drafts that do not read are refused
        load_card(page, DS)
        x, y = center(page, '.node[data-node="grant_download"] [data-comp]')
        drag(page, x, y, x + 60, y + 40)
        page.locator("#tab-sim").click()
        page.fill("#pd-disease_specific_research-allowedDiseases", "MONDO:0005015")
        before = (graph_text(page), page.evaluate("Object.values(S.nodes).map(n => [n.id, n.x, n.y])"))
        page.wait_for_timeout(400)
        page.reload()
        ready(page)
        after = (graph_text(page), page.evaluate("Object.values(S.nodes).map(n => [n.id, n.x, n.y])"))
        page.locator("#tab-sim").click()
        check("reload keeps the draft (components, wires, accept presented, places) but not the Simulate values",
              after == before and page.locator("#pd-disease_specific_research-allowedDiseases").input_value() == "", f"{before[1]} / {after[1]}")
        page.wait_for_timeout(400)   # let the draft save the page does after loading run first; leaving the page flushes a pending one
        page.evaluate("""localStorage.setItem('pf-policy-composer-v5', JSON.stringify({v: 5, positions: {},
            graph: {version: 1, name: 'Old', root: null, nodes: {}, trusted_issuers: {}}}))""")
        page.reload()
        ready(page)
        text = toast(page)
        check("a saved draft that does not read is not restored, and the page says why",
              node_ids(page) == [] and "Your saved draft was not restored" in text and "version 1" in text, text)
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
        layout_ok = frame.evaluate("""(() => { const s = document.querySelector('.stage').getBoundingClientRect(), d = document.querySelector('.side').getBoundingClientRect();
            return d.left >= s.right && document.documentElement.scrollWidth <= window.innerWidth; })()""")
        check("at 1440px the framed composer has its full layout, the side panel beside the canvas", layout_ok)
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
