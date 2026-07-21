import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

import config


@dataclass
class MountStatus:
    mounted: bool
    mount_point: str
    checked_at: str
    error: str | None = None


def _now():
    return datetime.now(timezone.utc).isoformat()


def is_mounted(mount_point=None):
    mount_point = mount_point or config.MOUNT_POINT
    return os.path.ismount(mount_point)


def ensure_mounted():
    if is_mounted():
        return MountStatus(mounted=True, mount_point=config.MOUNT_POINT, checked_at=_now())

    try:
        result = subprocess.run(
            ["sudo", "-n", config.MOUNT_WRAPPER],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return MountStatus(mounted=False, mount_point=config.MOUNT_POINT, checked_at=_now(), error=str(exc))

    mounted = is_mounted()
    error = None
    if not mounted:
        error = result.stderr.strip() or result.stdout.strip() or "mount command failed"
    return MountStatus(mounted=mounted, mount_point=config.MOUNT_POINT, checked_at=_now(), error=error)


def get_status():
    mounted = is_mounted()
    return MountStatus(mounted=mounted, mount_point=config.MOUNT_POINT, checked_at=_now())
