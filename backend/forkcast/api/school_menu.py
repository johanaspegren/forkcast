import html
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException


MATILDA_HOST = "menu.matildaplatform.com"


def fetch_matilda_school_menu(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != MATILDA_HOST:
        raise HTTPException(status_code=422, detail="Only menu.matildaplatform.com URLs are supported")

    request = Request(url, headers={"User-Agent": "Forkcast/0.1"})
    try:
        with urlopen(request, timeout=8) as response:
            page = response.read().decode("utf-8")
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch school menu: {exc}") from exc

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        page,
        re.DOTALL,
    )
    if not match:
        raise HTTPException(status_code=502, detail="Could not find embedded menu data")

    data = json.loads(html.unescape(match.group(1)))
    page_props = data.get("props", {}).get("pageProps", {})
    return {
        "source_url": url,
        "start_date": page_props.get("startDate"),
        "end_date": page_props.get("endDate"),
        "distributor": page_props.get("distributor", {}).get("name"),
        "days": [_format_day(meal) for meal in page_props.get("meals", [])],
    }


def _format_day(meal: dict) -> dict:
    courses = []
    for course in meal.get("courses", []):
        tags = [tag.get("name") for tag in course.get("tags", []) if tag.get("name")]
        media = course.get("media") or []
        courses.append(
            {
                "name": course.get("name"),
                "option_name": course.get("optionName"),
                "tags": tags,
                "image": media[0].get("src") if media else None,
            }
        )
    return {
        "date": meal.get("date"),
        "name": meal.get("name"),
        "courses": courses,
    }
