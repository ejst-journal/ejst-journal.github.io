#!/usr/bin/env python3
"""Read-only technical audit for an EJST GitHub Pages archive.
Does not submit URLs to Google Scholar and never edits site files.
"""
from __future__ import annotations
import argparse, html, json, re, sys, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ejst-journal.github.io"

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.links = {}; self.title_parts=[]; self.in_title=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag.lower()=="meta":
            key=(a.get("name") or a.get("property") or "").strip().lower()
            if key: self.meta.setdefault(key, []).append(a.get("content", "").strip())
        if tag.lower()=="link" and a.get("rel","").lower()=="canonical": self.links["canonical"]=a.get("href","").strip()
        if tag.lower()=="title": self.in_title=True
    def handle_endtag(self, tag):
        if tag.lower()=="title": self.in_title=False
    def handle_data(self, data):
        if self.in_title: self.title_parts.append(data)

def norm(s): return re.sub(r"\s+", " ", html.unescape(str(s or ""))).strip().casefold()
def getmeta(p, key): return p.meta.get(key.lower(), [])
def fetch(url, method="GET", headers=None, timeout=8):
    req=urllib.request.Request(url, method=method, headers=headers or {"User-Agent":"EJST-Scholar-Audit/1.0 (+https://ejst-journal.github.io/)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.headers, r.read(512) if method!="HEAD" else b""
    except urllib.error.HTTPError as e: return e.code, e.headers, b""
    except Exception as e: return None, {}, str(e).encode()[:300]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base-url",default=BASE); ap.add_argument("--live",action="store_true",help="also test published URLs"); ap.add_argument("--out",default="scholar-audit-report.md"); args=ap.parse_args()
    base=args.base_url.rstrip("/"); findings=[]; stats=Counter(); rows=[]
    def add(level, code, msg, article=""):
        findings.append((level,code,article,msg)); stats[level]+=1
    data_path=ROOT/"data/articles.json"
    if not data_path.exists(): print("ERROR: data/articles.json missing",file=sys.stderr); return 2
    try: articles=json.loads(data_path.read_text(encoding="utf-8"))
    except Exception as e: print(f"ERROR: invalid articles.json: {e}",file=sys.stderr); return 2
    if not isinstance(articles,list): print("ERROR: articles.json must be a list",file=sys.stderr); return 2
    sitemap_path=ROOT/"sitemap.xml"; sitemap_text=sitemap_path.read_text(encoding="utf-8") if sitemap_path.exists() else ""
    if not sitemap_text: add("ERROR","SITEMAP_MISSING","sitemap.xml is missing or empty")
    else:
        if "http://www.sitemaps.org/schemas/sitemap/0.9" not in sitemap_text: add("ERROR","SITEMAP_NAMESPACE","Sitemap namespace is missing or unexpected")
        if "<loc>" not in sitemap_text: add("ERROR","SITEMAP_EMPTY","No URL entries found in sitemap")
    if not (ROOT/"robots.txt").exists(): add("WARN","ROBOTS_MISSING","robots.txt is absent; no changes were made")
    else:
        rt=(ROOT/"robots.txt").read_text(encoding="utf-8",errors="replace")
        if "Sitemap:" not in rt: add("WARN","ROBOTS_SITEMAP","robots.txt does not declare a Sitemap URL")
    dois=Counter(a.get("doi","").strip().lower() for a in articles if a.get("doi")); slugs=Counter(a.get("slug","").strip() for a in articles if a.get("slug"))
    for d,n in dois.items():
        if n>1: add("ERROR","DUPLICATE_DOI",f"DOI appears {n} times: {d}")
    for s,n in slugs.items():
        if n>1: add("ERROR","DUPLICATE_SLUG",f"Slug appears {n} times: {s}")
    sitemap_locs=set(re.findall(r"<loc>\s*(.*?)\s*</loc>",sitemap_text,re.I|re.S))
    expected=[]
    for i,a in enumerate(articles,1):
        slug=a.get("slug") or ""; title=a.get("title") or ""; doi=a.get("doi") or ""; authors=a.get("authors") or []; pdf=a.get("pdf") or ""
        label=slug or f"record-{i}"; page_rel=f"articles/{slug}.html" if slug else ""
        page=ROOT/page_rel if page_rel else None; page_url=f"{base}/{page_rel}" if page_rel else ""
        if page_url: expected.append(page_url)
        missing=[k for k,v in (("title",title),("authors",authors),("doi",doi),("slug",slug),("pdf",pdf),("abstract",a.get("abstract"))) if not v]
        if missing: add("ERROR","DATA_FIELDS",f"Missing data fields: {', '.join(missing)}",label)
        if not page or not page.exists():
            add("ERROR","HTML_MISSING",f"Article HTML page not found: {page_rel}",label); rows.append((label,title,"HTML MISSING","")); continue
        parser=MetaParser()
        try: parser.feed(page.read_text(encoding="utf-8",errors="replace"))
        except Exception as e: add("ERROR","HTML_READ",f"Cannot parse HTML: {e}",label)
        checks={
          "citation_title": bool(getmeta(parser,"citation_title")) and norm(getmeta(parser,"citation_title")[0])==norm(title),
          "citation_author": [norm(x) for x in getmeta(parser,"citation_author")]==[norm(x) for x in authors],
          "citation_doi": bool(getmeta(parser,"citation_doi")) and norm(getmeta(parser,"citation_doi")[0])==norm(doi),
          "citation_pdf_url": bool(getmeta(parser,"citation_pdf_url")) and getmeta(parser,"citation_pdf_url")[0].rstrip("/")==f"{base}/{pdf}".rstrip("/"),
          "canonical": parser.links.get("canonical","")==page_url,
          "citation_publication_date": bool(getmeta(parser,"citation_publication_date")),
          "citation_abstract": bool(getmeta(parser,"citation_abstract")),
        }
        for k,ok in checks.items():
            if not ok: add("ERROR","META_"+k.upper(),f"Metadata missing or does not match archive data: {k}",label)
        if pdf:
            pdf_path=ROOT/pdf
            if not pdf_path.exists(): add("ERROR","PDF_MISSING",f"PDF file not found: {pdf}",label)
            else:
                size=pdf_path.stat().st_size; sig=pdf_path.open("rb").read(5)
                if sig!=b"%PDF-": add("ERROR","PDF_SIGNATURE","File does not start with a valid PDF signature",label)
                if size==0: add("ERROR","PDF_EMPTY","PDF file is empty",label)
                if size>5*1024*1024: add("WARN","PDF_LARGE",f"PDF is {size/1024/1024:.2f} MB; consider checking download/access performance",label)
                if args.live:
                    u=f"{base}/{pdf}"; status,_,_=fetch(u,"HEAD")
                    if status is None or status>=400: add("ERROR","LIVE_PDF_HTTP",f"Live PDF HEAD check failed: {status}",label)
                    elif status>=300: add("WARN","LIVE_PDF_REDIRECT",f"Live PDF returned HTTP {status}",label)
        if page_url not in sitemap_locs: add("ERROR","SITEMAP_ARTICLE_MISSING",f"Article URL absent from sitemap: {page_url}",label)
        if args.live:
            status,_,_=fetch(page_url,"HEAD")
            if status is None or status>=400: add("ERROR","LIVE_HTML_HTTP",f"Live article page returned {status}",label)
            elif status>=300: add("WARN","LIVE_HTML_REDIRECT",f"Live article page returned HTTP {status}",label)
        scholar_q=urllib.parse.quote('"'+title+'" '+doi)
        rows.append((label,title,"PASS" if all(checks.values()) else "CHECK","https://scholar.google.com/scholar?q="+scholar_q))
    local_pages={f"{base}/articles/{p.name}" for p in (ROOT/"articles").glob("*.html")} if (ROOT/"articles").exists() else set()
    for extra in sorted(local_pages-set(expected)): add("WARN","ORPHAN_HTML",f"HTML article page is not represented in data/articles.json or expected URL list: {extra}")
    # Ensure all issue pages and homepage are discoverable in the sitemap.
    for rel in ["index.html"]+[f"issues/issue-{i}.html" for i in range(1,5)]:
        u=f"{base}/{rel}"
        if u not in sitemap_locs and f"{base}/" not in sitemap_locs: add("WARN","SITEMAP_SECTION_MISSING",f"Section URL absent from sitemap: {u}")
    if args.live:
        for rel in ["robots.txt","sitemap.xml"]:
            status,_,_=fetch(f"{base}/{rel}","GET")
            if status is None or status>=400: add("ERROR","LIVE_"+rel.upper().replace(".","_"),f"Live {rel} returned HTTP {status}")
            else: add("INFO","LIVE_"+rel.upper().replace(".","_"),f"Live {rel} responded with HTTP {status}")
    now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines=["# EJST Google Scholar technical audit", "", f"- Generated: {now}",f"- Site: {base}",f"- Articles in data file: **{len(articles)}**",f"- Live HTTP checks: **{'enabled' if args.live else 'disabled (local archive only)'}**","","> This report checks technical discoverability and metadata. It cannot force Google Scholar to crawl or confirm Scholar indexing. Use the Scholar search links below for manual title/DOI verification.","", "## Summary", "", f"- Errors: **{stats['ERROR']}**",f"- Warnings: **{stats['WARN']}**",f"- Informational: **{stats['INFO']}**", "", "## Article-level review", "", "| Article slug | Metadata/PDF check | Google Scholar search |", "|---|---|---|"]
    for slug,title,status,url in rows: lines.append(f"| `{slug}` | {status} | [Search title + DOI]({url}) |" if url else f"| `{slug}` | {status} | — |")
    lines += ["", "## Findings", ""]
    if findings:
        for level,code,article,msg in findings: lines.append(f"- **{level} · {code}**"+(f" · `{article}`" if article else "")+f": {msg}")
    else: lines.append("No technical issues were detected in the checks that were run.")
    lines += ["", "## Interpretation", "", "- `ERROR` means a technical inconsistency or access problem should be reviewed.", "- `WARN` means a potential risk or item requiring human review.", "- A clean report means the archive passed these checks; it does **not** mean Google Scholar has indexed every article.", "- This audit is read-only: it does not edit `sitemap.xml`, `robots.txt`, article HTML, PDFs, or article data.", ""]
    out=ROOT/args.out; out.write_text("\n".join(lines),encoding="utf-8")
    print(f"EJST audit finished: {len(articles)} articles; {stats['ERROR']} errors; {stats['WARN']} warnings; report={out}")
    if "GITHUB_STEP_SUMMARY" in __import__('os').environ:
        with open(__import__('os').environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f: f.write("\n".join(lines)+"\n")
    return 1 if stats['ERROR'] else 0
if __name__=="__main__": sys.exit(main())
