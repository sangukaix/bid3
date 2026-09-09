"""Non-OpenAI public web references. Search failures are reported, never invented."""
from html.parser import HTMLParser
import os
import re
from urllib.parse import parse_qs, urlparse, urljoin
import requests
from .company_website import CompanyPageParser, _download_html


class SearchParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.active = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "result__a" in attrs.get("class", "").split():
            self.active = attrs.get("href", "")
            self.text = []
    def handle_data(self, data):
        if self.active is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            href = urljoin("https://duckduckgo.com", self.active)
            parsed = urlparse(href)
            if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
                href = parse_qs(parsed.query).get("uddg", [""])[0]
            target = urlparse(href)
            if target.scheme in {"http", "https"} and target.hostname and not target.username:
                self.items.append({"url": href, "title": "".join(self.text).strip() or target.hostname})
            self.active = None


def search_public_references(instruction):
    if os.getenv("LOCAL_WEB_SEARCH", "duckduckgo") == "disabled":
        return "웹 검색이 비활성화되어 외부 참고 자료를 추가하지 않았습니다.", []
    # Search only the explicit user request, never attached company documents.
    urls = re.findall(r'https?://[^\s<>"\)]+', instruction)[:3]
    with requests.Session() as session:
        session.headers.update({"User-Agent": "BID3/1.0 (public reference lookup)"})
        if urls:
            candidates = [{"url": u, "title": u} for u in urls]
        else:
            try:
                response = session.get("https://html.duckduckgo.com/html/",
                                       params={"q": instruction[:300]}, timeout=(5, 15), stream=True)
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(32768):
                    content.extend(chunk)
                    if len(content) > 2 * 1024 * 1024:
                        raise ValueError("검색 응답 크기 초과")
                parser = SearchParser()
                parser.feed(bytes(content).decode("utf-8", errors="replace"))
                candidates = parser.items[:5]
            except (requests.RequestException, ValueError):
                return "웹 검색 서비스에 연결하지 못했습니다. 공개 자료 URL을 직접 입력해 주세요.", []
        references, sources = [], []
        for item in candidates:
            if len(sources) >= 3:
                break
            try:
                final_url, html = _download_html(session, item["url"])
                if any(s["url"] == final_url for s in sources):
                    continue
                parser = CompanyPageParser(); parser.feed(html)
                text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
                if not text:
                    continue
                title = "".join(parser.title_parts).strip() or item["title"]
                sources.append({"title": title, "url": final_url})
                references.append(f"[외부 참고 {len(sources)}: {title}]\nURL: {final_url}\n{text[:2200]}")
            except (requests.RequestException, ValueError):
                continue
    if not sources:
        return "읽을 수 있는 공개 웹 자료를 찾지 못했습니다. 검색 결과를 생성하거나 추측하지 않았습니다.", []
    return "\n\n".join(references), sources
