import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Cloud as CloudIcon, CheckCircle, XCircle, Activity, Upload, Download, Settings } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Cloud() {
  const queryClient = useQueryClient()
  const [selectedProvider, setSelectedProvider] = useState<string>('aws')
  const [deviceId, setDeviceId] = useState('')

  const { data: status } = useQuery({
    queryKey: ['cloud-status'],
    queryFn: async () => {
      const res = await apiClient.getCloudStatus()
      return res.data
    },
    refetchInterval: 5000,
  })

  const { data: config } = useQuery({
    queryKey: ['cloud-config'],
    queryFn: async () => {
      const res = await apiClient.getCloudConfig()
      return res.data
    },
  })

  const connectCloud = useMutation({
    mutationFn: () => apiClient.connectCloud(),
    onSuccess: () => {
      toast.success('Cloud connection initiated')
      queryClient.invalidateQueries({ queryKey: ['cloud-status'] })
    },
    onError: () => {
      toast.error('Failed to connect to cloud')
    },
  })

  const disconnectCloud = useMutation({
    mutationFn: () => apiClient.disconnectCloud(),
    onSuccess: () => {
      toast.success('Cloud disconnected')
      queryClient.invalidateQueries({ queryKey: ['cloud-status'] })
    },
    onError: () => {
      toast.error('Failed to disconnect from cloud')
    },
  })

  const publishTelemetry = useMutation({
    mutationFn: () =>
      apiClient.publishTelemetry({
        device_id: deviceId,
        provider: selectedProvider,
      }),
    onSuccess: () => {
      toast.success('Telemetry published successfully')
      setDeviceId('')
    },
    onError: () => {
      toast.error('Failed to publish telemetry')
    },
  })

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'aws':
        return '☁️'
      case 'azure':
        return '🔷'
      case 'mqtt':
        return '📡'
      default:
        return '☁️'
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Cloud Connectivity</h1>
        <p className="mt-2 text-gray-600">
          Monitor and manage cloud platform integrations
        </p>
      </div>

      {/* Connection Status Overview */}
      <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-3">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className={`p-3 rounded-lg ${status?.connected ? 'bg-green-100' : 'bg-red-100'}`}>
                {status?.connected ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <div>
                <p className="text-sm text-gray-600">Connection Status</p>
                <p className="text-lg font-semibold text-gray-900">
                  {status?.connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Upload className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Messages Sent</p>
              <p className="text-lg font-semibold text-gray-900">
                {status?.messages_sent || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Download className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Messages Received</p>
              <p className="text-lg font-semibold text-gray-900">
                {status?.messages_received || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cloud Providers */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Cloud Providers
            </h2>

            <div className="space-y-4">
              {config?.providers?.map((provider: any) => (
                <div
                  key={provider.name}
                  className="p-4 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{getProviderIcon(provider.name)}</span>
                      <div>
                        <h3 className="font-semibold text-gray-900 capitalize">
                          {provider.name}
                        </h3>
                        <p className="text-sm text-gray-600">{provider.endpoint}</p>
                      </div>
                    </div>
                    <span
                      className={`badge ${
                        provider.enabled ? 'badge-success' : 'badge-danger'
                      }`}
                    >
                      {provider.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-600">Protocol</span>
                      <p className="font-medium text-gray-900">
                        {provider.protocol || 'MQTT'}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Port</span>
                      <p className="font-medium text-gray-900">{provider.port}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">TLS</span>
                      <p className="font-medium text-gray-900">
                        {provider.use_tls ? 'Enabled' : 'Disabled'}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">QoS</span>
                      <p className="font-medium text-gray-900">
                        {provider.qos || 1}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {(!config?.providers || config.providers.length === 0) && (
              <div className="text-center py-8">
                <CloudIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">No cloud providers configured</p>
              </div>
            )}
          </div>

          {/* Telemetry Configuration */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Telemetry Settings
            </h2>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Telemetry Interval</span>
                <span className="font-medium text-gray-900">
                  {config?.telemetry_interval || 60}s
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Batch Size</span>
                <span className="font-medium text-gray-900">
                  {config?.batch_size || 10} devices
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Retry Attempts</span>
                <span className="font-medium text-gray-900">
                  {config?.retry_attempts || 3}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Queue Size</span>
                <span className="font-medium text-gray-900">
                  {status?.queue_size || 0} messages
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Connection Control */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Connection Control
            </h2>

            <div className="space-y-3">
              {status?.connected ? (
                <button
                  onClick={() => disconnectCloud.mutate()}
                  disabled={disconnectCloud.isPending}
                  className="w-full btn btn-danger"
                >
                  Disconnect from Cloud
                </button>
              ) : (
                <button
                  onClick={() => connectCloud.mutate()}
                  disabled={connectCloud.isPending}
                  className="w-full btn btn-primary"
                >
                  Connect to Cloud
                </button>
              )}

              <button className="w-full btn btn-secondary flex items-center justify-center">
                <Settings className="w-4 h-4 mr-2" />
                Configure
              </button>
            </div>
          </div>

          {/* Manual Telemetry */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Manual Telemetry
            </h2>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (deviceId) {
                  publishTelemetry.mutate()
                }
              }}
              className="space-y-3"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Provider
                </label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="input"
                >
                  <option value="aws">AWS IoT Core</option>
                  <option value="azure">Azure IoT Hub</option>
                  <option value="mqtt">Generic MQTT</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device ID
                </label>
                <input
                  type="text"
                  value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                  placeholder="Enter device ID"
                  className="input"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={!deviceId || publishTelemetry.isPending}
                className="w-full btn btn-primary"
              >
                Publish Now
              </button>
            </form>
          </div>

          {/* Recent Activity */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Recent Activity
            </h2>

            <div className="space-y-3">
              {status?.recent_messages?.slice(0, 5).map((msg: any, idx: number) => (
                <div key={idx} className="flex items-start space-x-3 text-sm">
                  <Activity className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-gray-900">{msg.topic}</p>
                    <p className="text-xs text-gray-500">{msg.timestamp}</p>
                  </div>
                </div>
              ))}

              {(!status?.recent_messages || status.recent_messages.length === 0) && (
                <p className="text-sm text-gray-500 text-center py-4">
                  No recent activity
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
