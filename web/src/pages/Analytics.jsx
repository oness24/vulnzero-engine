import { motion } from 'framer-motion'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, TrophyIcon } from '@heroicons/react/24/outline'

const vulnerabilityTrend = [
  { month: 'Jul', discovered: 45, patched: 38, remaining: 7 },
  { month: 'Aug', discovered: 52, patched: 48, remaining: 4 },
  { month: 'Sep', discovered: 38, patched: 35, remaining: 3 },
  { month: 'Oct', discovered: 61, patched: 56, remaining: 5 },
  { month: 'Nov', discovered: 48, patched: 45, remaining: 3 },
  { month: 'Dec', discovered: 55, patched: 50, remaining: 5 },
  { month: 'Jan', discovered: 42, patched: 40, remaining: 2 },
]

const severityDistribution = [
  { name: 'Critical', value: 12, color: '#ff0055' },
  { name: 'High', value: 34, color: '#ff6b35' },
  { name: 'Medium', value: 67, color: '#ffa500' },
  { name: 'Low', value: 43, color: '#00ff88' },
]

const patchPerformance = [
  { category: 'SQL Injection', generated: 15, deployed: 14, success_rate: 93 },
  { category: 'XSS', generated: 28, deployed: 26, success_rate: 93 },
  { category: 'Path Traversal', generated: 8, deployed: 7, success_rate: 88 },
  { category: 'Dependency', generated: 45, deployed: 44, success_rate: 98 },
  { category: 'Auth Issues', generated: 12, deployed: 11, success_rate: 92 },
  { category: 'Other', generated: 34, deployed: 31, success_rate: 91 },
]

const deploymentMetrics = [
  { strategy: 'Rolling', count: 67, avg_duration: 15, success_rate: 96 },
  { strategy: 'Blue-Green', count: 38, avg_duration: 22, success_rate: 97 },
  { strategy: 'Canary', count: 14, avg_duration: 28, success_rate: 100 },
]

