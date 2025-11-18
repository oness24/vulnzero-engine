import { motion } from 'framer-motion'
import { RocketLaunchIcon, CheckCircleIcon, XCircleIcon, ClockIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

const mockDeployments = [
  {
    id: 1,
    patch_id: 2,
    patch_title: 'DOMPurify Integration for XSS Prevention',
    strategy: 'canary',
    target_environment: 'production',
    status: 'in_progress',
    progress: 0.45,
    started_at: '2024-01-17T10:00:00Z',
    estimated_completion: '2024-01-17T10:30:00Z',
    current_step: 'health_checks',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'healthy',
      response_time: 'healthy',
    },
  },
  {
    id: 2,
    patch_id: 1,
    patch_title: 'Parameterized Queries for Auth Module',
    strategy: 'blue-green',
    target_environment: 'staging',
    status: 'completed',
    progress: 1.0,
    started_at: '2024-01-16T14:00:00Z',
    completed_at: '2024-01-16T14:25:00Z',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'healthy',
      response_time: 'healthy',
    },
  },
  {
    id: 3,
    patch_id: 3,
    patch_title: 'Upgrade lodash to 4.17.21',
    strategy: 'rolling',
    target_environment: 'production',
    status: 'completed',
    progress: 1.0,
    started_at: '2024-01-15T09:00:00Z',
    completed_at: '2024-01-15T09:45:00Z',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'healthy',
      response_time: 'healthy',
    },
  },
  {
    id: 4,
    patch_id: 4,
    patch_title: 'Path Sanitization for File Upload',
    strategy: 'blue-green',
    target_environment: 'staging',
    status: 'failed',
    progress: 0.65,
    started_at: '2024-01-14T18:00:00Z',
    failed_at: '2024-01-14T18:20:00Z',
    rollback_at: '2024-01-14T18:25:00Z',
    failure_reason: 'Health check failed: Error rate exceeded threshold (5.2%)',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'unhealthy',
      response_time: 'degraded',
    },
  },
]

const statusConfig = {
  pending: { label: 'Pending', color: 'text-cyber-gray-400', icon: ClockIcon },
  in_progress: { label: 'In Progress', color: 'text-cyber-blue', icon: ArrowPathIcon },
  completed: { label: 'Completed', color: 'text-cyber-green', icon: CheckCircleIcon },
  failed: { label: 'Failed', color: 'text-cyber-red', icon: XCircleIcon },
  rolled_back: { label: 'Rolled Back', color: 'text-cyber-orange', icon: ArrowPathIcon },
}

const strategyConfig = {
  rolling: { label: 'Rolling', color: 'bg-cyber-blue/20 text-cyber-blue' },
  'blue-green': { label: 'Blue-Green', color: 'bg-cyber-purple/20 text-cyber-purple' },
  canary: { label: 'Canary', color: 'bg-cyber-green/20 text-cyber-green' },
}

const healthConfig = {
  healthy: { label: 'Healthy', color: 'text-cyber-green' },
  degraded: { label: 'Degraded', color: 'text-cyber-orange' },
  unhealthy: { label: 'Unhealthy', color: 'text-cyber-red' },
}

export default function Deployments() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">Deployments</h1>
        <p className="text-cyber-gray-400">Track and manage patch deployments across environments</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="glass-card p-4 rounded-lg border border-cyber-blue/20">
          <p className="text-cyber-gray-400 text-sm">Total Deployments</p>
          <p className="text-3xl font-bold text-white mt-1">{mockDeployments.length}</p>
        </div>
        <div className="glass-card p-4 rounded-lg border border-cyber-green/20">
          <p className="text-cyber-gray-400 text-sm">Success Rate</p>
          <p className="text-3xl font-bold text-cyber-green mt-1">
            {Math.round((mockDeployments.filter((d) => d.status === 'completed').length / mockDeployments.length) * 100)}%
          </p>
        </div>
        <div className="glass-card p-4 rounded-lg border border-cyber-purple/20">
          <p className="text-cyber-gray-400 text-sm">In Progress</p>
          <p className="text-3xl font-bold text-cyber-purple mt-1">
            {mockDeployments.filter((d) => d.status === 'in_progress').length}
          </p>
        </div>
        <div className="glass-card p-4 rounded-lg border border-cyber-orange/20">
          <p className="text-cyber-gray-400 text-sm">Avg Duration</p>
          <p className="text-3xl font-bold text-cyber-orange mt-1">18.5m</p>
        </div>
      </div>

      {/* Deployments List */}
      <div className="space-y-4">
        {mockDeployments.map((deployment, index) => {
          const status = statusConfig[deployment.status]

          return (
            <motion.div
              key={deployment.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass-card p-6 rounded-xl border border-cyber-gray-800/50 hover:border-cyber-blue/30 transition-all"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-3 py-1 rounded-md text-xs font-medium ${strategyConfig[deployment.strategy].color}`}>
                      {strategyConfig[deployment.strategy].label}
                    </span>
                    <span className="text-cyber-gray-500 text-sm">{deployment.target_environment}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-1">{deployment.patch_title}</h3>
                  <p className="text-cyber-gray-500 text-sm">Deployment #{deployment.id}</p>
                </div>
                <div className="flex items-center gap-2">
                  <status.icon className={`h-5 w-5 ${status.color}`} />
                  <span className={`text-sm font-medium ${status.color}`}>{status.label}</span>
                </div>
              </div>

              {/* Progress Bar */}
              {deployment.status === 'in_progress' && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-cyber-gray-400">Progress</span>
                    <span className="text-white font-medium">{Math.round(deployment.progress * 100)}%</span>
                  </div>
                  <div className="h-2 bg-cyber-gray-900 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${deployment.progress * 100}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full bg-gradient-to-r from-cyber-blue to-cyber-purple"
                    />
                  </div>
                  <p className="text-cyber-gray-500 text-xs mt-2">Current step: {deployment.current_step}</p>
                </div>
              )}

              {/* Health Checks */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                {Object.entries(deployment.health_checks).map(([metric, health]) => (
                  <div key={metric} className="glass-card p-3 rounded-lg border border-cyber-gray-800/50">
                    <p className="text-cyber-gray-400 text-xs capitalize mb-1">{metric.replace('_', ' ')}</p>
                    <p className={`text-sm font-medium ${healthConfig[health].color}`}>{healthConfig[health].label}</p>
                  </div>
                ))}
              </div>

              {/* Failure Reason */}
              {deployment.failure_reason && (
                <div className="bg-cyber-red/10 border border-cyber-red/30 rounded-lg p-3 mb-4">
                  <p className="text-cyber-red text-sm font-medium">⚠ {deployment.failure_reason}</p>
                </div>
              )}

              {/* Timestamps */}
              <div className="flex items-center gap-4 text-xs text-cyber-gray-500">
                <div className="flex items-center gap-1">
                  <ClockIcon className="h-3 w-3" />
                  <span>Started: {new Date(deployment.started_at).toLocaleString()}</span>
                </div>
                {deployment.completed_at && (
                  <span>Completed: {new Date(deployment.completed_at).toLocaleString()}</span>
                )}
                {deployment.failed_at && <span>Failed: {new Date(deployment.failed_at).toLocaleString()}</span>}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
