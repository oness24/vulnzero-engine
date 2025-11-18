import { motion } from 'framer-motion'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { CpuChipIcon, ServerIcon, ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

const systemMetrics = [
  { time: '10:00', cpu: 45, memory: 62, api_latency: 42, error_rate: 0.1 },
  { time: '10:05', cpu: 48, memory: 64, api_latency: 45, error_rate: 0.2 },
  { time: '10:10', cpu: 52, memory: 66, api_latency: 48, error_rate: 0.15 },
  { time: '10:15', cpu: 55, memory: 68, api_latency: 52, error_rate: 0.3 },
  { time: '10:20', cpu: 50, memory: 65, api_latency: 46, error_rate: 0.1 },
  { time: '10:25', cpu: 47, memory: 63, api_latency: 43, error_rate: 0.2 },
]

const recentAlerts = [
  {
    id: 1,
    type: 'deployment_failed',
    severity: 'high',
    title: 'Deployment Failed: Patch #42',
    message: 'Blue-green deployment failed due to health check failure',
    timestamp: '2024-01-17T11:30:00Z',
    acknowledged: false,
  },
  {
    id: 2,
    type: 'high_error_rate',
    severity: 'medium',
    title: 'Elevated Error Rate Detected',
    message: 'Error rate increased to 3.2% on production API',
    timestamp: '2024-01-17T11:15:00Z',
    acknowledged: true,
  },
  {
    id: 3,
    type: 'critical_vulnerability',
    severity: 'critical',
    title: 'New Critical Vulnerability',
    message: 'CVE-2024-9999: Remote code execution in auth module',
    timestamp: '2024-01-17T09:15:00Z',
    acknowledged: true,
  },
]

const serviceStatus = [
  { name: 'API Gateway', status: 'healthy', uptime: 99.98, response_time: 42 },
  { name: 'Aggregator Service', status: 'healthy', uptime: 99.95, response_time: 156 },
  { name: 'Patch Generator', status: 'healthy', uptime: 99.92, response_time: 1240 },
  { name: 'Deployment Engine', status: 'healthy', uptime: 99.89, response_time: 890 },
  { name: 'Database', status: 'healthy', uptime: 99.99, response_time: 12 },
  { name: 'Redis Cache', status: 'healthy', uptime: 99.97, response_time: 3 },
  { name: 'Celery Workers', status: 'degraded', uptime: 98.5, response_time: 450 },
]

const severityColors = {
  critical: 'text-status-critical bg-status-critical/20',
  high: 'text-status-high bg-status-high/20',
  medium: 'text-status-medium bg-status-medium/20',
  low: 'text-status-low bg-status-low/20',
}

const statusColors = {
  healthy: 'text-cyber-green bg-cyber-green/20',
  degraded: 'text-cyber-orange bg-cyber-orange/20',
  unhealthy: 'text-cyber-red bg-cyber-red/20',
}

export default function Monitoring() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">System Monitoring</h1>
        <p className="text-cyber-gray-400">Real-time health metrics and system alerts</p>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
          <div className="flex items-center justify-between mb-4">
            <CpuChipIcon className="h-8 w-8 text-cyber-blue" />
            <span className="text-2xl font-bold text-white">58%</span>
          </div>
          <p className="text-sm text-cyber-gray-400">CPU Usage</p>
          <div className="mt-2 h-1 bg-cyber-gray-900 rounded-full overflow-hidden">
            <div className="h-full w-[58%] bg-cyber-blue rounded-full" />
          </div>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-purple/20">
          <div className="flex items-center justify-between mb-4">
            <ServerIcon className="h-8 w-8 text-cyber-purple" />
            <span className="text-2xl font-bold text-white">72%</span>
          </div>
          <p className="text-sm text-cyber-gray-400">Memory Usage</p>
          <div className="mt-2 h-1 bg-cyber-gray-900 rounded-full overflow-hidden">
            <div className="h-full w-[72%] bg-cyber-purple rounded-full" />
          </div>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-green/20">
          <div className="flex items-center justify-between mb-4">
            <ClockIcon className="h-8 w-8 text-cyber-green" />
            <span className="text-2xl font-bold text-white">42ms</span>
          </div>
          <p className="text-sm text-cyber-gray-400">API Latency</p>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-red/20">
          <div className="flex items-center justify-between mb-4">
            <ExclamationTriangleIcon className="h-8 w-8 text-cyber-red" />
            <span className="text-2xl font-bold text-white">0.2%</span>
          </div>
          <p className="text-sm text-cyber-gray-400">Error Rate</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & Memory Usage */}
        <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
          <h2 className="text-lg font-semibold text-white mb-4">Resource Usage</h2>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={systemMetrics}>
              <defs>
                <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d9ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d9ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#b537f2" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#b537f2" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(0, 217, 255, 0.3)',
                  borderRadius: '8px',
                }}
              />
              <Area type="monotone" dataKey="cpu" stroke="#00d9ff" fill="url(#cpuGradient)" name="CPU %" />
              <Area type="monotone" dataKey="memory" stroke="#b537f2" fill="url(#memoryGradient)" name="Memory %" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* API Latency & Error Rate */}
        <div className="glass-card p-6 rounded-xl border border-cyber-green/20">
          <h2 className="text-lg font-semibold text-white mb-4">API Performance</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={systemMetrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis yAxisId="left" stroke="#64748b" />
              <YAxis yAxisId="right" orientation="right" stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(0, 255, 136, 0.3)',
                  borderRadius: '8px',
                }}
              />
              <Line yAxisId="left" type="monotone" dataKey="api_latency" stroke="#00ff88" name="Latency (ms)" strokeWidth={2} />
              <Line yAxisId="right" type="monotone" dataKey="error_rate" stroke="#ff0055" name="Error Rate %" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Service Status */}
      <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
        <h2 className="text-lg font-semibold text-white mb-4">Service Status</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {serviceStatus.map((service) => (
            <div key={service.name} className="glass-card p-4 rounded-lg border border-cyber-gray-800/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-medium">{service.name}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[service.status]}`}>
                  {service.status.toUpperCase()}
                </span>
              </div>
              <div className="flex gap-4 text-xs text-cyber-gray-500">
                <span>Uptime: {service.uptime}%</span>
                <span>Response: {service.response_time}ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="glass-card p-6 rounded-xl border border-cyber-red/20">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Alerts</h2>
        <div className="space-y-3">
          {recentAlerts.map((alert) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`p-4 rounded-lg border ${
                alert.acknowledged ? 'bg-cyber-gray-900/30 border-cyber-gray-800' : 'bg-cyber-red/5 border-cyber-red/30'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${severityColors[alert.severity]}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-cyber-gray-500 text-xs">{new Date(alert.timestamp).toLocaleString()}</span>
                  </div>
                  <h4 className="text-white font-medium mb-1">{alert.title}</h4>
                  <p className="text-cyber-gray-400 text-sm">{alert.message}</p>
                </div>
                {!alert.acknowledged && (
                  <button className="px-3 py-1 bg-cyber-blue/20 text-cyber-blue text-xs rounded hover:bg-cyber-blue/30 transition-colors">
                    Acknowledge
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
