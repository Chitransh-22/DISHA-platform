import React, { useState, useRef } from 'react';
import { MapPin, Clock, Plus, Minus, Maximize2 } from 'lucide-react';
import { RealisticIndiaMap } from './RealisticIndiaMap';

export const LiveDisasterMap = () => {
  // Zoom & Pan state (controlled explicitly via buttons, preserving standard page scrolling)
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(2.5, +(prev + 0.25).toFixed(2)));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => {
      const next = Math.max(0.85, +(prev - 0.25).toFixed(2));
      if (next <= 1) {
        setPanOffset({ x: 0, y: 0 });
      }
      return next;
    });
  };

  const handleRecenter = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Drag Panning Handlers (when zoomed in)
  const handleMouseDown = (e) => {
    if (zoomLevel <= 1) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - panOffset.x,
      y: e.clientY - panOffset.y,
    };
  };

  const handleMouseMove = (e) => {
    if (!isDragging || zoomLevel <= 1) return;
    const maxOffset = (zoomLevel - 1) * 320;
    const newX = Math.max(-maxOffset, Math.min(maxOffset, e.clientX - dragStartRef.current.x));
    const newY = Math.max(-maxOffset, Math.min(maxOffset, e.clientY - dragStartRef.current.y));
    setPanOffset({ x: newX, y: newY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e) => {
    if (zoomLevel <= 1 || e.touches.length !== 1) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.touches[0].clientX - panOffset.x,
      y: e.touches[0].clientY - panOffset.y,
    };
  };

  const handleTouchMove = (e) => {
    if (!isDragging || zoomLevel <= 1 || e.touches.length !== 1) return;
    const maxOffset = (zoomLevel - 1) * 320;
    const newX = Math.max(-maxOffset, Math.min(maxOffset, e.touches[0].clientX - dragStartRef.current.x));
    const newY = Math.max(-maxOffset, Math.min(maxOffset, e.touches[0].clientY - dragStartRef.current.y));
    setPanOffset({ x: newX, y: newY });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      {/* Map Container Card */}
      <div className="bg-white rounded-2xl sm:rounded-3xl shadow-xl border border-slate-200/80 overflow-hidden flex flex-col">
        
        {/* Header Bar */}
        <div className="px-4 sm:px-6 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 sm:gap-4 bg-white z-20 relative">
          
          {/* Left Title: Pin + "Live Disaster Map" */}
          <div className="flex items-center gap-2.5">
            <div className="text-[#ea580c] flex items-center justify-center">
              <MapPin className="w-6 h-6 fill-[#ea580c] text-white" />
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[#111827] tracking-tight font-sans">
              Live Disaster Map
            </h2>
          </div>

          {/* Right Status: Last Updated Live Badge */}
          <div className="flex items-center gap-2 text-xs sm:text-sm font-medium text-slate-700">
            <Clock className="w-4 h-4 text-slate-500" />
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-1.5">
              <span className="text-[11px] sm:text-xs text-slate-500 font-semibold">Last Updated</span>
              <span className="text-xs sm:text-sm font-bold text-slate-800">18 May 2024, 10:24 AM IST</span>
            </div>
            {/* Green Pulsing Live Indicator */}
            <span className="relative flex h-2.5 w-2.5 ml-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          </div>

        </div>

        {/* Map Stage with Photo of Map, Highlighted India & State Borders & State Names */}
        <div className="relative w-full bg-[#cbe0ec] overflow-hidden">
          
          <RealisticIndiaMap
            zoomLevel={zoomLevel}
            panOffset={panOffset}
            isDragging={isDragging}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          />

          {/* Zoom In / Zoom Out / Recenter Controls */}
          <div className="absolute top-4 left-4 z-30 flex flex-col gap-1.5 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-200/90 p-1.5">
            {/* Zoom In (+) */}
            <button
              id="map-zoom-in-btn"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 2.5}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-50 text-slate-700 hover:text-orange-600 font-bold disabled:opacity-40 disabled:hover:bg-slate-50 disabled:hover:text-slate-700 transition-colors shadow-xs cursor-pointer"
              title="Zoom In"
              aria-label="Zoom In"
            >
              <Plus className="w-4 h-4" />
            </button>

            {/* Zoom Percentage */}
            <div className="text-[10px] font-bold text-slate-600 text-center py-0.5 select-none">
              {Math.round(zoomLevel * 100)}%
            </div>

            {/* Zoom Out (-) */}
            <button
              id="map-zoom-out-btn"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.85}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-50 text-slate-700 hover:text-orange-600 font-bold disabled:opacity-40 disabled:hover:bg-slate-50 disabled:hover:text-slate-700 transition-colors shadow-xs cursor-pointer"
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <Minus className="w-4 h-4" />
            </button>

            {/* Recenter View */}
            <button
              id="map-recenter-btn"
              onClick={handleRecenter}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-50 text-slate-700 hover:text-orange-600 transition-colors shadow-xs cursor-pointer mt-0.5"
              title="Recenter Map"
              aria-label="Recenter Map"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

        </div>

      </div>
    </section>
  );
};
