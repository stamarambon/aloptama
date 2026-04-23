import React from 'react';
import DeviceCard from './DeviceCard';
import './DeviceGrid.css';

export default function DeviceGrid({ devices, loading, error }) {
  if (loading) {
    return (
      <div className="device-grid-state">
        <div className="spinner"></div>
        <p className="text-gray mt-2">Loading devices...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="device-grid-state error-state">
        <p>Error loading devices: {error}</p>
      </div>
    );
  }

  if (!devices || devices.length === 0) {
    return (
      <div className="device-grid-state">
        <p className="text-gray">No devices found.</p>
      </div>
    );
  }

  return (
    <div className="device-grid">
      {devices.map(device => (
        <DeviceCard key={device.id} device={device} />
      ))}
    </div>
  );
}
