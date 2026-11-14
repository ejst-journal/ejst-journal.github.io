# EJST Volume 6 – Google Scholar metadata update

## Summary
- 28 article landing pages updated with article-specific Highwire Press / Google Scholar citation metadata.
- 28 matching PDF files verified in the archive.
- 28 unique DOI values verified; every DOI begins with `10.48309/`.
- Every article page has a canonical URL and `robots=index,follow` metadata.
- Issue distribution verified: Issue 1 = 8, Issue 2 = 7, Issue 3 = 7, Issue 4 = 6.
- Added `robots.txt` and `sitemap.xml` listing the home page, four issue pages, and all 28 article landing pages.

## Metadata added to each article page
`citation_title`, repeated `citation_author` tags (one per author), `citation_publication_date`, `citation_journal_title`, `citation_volume`, `citation_issue`, `citation_firstpage`, `citation_lastpage`, `citation_doi`, `citation_pdf_url`, `citation_language`, `citation_keywords`, and `citation_abstract`.

## QA results
- Required metadata completeness: 28/28 passed.
- Author metadata present: 28/28 passed.
- Publication year metadata corrected and checked against the year embedded in each DOI: 28/28 passed.
- Canonical URL checks: 28/28 passed.
- PDF target checks against files included in this archive: 28/28 passed.
- DOI consistency checks against the existing article page: 28/28 passed.
- No article content, DOI, page range, author list, abstract, keywords, or PDF files were intentionally rewritten; metadata was added to the HTML head.

## Deployment
Upload the contents of this ZIP to the root of the existing `ejst-journal.github.io` repository and allow GitHub to replace the matching files. This package includes the existing site files plus the updated article HTML files, `robots.txt`, and `sitemap.xml`.

After deployment, verify:
1. `https://ejst-journal.github.io/robots.txt`
2. `https://ejst-journal.github.io/sitemap.xml`
3. At least two article pages and their `view-source:` metadata.
4. Submit the sitemap in Google Search Console if the domain is verified there.

## Important
Correct metadata and crawlable pages improve eligibility for discovery; they do not guarantee inclusion or immediate indexing in Google Scholar. Google Scholar independently decides whether and when to crawl and include records. Also ensure the PDF text remains machine-readable and that server responses do not block Googlebot.