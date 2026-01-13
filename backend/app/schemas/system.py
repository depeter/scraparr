"""System statistics schemas"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DiskUsage(BaseModel):
    """Disk usage for a single mount point"""
    mount_point: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class SystemStats(BaseModel):
    """System statistics response"""
    # CPU
    cpu_percent: float
    cpu_count: int

    # Memory
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float

    # Disk
    disks: List[DiskUsage]

    # Network (bytes)
    network_bytes_sent: int
    network_bytes_recv: int

    # System info
    uptime_seconds: int
    boot_time: datetime

    # Process info
    process_count: int

    # Docker (optional, if available)
    docker_containers_running: Optional[int] = None
    docker_containers_total: Optional[int] = None

    # Database size (optional)
    database_size_mb: Optional[float] = None

    # Timestamp
    timestamp: datetime

    class Config:
        from_attributes = True
