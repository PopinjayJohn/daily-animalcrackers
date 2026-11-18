import logging
import os
import asyncio
import socket
from datetime import timedelta
import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import FILENAME, FEED_URL, DEFAULT_NAME, DOMAIN
from .feed import extract_latest_comic
from .image_entity import AnimalCrackersImage

_LOGGER = logging.getLogger(__name__)

# Helper to perform blocking file write on executor
def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
):
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
                img_url, _pub_date_str = extract_latest_comic(text)

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
                    return data
                else:
                    _LOGGER.debug("Keeping existing image file (download failed).")
        except Exception as e:
            _LOGGER.warning("Failed to download Animal Crackers comic: %s", e)
        return None

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="animalcrackers_image",
        update_method=update_image,
        update_interval=timedelta(hours=1),  # fallback for platform setup
    )

    await coordinator.async_refresh()
    # When created from platform (legacy) we can't tie to a config entry;
    # use None for config_entry_id so unique_id is based on feed filename.
    async_add_entities([AnimalCrackersImage(hass, coordinator, image_path, None, DEFAULT_NAME)])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    # Get coordinator and image path from hass.data (created in __init__.py)
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    image_path = hass.data[DOMAIN][entry.entry_id]["image_path"]

    # Pass config entry id and entry title so entity gets a stable unique_id
    async_add_entities([AnimalCrackersImage(hass, coordinator, image_path, entry.entry_id, entry.title or DEFAULT_NAME)])
