import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import {
  Wifi,
  WifiOff,
  Radio,
  Cloud,
  AlertCircle,
  TrendingUp,
  Activity
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

const COLORS = ['#0ea5e9', '#f59e0b', '#ef4444', '#8b5cf6']

export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['device-statistics'],
    queryFn: async () => {
      const res = await apiClient.getDeviceStatistics()
      return res.data
    },
    refetchInterval: 5000,
  })

  const { data: cloudStatus } = useQuery({
    queryKey: ['cloud-status'],
    queryFn: async () => {
      const res = await apiClient.getCloudStatus()
      return res.data
    },
    refetchInterval: 10000,
  })

  const { data: routers } = useQuery({
    queryKey: ['routers'],
    queryFn: async () => {
      const res = await apiClient.getRouters()
      return res.data
    },
  })

  // Mock data for charts - in production, get from API
  const networkActivityData = [
    { time: '00:00', messages: 120 },
    { time: '04:00', messages: 80 },
    { time: '08:00', messages: 200 },
    { time: '12:00', messages: 350 },
    { time: '16:00', messages: 420 },
    { time: '20:00', messages: 280 },
  ]

  const deviceTypeData = stats?.device_types ? Object.entries(stats.device_types).map(([name, value]) => ({
    name: name.toUpperCase(),
    value
  })) : []

  const statCards = [
    {
      name: 'Total Devices',
      value: stats?.total_devices || 0,
      icon: Wifi,
      color: 'bg-blue-500',
      change: '+12%',
    },
    {
      name: 'Online Devices',
      value: stats?.online || 0,
      icon: Activity,
      color: 'bg-green-500',
      change: '+5%',
    },
    {
      name: 'Offline Devices',
      value: stats?.offline || 0,
      icon: WifiOff,
      color: 'bg-red-500',
      change: '-2%',
    },
    {
      name: 'Border Routers',
      value: routers?.length || 0,
      icon: Radio,
      color: 'bg-purple-500',
      change: 'Stable',
    },
  ]

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of your OpenThread Border Router network
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 mb-8 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{stat.value}</p>
                <p className="mt-2 text-sm text-green-600">{stat.change}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-2">
        {/* Network Activity */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Network Activity</h2>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={networkActivityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="messages"
                stroke="#0ea5e9"
                fill="#0ea5e9"
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Device Types */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Types</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={deviceTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {deviceTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cloud Status & Alerts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Cloud Connectivity Status */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Cloud Connectivity</h2>
            <Link to="/cloud" className="text-sm text-primary-600 hover:text-primary-700">
              View Details →
            </Link>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Status</span>
              <span className={`badge ${cloudStatus?.running ? 'badge-success' : 'badge-danger'}`}>
                {cloudStatus?.running ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Connections</span>
              <span className="text-sm font-medium text-gray-900">
                {cloudStatus?.connections || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Telemetry Interval</span>
              <span className="text-sm font-medium text-gray-900">
                {cloudStatus?.telemetry_interval || 60}s
              </span>
            </div>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Alerts</h2>
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Low RSSI detected on 3 devices
                </p>
                <p className="text-xs text-gray-500 mt-1">2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <TrendingUp className="w-5 h-5 text-green-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Network performance improved
                </p>
                <p className="text-xs text-gray-500 mt-1">1 hour ago</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Cloud className="w-5 h-5 text-blue-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Cloud sync completed
                </p>
                <p className="text-xs text-gray-500 mt-1">2 hours ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card p-6 mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Link to="/commissioning" className="btn btn-primary">
            Commission New Device
          </Link>
          <Link to="/devices" className="btn btn-secondary">
            View All Devices
          </Link>
          <Link to="/topology" className="btn btn-secondary">
            Network Topology
          </Link>
          <Link to="/cloud" className="btn btn-secondary">
            Cloud Settings
          </Link>
        </div>
      </div>
    </div>
  )
}
