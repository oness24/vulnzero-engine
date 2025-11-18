import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  BellIcon,
  ShieldCheckIcon,
  CogIcon,
  KeyIcon,
  UserGroupIcon,
  ServerIcon,
} from '@heroicons/react/24/outline'

export default function Settings() {
  const [activeTab, setActiveTab] = useState('general')
  const [notifications, setNotifications] = useState({
    email: true,
    slack: true,
    webhook: false,
    critical_only: false,
  })

  const tabs = [
    { id: 'general', name: 'General', icon: CogIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'api', name: 'API Keys', icon: KeyIcon },
    { id: 'team', name: 'Team', icon: UserGroupIcon },
    { id: 'integrations', name: 'Integrations', icon: ServerIcon },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-heading font-bold text-white mb-2">Settings</h1>
        <p className="text-cyber-gray-400">Manage your VulnZero configuration and preferences</p>
      </div>

      {/* Settings Container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <nav className="glass-card rounded-xl border border-cyber-blue/20 p-2">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all mb-1 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-cyber-blue/20 to-cyber-purple/20 text-white border border-cyber-blue/30'
                      : 'text-cyber-gray-400 hover:text-white hover:bg-cyber-gray-800/50'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{tab.name}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Content Area */}
        <div className="lg:col-span-3">
          <div className="glass-card p-6 rounded-xl border border-cyber-blue/20">
            {/* General Settings */}
            {activeTab === 'general' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-white mb-4">General Settings</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-cyber-gray-300 mb-2">Organization Name</label>
                      <input
                        type="text"
                        defaultValue="Acme Corporation"
                        className="w-full bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-cyber-gray-300 mb-2">Time Zone</label>
                      <select className="w-full bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue">
                        <option>UTC</option>
                        <option>America/New_York</option>
                        <option>Europe/London</option>
                        <option>Asia/Tokyo</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-cyber-gray-300 mb-2">Scan Schedule</label>
                      <select className="w-full bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue">
                        <option>Every 6 hours</option>
                        <option>Every 12 hours</option>
                        <option>Daily</option>
                        <option>Weekly</option>
                      </select>
                    </div>
                  </div>
                </div>
                <button className="btn-cyber px-6 py-2">Save Changes</button>
              </motion.div>
            )}

            {/* Security Settings */}
            {activeTab === 'security' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-white mb-4">Security Settings</h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                      <div>
                        <h4 className="text-white font-medium">Two-Factor Authentication</h4>
                        <p className="text-cyber-gray-500 text-sm">Add an extra layer of security</p>
                      </div>
                      <button className="px-4 py-2 bg-cyber-green/20 text-cyber-green rounded-lg text-sm font-medium border border-cyber-green/40">
                        Enabled
                      </button>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                      <div>
                        <h4 className="text-white font-medium">Auto-Deploy Patches</h4>
                        <p className="text-cyber-gray-500 text-sm">Automatically deploy approved patches</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-cyber-gray-800 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyber-blue rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyber-green"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                      <div>
                        <h4 className="text-white font-medium">Require Approval for Critical</h4>
                        <p className="text-cyber-gray-500 text-sm">Manual approval for critical vulnerabilities</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-cyber-gray-800 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyber-blue rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyber-green"></div>
                      </label>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Notifications Settings */}
            {activeTab === 'notifications' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-white mb-4">Notification Preferences</h2>
                  <div className="space-y-4">
                    {Object.entries(notifications).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                        <div>
                          <h4 className="text-white font-medium capitalize">{key.replace('_', ' ')}</h4>
                          <p className="text-cyber-gray-500 text-sm">Send notifications via {key}</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={value}
                            onChange={() => setNotifications({ ...notifications, [key]: !value })}
                          />
                          <div className="w-11 h-6 bg-cyber-gray-800 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyber-blue rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyber-green"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
                <button className="btn-cyber px-6 py-2">Save Preferences</button>
              </motion.div>
            )}

            {/* API Keys */}
            {activeTab === 'api' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-white mb-4">API Keys</h2>
                  <div className="space-y-4">
                    <div className="p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-white font-medium">Production API Key</h4>
                        <span className="text-cyber-green text-xs">Active</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <input
                          type="password"
                          value="sk_live_••••••••••••••••"
                          readOnly
                          className="flex-1 bg-cyber-gray-900 border border-cyber-gray-800 rounded px-3 py-2 text-cyber-gray-400 text-sm font-mono"
                        />
                        <button className="px-4 py-2 bg-cyber-blue/20 text-cyber-blue rounded text-sm font-medium hover:bg-cyber-blue/30">
                          Reveal
                        </button>
                      </div>
                    </div>
                    <button className="px-4 py-2 bg-cyber-purple/20 text-cyber-purple rounded-lg text-sm font-medium border border-cyber-purple/40 hover:bg-cyber-purple/30">
                      + Generate New Key
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Team */}
            {activeTab === 'team' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-white">Team Members</h2>
                    <button className="btn-cyber px-4 py-2 text-sm">+ Invite Member</button>
                  </div>
                  <div className="space-y-3">
                    {[
                      { name: 'John Doe', email: 'john@example.com', role: 'Admin', status: 'active' },
                      { name: 'Jane Smith', email: 'jane@example.com', role: 'Developer', status: 'active' },
                      { name: 'Bob Johnson', email: 'bob@example.com', role: 'Viewer', status: 'pending' },
                    ].map((member) => (
                      <div key={member.email} className="flex items-center justify-between p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800">
                        <div>
                          <h4 className="text-white font-medium">{member.name}</h4>
                          <p className="text-cyber-gray-500 text-sm">{member.email}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-cyber-gray-400 text-sm">{member.role}</span>
                          <span className={`px-2 py-1 rounded text-xs ${member.status === 'active' ? 'bg-cyber-green/20 text-cyber-green' : 'bg-cyber-orange/20 text-cyber-orange'}`}>
                            {member.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Integrations */}
            {activeTab === 'integrations' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-white mb-4">Integrations</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { name: 'GitHub', status: 'connected', icon: '🐙' },
                      { name: 'Slack', status: 'connected', icon: '💬' },
                      { name: 'Jira', status: 'disconnected', icon: '📋' },
                      { name: 'PagerDuty', status: 'connected', icon: '🚨' },
                      { name: 'Datadog', status: 'disconnected', icon: '📊' },
                      { name: 'Sentry', status: 'disconnected', icon: '🔍' },
                    ].map((integration) => (
                      <div key={integration.name} className="p-4 bg-cyber-gray-900/30 rounded-lg border border-cyber-gray-800 hover:border-cyber-blue/30 transition-all">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{integration.icon}</span>
                            <h4 className="text-white font-medium">{integration.name}</h4>
                          </div>
                          {integration.status === 'connected' ? (
                            <span className="px-2 py-1 bg-cyber-green/20 text-cyber-green rounded text-xs">Connected</span>
                          ) : (
                            <button className="px-3 py-1 bg-cyber-blue/20 text-cyber-blue rounded text-xs hover:bg-cyber-blue/30">
                              Connect
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
