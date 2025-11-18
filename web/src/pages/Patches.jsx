import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  CodeBracketIcon,
  SparklesIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'

const mockPatches = [
  {
    id: 1,
    vulnerability_id: 1,
    vulnerability_cve: 'CVE-2024-1234',
    patch_type: 'code',
    title: 'Parameterized Queries for Auth Module',
    description: 'Replace string concatenation with parameterized queries to prevent SQL injection',
    status: 'approved',
    ai_confidence: 0.95,
    estimated_risk: 'low',
    created_at: '2024-01-15T11:00:00Z',
    approved_at: '2024-01-15T12:30:00Z',
    patch_script: '#!/bin/bash\nnpm install secure-auth@2.0.0\nsystemctl restart auth-service\n',
    rollback_script: '#!/bin/bash\nnpm install auth-module@1.2.3\nsystemctl restart auth-service\n',
    validation_tests: ['test_auth_injection.py', 'test_auth_security.py', 'test_auth_integration.py'],
  },
  {
    id: 2,
    vulnerability_id: 2,
    vulnerability_cve: 'CVE-2024-5678',
    patch_type: 'dependency',
    title: 'DOMPurify Integration for XSS Prevention',
    description: 'Install and configure DOMPurify to sanitize user input in profile fields',
    status: 'pending_approval',
    ai_confidence: 0.92,
    estimated_risk: 'low',
    created_at: '2024-01-16T15:00:00Z',
    patch_script: '#!/bin/bash\nnpm install dompurify@3.0.0\n',
    rollback_script: '#!/bin/bash\nnpm uninstall dompurify\n',
    validation_tests: ['test_xss_prevention.py', 'test_input_sanitization.py'],
  },
  {
    id: 3,
    vulnerability_id: 3,
    vulnerability_cve: 'CVE-2024-9012',
    patch_type: 'dependency',
    title: 'Upgrade lodash to 4.17.21',
    description: 'Update lodash to latest version to fix prototype pollution vulnerability',
    status: 'deployed',
    ai_confidence: 0.98,
    estimated_risk: 'very_low',
    created_at: '2024-01-10T09:30:00Z',
    approved_at: '2024-01-10T10:00:00Z',
    deployed_at: '2024-01-17T11:00:00Z',
    patch_script: '#!/bin/bash\nnpm update lodash@4.17.21\n',
    rollback_script: '#!/bin/bash\nnpm install lodash@4.17.15\n',
    validation_tests: ['test_lodash_update.py'],
  },
  {
    id: 4,
    vulnerability_id: 4,
    vulnerability_cve: 'CVE-2024-3456',
    patch_type: 'code',
    title: 'Path Sanitization for File Upload',
    description: 'Add path validation and sanitization to prevent directory traversal',
    status: 'testing',
    ai_confidence: 0.89,
    estimated_risk: 'medium',
    created_at: '2024-01-14T17:00:00Z',
    patch_script: '#!/bin/bash\n# Apply path sanitization patch\ncp path_validator.py /app/validators/\nsystemctl restart file-service\n',
    rollback_script: '#!/bin/bash\nrm /app/validators/path_validator.py\nsystemctl restart file-service\n',
    validation_tests: ['test_path_traversal.py', 'test_file_upload.py', 'test_path_sanitization.py'],
  },
]

const statusConfig = {
  pending_approval: {
    label: 'Pending Approval',
    icon: ClockIcon,
    color: 'text-cyber-orange',
    bg: 'bg-cyber-orange/20',
    border: 'border-cyber-orange/40',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircleIcon,
    color: 'text-cyber-green',
    bg: 'bg-cyber-green/20',
    border: 'border-cyber-green/40',
  },
  testing: {
    label: 'Testing',
    icon: SparklesIcon,
    color: 'text-cyber-blue',
    bg: 'bg-cyber-blue/20',
    border: 'border-cyber-blue/40',
  },
  deployed: {
    label: 'Deployed',
    icon: CheckCircleIcon,
    color: 'text-cyber-purple',
    bg: 'bg-cyber-purple/20',
    border: 'border-cyber-purple/40',
  },
  failed: {
    label: 'Failed',
    icon: XCircleIcon,
    color: 'text-cyber-red',
    bg: 'bg-cyber-red/20',
    border: 'border-cyber-red/40',
  },
}

const riskConfig = {
  very_low: { label: 'Very Low', color: 'text-cyber-green' },
  low: { label: 'Low', color: 'text-cyber-blue' },
  medium: { label: 'Medium', color: 'text-cyber-orange' },
  high: { label: 'High', color: 'text-cyber-red' },
}

