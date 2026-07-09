from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning


BASE_URL = "https://web.pcc.gov.tw"
SEARCH_URL = f"{BASE_URL}/prkms/tender/common/basic/readTenderBasic"
APPEAL_URL = f"{BASE_URL}/prkms/tpAppeal/common/readTpAppeal"
APPEAL_SORT = "d-4025577"

CSV_FIELDS = [
    "query_keyword",
    "item_no",
    "agency",
    "tender_id",
    "is_correction",
    "tender_name",
    "transmission_count",
    "tender_method",
    "procurement_category",
    "announcement_date",
    "bid_deadline",
    "budget_amount",
    "detail_url",
]

DATE_TYPE_MAP = {
    "today": "isNow",
    "period": "isSpdt",
    "range": "isDate",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_cell(cell) -> str:
    return clean_text(cell.get_text(" ", strip=True))


def normalize_roc_date(value: str) -> str:
    value = value.strip()
    if not value:
        return value

    match = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value)
    if match:
        year, month, day = map(int, match.groups())
        return f"{year:04d}/{month:02d}/{day:02d}"

    match = re.fullmatch(r"(\d{2,3})[-/](\d{1,2})[-/](\d{1,2})", value)
    if match:
        year, month, day = map(int, match.groups())
        return f"{year + 1911:04d}/{month:02d}/{day:02d}"

    raise ValueError(f"日期格式不支援：{value}，請用 115/07/08 或 2026-07-08")


def read_keywords(args: argparse.Namespace) -> list[str]:
    keywords: list[str] = []
    keywords.extend(args.keywords or [])

    if args.keyword_file:
        keyword_file = Path(args.keyword_file)
        for line in keyword_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                keywords.append(line)

    seen = set()
    unique_keywords = []
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword and keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def build_params(
    keyword: str,
    args: argparse.Namespace,
    page: int | None = None,
    page_param: str = "d-49738-p",
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "pageSize": args.page_size,
        "firstSearch": "true",
        "searchType": "basic",
        "isBinding": "N",
        "isLogIn": "N",
        "orgName": args.org_name or "",
        "orgId": args.org_id or "",
        "tenderName": keyword,
        "tenderId": args.tender_id or "",
        "tenderType": args.tender_type,
        "tenderWay": args.tender_way,
        "dateType": DATE_TYPE_MAP[args.date_type],
        "radProctrgCate": args.category,
        "policyAdvocacy": args.policy_advocacy,
    }

    if args.date_type == "range":
        params["tenderStartDate"] = normalize_roc_date(args.start_date)
        params["tenderEndDate"] = normalize_roc_date(args.end_date)

    if page and page > 1:
        params[page_param] = page

    return params


def fetch_html(
    session: requests.Session,
    params: dict[str, str | int],
    timeout: int,
) -> str:
    response = session.get(SEARCH_URL, params=params, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_pagination(soup: BeautifulSoup) -> tuple[int, str]:
    pages = {1}
    page_param = "d-49738-p"
    page_box = soup.select_one("#displaytagBannerDiv")
    if not page_box:
        return 1, page_param

    for link in page_box.select("a[href]"):
        query = urlparse(link["href"]).query
        for key, value in parse_qsl(query):
            if key.endswith("-p") and value.isdigit():
                page_param = key
                pages.add(int(value))
    return max(pages), page_param


def extract_tender_name(row) -> str:
    view_link = row.select_one('a[title*="標案名稱:"]')
    if view_link and view_link.get("title"):
        return clean_text(view_link["title"].split("標案名稱:", 1)[1])

    scripts = " ".join(script.get_text(" ", strip=True) for script in row.select("script"))
    match = re.search(r'pageCode2Img\("(.+?)"\)', scripts)
    if match:
        return match.group(1)

    return ""


def parse_rows(html: str, keyword: str) -> tuple[list[dict[str, str]], int]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#tpam")
    if not table:
        return [], 1

    rows: list[dict[str, str]] = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) < 10:
            continue

        tender_id_raw = clean_cell(cells[2])
        is_correction = "更正公告" in tender_id_raw
        tender_id = clean_text(tender_id_raw.replace("(更正公告)", ""))

        view_link = tr.select_one('a[href*="/prkms/urlSelector/common/tpam"]')
        detail_url = urljoin(BASE_URL, view_link["href"]) if view_link else ""

        rows.append(
            {
                "query_keyword": keyword,
                "item_no": clean_cell(cells[0]),
                "agency": clean_cell(cells[1]),
                "tender_id": tender_id,
                "is_correction": "Y" if is_correction else "N",
                "tender_name": extract_tender_name(tr),
                "transmission_count": clean_cell(cells[3]),
                "tender_method": clean_cell(cells[4]),
                "procurement_category": clean_cell(cells[5]),
                "announcement_date": clean_cell(cells[6]),
                "bid_deadline": clean_cell(cells[7]),
                "budget_amount": clean_cell(cells[8]),
                "detail_url": detail_url,
            }
        )

    total_pages, page_param = parse_pagination(soup)
    return rows, total_pages, page_param


