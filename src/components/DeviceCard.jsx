import React from 'react';
import { Clock, MapPin, Monitor } from 'lucide-react';
import './DeviceCard.css';

export default function DeviceCard({ device }) {
  const date = new Date(device.timestamp);
  
  const formattedDate = new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Jayapura'
  }).format(date) + ' WIT';

  // Check if delayed by more than 3 hours
  const now = new Date();
  const diffHours = (now - date) / (1000 * 60 * 60);
  const isDelayed = diffHours >= 3;

  // Determine final status
  let rawStatus = device.status?.toLowerCase();
  if (isDelayed) {
    rawStatus = 'red'; // Force OFF if delayed
  }

  const statusClass = rawStatus === 'green' ? 'status-green' : 'status-red';
  const displayStatus = rawStatus === 'green' ? 'ON' : 'OFF';
  
  return (
    <div className="device-card">
      <div className="device-card-image-container">
        {device.gambar_url ? (
          <img src={device.gambar_url} alt={`Display ${device.kode}`} className="device-card-image" />
        ) : (
          <div className="device-card-placeholder">
            <Monitor size={48} className="text-gray" />
            <p>No Image</p>
          </div>
        )}
        <div className="device-card-badge">
          <span className={`status-badge ${statusClass}`}>{displayStatus}</span>
        </div>
      </div>
      
      <div className="device-card-content">
        <h3 className="device-card-title">{device.kode}</h3>
        
        <div className="device-card-details">
          <div className="detail-item text-gray">
            <Monitor size={14} />
            <span>{device.jenis || 'Display'}</span>
          </div>
          <div className="detail-item text-gray">
            <MapPin size={14} />
            <span>{device.lintang}, {device.bujur}</span>
          </div>
          <div className="detail-item text-gray">
            <Clock size={14} />
            <span>{formattedDate}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
