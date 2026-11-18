"""Shared RSS feed parsing for Daily Animal Crackers."""
import html
import logging
import re
import xml.etree.ElementTree as ET

_LOGGER = logging.getLogger(__name__)

# Matches any src="..." URL; comic image URLs have no file extension,
# so we cannot require .(gif|png|jpg) like the old Fingerpori feed did.
_SRC_RE = re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE)


def extract_latest_comic(feed_xml: str) -> tuple[str | None, str | None]:
    """Return (image_url, pub_date) for the newest feed item containing an image.

    Iterates over <item> elements in order and returns the first one that
    yields an image URL, either via an <enclosure> tag or an <img src>
    in the item content. Returns (None, None) when nothing is found.
    """
    try:
        root = ET.fromstring(feed_xml)
    except Exception as e:
        _LOGGER.warning("Failed to parse RSS feed: %s", e)
        return None, None

    items = root.findall(".//item")
    if not items:
        _LOGGER.warning("No items found in RSS feed")
        return None, None

    for item in items:
        img_url: str | None = None

        enclosure = item.find("enclosure")
        if enclosure is not None and enclosure.attrib.get("url"):
            img_url = html.unescape(enclosure.attrib["url"].strip())

        if not img_url:
            item_xml = ET.tostring(item, encoding="unicode")
            for m in _SRC_RE.finditer(item_xml):
                candidate = html.unescape(m.group(1).strip())
                if candidate.startswith("http://") or candidate.startswith("https://"):
                    img_url = candidate
                    break

        if not img_url:
            continue

        pub_date_str: str | None = None
        pub_date_elem = item.find("pubDate")
        if pub_date_elem is not None and pub_date_elem.text:
            pub_date_str = pub_date_elem.text.strip()

        return img_url, pub_date_str

    _LOGGER.warning("No image URL found in any feed item")
    return None, None
