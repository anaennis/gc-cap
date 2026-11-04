"""Fetch the arm-S TRILEGAL v1.6 star catalog (CRITERIA §4.3).

All form parameters are taken from the live form's defaults; only the fields
§4.3 fixes are overridden. The exact submitted parameters, the server's reply
and the catalog are written to the output directory. TLS is verified with
ext/certs/bundle.pem (DATA_LOG #23); never disabled.

Usage: python fetch_trilegal.py OUTDIR CAFILE
"""
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://stev.oapd.inaf.it/cgi-bin/"
FORM = BASE + "trilegal"
OVERRIDES = {  # CRITERIA §4.3
    "trilegal_version": "1.6",
    "gal_coord": "2",               # equatorial
    "eq_alpha": "3.6414",           # h, NGC 1399
    "eq_delta": "-35.4508",         # deg
    "field": "10",                  # deg^2, the form's maximum per call
    "photsys_file": "tab_mag_odfnew/tab_mag_lsstR1.9.dat",
    "icm_lim": "4",                 # 4th filter; checked to be i below
    "mag_lim": "27.5",
}
POLL_S, MAX_WAIT_S = 60, 45 * 60


def get(url, ctx, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        return r.read()


def form_defaults(html):
    """(name, value) pairs a browser would submit for an untouched form."""
    fields = []
    pat = r"<select\b([^>]*)>(.*?)</select>|<input\b([^>]*)>"
    for m in re.finditer(pat, html, re.I | re.S):
        tag = "select" if m.group(1) is not None else "input"
        attrs, body = (m.group(1), m.group(2)) if tag == "select" else (m.group(3), "")
        name = re.search(r'name="([^"]+)"', attrs)
        if not name:
            continue
        name = name.group(1)
        if tag == "select":
            opt = re.search(r'<option\s+selected\s+value="([^"]*)"', body, re.I)
            fields.append((name, opt.group(1) if opt else ""))
            continue
        typ = (re.search(r'type="(\w+)"', attrs) or [None, "text"])[1].lower()
        val = (re.search(r'value="([^"]*)"', attrs) or [None, ""])[1]
        if typ == "radio" and not re.search(r"\bchecked\b", attrs, re.I):
            continue
        if typ == "submit" and name != "submit_form":
            continue
        if typ == "submit" and any(n == "submit_form" for n, _ in fields):
            continue
        fields.append((name, val))
    return fields


def multipart(fields):
    b = uuid.uuid4().hex
    out = b"".join(
        f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
        for n, v in fields
    ) + f"--{b}--\r\n".encode()
    return out, {"Content-Type": f"multipart/form-data; boundary={b}"}


def main(outdir, cafile):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context(cafile=cafile)
    html = get(FORM, ctx).decode("utf-8", "replace")
    (out / "form.html").write_text(html)
    assert "TRILEGAL 1.6" in html, "form is not TRILEGAL 1.6"
    assert OVERRIDES["photsys_file"] in html, "LSST R1.9 system not offered"

    defaults = form_defaults(html)
    names = {n for n, _ in defaults}
    missing = set(OVERRIDES) - names
    assert not missing, f"override fields not in form: {missing}"
    seen, fields = set(), []
    for n, v in defaults:
        if n in OVERRIDES:
            if n in seen:
                continue
            seen.add(n)
            v = OVERRIDES[n]
        fields.append((n, v))
    record = {
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "url": BASE + "trilegal_1.6",
        "form_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "overrides": OVERRIDES,
        "fields": fields,
    }
    (out / "request.json").write_text(json.dumps(record, indent=1))
    print("submitting", OVERRIDES, flush=True)

    body, hdr = multipart(fields)
    reply = get(BASE + "trilegal_1.6", ctx, data=body, headers=hdr).decode("utf-8", "replace")
    (out / "reply.html").write_text(reply)
    link = re.search(r'href="?([^"\s>]*tmp/[^"\s>]+\.dat)', reply, re.I)
    if not link:
        sys.exit("no output link in reply; see reply.html")
    url = urllib.request.urljoin(BASE + "trilegal_1.6", link.group(1))
    print("output url", url, flush=True)

    t0 = time.time()
    while True:
        time.sleep(POLL_S)
        try:
            data = get(url, ctx)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            data = b""
        if b"normally terminated" in data[-2000:]:
            break
        if time.time() - t0 > MAX_WAIT_S:
            (out / "partial.dat").write_bytes(data)
            sys.exit(f"not terminated after {MAX_WAIT_S}s ({len(data)} bytes); see partial.dat")
        print(f"waiting ({len(data)} bytes, {time.time() - t0:.0f}s)", flush=True)

    cat = out / "trilegal_ngc1399_10deg2_i27.5.dat"
    cat.write_bytes(data)
    header = data.split(b"\n", 1)[0].decode()
    cols = header.lstrip("#").split()
    bands = [c for c in cols if c in ("u", "g", "r", "i", "z", "y", "Y")]
    print("header", header)
    print("bands", bands, "rows", data.count(b"\n") - 2)
    assert bands[:6] and bands[3] == "i", f"4th filter is not i: {bands}"
    print("sha256", hashlib.sha256(data).hexdigest(), cat.name)


if __name__ == "__main__":
    main(*sys.argv[1:3])
