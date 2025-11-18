import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FunnelIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  TagIcon,
} from '@heroicons/react/24/outline'

// Mock data - will be replaced with real API calls
const mockVulnerabilities = [
  {
    id: 1,
    cve_id: 'CVE-2024-1234',
    title: 'Critical SQL Injection in Authentication Module',
    description: 'SQL injection vulnerability allows unauthorized database access through login form',
    severity: 'critical',
    cvss_score: 9.8,
    status: 'open',
    affected_packages: ['auth-module@1.2.3', 'user-service@2.1.0'],
    discovered_at: '2024-01-15T10:30:00Z',
    tags: ['sql-injection', 'authentication', 'high-priority'],
  },
  {
    id: 2,
    cve_id: 'CVE-2024-5678',
    title: 'Cross-Site Scripting (XSS) in User Profile',
    description: 'Stored XSS vulnerability in user profile bio field',
    severity: 'high',
    cvss_score: 7.5,
    status: 'open',
    affected_packages: ['frontend@2.1.0'],
    discovered_at: '2024-01-16T14:20:00Z',
    tags: ['xss', 'frontend', 'user-input'],
  },
  {
    id: 3,
    cve_id: 'CVE-2024-9012',
    title: 'Prototype Pollution in lodash',
    description: 'Outdated lodash version vulnerable to prototype pollution',
    severity: 'medium',
    cvss_score: 5.3,
    status: 'patched',
    affected_packages: ['lodash@4.17.15'],
    discovered_at: '2024-01-10T09:15:00Z',
    patched_at: '2024-01-17T11:00:00Z',
    tags: ['dependency', 'prototype-pollution'],
  },
  {
    id: 4,
    cve_id: 'CVE-2024-3456',
    title: 'Path Traversal in File Upload',
    description: 'Insufficient path validation allows directory traversal attacks',
    severity: 'high',
    cvss_score: 8.1,
    status: 'in_progress',
    affected_packages: ['file-service@1.5.2'],
    discovered_at: '2024-01-14T16:45:00Z',
    tags: ['path-traversal', 'file-upload', 'critical'],
  },
  {
    id: 5,
    cve_id: 'CVE-2024-7890',
    title: 'Missing Rate Limiting on API Endpoints',
    description: 'No rate limiting allows brute force and DoS attacks',
    severity: 'low',
    cvss_score: 4.2,
    status: 'open',
    affected_packages: ['api-gateway@3.0.1'],
    discovered_at: '2024-01-12T11:20:00Z',
    tags: ['rate-limiting', 'security', 'api'],
  },
]

const severityConfig = {
  critical: {
    color: 'status-critical',
    bg: 'bg-status-critical/20',
    border: 'border-status-critical/40',
    text: 'text-status-critical',
  },
  high: {
    color: 'status-high',
    bg: 'bg-status-high/20',
    border: 'border-status-high/40',
    text: 'text-status-high',
  },
  medium: {
    color: 'status-medium',
    bg: 'bg-status-medium/20',
    border: 'border-status-medium/40',
    text: 'text-status-medium',
  },
  low: {
    color: 'status-low',
    bg: 'bg-status-low/20',
    border: 'border-status-low/40',
    text: 'text-status-low',
  },
}

const statusConfig = {
  open: { label: 'Open', color: 'text-cyber-red', bg: 'bg-cyber-red/20' },
  in_progress: { label: 'In Progress', color: 'text-cyber-orange', bg: 'bg-cyber-orange/20' },
  patched: { label: 'Patched', color: 'text-cyber-green', bg: 'bg-cyber-green/20' },
}

