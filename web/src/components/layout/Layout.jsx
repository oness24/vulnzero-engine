import { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheckIcon,
  BugAntIcon,
  WrenchScrewdriverIcon,
  RocketLaunchIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  BellIcon,
  UserCircleIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/', icon: ChartBarIcon },
  { name: 'Vulnerabilities', href: '/vulnerabilities', icon: BugAntIcon },
  { name: 'Patches', href: '/patches', icon: WrenchScrewdriverIcon },
  { name: 'Deployments', href: '/deployments', icon: RocketLaunchIcon },
  { name: 'Monitoring', href: '/monitoring', icon: ShieldCheckIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifications, setNotifications] = useState(3)
  const location = useLocation()

  return (
    <div className="flex h-screen bg-cyber-darker">
      {/* Mobile sidebar backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar for desktop and mobile */}
      <AnimatePresence>
        <motion.aside
          initial={{ x: -300 }}
          animate={{ x: sidebarOpen ? 0 : -300 }}
          className="fixed inset-y-0 left-0 z-50 w-64 glass-card border-r border-cyber-blue/20 lg:translate-x-0 lg:static lg:z-0"
        >
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-6 border-b border-cyber-blue/20">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <ShieldCheckIcon className="h-8 w-8 text-cyber-blue animate-glow" />
                <div className="absolute inset-0 bg-cyber-blue/20 blur-xl" />
              </div>
              <span className="text-xl font-heading font-bold text-white">
                Vuln<span className="text-cyber-blue">Zero</span>
              </span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-cyber-gray-400 hover:text-white"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={({ isActive }) =>
                    `group flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-gradient-to-r from-cyber-blue/20 to-cyber-purple/20 text-white border border-cyber-blue/30 shadow-lg shadow-cyber-blue/20'
                        : 'text-cyber-gray-400 hover:text-white hover:bg-cyber-gray-800/50'
                    }`
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      isActive ? 'text-cyber-blue' : 'text-cyber-gray-500 group-hover:text-cyber-blue'
                    }`}
                  />
                  {item.name}
                  {isActive && (
                    <motion.div
                      layoutId="activeIndicator"
                      className="ml-auto h-2 w-2 rounded-full bg-cyber-blue shadow-glow-sm"
                      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    />
                  )}
                </NavLink>
              )
            })}
          </nav>

          {/* System Status */}
          <div className="p-4 border-t border-cyber-blue/20">
            <div className="glass-card p-3 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-cyber-gray-400">System Status</span>
                <div className="flex items-center space-x-1">
                  <div className="h-2 w-2 rounded-full bg-cyber-green animate-pulse" />
                  <span className="text-xs text-cyber-green">Healthy</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-cyber-gray-500">API</span>
                  <span className="text-cyber-green">42ms</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-cyber-gray-500">Workers</span>
                  <span className="text-cyber-green">4/4</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-cyber-gray-500">Queue</span>
                  <span className="text-cyber-blue">12 jobs</span>
                </div>
              </div>
            </div>
          </div>
        </motion.aside>
      </AnimatePresence>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header */}
        <header className="glass-card border-b border-cyber-blue/20 z-10">
          <div className="flex h-16 items-center justify-between px-4 sm:px-6">
            {/* Mobile menu button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden text-cyber-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue rounded-lg p-2"
            >
              <Bars3Icon className="h-6 w-6" />
            </button>

            {/* Search bar */}
            <div className="flex-1 max-w-2xl mx-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search vulnerabilities, patches, deployments..."
                  className="w-full bg-cyber-gray-900/50 border border-cyber-gray-800 rounded-lg px-4 py-2 pl-10 text-sm text-white placeholder-cyber-gray-500 focus:outline-none focus:ring-2 focus:ring-cyber-blue focus:border-transparent transition-all"
                />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg
                    className="h-5 w-5 text-cyber-gray-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </div>
              </div>
            </div>

            {/* Right section */}
            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <button className="relative p-2 text-cyber-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyber-blue rounded-lg transition-colors">
                <BellIcon className="h-6 w-6" />
                {notifications > 0 && (
                  <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-cyber-red text-xs text-white flex items-center justify-center animate-pulse">
                    {notifications}
                  </span>
                )}
              </button>

              {/* User menu */}
              <button className="flex items-center space-x-2 p-2 rounded-lg hover:bg-cyber-gray-800/50 transition-colors focus:outline-none focus:ring-2 focus:ring-cyber-blue">
                <UserCircleIcon className="h-8 w-8 text-cyber-blue" />
                <span className="hidden sm:block text-sm font-medium text-white">Admin</span>
              </button>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto bg-cyber-darker">
          <div className="container mx-auto px-4 sm:px-6 py-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  )
}
