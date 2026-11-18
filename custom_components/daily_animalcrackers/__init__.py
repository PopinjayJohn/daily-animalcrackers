import logging
import os
import asyncio
import socket
from datetime import timedelta
import aiohttp
import logging
import os
import asyncio
import socket
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_REFRESH_INTERVAL, FILENAME, FEED_URL
from .feed import extract_latest_comic

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Helper to perform blocking file write on executor
def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Initialize domain data storage if it doesn't exist
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Create coordinator here so both image and button platforms can access it
    image_path = hass.config.path(f"www/{FILENAME}")
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    async def update_image():
        """Download latest comic from RSS feed with retries and timeout.
        If download fails, keep existing file (do not overwrite with empty data)."""
        timeout = aiohttp.ClientTimeout(total=30)
        max_retries = 3
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch RSS feed (with retries)
                text = None
                for attempt in range(1, max_retries + 1):
                    try:
                        async with session.get(FEED_URL, timeout=timeout) as resp:
                            if resp.status != 200:
                                _LOGGER.warning("Failed to fetch feed (attempt %s): HTTP %s", attempt, resp.status)
                                raise aiohttp.ClientError(f"HTTP {resp.status}")
                            text = await resp.text()
                            break
                    except (aiohttp.ClientError, asyncio.TimeoutError, socket.gaierror) as err:
                        _LOGGER.debug("Feed fetch attempt %s failed: %s", attempt, err)
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** (attempt - 1))
                        else:
                            _LOGGER.warning("Failed to fetch feed after %s attempts: %s", max_retries, err)
                if not text:
                    _LOGGER.debug("Keeping existing image file (no new feed content).")
                    return None

                # Parse feed and find newest item containing an image
                # (some feeds put text-only items first, so items[0] may have no image)
                img_url, pub_date_str = extract_latest_comic(text)

                if not img_url:
                    return None

                # Download the image (with retries)
                data = None
                for attempt in range(1, max_retries + 1):
                    try:
                        async with session.get(img_url, timeout=timeout) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                break
                            else:
                                _LOGGER.warning("Failed to download image (attempt %s): HTTP %s", attempt, resp.status)
                                raise aiohttp.ClientError(f"HTTP {resp.status}")
                    except (aiohttp.ClientError, asyncio.TimeoutError, socket.gaierror) as err:
                        _LOGGER.debug("Image download attempt %s failed: %s", attempt, err)
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** (attempt - 1))
                        else:
                            _LOGGER.warning("Failed to download image after %s attempts: %s", max_retries, err)

                if data:
                    # Write file on executor to avoid blocking the event loop
                    await hass.async_add_executor_job(_write_bytes, image_path, data)
                    _LOGGER.debug("Downloaded Animal Crackers comic from feed: %s", img_url)
                    # Return dict with image data and publication date
                    return {
                        "image_data": data,
                        "pub_date": pub_date_str,
                    }
                else:
                    _LOGGER.debug("Keeping existing image file (download failed).")
        except Exception as e:
            _LOGGER.warning("Failed to download Animal Crackers comic: %s", e)
        return None

    interval = get_refresh_interval(entry)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="animalcrackers_image",
        update_method=update_image,
        update_interval=timedelta(hours=interval),
    )
    await coordinator.async_refresh()
    
    # Store coordinator and image path so platforms can access them
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "image_path": image_path,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, ["image", "button"])
    return True

def get_refresh_interval(entry):
    # Default to 3 hours if not set
    return entry.options.get(CONF_REFRESH_INTERVAL, 3)