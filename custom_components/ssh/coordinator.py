from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from ssh_terminal_manager import (
    CommandError,
    SensorCommand,
    SSHAuthError,
    SSHHostKeyUnknownError,
    SSHManager,
)

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


class StateCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        manager: SSHManager,
        update_interval: int,
    ) -> None:
        super().__init__(
            hass,
            manager.logger,
            name=f"{manager.name} state",
            update_interval=timedelta(seconds=update_interval),
        )
        self.manager = manager
        # Add listener to keep updating without any entities
        self.stop: Callable = self.async_add_listener(lambda: None)

    async def _async_update_data(self) -> None:
        try:
            await self.manager.async_update_state()
        except SSHHostKeyUnknownError as exc:
            self.stop()
            raise ConfigEntryError from exc
        except SSHAuthError as exc:
            self.stop()
            raise ConfigEntryAuthFailed from exc
        except Exception as exc:
            raise UpdateFailed(f"Exception during update: {exc}") from exc


class SensorCommandCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        manager: SSHManager,
        command: SensorCommand,
    ) -> None:
        super().__init__(
            hass,
            manager.logger,
            name=f"{manager.name} {', '.join(sensor.key for sensor in command.sensors)}",
            update_interval=timedelta(seconds=command.interval),
        )
        self.manager = manager
        self._command = command
        # Add listener to keep updating without any entities
        self.stop: Callable = self.async_add_listener(lambda: None)

    async def _async_update_data(self) -> None:
        if not self.manager.state.is_connected:
            return
        try:
            await self.manager.async_execute_command(self._command)
        except CommandError:
            pass
        except Exception as exc:
            raise UpdateFailed(f"Exception updating {self.name}: {exc}") from exc
