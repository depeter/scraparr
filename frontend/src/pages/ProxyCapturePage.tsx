import React from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  AlertTitle,
  Chip,
  Stack,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Link as MuiLink,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Android as AndroidIcon,
  Wifi as WifiIcon,
  Security as SecurityIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE_URL = 'http://192.168.1.6:8000/api';

interface ProxyStatus {
  running: boolean;
  status: string;
  server_ip: string;
  proxy_port: number;
  web_port: number;
  capture_file: string;
  capture_exists: boolean;
  capture_size: number;
}

interface ProxyInstructions {
  server_ip: string;
  proxy_port: number;
  web_interface_url: string;
  certificate_url: string;
  steps: Array<{
    step: number;
    title: string;
    instructions: string[];
  }>;
  troubleshooting: {
    [key: string]: {
      title: string;
      description: string;
      solutions: string[];
    };
  };
}

const ProxyCapturePage: React.FC = () => {
  const queryClient = useQueryClient();

  // Fetch proxy status
  const { data: status, isLoading: statusLoading } = useQuery<ProxyStatus>({
    queryKey: ['proxyStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/proxy/status`);
      return response.data;
    },
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Fetch instructions
  const { data: instructions } = useQuery<ProxyInstructions>({
    queryKey: ['proxyInstructions'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/proxy/instructions`);
      return response.data;
    },
  });

  // Start proxy mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/proxy/start`, {
        web_interface: true,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proxyStatus'] });
    },
  });

  // Stop proxy mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/proxy/stop`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proxyStatus'] });
    },
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (statusLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        📱 API Traffic Capture
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Capture network traffic from the CamperContact Android app to discover API endpoints
      </Typography>

      {/* Status Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
            <Box>
              <Typography variant="h6" gutterBottom>
                Proxy Status
              </Typography>
              <Stack direction="row" spacing={2} alignItems="center">
                <Chip
                  label={status?.running ? 'Running' : 'Stopped'}
                  color={status?.running ? 'success' : 'default'}
                  icon={status?.running ? <PlayIcon /> : <StopIcon />}
                />
                {status?.running && status?.server_ip && (
                  <>
                    <Typography variant="body2">
                      Server: <strong>{status.server_ip}:{status.proxy_port}</strong>
                    </Typography>
                    {status.web_port && (
                      <MuiLink
                        href={`http://${status.server_ip}:${status.web_port}`}
                        target="_blank"
                        rel="noopener"
                      >
                        <Chip
                          label="Open Web Interface"
                          size="small"
                          icon={<OpenInNewIcon />}
                          clickable
                        />
                      </MuiLink>
                    )}
                  </>
                )}
              </Stack>
              {status?.capture_exists && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Captured: {formatFileSize(status.capture_size)}
                </Typography>
              )}
            </Box>
            <Box>
              {status?.running ? (
                <Button
                  variant="contained"
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={() => stopMutation.mutate()}
                  disabled={stopMutation.isPending}
                >
                  Stop Capture
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayIcon />}
                  onClick={() => startMutation.mutate()}
                  disabled={startMutation.isPending}
                >
                  Start Capture
                </Button>
              )}
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Android Warning for Latest Version */}
      <Alert severity="warning" icon={<AndroidIcon />} sx={{ mb: 3 }}>
        <AlertTitle>Using Latest Android?</AlertTitle>
        Modern Android (7+) doesn't trust user certificates by default. If you see SSL errors:
        <ul style={{ marginTop: 8, marginBottom: 0 }}>
          <li>The app likely uses <strong>SSL certificate pinning</strong></li>
          <li>You may need to use Frida to bypass (see troubleshooting below)</li>
          <li>Or try an older Android device (Android 6 or lower)</li>
        </ul>
      </Alert>

      {/* Setup Instructions */}
      {status?.running && instructions && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📋 Setup Instructions
            </Typography>
            <Stepper orientation="vertical">
              {instructions.steps.map((step) => (
                <Step key={step.step} active>
                  <StepLabel>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {step.title}
                    </Typography>
                  </StepLabel>
                  <StepContent>
                    <Box component="ol" sx={{ pl: 2, mt: 1 }}>
                      {step.instructions.map((instruction, idx) => (
                        <Typography component="li" variant="body2" key={idx} sx={{ mb: 0.5 }}>
                          {instruction}
                        </Typography>
                      ))}
                    </Box>
                  </StepContent>
                </Step>
              ))}
            </Stepper>

            <Box sx={{ mt: 3, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                🔗 Quick Links:
              </Typography>
              <Stack direction="row" spacing={2}>
                <MuiLink href="http://mitm.it" target="_blank" rel="noopener">
                  <Chip label="Certificate Download" size="small" clickable icon={<SecurityIcon />} />
                </MuiLink>
                {status.web_port && (
                  <MuiLink href={instructions.web_interface_url} target="_blank" rel="noopener">
                    <Chip label="Live Traffic View" size="small" clickable icon={<WifiIcon />} />
                  </MuiLink>
                )}
              </Stack>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Troubleshooting */}
      {instructions && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🛠️ Troubleshooting
            </Typography>
            {Object.entries(instructions.troubleshooting).map(([key, issue]) => (
              <Accordion key={key}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <WarningIcon color="warning" fontSize="small" />
                    <Typography>{issue.title}</Typography>
                  </Stack>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" paragraph>
                    {issue.description}
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    Solutions:
                  </Typography>
                  <Box component="ul" sx={{ mt: 1 }}>
                    {issue.solutions.map((solution, idx) => (
                      <Typography component="li" variant="body2" key={idx}>
                        {solution}
                      </Typography>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}

            {/* Additional Info */}
            <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.100' }}>
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                Need more help?
              </Typography>
              <Typography variant="body2">
                Check the documentation at: <code>/home/peter/scraparr/campercontact/HEADLESS_SETUP.md</code>
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                For Frida SSL bypass setup: <code>./setup_frida.sh</code>
              </Typography>
            </Paper>
          </CardContent>
        </Card>
      )}

      {/* When not running */}
      {!status?.running && (
        <Alert severity="info" sx={{ mt: 3 }}>
          <AlertTitle>Ready to Start</AlertTitle>
          Click "Start Capture" above to begin intercepting traffic from your Android device.
          Make sure your phone is on the same network as this server.
        </Alert>
      )}
    </Box>
  );
};

export default ProxyCapturePage;
