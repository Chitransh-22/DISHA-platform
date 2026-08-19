import React, { useRef } from 'react';
import { indiaMapPhoto } from '../../../assets/images';

export const RealisticIndiaMap = ({
  zoomLevel,
  panOffset,
  isDragging,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
}) => {
  const containerRef = useRef(null);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-135 sm:h-162.5 lg:h-190 overflow-hidden rounded-2xl bg-[#9fc4e4] select-none flex items-center justify-center ${
        zoomLevel > 1 ? (isDragging ? 'cursor-grabbing' : 'cursor-grab') : 'cursor-default'
      }`}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      {/* Scalable & Pannable Map Image Container */}
      <div
        className="w-full h-full relative transition-transform duration-150 ease-out origin-center flex items-center justify-center p-2 sm:p-4"
        style={{
          transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
        }}
      >
        {/* Map Image (High-Resolution Outline with States and Highlighted Borders) */}
        <img
          src={indiaMapPhoto}
          alt="India Political States Map"
          className="max-h-full max-w-full object-contain rounded-xl shadow-sm pointer-events-none"
          referrerPolicy="no-referrer"
        />
      </div>
    </div>
  );
};
