import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Wifi,
  Radio,
  Cloud,
  Network,
  Thermometer,
  Settings
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Devices', href: '/devices', icon: Wifi },
  { name: 'Commissioning', href: '/commissioning', icon: Radio },
  { name: 'Topology', href: '/topology', icon: Network },
  { name: 'Border Routers', href: '/routers', icon: Settings },
  { name: 'Sensors', href: '/sensors', icon: Thermometer },
  { name: 'Cloud', href: '/cloud', icon: Cloud },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center h-16 px-6 border-b border-gray-200">
            <Network className="w-8 h-8 text-primary-600" />
            <span className="ml-3 text-xl font-bold text-gray-900">
              OT-BRM
            </span>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== '/' && location.pathname.startsWith(item.href))

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors
                    ${isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                    }
                  `}
                >
                  <item.icon className={`w-5 h-5 mr-3 ${isActive ? 'text-primary-600' : 'text-gray-400'}`} />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500">
              <div>Version 1.0.0</div>
              <div className="mt-1">OpenThread Border Router Manager</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <div className="min-h-screen">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