def search_keyword(
    session: requests.Session,
    keyword: str,
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    print(f"查詢：{keyword}", file=sys.stderr)
    first_html = fetch_html(session, build_params(keyword, args), args.timeout)
    rows, total_pages, page_param = parse_rows(first_html, keyword)

    for page in range(2, total_pages + 1):
        time.sleep(args.delay)
        html = fetch_html(
            session,
            build_params(keyword, args, page=page, page_param=page_param),
            args.timeout,
        )
        page_rows, _, _ = parse_rows(html, keyword)
        rows.extend(page_rows)

    print(f"  取得 {len(rows)} 筆", file=sys.stderr)
    return rows


# ---------- 公開徵求查詢 ----------

def build_appeal_params(
    keyword: str,
    start_date: str,
    end_date: str,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, str | int]:
    """公開徵求查詢是 GET，日期用西元斜線格式（normalize_roc_date 已可產出）。"""
    params: dict[str, str | int] = {
        "pageSize": page_size,
        "firstSearch": "true",
        "tenderId": "",
        "orgId": "",
        "orgName": "",
        "tenderName": keyword,
        "startDate": normalize_roc_date(start_date),
        "endDate": normalize_roc_date(end_date),
        f"{APPEAL_SORT}-n": 1,
        f"{APPEAL_SORT}-o": 1,
        f"{APPEAL_SORT}-s": "startDate",
        f"{APPEAL_SORT}-p": page,
    }
    return params


def fetch_appeal_html(
    session: requests.Session,
    params: dict[str, str | int],
    timeout: int,
) -> str:
    response = session.get(APPEAL_URL, params=params, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_appeal_rows(html: str, keyword: str) -> tuple[list[dict[str, str]], int, str]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#tpAppeal")
    page_param = f"{APPEAL_SORT}-p"
    if not table:
        return [], 1, page_param

    rows: list[dict[str, str]] = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) < 7:
            continue

        # 公開徵求日期欄位格式為「公告日 ─ 截止日」，直接抓出兩個日期
        date_text = clean_cell(cells[5])
        found_dates = re.findall(r"\d{2,4}/\d{1,2}/\d{1,2}", date_text)
        announcement_date = found_dates[0] if found_dates else ""
        deadline = found_dates[1] if len(found_dates) > 1 else ""

        view_link = tr.select_one('a[href*="/prkms/urlSelector/common/tpAppeal"]')
        detail_url = urljoin(BASE_URL, view_link["href"]) if view_link else ""

        rows.append(
            {
                "query_keyword": keyword,
                "item_no": clean_cell(cells[0]),
                "agency": clean_cell(cells[1]),
                "tender_id": clean_cell(cells[2]),
                "tender_name": extract_tender_name(tr),
                "announcement_count": clean_cell(cells[4]),
                "announcement_date": announcement_date,
                "deadline": deadline,
                "detail_url": detail_url,
            }
        )

    total_pages, page_param = parse_pagination(soup)
    return rows, total_pages, page_param


def search_appeal(
    session: requests.Session,
    keyword: str,
    start_date: str,
    end_date: str,
    delay: float = 0.45,
    timeout: int = 30,
    page_size: int = 100,
) -> list[dict[str, str]]:
    print(f"公開徵求查詢：{keyword or '(全部)'}", file=sys.stderr)
    first_html = fetch_appeal_html(
        session,
        build_appeal_params(keyword, start_date, end_date, page_size=page_size),
        timeout,
    )
    rows, total_pages, _page_param = parse_appeal_rows(first_html, keyword)

    for page in range(2, total_pages + 1):
        time.sleep(delay)
        html = fetch_appeal_html(
            session,
            build_appeal_params(keyword, start_date, end_date, page=page, page_size=page_size),
            timeout,
        )
        page_rows, _, _ = parse_appeal_rows(html, keyword)
        rows.extend(page_rows)

    print(f"  取得 {len(rows)} 筆", file=sys.stderr)
    return rows


def dedupe_appeal_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[tuple[str, str, str], dict[str, str]] = {}
    keyword_order: dict[tuple[str, str, str], list[str]] = {}

    for row in rows:
        key = (row["tender_id"], row["agency"], row["detail_url"])
        keyword = row["query_keyword"]
        if key not in merged:
            merged[key] = dict(row)
            keyword_order[key] = [keyword]
            continue
        if keyword not in keyword_order[key]:
            keyword_order[key].append(keyword)
            merged[key]["query_keyword"] = "/".join(keyword_order[key])

    return list(merged.values())


def dedupe_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[tuple[str, str, str], dict[str, str]] = {}
    keyword_order: dict[tuple[str, str, str], list[str]] = {}

    for row in rows:
        key = (
            row["tender_id"],
            row["agency"],
            row["detail_url"],
        )
        keyword = row["query_keyword"]
        if key not in merged:
            merged[key] = dict(row)
            keyword_order[key] = [keyword]
            continue

        if keyword not in keyword_order[key]:
            keyword_order[key].append(keyword)
            merged[key]["query_keyword"] = "/".join(keyword_order[key])

    return list(merged.values())


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: list[dict[str, str]], limit: int) -> None:
    if not rows:
        print("沒有查到資料。")
        return

    headers = ["關鍵字", "機關", "案號", "標案名稱", "公告日期", "截止投標", "預算"]
    widths = [10, 18, 14, 34, 10, 10, 12]
    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))

    for row in rows[:limit]:
        values = [
            row["query_keyword"],
            row["agency"],
            row["tender_id"],
            row["tender_name"],
            row["announcement_date"],
            row["bid_deadline"],
            row["budget_amount"],
        ]
        print(
            " | ".join(
                clean_text(value)[:width].ljust(width)
                for value, width in zip(values, widths)
            )
        )

    if len(rows) > limit:
        print(f"... 尚有 {len(rows) - limit} 筆，完整資料請看 CSV。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批次查詢政府電子採購網標案，列出結果並匯出 CSV。"
    )
    parser.add_argument("keywords", nargs="*", help="要查詢的標案名稱關鍵字，可輸入多個")
    parser.add_argument("-f", "--keyword-file", help="關鍵字文字檔，一行一個標案名稱")
    parser.add_argument("-o", "--output", help="輸出 CSV 檔名")
    parser.add_argument(
        "--date-type",
        choices=DATE_TYPE_MAP.keys(),
        default="today",
        help="today=當日，period=等標期內，range=日期區間",
    )
    parser.add_argument("--start-date", help="日期區間起日，例如 115/07/01 或 2026-07-01")
    parser.add_argument("--end-date", help="日期區間迄日，例如 115/07/08 或 2026-07-08")
    parser.add_argument("--page-size", type=int, default=100, choices=[10, 20, 50, 100])
    parser.add_argument("--delay", type=float, default=0.5, help="分頁/關鍵字之間等待秒數")
    parser.add_argument("--timeout", type=int, default=30, help="網路逾時秒數")
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="啟用 SSL 憑證驗證；政府採購網在部分 Python 版本可能驗證失敗",
    )
    parser.add_argument("--no-dedupe", action="store_true", help="不要移除重複標案")
    parser.add_argument("--print-limit", type=int, default=50, help="終端最多列出幾筆")

    parser.add_argument("--org-name", default="", help="機關名稱")
    parser.add_argument("--org-id", default="", help="機關代碼")
    parser.add_argument("--tender-id", default="", help="標案案號")
    parser.add_argument(
        "--tender-type",
        default="TENDER_DECLARATION",
        choices=["TENDER_DECLARATION", "SEARCH_APPEAL", "PUBLIC_READ", "PREDICT"],
        help="招標類型",
    )
    parser.add_argument(
        "--tender-way",
        default="TENDER_WAY_ALL_DECLARATION",
        help="招標方式代碼，預設為各式招標公告",
    )
    parser.add_argument(
        "--category",
        default="",
        choices=["", "RAD_PROCTRG_CATE_1", "RAD_PROCTRG_CATE_2", "RAD_PROCTRG_CATE_3"],
        help="採購性質：空白=不限，1=工程，2=財物，3=勞務",
    )
    parser.add_argument(
        "--policy-advocacy",
        default="",
        choices=["", "Y", "N"],
        help="是否為政策及業務宣導業務：空白=不限",
    )
    args = parser.parse_args()

    if args.date_type == "range" and (not args.start_date or not args.end_date):
        parser.error("--date-type range 需要同時提供 --start-date 和 --end-date")

    return args


def main() -> int:
    args = parse_args()
    keywords = read_keywords(args)
    if not keywords:
        print("請提供至少一個標案名稱關鍵字，或使用 --keyword-file。", file=sys.stderr)
        return 2

    output = (
        Path(args.output)
        if args.output
        else Path(f"tender_results_{datetime.now():%Y%m%d_%H%M%S}.csv")
    )

    session = requests.Session()
    session.verify = args.verify_ssl
    if not args.verify_ssl:
        urllib3.disable_warnings(InsecureRequestWarning)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        }
    )

    all_rows: list[dict[str, str]] = []
    for index, keyword in enumerate(keywords):
        if index:
            time.sleep(args.delay)
        all_rows.extend(search_keyword(session, keyword, args))

    if not args.no_dedupe:
        all_rows = dedupe_rows(all_rows)

    write_csv(all_rows, output)
    print_table(all_rows, args.print_limit)
    print(f"\n共 {len(all_rows)} 筆，已輸出：{output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
