import { motion } from 'framer-motion'
import {
  BugAntIcon,
  WrenchScrewdriverIcon,
  RocketLaunchIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// Mock data - will be replaced with real API calls
const stats = [
  {
    name: 'Total Vulnerabilities',
    value: '156',
    change: '-8',
    changeType: 'decrease',
    icon: BugAntIcon,
    color: 'cyber-red',
    bgColor: 'bg-status-critical/10',
    borderColor: 'border-status-critical/30',
  },
  {
    name: 'Patches Generated',
    value: '142',
    change: '+12',
    changeType: 'increase',
    icon: WrenchScrewdriverIcon,
    color: 'cyber-blue',
    bgColor: 'bg-cyber-blue/10',
    borderColor: 'border-cyber-blue/30',
  },
  {
    name: 'Active Deployments',
    value: '8',
    change: '+3',
    changeType: 'increase',
    icon: RocketLaunchIcon,
    color: 'cyber-purple',
    bgColor: 'bg-cyber-purple/10',
    borderColor: 'border-cyber-purple/30',
  },
  {
    name: 'Success Rate',
    value: '94%',
    change: '+2%',
    changeType: 'increase',
    icon: CheckCircleIcon,
    color: 'cyber-green',
    bgColor: 'bg-cyber-green/10',
    borderColor: 'border-cyber-green/30',
  },
]

const recentVulnerabilities = [
  { id: 1, cve: 'CVE-2024-1234', severity: 'critical', title: 'SQL Injection in Auth Module', time: '5m ago' },
  { id: 2, cve: 'CVE-2024-5678', severity: 'high', title: 'XSS in User Profile', time: '15m ago' },
  { id: 3, cve: 'CVE-2024-9012', severity: 'medium', title: 'Outdated lodash Dependency', time: '1h ago' },
  { id: 4, cve: 'CVE-2024-3456', severity: 'high', title: 'Path Traversal in File Upload', time: '2h ago' },
  { id: 5, cve: 'CVE-2024-7890', severity: 'low', title: 'Missing Rate Limiting', time: '3h ago' },
]

const vulnerabilityTrend = [
  { date: 'Mon', critical: 8, high: 15, medium: 25, low: 12 },
  { date: 'Tue', critical: 12, high: 18, medium: 28, low: 15 },
  { date: 'Wed', critical: 10, high: 22, medium: 30, low: 18 },
  { date: 'Thu', critical: 15, high: 25, medium: 32, low: 20 },
  { date: 'Fri', critical: 12, high: 20, medium: 28, low: 16 },
  { date: 'Sat', critical: 10, high: 18, medium: 25, low: 14 },
  { date: 'Sun', critical: 8, high: 15, medium: 22, low: 12 },
]

const deploymentActivity = [
  { time: '00:00', deployments: 2 },
  { time: '04:00', deployments: 1 },
  { time: '08:00', deployments: 5 },
  { time: '12:00', deployments: 8 },
  { time: '16:00', deployments: 6 },
  { time: '20:00', deployments: 4 },
]

const getSeverityColor = (severity) => {
  const colors = {
    critical: 'text-status-critical bg-status-critical/20 ring-status-critical/40',
    high: 'text-status-high bg-status-high/20 ring-status-high/40',
    medium: 'text-status-medium bg-status-medium/20 ring-status-medium/40',
    low: 'text-status-low bg-status-low/20 ring-status-low/40',
  }
  return colors[severity] || colors.low
}

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">
          Dashboard
        </h1>
        <p className="text-cyber-gray-400">
          Real-time overview of your vulnerability management system
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`glass-card p-6 rounded-xl border ${stat.borderColor} hover:shadow-lg hover:shadow-${stat.color}/20 transition-all duration-300`}
          >
            <div className="flex items-center justify-between">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 text-${stat.color}`} />
              </div>
              <span
                className={`text-sm font-medium ${
                  stat.changeType === 'increase' ? 'text-cyber-green' : 'text-cyber-red'
                }`}
              >
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <h3 className="text-2xl font-bold text-white">{stat.value}</h3>
              <p className="text-sm text-cyber-gray-400 mt-1">{stat.name}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vulnerability Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6 rounded-xl border border-cyber-blue/20"
        >
          <h2 className="text-lg font-semibold text-white mb-4">Vulnerability Trend</h2>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={vulnerabilityTrend}>
              <defs>
                <linearGradient id="criticalGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff0055" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ff0055" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="highGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(0, 217, 255, 0.3)',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Area
                type="monotone"
                dataKey="critical"
                stackId="1"
                stroke="#ff0055"
                fill="url(#criticalGradient)"
              />
              <Area
                type="monotone"
                dataKey="high"
                stackId="1"
                stroke="#ff6b35"
                fill="url(#highGradient)"
              />
              <Area
                type="monotone"
                dataKey="medium"
                stackId="1"
                stroke="#ffa500"
                fill="#ffa50020"
              />
              <Area
                type="monotone"
                dataKey="low"
                stackId="1"
                stroke="#00ff88"
                fill="#00ff8820"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Deployment Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-6 rounded-xl border border-cyber-purple/20"
        >
          <h2 className="text-lg font-semibold text-white mb-4">Deployment Activity (24h)</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={deploymentActivity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(181, 55, 242, 0.3)',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Bar dataKey="deployments" fill="#b537f2" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Recent Vulnerabilities */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="glass-card p-6 rounded-xl border border-cyber-blue/20"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">Recent Vulnerabilities</h2>
          <a href="/vulnerabilities" className="text-sm text-cyber-blue hover:text-cyber-purple transition-colors">
            View all →
          </a>
        </div>
        <div className="space-y-4">
          {recentVulnerabilities.map((vuln, index) => (
            <motion.div
              key={vuln.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.7 + index * 0.05 }}
              className="flex items-center justify-between p-4 rounded-lg bg-cyber-gray-900/30 hover:bg-cyber-gray-900/50 border border-cyber-gray-800/50 hover:border-cyber-blue/30 transition-all cursor-pointer"
            >
              <div className="flex items-center space-x-4 flex-1">
                <span className={`px-2 py-1 rounded-md text-xs font-medium ring-1 ${getSeverityColor(vuln.severity)}`}>
                  {vuln.severity.toUpperCase()}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{vuln.title}</p>
                  <p className="text-xs text-cyber-gray-500">{vuln.cve}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2 text-xs text-cyber-gray-500">
                <ClockIcon className="h-4 w-4" />
                <span>{vuln.time}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <button className="glass-card p-6 rounded-xl border border-cyber-blue/20 hover:border-cyber-blue/50 hover:shadow-lg hover:shadow-cyber-blue/20 transition-all text-left group">
          <BugAntIcon className="h-8 w-8 text-cyber-blue mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="text-white font-semibold mb-1">Scan for Vulnerabilities</h3>
          <p className="text-cyber-gray-400 text-sm">Run a new vulnerability scan</p>
        </button>
        <button className="glass-card p-6 rounded-xl border border-cyber-purple/20 hover:border-cyber-purple/50 hover:shadow-lg hover:shadow-cyber-purple/20 transition-all text-left group">
          <WrenchScrewdriverIcon className="h-8 w-8 text-cyber-purple mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="text-white font-semibold mb-1">Generate Patches</h3>
          <p className="text-cyber-gray-400 text-sm">Create AI-powered patches</p>
        </button>
        <button className="glass-card p-6 rounded-xl border border-cyber-green/20 hover:border-cyber-green/50 hover:shadow-lg hover:shadow-cyber-green/20 transition-all text-left group">
          <RocketLaunchIcon className="h-8 w-8 text-cyber-green mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="text-white font-semibold mb-1">Deploy Updates</h3>
          <p className="text-cyber-gray-400 text-sm">Deploy pending patches</p>
        </button>
      </motion.div>
    </div>
  )
}
