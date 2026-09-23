import React, { useState, useEffect } from 'react';
import { fetchDevices, subscribeToDevices, emptyImageBucket } from './services/dataService';
import DeviceGrid from './components/DeviceGrid';
import { LayoutDashboard, RefreshCcw, Trash2 } from 'lucide-react';

function App() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [emptying, setEmptying] = useState(false);
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

  const handleEmptyBucket = async () => {
    const confirmed = window.confirm(
      'Hapus seluruh file di bucket aloptama-images?\n\nTindakan ini tidak bisa dibatalkan. Kartu perangkat akan kehilangan gambar sampai screenshot baru terkirim.'
    );
    if (!confirmed || emptying) {
      return;
    }

    setEmptying(true);
    const { deleted, error: emptyError } = await emptyImageBucket();
    setEmptying(false);

    if (emptyError) {
      setError(emptyError);
      return;
    }

    await loadData();
    window.alert(`Bucket dikosongkan. ${deleted} file dihapus.`);
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
      <header className="page-header">
        <div>
          <div className="page-title-row">
            <LayoutDashboard size={28} style={{ color: 'var(--text-main)' }} />
            <h1 className="page-title">Monitoring Devices</h1>
          </div>
          <p className="text-gray" style={{ margin: 0 }}>Real-time display status overview.</p>
        </div>

        <div className="header-actions">
          <button className="header-btn" onClick={loadData} disabled={emptying}>
            <RefreshCcw size={14} className={loading ? 'spin' : ''} style={{ opacity: 0.7 }} />
            Refresh
          </button>
          <button className="header-btn header-btn-danger" onClick={handleEmptyBucket} disabled={emptying}>
            <Trash2 size={14} />
            {emptying ? 'Menghapus...' : 'Hapus seluruh bucket'}
          </button>
        </div>
      </header>

      <main>
        <DeviceGrid devices={devices} loading={loading && devices.length === 0} error={error} />
      </main>
    </div>
  );
}

export default App;