export default function Analytics() {
  const totalVulnerabilities = severityDistribution.reduce((sum, item) => sum + item.value, 0)
  const totalPatches = patchPerformance.reduce((sum, item) => sum + item.generated, 0)
  const avgSuccessRate = Math.round(patchPerformance.reduce((sum, item) => sum + item.success_rate, 0) / patchPerformance.length)
  const totalDeployments = deploymentMetrics.reduce((sum, item) => sum + item.count, 0)

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">Analytics</h1>
        <p className="text-cyber-gray-400">Comprehensive insights into vulnerability management performance</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
          <div className="flex items-center justify-between mb-2">
            <p className="text-cyber-gray-400 text-sm">Total Vulnerabilities</p>
            <ArrowTrendingDownIcon className="h-5 w-5 text-cyber-green" />
          </div>
          <p className="text-3xl font-bold text-white mb-1">{totalVulnerabilities}</p>
          <p className="text-cyber-green text-sm">↓ 8 from last month</p>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-purple/20">
          <div className="flex items-center justify-between mb-2">
            <p className="text-cyber-gray-400 text-sm">Patches Generated</p>
            <TrophyIcon className="h-5 w-5 text-cyber-purple" />
          </div>
          <p className="text-3xl font-bold text-white mb-1">{totalPatches}</p>
          <p className="text-cyber-purple text-sm">{avgSuccessRate}% success rate</p>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-green/20">
          <div className="flex items-center justify-between mb-2">
            <p className="text-cyber-gray-400 text-sm">Deployments</p>
            <ArrowTrendingUpIcon className="h-5 w-5 text-cyber-green" />
          </div>
          <p className="text-3xl font-bold text-white mb-1">{totalDeployments}</p>
          <p className="text-cyber-green text-sm">↑ 12 from last month</p>
        </div>

        <div className="glass-card p-6 rounded-xl border border-cyber-orange/20">
          <div className="flex items-center justify-between mb-2">
            <p className="text-cyber-gray-400 text-sm">MTTR</p>
            <span className="text-cyber-orange text-xs">Mean Time To Remediate</span>
          </div>
          <p className="text-3xl font-bold text-white mb-1">2.3h</p>
          <p className="text-cyber-green text-sm">↓ 0.5h improvement</p>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vulnerability Trend */}
        <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
          <h2 className="text-lg font-semibold text-white mb-4">Vulnerability Trend (7 Months)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={vulnerabilityTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="month" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(0, 217, 255, 0.3)',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="discovered" stroke="#ff6b35" strokeWidth={2} name="Discovered" />
              <Line type="monotone" dataKey="patched" stroke="#00ff88" strokeWidth={2} name="Patched" />
              <Line type="monotone" dataKey="remaining" stroke="#00d9ff" strokeWidth={2} name="Remaining" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Distribution */}
        <div className="glass-card p-6 rounded-xl border border-cyber-purple/20">
          <h2 className="text-lg font-semibold text-white mb-4">Severity Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={severityDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {severityDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(181, 55, 242, 0.3)',
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Patch Performance by Category */}
        <div className="glass-card p-6 rounded-xl border border-cyber-green/20">
          <h2 className="text-lg font-semibold text-white mb-4">Patch Performance by Category</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={patchPerformance}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="category" stroke="#64748b" angle={-15} textAnchor="end" height={80} />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(0, 255, 136, 0.3)',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              <Bar dataKey="generated" fill="#00d9ff" name="Generated" radius={[8, 8, 0, 0]} />
              <Bar dataKey="deployed" fill="#00ff88" name="Deployed" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Deployment Strategy Performance */}
        <div className="glass-card p-6 rounded-xl border border-cyber-orange/20">
          <h2 className="text-lg font-semibold text-white mb-4">Deployment Strategy Performance</h2>
          <div className="space-y-4">
            {deploymentMetrics.map((strategy, index) => (
              <motion.div
                key={strategy.strategy}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass-card p-4 rounded-lg border border-cyber-gray-800/50"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-semibold">{strategy.strategy}</h3>
                  <span className="text-cyber-green text-sm font-medium">{strategy.success_rate}% success</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-cyber-gray-500 text-xs">Deployments</p>
                    <p className="text-white font-medium">{strategy.count}</p>
                  </div>
                  <div>
                    <p className="text-cyber-gray-500 text-xs">Avg Duration</p>
                    <p className="text-white font-medium">{strategy.avg_duration}min</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Insights */}
      <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
        <h2 className="text-lg font-semibold text-white mb-4">Key Insights</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-cyber-green/10 border border-cyber-green/30 rounded-lg">
            <h4 className="text-cyber-green font-medium mb-2">✓ Improvement</h4>
            <p className="text-cyber-gray-300 text-sm">Dependency vulnerabilities have 98% patch success rate, the highest across all categories</p>
          </div>
          <div className="p-4 bg-cyber-blue/10 border border-cyber-blue/30 rounded-lg">
            <h4 className="text-cyber-blue font-medium mb-2">📊 Trend</h4>
            <p className="text-cyber-gray-300 text-sm">Canary deployments show 100% success rate but take 28min on average - optimal for critical patches</p>
          </div>
          <div className="p-4 bg-cyber-orange/10 border border-cyber-orange/30 rounded-lg">
            <h4 className="text-cyber-orange font-medium mb-2">⚠ Attention Needed</h4>
            <p className="text-cyber-gray-300 text-sm">Path traversal vulnerabilities have 88% patch success - review automated patch generation for this category</p>
          </div>
          <div className="p-4 bg-cyber-purple/10 border border-cyber-purple/30 rounded-lg">
            <h4 className="text-cyber-purple font-medium mb-2">🎯 Recommendation</h4>
            <p className="text-cyber-gray-300 text-sm">MTTR improved by 0.5h - continue optimizing patch generation and deployment automation</p>
          </div>
        </div>
      </div>
    </div>
  )
}
