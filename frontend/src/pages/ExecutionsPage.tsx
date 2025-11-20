import React from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { executionApi, scraperApi, jobApi } from '../api/client';
import ExecutionRow from '../components/ExecutionRow';

const ExecutionsPage: React.FC = () => {
  const { data: executions, isLoading } = useQuery({
    queryKey: ['executions'],
    queryFn: () => executionApi.list(0, 100),
    refetchInterval: 5000, // Refresh every 5 seconds to catch new executions
  });

  const { data: scrapers } = useQuery({
    queryKey: ['scrapers'],
    queryFn: () => scraperApi.list(0, 100),
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobApi.list(0, 100),
  });

  // Create a map of scraper ID to name
  const scraperMap = React.useMemo(() => {
    const map: Record<number, string> = {};
    if (scrapers) {
      scrapers.items.forEach(scraper => {
        map[scraper.id] = scraper.name;
      });
    }
    return map;
  }, [scrapers]);

  // Create a map of job ID to name
  const jobMap = React.useMemo(() => {
    const map: Record<number, string> = {};
    if (jobs) {
      jobs.items.forEach(job => {
        map[job.id] = job.name;
      });
    }
    return map;
  }, [jobs]);

  if (isLoading) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Executions
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Job / Scraper</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Items Scraped</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {executions?.items.map((execution) => {
              // Prefer job name, fallback to scraper name, then ID
              const displayName = execution.job_id
                ? (jobMap[execution.job_id] || `Job ${execution.job_id}`)
                : (scraperMap[execution.scraper_id] || `Scraper ${execution.scraper_id}`);

              return (
                <ExecutionRow
                  key={execution.id}
                  execution={execution}
                  scraperName={displayName}
                />
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {executions?.items.length === 0 && (
        <Box textAlign="center" mt={4}>
          <Typography color="textSecondary">No executions yet. Run a scraper to see results!</Typography>
        </Box>
      )}
    </Box>
  );
};

export default ExecutionsPage;
