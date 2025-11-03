import React from 'react';
import {
  Box,
  Button,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  IconButton,
} from '@mui/material';
import { PlayArrow, Delete } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApi } from '../api/client';
import { format } from 'date-fns';

const JobsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobApi.list(0, 100),
  });

  const runMutation = useMutation({
    mutationFn: (id: number) => jobApi.run(id),
    onSuccess: () => {
      alert('Job started!');
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => jobApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  if (isLoading) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Jobs</Typography>
        <Button variant="contained" color="primary">
          Create Job
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Schedule Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Run</TableCell>
              <TableCell>Next Run</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs?.items.map((job) => (
              <TableRow key={job.id}>
                <TableCell>{job.name}</TableCell>
                <TableCell>
                  <Chip label={job.schedule_type} size="small" />
                </TableCell>
                <TableCell>
                  <Chip
                    label={job.is_active ? 'Active' : 'Inactive'}
                    size="small"
                    color={job.is_active ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  {job.last_run_at ? format(new Date(job.last_run_at), 'PPp') : 'Never'}
                </TableCell>
                <TableCell>
                  {job.next_run_at ? format(new Date(job.next_run_at), 'PPp') : 'Not scheduled'}
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    color="primary"
                    onClick={() => runMutation.mutate(job.id)}
                  >
                    <PlayArrow />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => {
                      if (window.confirm('Delete this job?')) {
                        deleteMutation.mutate(job.id);
                      }
                    }}
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {jobs?.items.length === 0 && (
        <Box textAlign="center" mt={4}>
          <Typography color="textSecondary">No jobs yet. Create your first scheduled job!</Typography>
        </Box>
      )}
    </Box>
  );
};

export default JobsPage;
