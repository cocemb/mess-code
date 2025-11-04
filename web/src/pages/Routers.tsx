import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Router, Plus, Power, RefreshCw, Settings, Activity, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Routers() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    ip_address: '',
    ssh_port: 22,
    username: 'pi',
    password: '',
  })

  const { data: routers, isLoading } = useQuery({
    queryKey: ['routers'],
    queryFn: async () => {
      const res = await apiClient.getRouters()
      return res.data
    },
    refetchInterval: 5000,
  })

  const addRouter = useMutation({
    mutationFn: (data: any) => apiClient.addRouter(data),
    onSuccess: () => {
      toast.success('Border router added successfully')
      queryClient.invalidateQueries({ queryKey: ['routers'] })
      setShowAddForm(false)
      setFormData({
        name: '',
        ip_address: '',
        ssh_port: 22,
        username: 'pi',
        password: '',
      })
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to add router'
      toast.error(message)
    },
  })

  const startRouter = useMutation({
    mutationFn: (routerId: number) => apiClient.startRouter(routerId),
    onSuccess: () => {
      toast.success('Border router started')
      queryClient.invalidateQueries({ queryKey: ['routers'] })
    },
    onError: () => {
      toast.error('Failed to start router')
    },
  })

  const stopRouter = useMutation({
    mutationFn: (routerId: number) => apiClient.stopRouter(routerId),
    onSuccess: () => {
      toast.success('Border router stopped')
      queryClient.invalidateQueries({ queryKey: ['routers'] })
    },
    onError: () => {
      toast.error('Failed to stop router')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    addRouter.mutate(formData)
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Border Routers</h1>
          <p className="mt-2 text-gray-600">
            Manage your OpenThread Border Router instances
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Router
        </button>
      </div>

      {/* Add Router Form */}
      {showAddForm && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Add New Border Router
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Router Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Living Room Router"
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  IP Address *
                </label>
                <input
                  type="text"
                  value={formData.ip_address}
                  onChange={(e) =>
                    setFormData({ ...formData, ip_address: e.target.value })
                  }
                  placeholder="192.168.1.100"
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SSH Port
                </label>
                <input
                  type="number"
                  value={formData.ssh_port}
                  onChange={(e) =>
                    setFormData({ ...formData, ssh_port: Number(e.target.value) })
                  }
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) =>
                    setFormData({ ...formData, username: e.target.value })
                  }
                  className="input"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password *
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  placeholder="SSH password"
                  className="input"
                  required
                />
              </div>
            </div>

            <div className="flex space-x-3">
              <button type="submit" disabled={addRouter.isPending} className="btn btn-primary">
                Add Router
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Routers List */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading routers...</p>
        </div>
      ) : routers && routers.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {routers.map((router: any) => (
            <div key={router.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <div
                    className={`p-3 rounded-lg ${
                      router.status === 'online'
                        ? 'bg-green-100'
                        : router.status === 'error'
                        ? 'bg-red-100'
                        : 'bg-gray-100'
                    }`}
                  >
                    <Router
                      className={`w-8 h-8 ${
                        router.status === 'online'
                          ? 'text-green-600'
                          : router.status === 'error'
                          ? 'text-red-600'
                          : 'text-gray-400'
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{router.name}</h3>
                    <p className="text-sm text-gray-600">{router.ip_address}</p>
                  </div>
                </div>
                <span
                  className={`badge ${
                    router.status === 'online'
                      ? 'badge-success'
                      : router.status === 'offline'
                      ? 'badge-danger'
                      : 'badge-warning'
                  }`}
                >
                  {router.status}
                </span>
              </div>

              {/* Network Information */}
              <div className="space-y-3 mb-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600">Network Name</span>
                    <p className="font-medium text-gray-900">
                      {router.network_name || 'Not set'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Channel</span>
                    <p className="font-medium text-gray-900">
                      {router.channel || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">PAN ID</span>
                    <p className="font-medium text-gray-900 font-mono">
                      {router.pan_id || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Extended PAN ID</span>
                    <p className="font-medium text-gray-900 font-mono text-xs">
                      {router.extended_pan_id?.slice(0, 12) || 'N/A'}
                    </p>
                  </div>
                </div>

                {router.device_count !== undefined && (
                  <div className="pt-3 border-t border-gray-200">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Connected Devices</span>
                      <span className="font-semibold text-gray-900">
                        {router.device_count}
                      </span>
                    </div>
                  </div>
                )}

                {router.last_error && (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <div className="flex items-start space-x-2">
                      <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-800">Error</p>
                        <p className="text-xs text-red-700 mt-1">{router.last_error}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex space-x-2 pt-4 border-t border-gray-200">
                {router.status === 'online' ? (
                  <button
                    onClick={() => stopRouter.mutate(router.id)}
                    disabled={stopRouter.isPending}
                    className="btn btn-danger flex-1 flex items-center justify-center"
                  >
                    <Power className="w-4 h-4 mr-2" />
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={() => startRouter.mutate(router.id)}
                    disabled={startRouter.isPending}
                    className="btn btn-primary flex-1 flex items-center justify-center"
                  >
                    <Power className="w-4 h-4 mr-2" />
                    Start
                  </button>
                )}

                <button className="btn btn-secondary flex items-center justify-center">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </button>

                <button className="btn btn-secondary flex items-center justify-center">
                  <Settings className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <Router className="w-16 h-16 text-gray-300 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            No border routers configured
          </h3>
          <p className="mt-2 text-gray-600">
            Add your first border router to start managing your Thread network
          </p>
          <button
            onClick={() => setShowAddForm(true)}
            className="btn btn-primary mt-4"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Your First Router
          </button>
        </div>
      )}
    </div>
  )
}
