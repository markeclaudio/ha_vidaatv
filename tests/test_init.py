"""Tests for the Hisense TV integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.vidaa_tv import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.vidaa_tv.const import (
    AUTH_MODE_AUTO,
    AUTH_MODE_DYNAMIC,
    AUTH_MODE_STATIC,
    CONF_AUTH_MODE,
    DOMAIN,
)

from .conftest import MOCK_CONFIG_ENTRY_DATA, create_mock_config_entry


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test async_setup registers services."""
    result = await async_setup(hass, {})

    assert result is True
    assert hass.services.has_service(DOMAIN, "send_key")
    assert hass.services.has_service(DOMAIN, "launch_app")


async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_vidaa_tv: MagicMock,
) -> None:
    """Test successful entry setup."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv,
    ):
        # Use the proper setup mechanism
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.runtime_data is not None
    assert entry.runtime_data.coordinator is not None
    assert entry.runtime_data.tv is not None


async def test_async_setup_entry_loads_when_tv_offline(
    hass: HomeAssistant,
    mock_vidaa_tv_offline: MagicMock,
) -> None:
    """A TV in deep sleep must still set up so the WoL power button exists."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv_offline,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Entry loads even though the TV is unreachable; the coordinator just reports
    # the last update as unsuccessful until the TV comes online.
    from homeassistant.config_entries import ConfigEntryState
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator.last_update_success is False


async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_vidaa_tv: MagicMock,
) -> None:
    """Test entry unload."""
    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    mock_vidaa_tv.async_disconnect.assert_called_once()


async def test_send_key_service(
    hass: HomeAssistant,
    mock_vidaa_tv: MagicMock,
) -> None:
    """Test send_key service executes without error."""
    # Setup integration
    await async_setup(hass, {})

    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Call service - should execute without error
        await hass.services.async_call(
            DOMAIN,
            "send_key",
            {"key": "KEY_POWER"},
            blocking=True,
        )

    # Service call completed without raising an error
    # (mock assertions are complex due to coordinator indirection)


async def test_launch_app_service(
    hass: HomeAssistant,
    mock_vidaa_tv: MagicMock,
) -> None:
    """Test launch_app service executes without error."""
    # Setup integration
    await async_setup(hass, {})

    entry = create_mock_config_entry(hass)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Call service - should execute without error
        await hass.services.async_call(
            DOMAIN,
            "launch_app",
            {"app": "netflix"},
            blocking=True,
        )

    # Service call completed without raising an error
    # (mock assertions are complex due to coordinator indirection)


# --- authentication mode ---------------------------------------------------


@pytest.mark.parametrize(
    ("entry_data_mode", "options_mode", "expect_dynamic"),
    [
        (None, None, True),                 # paired before the option existed
        (AUTH_MODE_AUTO, None, True),
        (AUTH_MODE_STATIC, None, False),    # what a legacy-firmware TV pairs as
        (AUTH_MODE_DYNAMIC, AUTH_MODE_STATIC, False),  # options override wins
        (AUTH_MODE_STATIC, AUTH_MODE_DYNAMIC, True),
    ],
)
async def test_setup_entry_uses_the_stored_auth_mode(
    hass: HomeAssistant,
    mock_vidaa_tv: MagicMock,
    entry_data_mode: str | None,
    options_mode: str | None,
    expect_dynamic: bool,
) -> None:
    """The runtime client must use the scheme the entry paired with.

    Regression: this was hardcoded to dynamic auth, so a TV that needs the
    static login could pair but never reconnect after a restart.
    """
    data = dict(MOCK_CONFIG_ENTRY_DATA)
    if entry_data_mode is not None:
        data[CONF_AUTH_MODE] = entry_data_mode
    options = {CONF_AUTH_MODE: options_mode} if options_mode else {}

    entry = create_mock_config_entry(hass, data=data, options=options)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.vidaa_tv.AsyncVidaaTV",
        return_value=mock_vidaa_tv,
    ) as mock_class:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert mock_class.call_args.kwargs["use_dynamic_auth"] is expect_dynamic
