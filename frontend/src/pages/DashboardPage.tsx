import React from 'react';
import { Box, Card, CardContent, Grid, Typography, LinearProgress, Chip } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { scraperApi, jobApi, executionApi, systemApi } from '../api/client';
import MemoryIcon from '@mui/icons-material/Memory';
import StorageIcon from '@mui/icons-material/Storage';
import DnsIcon from '@mui/icons-material/Dns';
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck';

const DashboardPage: React.FC = () => {
  const { data: scrapers } = useQuery({
    queryKey: ['scrapers'],
    queryFn: () => scraperApi.list(0, 1000),
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobApi.list(0, 1000),
  });

  const { data: stats } = useQuery({
    queryKey: ['execution-stats'],
    queryFn: () => executionApi.getStats(),
  });

  const { data: systemStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: () => systemApi.getStats(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const activeScrapes = scrapers?.items.filter((s) => s.is_active).length || 0;
  const activeJobs = jobs?.items.filter((j) => j.is_active).length || 0;

  // Helper function to format bytes
  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Helper function to format uptime
  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  // Helper function to get color based on percentage
  const getColorForPercent = (percent: number): 'success' | 'warning' | 'error' => {
    if (percent < 60) return 'success';
    if (percent < 80) return 'warning';
    return 'error';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Scrapers
              </Typography>
              <Typography variant="h3">{scrapers?.total || 0}</Typography>
              <Typography variant="body2" color="textSecondary">
                {activeScrapes} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Jobs
              </Typography>
              <Typography variant="h3">{jobs?.total || 0}</Typography>
              <Typography variant="body2" color="textSecondary">
                {activeJobs} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Executions
              </Typography>
              <Typography variant="h3">{stats?.total_executions || 0}</Typography>
              <Typography variant="body2" color="success.main">
                {stats?.successful_executions || 0} successful
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Items Scraped
              </Typography>
              <Typography variant="h3">{stats?.total_items_scraped || 0}</Typography>
              <Typography variant="body2" color="textSecondary">
                {stats?.average_items_per_execution?.toFixed(1) || 0} avg per run
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          Quick Stats
        </Typography>
        <Card>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Success Rate
                </Typography>
                <Typography variant="h6">
                  {stats?.total_executions
                    ? ((stats.successful_executions / stats.total_executions) * 100).toFixed(1)
                    : 0}
                  %
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Failed Executions
                </Typography>
                <Typography variant="h6" color="error">
                  {stats?.failed_executions || 0}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Running Now
                </Typography>
                <Typography variant="h6" color="info.main">
                  {stats?.running_executions || 0}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Box>

      {/* System Statistics Section */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          System Statistics
        </Typography>
        <Grid container spacing={3}>
          {/* CPU Card */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <MemoryIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography color="textSecondary">CPU Usage</Typography>
                </Box>
                <Typography variant="h3" color={getColorForPercent(systemStats?.cpu_percent || 0) + '.main'}>
                  {systemStats?.cpu_percent?.toFixed(1) || 0}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemStats?.cpu_percent || 0}
                  color={getColorForPercent(systemStats?.cpu_percent || 0)}
                  sx={{ mt: 1, height: 8, borderRadius: 1 }}
                />
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  {systemStats?.cpu_count || 0} cores
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Memory Card */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <DnsIcon sx={{ mr: 1, color: 'secondary.main' }} />
                  <Typography color="textSecondary">Memory Usage</Typography>
                </Box>
                <Typography variant="h3" color={getColorForPercent(systemStats?.memory_percent || 0) + '.main'}>
                  {systemStats?.memory_percent?.toFixed(1) || 0}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemStats?.memory_percent || 0}
                  color={getColorForPercent(systemStats?.memory_percent || 0)}
                  sx={{ mt: 1, height: 8, borderRadius: 1 }}
                />
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  {systemStats?.memory_used_gb?.toFixed(1) || 0} / {systemStats?.memory_total_gb?.toFixed(1) || 0} GB
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Disk Card - show primary disk */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <StorageIcon sx={{ mr: 1, color: 'info.main' }} />
                  <Typography color="textSecondary">Disk Usage</Typography>
                </Box>
                {systemStats?.disks && systemStats.disks.length > 0 ? (
                  <>
                    <Typography variant="h3" color={getColorForPercent(systemStats.disks[0].percent_used) + '.main'}>
                      {systemStats.disks[0].percent_used.toFixed(1)}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={systemStats.disks[0].percent_used}
                      color={getColorForPercent(systemStats.disks[0].percent_used)}
                      sx={{ mt: 1, height: 8, borderRadius: 1 }}
                    />
                    <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                      {systemStats.disks[0].used_gb.toFixed(1)} / {systemStats.disks[0].total_gb.toFixed(1)} GB
                    </Typography>
                  </>
                ) : (
                  <Typography variant="h3">-</Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Network & Uptime Card */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <NetworkCheckIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography color="textSecondary">Network & System</Typography>
                </Box>
                <Typography variant="h5" sx={{ mb: 1 }}>
                  {systemStats ? formatUptime(systemStats.uptime_seconds) : '-'}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  uptime
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    <span style={{ color: '#4caf50' }}>↑</span> {systemStats ? formatBytes(systemStats.network_bytes_sent) : '-'}
                  </Typography>
                  <Typography variant="body2">
                    <span style={{ color: '#2196f3' }}>↓</span> {systemStats ? formatBytes(systemStats.network_bytes_recv) : '-'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Additional System Info */}
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Processes
                </Typography>
                <Typography variant="h6">
                  {systemStats?.process_count || 0}
                </Typography>
              </Grid>
              {systemStats?.docker_containers_total !== null && systemStats?.docker_containers_total !== undefined && (
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Docker Containers
                  </Typography>
                  <Typography variant="h6">
                    <Chip
                      label={`${systemStats.docker_containers_running || 0} running`}
                      color="success"
                      size="small"
                      sx={{ mr: 1 }}
                    />
                    <Chip
                      label={`${systemStats.docker_containers_total} total`}
                      size="small"
                    />
                  </Typography>
                </Grid>
              )}
              {systemStats?.database_size_mb !== null && systemStats?.database_size_mb !== undefined && (
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Database Size
                  </Typography>
                  <Typography variant="h6">
                    {systemStats.database_size_mb >= 1024
                      ? `${(systemStats.database_size_mb / 1024).toFixed(2)} GB`
                      : `${systemStats.database_size_mb.toFixed(1)} MB`}
                  </Typography>
                </Grid>
              )}
              {/* Additional disks if more than one */}
              {systemStats?.disks && systemStats.disks.length > 1 && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
                    All Disks
                  </Typography>
                  <Grid container spacing={1}>
                    {systemStats.disks.map((disk, index) => (
                      <Grid item xs={12} sm={6} md={4} key={index}>
                        <Box sx={{ p: 1, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                          <Typography variant="body2" fontWeight="bold">
                            {disk.mount_point}
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={disk.percent_used}
                            color={getColorForPercent(disk.percent_used)}
                            sx={{ my: 0.5, height: 6, borderRadius: 1 }}
                          />
                          <Typography variant="caption" color="textSecondary">
                            {disk.used_gb.toFixed(1)} / {disk.total_gb.toFixed(1)} GB ({disk.percent_used.toFixed(1)}%)
                          </Typography>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default DashboardPage;