export default function Patches() {
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedPatch, setSelectedPatch] = useState(null)

  const filteredPatches = mockPatches.filter((patch) => {
    return selectedStatus === 'all' || patch.status === selectedStatus
  })

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">Patches</h1>
        <p className="text-cyber-gray-400">AI-generated patches for discovered vulnerabilities</p>
      </div>

      {/* Stats and Filters */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Stats */}
        <div className="glass-card p-4 rounded-lg border border-cyber-blue/20">
          <p className="text-cyber-gray-400 text-sm">Total Patches</p>
          <p className="text-3xl font-bold text-white mt-1">{mockPatches.length}</p>
        </div>
        <div className="glass-card p-4 rounded-lg border border-cyber-green/20">
          <p className="text-cyber-gray-400 text-sm">Success Rate</p>
          <p className="text-3xl font-bold text-cyber-green mt-1">94%</p>
        </div>
        <div className="glass-card p-4 rounded-lg border border-cyber-purple/20">
          <p className="text-cyber-gray-400 text-sm">Avg Confidence</p>
          <p className="text-3xl font-bold text-cyber-purple mt-1">93.5%</p>
        </div>

        {/* Status Filter */}
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="glass-card border border-cyber-blue/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue"
        >
          <option value="all">All Statuses</option>
          <option value="pending_approval">Pending Approval</option>
          <option value="approved">Approved</option>
          <option value="testing">Testing</option>
          <option value="deployed">Deployed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Patches List */}
      <div className="space-y-4">
        {filteredPatches.map((patch, index) => {
          const status = statusConfig[patch.status]
          const risk = riskConfig[patch.estimated_risk]

          return (
            <motion.div
              key={patch.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => setSelectedPatch(selectedPatch?.id === patch.id ? null : patch)}
              className={`glass-card p-6 rounded-xl border ${
                selectedPatch?.id === patch.id
                  ? 'border-cyber-blue/50 shadow-lg shadow-cyber-blue/20'
                  : 'border-cyber-gray-800/50 hover:border-cyber-blue/30'
              } cursor-pointer transition-all duration-200`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-center gap-3 mb-3">
                    <span className={`px-2.5 py-1 rounded-md text-xs font-medium ring-1 ${status.bg} ${status.color} ${status.border}`}>
                      <status.icon className="inline h-3 w-3 mr-1" />
                      {status.label}
                    </span>
                    <span className="text-cyber-gray-500 text-sm">{patch.vulnerability_cve}</span>
                    <span className="text-cyber-gray-600 text-sm">•</span>
                    <span className="text-cyber-gray-500 text-sm capitalize">{patch.patch_type}</span>
                  </div>

                  {/* Title and Description */}
                  <h3 className="text-lg font-semibold text-white mb-2">{patch.title}</h3>
                  <p className="text-cyber-gray-400 text-sm mb-4">{patch.description}</p>

                  {/* Metadata */}
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <SparklesIcon className="h-4 w-4 text-cyber-blue" />
                      <span className="text-cyber-gray-500">Confidence:</span>
                      <span className="text-white font-medium">{(patch.ai_confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-cyber-gray-500">Risk:</span>
                      <span className={`font-medium ${risk.color}`}>{risk.label}</span>
                    </div>
                    <div className="flex items-center gap-2 text-cyber-gray-500">
                      <ClockIcon className="h-4 w-4" />
                      <span>Created {formatDate(patch.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Expand Indicator */}
                <motion.div animate={{ rotate: selectedPatch?.id === patch.id ? 180 : 0 }} transition={{ duration: 0.2 }}>
                  <ChevronDownIcon className="h-5 w-5 text-cyber-gray-500" />
                </motion.div>
              </div>

              {/* Expanded Details */}
              <AnimatePresence>
                {selectedPatch?.id === patch.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-6 pt-6 border-t border-cyber-gray-800/50 space-y-4"
                  >
                    {/* Patch Script */}
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                        <CodeBracketIcon className="h-4 w-4 text-cyber-blue" />
                        Patch Script
                      </h4>
                      <pre className="bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg p-4 text-xs text-cyber-gray-300 font-mono overflow-x-auto">
                        {patch.patch_script}
                      </pre>
                    </div>

                    {/* Rollback Script */}
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                        <CodeBracketIcon className="h-4 w-4 text-cyber-red" />
                        Rollback Script
                      </h4>
                      <pre className="bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg p-4 text-xs text-cyber-gray-300 font-mono overflow-x-auto">
                        {patch.rollback_script}
                      </pre>
                    </div>

                    {/* Validation Tests */}
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-2">Validation Tests</h4>
                      <div className="flex flex-wrap gap-2">
                        {patch.validation_tests.map((test, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-cyber-green/10 border border-cyber-green/30 rounded-md text-xs text-cyber-green font-mono"
                          >
                            ✓ {test}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                      {patch.status === 'pending_approval' && (
                        <>
                          <button className="btn-cyber px-4 py-2 text-sm">Approve Patch</button>
                          <button className="glass-card px-4 py-2 text-sm text-white border border-cyber-red/50 hover:border-cyber-red rounded-lg transition-all">
                            Reject
                          </button>
                        </>
                      )}
                      {patch.status === 'approved' && (
                        <button className="btn-cyber px-4 py-2 text-sm">Deploy Patch</button>
                      )}
                      <button className="glass-card px-4 py-2 text-sm text-white border border-cyber-gray-800 hover:border-cyber-blue/50 rounded-lg transition-all">
                        View Vulnerability
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
