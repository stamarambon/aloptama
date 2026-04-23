import React, { useState, useEffect } from 'react';
import { fetchDevices, subscribeToDevices } from './services/dataService';
import DeviceGrid from './components/DeviceGrid';
import { LayoutDashboard, RefreshCcw } from 'lucide-react';

function App() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    const { data, error } = await fetchDevices();
    if (error) {
      setError(error);
    } else {
      setDevices(data || []);
      setError(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();

    // Set up realtime subscription
    const subscription = subscribeToDevices((payload) => {
      console.log('Realtime update:', payload);
      // Reload data when there's a change
      loadData();
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  return (
    <div className="container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
            <LayoutDashboard size={28} style={{ color: 'var(--text-main)' }} />
            <h1 className="page-title">Monitoring Devices</h1>
          </div>
          <p className="text-gray" style={{ margin: 0 }}>Real-time display status overview.</p>
        </div>
        
        <button 
          onClick={loadData}
          style={{
            background: 'none',
            border: '1px solid var(--border-light)',
            borderRadius: '6px',
            padding: '6px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: '500',
            color: 'var(--text-main)',
            backgroundColor: 'var(--bg-color)',
            transition: 'background-color 0.2s ease, box-shadow 0.2s ease',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-color)'}
        >
          <RefreshCcw size={14} className={loading ? 'spin' : ''} style={{ opacity: 0.7 }} />
          Refresh
        </button>
      </header>

      <main>
        <DeviceGrid devices={devices} loading={loading && devices.length === 0} error={error} />
      </main>
    </div>
  );
}

export default App;
