# VulnZero Frontend-Backend Integration Guide

## Overview

This guide explains how the VulnZero frontend integrates with the backend API and WebSocket services for real-time updates.

---

## Architecture

```
┌─────────────────┐
│  React Frontend │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│  HTTP │ │WebSocket│
│  API  │ │Service  │
└───┬───┘ └──┬──────┘
    │        │
    └────┬───┘
         │
┌────────▼────────┐
│  FastAPI Backend│
└─────────────────┘
```

---

## Setup

### 1. Environment Variables

Create a `.env` file in the `web/` directory:

```bash
cp .env.example .env
```

Edit `.env` to match your backend configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
VITE_DEBUG=true
```

### 2. Install Dependencies

```bash
cd web
npm install
```

### 3. Start Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

---

## API Service (`src/services/api.js`)

### Features

- **Centralized API client** using Axios
- **Request/Response interceptors** for authentication and error handling
- **Automatic token refresh** on 401 errors
- **Request ID tracking** for distributed tracing
- **Global error handling** with toast notifications
- **Development logging** for debugging

### Usage

```javascript
import { vulnerabilitiesApi } from '@/services/api'

// List vulnerabilities with filters
const response = await vulnerabilitiesApi.list({
  severity: 'critical',
  status: 'open',
  page: 1,
  limit: 20,
})

// Get single vulnerability
const vuln = await vulnerabilitiesApi.get(123)

// Create vulnerability
const newVuln = await vulnerabilitiesApi.create({
  cve_id: 'CVE-2024-1234',
  title: 'SQL Injection',
  severity: 'critical',
})
```

### Available APIs

- **vulnerabilitiesApi**: CRUD operations for vulnerabilities
- **patchesApi**: Generate, approve, reject, test patches
- **deploymentsApi**: Create, monitor, rollback deployments
- **monitoringApi**: Health checks, metrics, alerts, analytics
- **dashboardApi**: Dashboard statistics and trends
- **settingsApi**: User settings and integrations
- **authApi**: Login, logout, token refresh

---

## WebSocket Service (`src/services/websocket.js`)

### Features

- **Real-time updates** for deployments, vulnerabilities, patches
- **Automatic reconnection** with exponential backoff
- **Event-based architecture** for easy subscription
- **Toast notifications** for important events
- **Room support** for filtered updates
- **Connection status tracking**

### Usage

```javascript
import wsService from '@/services/websocket'

// Connect (usually done in WebSocketProvider)
wsService.connect()

// Subscribe to events
const unsubscribe = wsService.on('deployment_progress', (data) => {
  console.log('Deployment progress:', data.progress)
  setProgress(data.progress)
})

// Unsubscribe when component unmounts
useEffect(() => {
  return () => unsubscribe()
}, [])

// Join a specific room for filtered updates
wsService.joinRoom('deployment:123')
```

### Available Events

**Deployment Events:**
- `deployment_started` - New deployment started
- `deployment_progress` - Progress update (0-1)
- `deployment_completed` - Deployment succeeded
- `deployment_failed` - Deployment failed
- `deployment_rolled_back` - Deployment rolled back

**Vulnerability Events:**
- `vulnerability_detected` - New vulnerability found

**Patch Events:**
- `patch_generated` - New patch created
- `patch_approved` - Patch approved
- `patch_rejected` - Patch rejected

**System Events:**
- `alert` - System alert
- `health_degraded` - Service health degraded
- `health_restored` - Service health restored
- `metrics_update` - Metrics updated

---

## Custom React Hooks

### useVulnerabilities

```javascript
import { useVulnerabilities } from '@/hooks'

function VulnerabilitiesPage() {
  const { vulnerabilities, loading, error, refetch, markFalsePositive } = useVulnerabilities({
    severity: 'critical',
    status: 'open',
  })

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div>
      {vulnerabilities.map((vuln) => (
        <div key={vuln.id}>
          <h3>{vuln.title}</h3>
          <button onClick={() => markFalsePositive(vuln.id)}>
            Mark False Positive
          </button>
        </div>
      ))}
    </div>
  )
}
```

### usePatches

```javascript
import { usePatches } from '@/hooks'

