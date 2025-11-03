import React from 'react';
import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { scraperApi, jobApi, executionApi } from '../api/client';

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

  const activeScrapes = scrapers?.items.filter((s) => s.is_active).length || 0;
  const activeJobs = jobs?.items.filter((j) => j.is_active).length || 0;

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
    </Box>
  );
};

export default DashboardPage;
