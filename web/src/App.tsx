import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Devices from './pages/Devices'
import DeviceDetail from './pages/DeviceDetail'
import Commissioning from './pages/Commissioning'
import Topology from './pages/Topology'
import Cloud from './pages/Cloud'
import Routers from './pages/Routers'
import Sensors from './pages/Sensors'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="devices" element={<Devices />} />
        <Route path="devices/:id" element={<DeviceDetail />} />
        <Route path="commissioning" element={<Commissioning />} />
        <Route path="topology" element={<Topology />} />
        <Route path="cloud" element={<Cloud />} />
        <Route path="routers" element={<Routers />} />
        <Route path="sensors" element={<Sensors />} />
      </Route>
    </Routes>
  )
}

export default App