function PatchesPage() {
  const { patches, loading, generatePatch, approvePatch, testPatch } = usePatches({
    status: 'pending_approval',
  })

  const handleGenerate = async (vulnId) => {
    await generatePatch(vulnId, 'code')
  }

  const handleApprove = async (patchId) => {
    await approvePatch(patchId)
  }

  return <div>...</div>
}
```

### useDeployments

```javascript
import { useDeployments } from '@/hooks'

function DeploymentsPage() {
  const {
    deployments,
    loading,
    createDeployment,
    rollbackDeployment,
    pauseDeployment
  } = useDeployments()

  // Real-time updates are automatic via WebSocket!

  return <div>...</div>
}
```

### useDashboardStats

```javascript
import { useDashboardStats } from '@/hooks'

function Dashboard() {
  const { stats, loading, error } = useDashboardStats()

  // Auto-refreshes every 30 seconds
  // Updates in real-time via WebSocket

  return <div>...</div>
}
```

### useSystemHealth

```javascript
import { useSystemHealth } from '@/hooks'

function HealthIndicator() {
  const { health, loading } = useSystemHealth()

  // Auto-refreshes every 10 seconds

  return (
    <div>
      {health?.status === 'healthy' ? '✅' : '⚠️'}
      Database: {health?.checks?.database}
      Redis: {health?.checks?.redis}
      Celery: {health?.checks?.celery}
    </div>
  )
}
```

---

## WebSocket Provider

The `WebSocketProvider` manages the WebSocket connection lifecycle globally.

### Usage in App.jsx

```javascript
import { WebSocketProvider } from './components/providers/WebSocketProvider'

function App() {
  return (
    <Router>
      <WebSocketProvider>
        {/* Your app components */}
      </WebSocketProvider>
    </Router>
  )
}
```

### Access Connection Status

```javascript
import { useWebSocket } from './components/providers/WebSocketProvider'

