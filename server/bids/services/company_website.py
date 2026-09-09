import hashlib
import ipaddress
import re
import socket
from collections import deque
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

import requests
import chardet
from django.db import transaction
from django.utils import timezone

from bids.models import CompanyProfile, CompanyWebsitePage


MAX_PAGES_PER_SITE = 8
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_SITE_TEXT_CHARS = 120000
CACHE_DAYS = 30
REQUEST_TIMEOUT = (3, 8)
LINK_HINTS = (
    "about",
    "company",
    "business",
    "service",
    "portfolio",
    "history",
    "intro",
    "회사",
    "소개",
    "사업",
    "서비스",
    "실적",
    "연혁",
)
SKIPPED_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".hwp",
    ".hwpx",
    ".xls",
    ".xlsx",
}


class CompanyPageParser(HTMLParser):
    """HTML에서 화면에 보이는 글과 같은 사이트 링크만 모읍니다."""

    BLOCK_TAGS = {
        "article",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "header",
        "li",
        "main",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }
    HIDDEN_TAGS = {"script", "style", "noscript", "svg", "canvas"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.links = []
        self.hidden_depth = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.HIDDEN_TAGS:
            self.hidden_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")
        if tag == "a":
            href = dict(attrs).get("href", "").strip()
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.HIDDEN_TAGS and self.hidden_depth:
            self.hidden_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        value = data.strip()
        if not value or self.hidden_depth:
            return
        if self.in_title:
            self.title_parts.append(value)
        self.text_parts.append(value)

    def result(self):
        title = " ".join(self.title_parts).strip()[:300]
        lines = []
        for line in " ".join(self.text_parts).splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if normalized and (not lines or lines[-1] != normalized):
                lines.append(normalized)
        return title, "\n".join(lines), self.links


def normalize_website_url(value):
    """비교와 저장에 사용할 안정적인 홈페이지 URL을 만듭니다."""

    value = str(value or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("올바른 회사 홈페이지 주소가 아닙니다.")
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError("회사 홈페이지는 일반 HTTP 또는 HTTPS 주소만 사용할 수 있습니다.")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            "",
            "",
            "",
        )
    )


def _public_host(hostname):
    """회사 홈페이지 수집이 내부망으로 접근하지 못하게 검사합니다."""

    lowered = hostname.casefold().rstrip(".")
    if lowered == "localhost" or lowered.endswith(".localhost"):
        return False
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as error:
        raise ValueError("회사 홈페이지 주소를 찾을 수 없습니다.") from error
    if not addresses:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            return False
    return True


def _validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("수집할 수 없는 홈페이지 주소입니다.")
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError("수집할 수 없는 홈페이지 주소입니다.")
    if not _public_host(parsed.hostname):
        raise ValueError("내부 네트워크 주소는 회사 홈페이지로 수집할 수 없습니다.")


def _read_response_content(response):
    content = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        content.extend(chunk)
        if len(content) > MAX_PAGE_BYTES:
            raise ValueError("홈페이지 한 페이지의 크기가 2MB를 초과합니다.")
    raw_content = bytes(content)
    detected = chardet.detect(raw_content).get("encoding")
    encoding = response.encoding or detected or "utf-8"
    return raw_content.decode(encoding, errors="replace")


def _download_html(session, url):
    """리다이렉트 주소도 검사하며 HTML 한 페이지를 내려받습니다."""

    current_url = url
    for _ in range(4):
        _validate_public_url(current_url)
        response = session.get(
            current_url,
            allow_redirects=False,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location", "")
            if not location:
                raise ValueError("홈페이지 이동 주소를 확인할 수 없습니다.")
            current_url = normalize_website_url(urljoin(current_url, location))
            continue
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and "html" not in content_type:
            raise ValueError("HTML 페이지가 아니어서 수집하지 않았습니다.")
        return current_url, _read_response_content(response)
    raise ValueError("홈페이지 이동 횟수가 너무 많습니다.")


def _same_site(first_url, second_url):
    first = (urlparse(first_url).hostname or "").removeprefix("www.")
    second = (urlparse(second_url).hostname or "").removeprefix("www.")
    return first.casefold() == second.casefold()


def _normalize_link(base_url, href):
    candidate = urljoin(base_url, href)
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    if not _same_site(base_url, candidate):
        return ""
    path = parsed.path or "/"
    if any(path.casefold().endswith(extension) for extension in SKIPPED_EXTENSIONS):
        return ""
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, "")
    )


