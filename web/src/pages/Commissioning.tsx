import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Radio, CheckCircle, XCircle, Clock, Loader } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Commissioning() {
  const queryClient = useQueryClient()
  const [borderRouterId, setBorderRouterId] = useState(1)
  const [pskd, setPskd] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [deviceType, setDeviceType] = useState('sed')
  const [timeout, setTimeout] = useState(120)

  const { data: status } = useQuery({
    queryKey: ['commissioner-status'],
    queryFn: async () => {
      const res = await apiClient.getCommissionerStatus()
      return res.data
    },
    refetchInterval: 2000,
  })

  const { data: routers } = useQuery({
    queryKey: ['routers'],
    queryFn: async () => {
      const res = await apiClient.getRouters()
      return res.data
    },
  })

  const startCommissioner = useMutation({
    mutationFn: () => apiClient.startCommissioner({ border_router_id: borderRouterId }),
    onSuccess: () => {
      toast.success('Commissioner started')
      queryClient.invalidateQueries({ queryKey: ['commissioner-status'] })
    },
    onError: () => {
      toast.error('Failed to start commissioner')
    },
  })

  const stopCommissioner = useMutation({
    mutationFn: () => apiClient.stopCommissioner(),
    onSuccess: () => {
      toast.success('Commissioner stopped')
      queryClient.invalidateQueries({ queryKey: ['commissioner-status'] })
    },
    onError: () => {
      toast.error('Failed to stop commissioner')
    },
  })

  const commissionDevice = useMutation({
    mutationFn: async () => {
      return apiClient.commissionDevice({
        border_router_id: borderRouterId,
        pskd,
        device_name: deviceName || undefined,
        device_type: deviceType,
        timeout,
      })
    },
    onSuccess: (res) => {
      toast.success('Device commissioned successfully!')
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      queryClient.invalidateQueries({ queryKey: ['device-statistics'] })
      // Reset form
      setPskd('')
      setDeviceName('')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to commission device'
      toast.error(message)
    },
  })

  const activeSessions = status?.active_sessions || []

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Device Commissioning</h1>
        <p className="mt-2 text-gray-600">
          Commission new devices to join your Thread network
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Commissioning Form */}
        <div className="lg:col-span-2">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Commission New Device</h2>
              {status?.active ? (
                <span className="badge badge-success">Commissioner Active</span>
              ) : (
                <span className="badge badge-danger">Commissioner Inactive</span>
              )}
            </div>

            {!status?.active && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <div className="flex">
                  <Radio className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">
                      Commissioner Not Active
                    </h3>
                    <p className="mt-1 text-sm text-yellow-700">
                      You need to start the commissioner before commissioning devices.
                    </p>
                    <button
                      onClick={() => startCommissioner.mutate()}
                      disabled={startCommissioner.isPending}
                      className="mt-3 btn btn-primary text-sm"
                    >
                      {startCommissioner.isPending ? 'Starting...' : 'Start Commissioner'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (!status?.active) {
                  toast.error('Please start the commissioner first')
                  return
                }
                commissionDevice.mutate()
              }}
              className="space-y-4"
            >
              {/* Border Router Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Border Router
                </label>
                <select
                  value={borderRouterId}
                  onChange={(e) => setBorderRouterId(Number(e.target.value))}
                  className="input"
                  required
                >
                  {routers?.map((router: any) => (
                    <option key={router.id} value={router.id}>
                      {router.name} ({router.ip_address})
                    </option>
                  ))}
                </select>
              </div>

              {/* PSKd */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PSKd (Pre-Shared Key for Device) *
                </label>
                <input
                  type="text"
                  value={pskd}
                  onChange={(e) => setPskd(e.target.value)}
                  placeholder="J01NME"
                  className="input font-mono"
                  required
                  maxLength={32}
                />
                <p className="mt-1 text-xs text-gray-500">
                  The device's commissioning credential (6-32 characters)
                </p>
              </div>

              {/* Device Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device Name (Optional)
                </label>
                <input
                  type="text"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder="Temperature Sensor"
                  className="input"
                />
              </div>

              {/* Device Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device Type
                </label>
                <select
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value)}
                  className="input"
                >
                  <option value="sed">SED (Sleepy End Device)</option>
                  <option value="med">MED (Minimal End Device)</option>
                  <option value="fed">FED (Full End Device)</option>
                  <option value="reed">REED (Router Eligible End Device)</option>
                  <option value="router">Router</option>
                </select>
              </div>

              {/* Timeout */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  value={timeout}
                  onChange={(e) => setTimeout(Number(e.target.value))}
                  min={30}
                  max={300}
                  className="input"
                />
                <p className="mt-1 text-xs text-gray-500">
                  How long to wait for the device to join (30-300 seconds)
                </p>
              </div>

              {/* Submit Button */}
              <div className="flex space-x-3 pt-4">
                <button
                  type="submit"
                  disabled={!status?.active || commissionDevice.isPending}
                  className="btn btn-primary flex-1"
                >
                  {commissionDevice.isPending ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      Commissioning... ({timeout}s timeout)
                    </>
                  ) : (
                    <>
                      <Radio className="w-4 h-4 mr-2" />
                      Commission Device
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Instructions */}
          <div className="card p-6 mt-6">
            <h3 className="font-semibold text-gray-900 mb-3">How to Commission a Device</h3>
            <ol className="space-y-2 text-sm text-gray-600 list-decimal list-inside">
              <li>Ensure the commissioner is active (green badge above)</li>
              <li>Put your Thread device into commissioning mode</li>
              <li>Enter the device's PSKd (found in device documentation or label)</li>
              <li>Optionally provide a friendly name</li>
              <li>Click "Commission Device" and wait for the device to join</li>
              <li>The device will appear in the devices list when successfully joined</li>
            </ol>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Active Sessions */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Active Sessions
            </h2>
            {activeSessions.length === 0 ? (
              <p className="text-sm text-gray-500">No active commissioning sessions</p>
            ) : (
              <div className="space-y-3">
                {activeSessions.map((session: any) => (
                  <div key={session.session_id} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-900">
                        {session.eui64}
                      </span>
                      <Clock className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="text-xs text-gray-500">
                      {session.remaining_seconds}s remaining
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Commissioner Control */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Commissioner Control
            </h2>
            <div className="space-y-3">
              {status?.active ? (
                <button
                  onClick={() => stopCommissioner.mutate()}
                  disabled={stopCommissioner.isPending}
                  className="w-full btn btn-danger"
                >
                  Stop Commissioner
                </button>
              ) : (
                <button
                  onClick={() => startCommissioner.mutate()}
                  disabled={startCommissioner.isPending}
                  className="w-full btn btn-primary"
                >
                  Start Commissioner
                </button>
              )}
            </div>
          </div>

          {/* Recent Joins */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Recently Commissioned
            </h2>
            <div className="space-y-3">
              <div className="flex items-center space-x-3 text-sm">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-gray-900">Temp Sensor #1</span>
                <span className="text-gray-500 text-xs ml-auto">5m ago</span>
              </div>
              <div className="flex items-center space-x-3 text-sm">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-gray-900">Motion Detector</span>
                <span className="text-gray-500 text-xs ml-auto">12m ago</span>
              </div>
              <div className="flex items-center space-x-3 text-sm">
                <XCircle className="w-4 h-4 text-red-500" />
                <span className="text-gray-900">Unknown Device</span>
                <span className="text-gray-500 text-xs ml-auto">1h ago</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