function ConnectionIndicator() {
  const { isConnected, status } = useWebSocket()

  return (
    <div>
      {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
    </div>
  )
}
```

---

## Authentication Flow

### 1. Login

```javascript
import { authApi } from '@/services/api'

const handleLogin = async (username, password) => {
  try {
    const response = await authApi.login({ username, password })

    // Tokens are automatically stored in localStorage
    const { access_token, refresh_token } = response.data

    // Redirect to dashboard
    navigate('/dashboard')
  } catch (error) {
    console.error('Login failed:', error)
  }
}
```

### 2. Automatic Token Refresh

The API client automatically refreshes expired tokens:

```javascript
// User makes a request with expired token
const response = await vulnerabilitiesApi.list()

// If token is expired (401):
// 1. API client intercepts the 401 error
// 2. Attempts to refresh using refresh_token
// 3. Retries original request with new token
// 4. If refresh fails, redirects to /login
```

### 3. Logout

```javascript
import { authApi } from '@/services/api'

const handleLogout = async () => {
  await authApi.logout() // Clears tokens from localStorage
  navigate('/login')
}
```

---

## Error Handling

### Global Error Handling

The API client automatically handles common errors:

- **401 Unauthorized**: Attempts token refresh, redirects to login if fails
- **403 Forbidden**: Shows "Access denied" toast
- **404 Not Found**: Shows "Resource not found" toast
- **429 Rate Limited**: Shows "Too many requests" toast
- **500 Server Error**: Shows "Server error" toast
- **Network Error**: Shows "Network error" toast

### Custom Error Handling

```javascript
try {
  await patchesApi.approve(patchId)
} catch (error) {
  // Global handler already showed a toast
  // Handle specific error logic here
  console.error('Approval failed:', error)

  if (error.response?.status === 403) {
    // Redirect to permissions page
    navigate('/permissions')
  }
}
```

---

## Real-Time Updates

### Deployment Progress

```javascript
import { useDeployments } from '@/hooks'
import { useEffect } from 'react'
import wsService from '@/services/websocket'

function DeploymentDetail({ id }) {
  const { deployment } = useDeployment(id)

  // Progress updates are automatic via the hook!
  // The hook listens to WebSocket events and updates state

  return (
    <div>
      <h2>Deployment {id}</h2>
      <progress value={deployment.progress} max={1} />
      <p>Current step: {deployment.current_step}</p>
    </div>
  )
}
```

### New Vulnerability Notifications

```javascript
import { useEffect } from 'react'
import wsService from '@/services/websocket'

function App() {
  useEffect(() => {
    // Listen for new vulnerabilities
    const unsubscribe = wsService.on('vulnerability_detected', (data) => {
      // Toast notification is automatic
      // Optionally update UI
      console.log('New vulnerability:', data)
    })

    return unsubscribe
  }, [])

  return <div>...</div>
}
```

---

## Performance Optimization

### Automatic Polling

Some hooks auto-refresh data:

- `useDashboardStats()` - Every 30 seconds
- `useSystemHealth()` - Every 10 seconds
- `useMetrics()` - Every 5 seconds

To disable auto-refresh:

```javascript
// Custom implementation without auto-refresh
const [stats, setStats] = useState(null)

const fetchStats = async () => {
  const response = await dashboardApi.stats()
  setStats(response.data)
}

useEffect(() => {
  fetchStats()
  // No interval - manual refresh only
}, [])
```

### Pagination

```javascript
const { vulnerabilities, pagination, loading } = useVulnerabilities({
  page: 1,
  limit: 20,
})

// pagination = {
//   page: 1,
//   pageSize: 20,
//   total: 156,
//   totalPages: 8,
//   hasNext: true,
//   hasPrevious: false,
// }
```

---

## Testing

### Unit Tests for Hooks

```javascript
import { renderHook, waitFor } from '@testing-library/react'
import { useVulnerabilities } from '@/hooks'
import { vulnerabilitiesApi } from '@/services/api'

vi.mock('@/services/api')

test('useVulnerabilities fetches data', async () => {
  vulnerabilitiesApi.list.mockResolvedValue({
    data: { items: [{ id: 1, title: 'Test' }] },
  })

  const { result } = renderHook(() => useVulnerabilities())

  await waitFor(() => {
    expect(result.current.loading).toBe(false)
  })

  expect(result.current.vulnerabilities).toHaveLength(1)
})
```

---

## Troubleshooting

### WebSocket Not Connecting

1. Check VITE_WS_BASE_URL in `.env`
2. Verify backend WebSocket is running
3. Check browser console for errors
4. Ensure CORS allows WebSocket connections

### API Requests Failing

1. Check VITE_API_BASE_URL in `.env`
2. Verify backend API is running
3. Check authentication token in localStorage
4. Verify CORS configuration on backend

### Token Refresh Loop

If you see multiple refresh requests:

1. Clear localStorage
2. Delete cookies
3. Log in again

---

## Production Deployment

### Environment Variables

```env
VITE_API_BASE_URL=https://api.vulnzero.example.com
VITE_WS_BASE_URL=https://api.vulnzero.example.com
VITE_ENVIRONMENT=production
VITE_DEBUG=false
```

### Build

```bash
npm run build
```

### Deploy

Upload the `dist/` folder to your static hosting provider (Netlify, Vercel, S3, etc.)

---

## Security Considerations

1. **Never commit .env** - It's in .gitignore
2. **Use HTTPS in production** - For both API and WebSocket
3. **Validate all API responses** - Don't trust data blindly
4. **Sanitize user input** - Prevent XSS attacks
5. **Keep dependencies updated** - Run `npm audit` regularly

---

**Last Updated:** 2025-11-18
**Author:** VulnZero Team
