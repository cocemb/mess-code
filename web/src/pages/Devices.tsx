import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiClient } from '@/lib/api'
import { Search, Filter, Wifi, WifiOff, Clock, Signal } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Devices() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(0)
  const limit = 50

  const { data, isLoading } = useQuery({
    queryKey: ['devices', page, limit, statusFilter],
    queryFn: async () => {
      const res = await apiClient.getDevices({
        offset: page * limit,
        limit,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      return res.data
    },
    refetchInterval: 5000,
  })

  const devices = data?.devices || []
  const total = data?.total || 0

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'badge-success'
      case 'offline': return 'badge-danger'
      case 'sleeping': return 'badge-warning'
      default: return 'badge-info'
    }
  }

  const getSignalStrength = (rssi?: number) => {
    if (!rssi) return 'Unknown'
    if (rssi > -50) return 'Excellent'
    if (rssi > -60) return 'Good'
    if (rssi > -70) return 'Fair'
    return 'Poor'
  }

  const filteredDevices = devices.filter((device: any) =>
    device.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    device.eui64?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Devices</h1>
          <p className="mt-2 text-gray-600">
            Manage and monitor your Thread network devices
          </p>
        </div>
        <Link to="/commissioning" className="btn btn-primary">
          + Commission Device
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-6 mb-6">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name or EUI64..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input pl-10"
            >
              <option value="all">All Status</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
              <option value="sleeping">Sleeping</option>
            </select>
          </div>
        </div>
      </div>

      {/* Device Count */}
      <div className="mb-4 text-sm text-gray-600">
        Showing {filteredDevices.length} of {total} devices
      </div>

      {/* Devices Grid */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading devices...</p>
        </div>
      ) : filteredDevices.length === 0 ? (
        <div className="card p-12 text-center">
          <Wifi className="w-16 h-16 text-gray-300 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No devices found</h3>
          <p className="mt-2 text-gray-600">
            {searchQuery ? 'Try adjusting your search' : 'Start by commissioning your first device'}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredDevices.map((device: any) => (
              <Link
                key={device.id}
                to={`/devices/${device.id}`}
                className="card p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    {device.status === 'online' ? (
                      <Wifi className="w-8 h-8 text-green-500" />
                    ) : (
                      <WifiOff className="w-8 h-8 text-gray-400" />
                    )}
                    <div>
                      <h3 className="font-semibold text-gray-900">{device.name}</h3>
                      <p className="text-xs text-gray-500">{device.device_type?.toUpperCase()}</p>
                    </div>
                  </div>
                  <span className={`badge ${getStatusColor(device.status)}`}>
                    {device.status}
                  </span>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">EUI64</span>
                    <span className="font-mono text-gray-900">
                      {device.eui64?.slice(-8)}
                    </span>
                  </div>

                  {device.rssi && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Signal</span>
                      <div className="flex items-center space-x-2">
                        <Signal className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-900">
                          {device.rssi} dBm ({getSignalStrength(device.rssi)})
                        </span>
                      </div>
                    </div>
                  )}

                  {device.link_quality !== null && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Link Quality</span>
                      <span className="text-gray-900">{device.link_quality}/3</span>
                    </div>
                  )}

                  {device.last_seen && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Last Seen</span>
                      <div className="flex items-center space-x-1">
                        <Clock className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-900">
                          {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between mt-6">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="btn btn-secondary"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {page + 1} of {Math.ceil(total / limit)}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={(page + 1) * limit >= total}
                className="btn btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
