import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Network, Router, Wifi, Activity, GitBranch } from 'lucide-react'

export default function Topology() {
  const { data: topologies } = useQuery({
    queryKey: ['topologies'],
    queryFn: async () => {
      const res = await apiClient.getTopologies()
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

  const { data: deviceStats } = useQuery({
    queryKey: ['device-statistics'],
    queryFn: async () => {
      const res = await apiClient.getDeviceStatistics()
      return res.data
    },
  })

  const getTopologyIcon = (type: string) => {
    switch (type) {
      case 'star':
        return <Network className="w-6 h-6" />
      case 'mesh':
        return <GitBranch className="w-6 h-6" />
      case 'tree':
        return <Activity className="w-6 h-6" />
      default:
        return <Router className="w-6 h-6" />
    }
  }

  const getTopologyDescription = (type: string) => {
    switch (type) {
      case 'star':
        return 'All devices connect directly to a central border router'
      case 'mesh':
        return 'Devices can connect through multiple paths, providing redundancy'
      case 'tree':
        return 'Hierarchical structure with routers acting as intermediate nodes'
      default:
        return 'Custom network topology'
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Network Topology</h1>
        <p className="mt-2 text-gray-600">
          Visualize and manage your Thread network topology
        </p>
      </div>

      {/* Network Overview */}
      <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-4">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Devices</p>
              <p className="text-2xl font-bold text-gray-900">
                {deviceStats?.total_devices || 0}
              </p>
            </div>
            <Wifi className="w-8 h-8 text-primary-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Border Routers</p>
              <p className="text-2xl font-bold text-gray-900">
                {routers?.length || 0}
              </p>
            </div>
            <Router className="w-8 h-8 text-blue-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Thread Routers</p>
              <p className="text-2xl font-bold text-gray-900">
                {deviceStats?.device_types?.router || 0}
              </p>
            </div>
            <Activity className="w-8 h-8 text-green-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">End Devices</p>
              <p className="text-2xl font-bold text-gray-900">
                {(deviceStats?.device_types?.sed || 0) +
                  (deviceStats?.device_types?.med || 0) +
                  (deviceStats?.device_types?.fed || 0)}
              </p>
            </div>
            <Wifi className="w-8 h-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Topology Configurations */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Topology Configurations
        </h2>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
          {topologies?.map((topology: any) => (
            <div key={topology.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-100 rounded-lg text-primary-600">
                    {getTopologyIcon(topology.topology_type)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{topology.name}</h3>
                    <span className="text-xs text-gray-500 uppercase">
                      {topology.topology_type}
                    </span>
                  </div>
                </div>
                {topology.is_active && (
                  <span className="badge badge-success">Active</span>
                )}
              </div>

              <p className="text-sm text-gray-600 mb-4">
                {topology.description || getTopologyDescription(topology.topology_type)}
              </p>

              {topology.config && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Max Hops</span>
                    <span className="font-medium text-gray-900">
                      {topology.config.max_hops || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Router Threshold</span>
                    <span className="font-medium text-gray-900">
                      {topology.config.router_threshold || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Devices</span>
                    <span className="font-medium text-gray-900">
                      {topology.device_count || 0}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {(!topologies || topologies.length === 0) && (
          <div className="card p-12 text-center">
            <Network className="w-16 h-16 text-gray-300 mx-auto" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              No topologies configured
            </h3>
            <p className="mt-2 text-gray-600">
              Create a topology configuration to organize your network
            </p>
          </div>
        )}
      </div>

      {/* Border Router Network View */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Border Routers
        </h2>

        <div className="space-y-4">
          {routers?.map((router: any) => (
            <div key={router.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Router className="w-8 h-8 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {router.name}
                    </h3>
                    <p className="text-sm text-gray-600">{router.ip_address}</p>
                  </div>
                </div>
                <span className={`badge ${router.status === 'online' ? 'badge-success' : 'badge-danger'}`}>
                  {router.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Network Name</p>
                  <p className="text-sm font-medium text-gray-900">
                    {router.network_name || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">PAN ID</p>
                  <p className="text-sm font-medium text-gray-900 font-mono">
                    {router.pan_id || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Channel</p>
                  <p className="text-sm font-medium text-gray-900">
                    {router.channel || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Extended PAN ID</p>
                  <p className="text-sm font-medium text-gray-900 font-mono">
                    {router.extended_pan_id?.slice(0, 8) || 'N/A'}...
                  </p>
                </div>
              </div>

              {router.device_count !== undefined && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      Connected Devices
                    </span>
                    <span className="text-sm font-semibold text-gray-900">
                      {router.device_count} devices
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}

          {(!routers || routers.length === 0) && (
            <div className="card p-12 text-center">
              <Router className="w-16 h-16 text-gray-300 mx-auto" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                No border routers configured
              </h3>
              <p className="mt-2 text-gray-600">
                Add a border router to start building your Thread network
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
