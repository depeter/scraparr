"""System statistics API endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import psutil
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User
from app.schemas.system import SystemStats, DiskUsage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


def get_disk_usage() -> list[DiskUsage]:
    """Get disk usage for all mounted partitions"""
    disks = []
    seen_devices = set()
    partitions = psutil.disk_partitions(all=False)

    for partition in partitions:
        try:
            # Skip virtual and bind mounts (common in Docker)
            # Only include real disk partitions
            if partition.fstype in ('', 'overlay', 'tmpfs', 'devtmpfs', 'squashfs'):
                continue

            # Skip if we've already seen this device (to avoid duplicates from bind mounts)
            device_key = partition.device
            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)

            usage = psutil.disk_usage(partition.mountpoint)

            # Skip tiny partitions (like boot partitions under 1GB)
            if usage.total < 1024**3:
                continue

            disks.append(DiskUsage(
                mount_point=partition.mountpoint,
                total_gb=round(usage.total / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                free_gb=round(usage.free / (1024**3), 2),
                percent_used=usage.percent
            ))
        except (PermissionError, OSError):
            # Skip partitions we can't access
            continue

    # If we're in a container and only got bind mounts, try to get root filesystem info
    if not disks:
        try:
            usage = psutil.disk_usage('/')
            disks.append(DiskUsage(
                mount_point='/',
                total_gb=round(usage.total / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                free_gb=round(usage.free / (1024**3), 2),
                percent_used=usage.percent
            ))
        except (PermissionError, OSError):
            pass

    return disks


def get_docker_stats() -> tuple[int, int]:
    """Get Docker container stats if available"""
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(all=True)
        running = len([c for c in containers if c.status == 'running'])
        return running, len(containers)
    except Exception:
        return None, None


async def get_database_size(db: AsyncSession) -> float:
    """Get PostgreSQL database size in MB"""
    try:
        result = await db.execute(text(
            "SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 as size_mb"
        ))
        row = result.fetchone()
        return round(row[0], 2) if row else None
    except Exception as e:
        logger.warning(f"Could not get database size: {e}")
        return None


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive system statistics including CPU, memory, disk, and network"""

    # CPU info
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()

    # Memory info
    memory = psutil.virtual_memory()

    # Disk info
    disks = get_disk_usage()

    # Network info
    net_io = psutil.net_io_counters()

    # System uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = int((datetime.now() - boot_time).total_seconds())

    # Process count
    process_count = len(psutil.pids())

    # Docker stats (optional)
    docker_running, docker_total = get_docker_stats()

    # Database size
    db_size = await get_database_size(db)

    return SystemStats(
        cpu_percent=cpu_percent,
        cpu_count=cpu_count,
        memory_total_gb=round(memory.total / (1024**3), 2),
        memory_used_gb=round(memory.used / (1024**3), 2),
        memory_available_gb=round(memory.available / (1024**3), 2),
        memory_percent=memory.percent,
        disks=disks,
        network_bytes_sent=net_io.bytes_sent,
        network_bytes_recv=net_io.bytes_recv,
        uptime_seconds=uptime_seconds,
        boot_time=boot_time,
        process_count=process_count,
        docker_containers_running=docker_running,
        docker_containers_total=docker_total,
        database_size_mb=db_size,
        timestamp=datetime.now()
    )
