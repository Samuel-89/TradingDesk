"""News fetcher for offline market research."""

import xml.etree.ElementTree as ET
from typing import List, Dict
import requests


def fetch_ticker_news_rss(symbol: str, max_items: int = 5) -> List[Dict[str, str]]:
    """Fetch latest headlines and summaries for a ticker using Yahoo Finance RSS feed."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol.upper()}&region=US&lang=en-US"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    articles: List[Dict[str, str]] = []
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item")[:max_items]:
                    title_elem = item.find("title")
                    desc_elem = item.find("description")
                    link_elem = item.find("link")
                    pub_elem = item.find("pubDate")

                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                    if title:
                        articles.append({
                            "title": title,
                            "description": description,
                            "link": link,
                            "pub_date": pub_date,
                        })
    except Exception:
        # Fallback if network issue or parse error
        pass

    return articles
