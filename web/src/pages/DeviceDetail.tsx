import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import {
  ArrowLeft,
  Wifi,
  Signal,
  Battery,
  Thermometer,
  Lightbulb,
  Power,
  RefreshCw
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'

export default function DeviceDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [actuatorStates, setActuatorStates] = useState<Record<string, boolean>>({})

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', id],
    queryFn: async () => {
      const res = await apiClient.getDevice(Number(id))
      return res.data
    },
    refetchInterval: 5000,
  })

  const { data: sensors } = useQuery({
    queryKey: ['sensors', device?.id],
    queryFn: async () => {
      const res = await apiClient.getSensors({ device_id: device.id })
      return res.data
    },
    enabled: !!device,
  })

  const controlActuator = useMutation({
    mutationFn: async ({ path, state }: { path: string; state: boolean }) => {
      // This would actually send CoAP command via cloud
      await apiClient.publishTelemetry({
        device_id: device.eui64,
        data: {
          command: 'control_actuator',
          actuator_path: path,
          state
        }
      })
    },
    onSuccess: () => {
      toast.success('Command sent successfully')
    },
    onError: () => {
      toast.error('Failed to send command')
    }
  })

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
      </div>
    )
  }

  if (!device) {
    return (
      <div className="p-8">
        <div className="card p-12 text-center">
          <h3 className="text-lg font-medium text-gray-900">Device not found</h3>
        </div>
      </div>
    )
  }

  // Mock sensor data for chart
  const sensorData = [
    { time: '00:00', temperature: 22.5, humidity: 45 },
    { time: '04:00', temperature: 21.8, humidity: 48 },
    { time: '08:00', temperature: 23.2, humidity: 44 },
    { time: '12:00', temperature: 24.5, humidity: 42 },
    { time: '16:00', temperature: 25.1, humidity: 40 },
    { time: '20:00', temperature: 23.8, humidity: 43 },
  ]

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <Link to="/devices" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Devices
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Wifi className="w-12 h-12 text-primary-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{device.name}</h1>
              <p className="text-gray-600">{device.eui64}</p>
            </div>
          </div>
          <span className={`badge ${device.status === 'online' ? 'badge-success' : 'badge-danger'}`}>
            {device.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Device Info Card */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Information</h2>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-gray-600">Device Type</dt>
                <dd className="mt-1 text-sm font-medium text-gray-900">
                  {device.device_type?.toUpperCase()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-600">RLOC16</dt>
                <dd className="mt-1 text-sm font-mono font-medium text-gray-900">
                  {device.rloc16 || 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-600">RSSI</dt>
                <dd className="mt-1 text-sm font-medium text-gray-900 flex items-center">
                  <Signal className="w-4 h-4 mr-2 text-gray-400" />
                  {device.rssi ? `${device.rssi} dBm` : 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-600">Link Quality</dt>
                <dd className="mt-1 text-sm font-medium text-gray-900">
                  {device.link_quality !== null ? `${device.link_quality}/3` : 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-600">Firmware Version</dt>
                <dd className="mt-1 text-sm font-medium text-gray-900">
                  {device.firmware_version || 'Unknown'}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-600">Last Seen</dt>
                <dd className="mt-1 text-sm font-medium text-gray-900">
                  {device.last_seen
                    ? formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })
                    : 'Never'}
                </dd>
              </div>
            </dl>
          </div>

          {/* Sensor Data Chart */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Sensor Data</h2>
              <button className="btn btn-secondary text-sm">
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </button>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sensorData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="temperature"
                  stroke="#ef4444"
                  name="Temperature (°C)"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="humidity"
                  stroke="#3b82f6"
                  name="Humidity (%)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Sensors List */}
          {sensors && sensors.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Sensors</h2>
              <div className="space-y-3">
                {sensors.map((sensor: any) => (
                  <div key={sensor.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Thermometer className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{sensor.name}</p>
                        <p className="text-xs text-gray-500">{sensor.sensor_type}</p>
                      </div>
                    </div>
                    <Link
                      to={`/sensors/${sensor.id}`}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      View Details →
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar - Controls */}
        <div className="space-y-6">
          {/* Control Panel */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Control</h2>
            <div className="space-y-4">
              {/* LED Control */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Lightbulb className="w-5 h-5 text-yellow-500" />
                    <span className="font-medium text-gray-900">LED</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={actuatorStates['/led'] || false}
                      onChange={(e) => {
                        setActuatorStates({ ...actuatorStates, '/led': e.target.checked })
                        controlActuator.mutate({ path: '/led', state: e.target.checked })
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
                <p className="text-xs text-gray-500">Toggle device LED on/off</p>
              </div>

              {/* Relay Control */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Power className="w-5 h-5 text-blue-500" />
                    <span className="font-medium text-gray-900">Relay</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={actuatorStates['/relay'] || false}
                      onChange={(e) => {
                        setActuatorStates({ ...actuatorStates, '/relay': e.target.checked })
                        controlActuator.mutate({ path: '/relay', state: e.target.checked })
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
                <p className="text-xs text-gray-500">Control connected relay</p>
              </div>

              {/* Read Sensor Button */}
              <button
                className="w-full btn btn-primary"
                onClick={() => {
                  toast.promise(
                    apiClient.publishTelemetry({
                      device_id: device.eui64,
                      data: { command: 'read_sensor', sensor_path: '/temperature' }
                    }),
                    {
                      loading: 'Reading sensor...',
                      success: 'Sensor read command sent',
                      error: 'Failed to read sensor',
                    }
                  )
                }}
              >
                <Thermometer className="w-4 h-4 mr-2" />
                Read All Sensors
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Stats</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium text-gray-900">24h 15m</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Messages Sent</span>
                <span className="text-sm font-medium text-gray-900">1,234</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Battery</span>
                <div className="flex items-center space-x-2">
                  <Battery className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-medium text-gray-900">85%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="space-y-2">
              <button className="w-full btn btn-secondary text-sm">
                Update Firmware
              </button>
              <button className="w-full btn btn-secondary text-sm">
                Reset Device
              </button>
              <button className="w-full btn btn-danger text-sm">
                Remove from Network
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
