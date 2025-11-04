import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Thermometer, Droplets, Activity, Wind, Battery, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatDistanceToNow } from 'date-fns'

export default function Sensors() {
  const [selectedSensor, setSelectedSensor] = useState<number | null>(null)

  const { data: sensors, isLoading } = useQuery({
    queryKey: ['sensors'],
    queryFn: async () => {
      const res = await apiClient.getSensors()
      return res.data
    },
    refetchInterval: 5000,
  })

  const { data: readings } = useQuery({
    queryKey: ['sensor-readings', selectedSensor],
    queryFn: async () => {
      if (!selectedSensor) return null
      const res = await apiClient.getSensorReadings(selectedSensor, { limit: 100 })
      return res.data
    },
    enabled: !!selectedSensor,
    refetchInterval: 3000,
  })

  const getSensorIcon = (type: string) => {
    switch (type) {
      case 'temperature':
        return <Thermometer className="w-6 h-6" />
      case 'humidity':
        return <Droplets className="w-6 h-6" />
      case 'pressure':
        return <Activity className="w-6 h-6" />
      case 'motion':
        return <Wind className="w-6 h-6" />
      case 'battery':
        return <Battery className="w-6 h-6" />
      case 'power':
        return <Zap className="w-6 h-6" />
      default:
        return <Activity className="w-6 h-6" />
    }
  }

  const getSensorColor = (type: string) => {
    switch (type) {
      case 'temperature':
        return 'text-red-600 bg-red-100'
      case 'humidity':
        return 'text-blue-600 bg-blue-100'
      case 'pressure':
        return 'text-purple-600 bg-purple-100'
      case 'motion':
        return 'text-green-600 bg-green-100'
      case 'battery':
        return 'text-yellow-600 bg-yellow-100'
      case 'power':
        return 'text-orange-600 bg-orange-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const formatValue = (value: number, unit: string) => {
    return `${value.toFixed(2)} ${unit}`
  }

  const prepareChartData = () => {
    if (!readings) return []
    return readings.map((reading: any) => ({
      timestamp: new Date(reading.timestamp).toLocaleTimeString(),
      value: reading.value,
    }))
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Sensors</h1>
        <p className="mt-2 text-gray-600">
          Monitor environmental sensors across your Thread network
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Sensor List */}
        <div className="lg:col-span-1">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Active Sensors
            </h2>

            {isLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              </div>
            ) : sensors && sensors.length > 0 ? (
              <div className="space-y-3">
                {sensors.map((sensor: any) => (
                  <button
                    key={sensor.id}
                    onClick={() => setSelectedSensor(sensor.id)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-colors ${
                      selectedSensor === sensor.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`p-2 rounded-lg ${getSensorColor(sensor.sensor_type)}`}>
                        {getSensorIcon(sensor.sensor_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <p className="font-semibold text-gray-900 truncate">
                            {sensor.name}
                          </p>
                          <span className={`badge ${sensor.is_active ? 'badge-success' : 'badge-danger'}`}>
                            {sensor.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 capitalize mb-2">
                          {sensor.sensor_type}
                        </p>
                        {sensor.last_value !== null && (
                          <p className="text-sm font-medium text-gray-900">
                            {formatValue(sensor.last_value, sensor.unit)}
                          </p>
                        )}
                        {sensor.last_reading_time && (
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDistanceToNow(new Date(sensor.last_reading_time), {
                              addSuffix: true,
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">No sensors found</p>
              </div>
            )}
          </div>
        </div>

        {/* Sensor Details */}
        <div className="lg:col-span-2">
          {selectedSensor ? (
            <>
              {/* Current Reading */}
              <div className="card p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Current Reading
                </h2>
                {sensors && sensors.find((s: any) => s.id === selectedSensor) && (
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                    {(() => {
                      const sensor = sensors.find((s: any) => s.id === selectedSensor)
                      return (
                        <>
                          <div className="text-center p-4 bg-gray-50 rounded-lg">
                            <div className={`inline-flex p-3 rounded-lg mb-2 ${getSensorColor(sensor.sensor_type)}`}>
                              {getSensorIcon(sensor.sensor_type)}
                            </div>
                            <p className="text-2xl font-bold text-gray-900">
                              {sensor.last_value?.toFixed(2) || 'N/A'}
                            </p>
                            <p className="text-sm text-gray-600">{sensor.unit}</p>
                          </div>
                          <div className="p-4 bg-gray-50 rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Device</p>
                            <p className="font-medium text-gray-900">{sensor.device?.name || 'Unknown'}</p>
                          </div>
                          <div className="p-4 bg-gray-50 rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Last Update</p>
                            <p className="font-medium text-gray-900 text-sm">
                              {sensor.last_reading_time
                                ? formatDistanceToNow(new Date(sensor.last_reading_time), {
                                    addSuffix: true,
                                  })
                                : 'Never'}
                            </p>
                          </div>
                        </>
                      )
                    })()}
                  </div>
                )}
              </div>

              {/* Historical Data Chart */}
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Historical Data
                </h2>
                {readings && readings.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={prepareChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="timestamp"
                        tick={{ fontSize: 12 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#2563eb"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        name={
                          sensors?.find((s: any) => s.id === selectedSensor)?.unit || 'Value'
                        }
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-12">
                    <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">No historical data available</p>
                  </div>
                )}
              </div>

              {/* Statistics */}
              {readings && readings.length > 0 && (
                <div className="card p-6 mt-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Statistics
                  </h2>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    {(() => {
                      const values = readings.map((r: any) => r.value)
                      const min = Math.min(...values)
                      const max = Math.max(...values)
                      const avg = values.reduce((a: number, b: number) => a + b, 0) / values.length
                      const unit = sensors?.find((s: any) => s.id === selectedSensor)?.unit || ''

                      return (
                        <>
                          <div className="text-center p-4 bg-blue-50 rounded-lg">
                            <p className="text-xs text-blue-600 mb-1">Minimum</p>
                            <p className="text-lg font-bold text-blue-900">
                              {min.toFixed(2)} {unit}
                            </p>
                          </div>
                          <div className="text-center p-4 bg-green-50 rounded-lg">
                            <p className="text-xs text-green-600 mb-1">Average</p>
                            <p className="text-lg font-bold text-green-900">
                              {avg.toFixed(2)} {unit}
                            </p>
                          </div>
                          <div className="text-center p-4 bg-red-50 rounded-lg">
                            <p className="text-xs text-red-600 mb-1">Maximum</p>
                            <p className="text-lg font-bold text-red-900">
                              {max.toFixed(2)} {unit}
                            </p>
                          </div>
                          <div className="text-center p-4 bg-purple-50 rounded-lg">
                            <p className="text-xs text-purple-600 mb-1">Readings</p>
                            <p className="text-lg font-bold text-purple-900">{readings.length}</p>
                          </div>
                        </>
                      )
                    })()}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="card p-12 text-center">
              <Activity className="w-16 h-16 text-gray-300 mx-auto" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                No sensor selected
              </h3>
              <p className="mt-2 text-gray-600">
                Select a sensor from the list to view its readings and history
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