def crawl_company_site(root_url, session=None):
    """회사 사이트에서 제안서에 유용한 대표 페이지를 제한적으로 수집합니다."""

    root_url = normalize_website_url(root_url)
    own_session = session is None
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Bid2CompanyKnowledgeBot/1.0"})
    queue = deque([root_url])
    queued = {root_url}
    visited = set()
    pages = []
    used_chars = 0

    try:
        while queue and len(pages) < MAX_PAGES_PER_SITE:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            try:
                final_url, html = _download_html(session, url)
            except (requests.RequestException, ValueError):
                continue

            parser = CompanyPageParser()
            parser.feed(html)
            title, text, links = parser.result()
            remaining = MAX_SITE_TEXT_CHARS - used_chars
            page_text = text[:remaining]
            if len(page_text) >= 100:
                pages.append(
                    {
                        "url": final_url,
                        "title": title,
                        "text": page_text,
                        "content_hash": hashlib.sha256(
                            page_text.encode("utf-8")
                        ).hexdigest(),
                    }
                )
                used_chars += len(page_text)
            if used_chars >= MAX_SITE_TEXT_CHARS:
                break

            candidates = []
            for href in links:
                linked_url = _normalize_link(final_url, href)
                if not linked_url or linked_url in queued:
                    continue
                queued.add(linked_url)
                score = sum(
                    hint in linked_url.casefold()
                    for hint in LINK_HINTS
                )
                candidates.append((score, linked_url))
            for _, linked_url in sorted(candidates, key=lambda item: (-item[0], item[1])):
                queue.append(linked_url)
    finally:
        if own_session:
            session.close()

    return pages


def collect_company_websites(user, force=False):
    """프로필의 홈페이지를 수집하고 바뀐 페이지만 DB에 갱신합니다."""

    profile = CompanyProfile.objects.filter(user=user).first()
    if profile is None:
        return {"processed_sites": [], "reused_sites": [], "failed_sites": [], "page_count": 0}

    roots = []
    invalid_roots = []
    for value in (profile.website_url_1, profile.website_url_2):
        try:
            normalized = normalize_website_url(value)
        except ValueError as error:
            if value:
                invalid_roots.append({"url": str(value), "reason": str(error)})
            continue
        if normalized and normalized not in roots:
            roots.append(normalized)

    valid_roots = roots
    active_hosts = {
        (urlparse(root).hostname or "").removeprefix("www.").casefold()
        for root in valid_roots
    }
    for page in CompanyWebsitePage.objects.filter(user=user):
        host = (urlparse(page.url).hostname or "").removeprefix("www.").casefold()
        if host not in active_hosts:
            page.delete()

    processed_sites = []
    reused_sites = []
    failed_sites = invalid_roots
    cutoff = timezone.now() - timedelta(days=CACHE_DAYS)

    for root in valid_roots:
        current_pages = [
            page
            for page in CompanyWebsitePage.objects.filter(user=user)
            if _same_site(root, page.url)
        ]
        if current_pages and not force and all(
            page.collected_at >= cutoff for page in current_pages
        ):
            reused_sites.append(root)
            continue

        try:
            crawled_pages = crawl_company_site(root)
        except (requests.RequestException, ValueError) as error:
            failed_sites.append({"url": root, "reason": str(error)})
            continue
        if not crawled_pages:
            failed_sites.append({"url": root, "reason": "읽을 수 있는 홈페이지 내용이 없습니다."})
            continue

        fetched_urls = []
        with transaction.atomic():
            for crawled in crawled_pages:
                page, created = CompanyWebsitePage.objects.get_or_create(
                    user=user,
                    url=crawled["url"],
                    defaults={
                        "title": crawled["title"],
                        "extracted_text": crawled["text"],
                        "content_hash": crawled["content_hash"],
                    },
                )
                changed = created or page.content_hash != crawled["content_hash"]
                if not created:
                    page.title = crawled["title"]
                    page.extracted_text = crawled["text"]
                    page.content_hash = crawled["content_hash"]
                    page.save()
                if changed:
                    page.knowledge_items.all().delete()
                fetched_urls.append(page.url)
            for old_page in current_pages:
                if old_page.url not in fetched_urls:
                    old_page.delete()
        processed_sites.append(root)

    return {
        "processed_sites": processed_sites,
        "reused_sites": reused_sites,
        "failed_sites": failed_sites,
        "page_count": CompanyWebsitePage.objects.filter(user=user).count(),
    }