export default function Vulnerabilities() {
  const [selectedSeverity, setSelectedSeverity] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedVuln, setSelectedVuln] = useState(null)

  const filteredVulnerabilities = mockVulnerabilities.filter((vuln) => {
    const matchesSeverity = selectedSeverity === 'all' || vuln.severity === selectedSeverity
    const matchesStatus = selectedStatus === 'all' || vuln.status === selectedStatus
    const matchesSearch =
      searchQuery === '' ||
      vuln.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      vuln.cve_id.toLowerCase().includes(searchQuery.toLowerCase())

    return matchesSeverity && matchesStatus && matchesSearch
  })

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">Vulnerabilities</h1>
        <p className="text-cyber-gray-400">Discovered security vulnerabilities across your infrastructure</p>
      </div>

      {/* Filters and Search */}
      <div className="glass-card p-4 rounded-xl border border-cyber-blue/20">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-cyber-gray-500" />
            <input
              type="text"
              placeholder="Search vulnerabilities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-cyber-gray-500 focus:outline-none focus:ring-2 focus:ring-cyber-blue focus:border-transparent"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="patched">Patched</option>
          </select>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Critical', count: mockVulnerabilities.filter((v) => v.severity === 'critical').length, color: 'status-critical' },
          { label: 'High', count: mockVulnerabilities.filter((v) => v.severity === 'high').length, color: 'status-high' },
          { label: 'Medium', count: mockVulnerabilities.filter((v) => v.severity === 'medium').length, color: 'status-medium' },
          { label: 'Low', count: mockVulnerabilities.filter((v) => v.severity === 'low').length, color: 'status-low' },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-4 rounded-lg border border-cyber-gray-800/50">
            <p className="text-cyber-gray-400 text-sm">{stat.label}</p>
            <p className={`text-2xl font-bold text-${stat.color} mt-1`}>{stat.count}</p>
          </div>
        ))}
      </div>

      {/* Vulnerabilities List */}
      <div className="space-y-4">
        {filteredVulnerabilities.length === 0 ? (
          <div className="glass-card p-12 rounded-xl border border-cyber-blue/20 text-center">
            <p className="text-cyber-gray-400">No vulnerabilities found matching your filters</p>
          </div>
        ) : (
          filteredVulnerabilities.map((vuln, index) => (
            <motion.div
              key={vuln.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => setSelectedVuln(selectedVuln?.id === vuln.id ? null : vuln)}
              className={`glass-card p-6 rounded-xl border ${
                selectedVuln?.id === vuln.id
                  ? 'border-cyber-blue/50 shadow-lg shadow-cyber-blue/20'
                  : 'border-cyber-gray-800/50 hover:border-cyber-blue/30'
              } cursor-pointer transition-all duration-200`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-center gap-3 mb-3">
                    <span
                      className={`px-2.5 py-1 rounded-md text-xs font-medium ring-1 ${severityConfig[vuln.severity].bg} ${severityConfig[vuln.severity].text} ${severityConfig[vuln.severity].border}`}
                    >
                      {vuln.severity.toUpperCase()}
                    </span>
                    <span
                      className={`px-2.5 py-1 rounded-md text-xs font-medium ${statusConfig[vuln.status].bg} ${statusConfig[vuln.status].color}`}
                    >
                      {statusConfig[vuln.status].label}
                    </span>
                    <span className="text-cyber-gray-500 text-sm">{vuln.cve_id}</span>
                  </div>

                  {/* Title and Description */}
                  <h3 className="text-lg font-semibold text-white mb-2">{vuln.title}</h3>
                  <p className="text-cyber-gray-400 text-sm mb-4">{vuln.description}</p>

                  {/* Metadata */}
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-2 text-cyber-gray-500">
                      <ExclamationTriangleIcon className="h-4 w-4" />
                      <span>CVSS: {vuln.cvss_score}</span>
                    </div>
                    <div className="flex items-center gap-2 text-cyber-gray-500">
                      <ClockIcon className="h-4 w-4" />
                      <span>{formatDate(vuln.discovered_at)}</span>
                    </div>
                    <div className="flex items-center gap-2 text-cyber-gray-500">
                      <TagIcon className="h-4 w-4" />
                      <span>{vuln.affected_packages.length} packages</span>
                    </div>
                  </div>
                </div>

                {/* Expand Indicator */}
                <motion.div animate={{ rotate: selectedVuln?.id === vuln.id ? 180 : 0 }} transition={{ duration: 0.2 }}>
                  <ChevronDownIcon className="h-5 w-5 text-cyber-gray-500" />
                </motion.div>
              </div>

              {/* Expanded Details */}
              <AnimatePresence>
                {selectedVuln?.id === vuln.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-6 pt-6 border-t border-cyber-gray-800/50"
                  >
                    {/* Affected Packages */}
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-white mb-2">Affected Packages</h4>
                      <div className="flex flex-wrap gap-2">
                        {vuln.affected_packages.map((pkg, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-md text-xs text-cyber-gray-300 font-mono"
                          >
                            {pkg}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Tags */}
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-white mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-2">
                        {vuln.tags.map((tag, i) => (
                          <span key={i} className="px-3 py-1 bg-cyber-blue/10 border border-cyber-blue/30 rounded-md text-xs text-cyber-blue">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                      <button className="btn-cyber px-4 py-2 text-sm">Generate Patch</button>
                      <button className="glass-card px-4 py-2 text-sm text-white border border-cyber-gray-800 hover:border-cyber-blue/50 rounded-lg transition-all">
                        View Details
                      </button>
                      <button className="glass-card px-4 py-2 text-sm text-white border border-cyber-gray-800 hover:border-cyber-red/50 rounded-lg transition-all">
                        Mark as False Positive
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
