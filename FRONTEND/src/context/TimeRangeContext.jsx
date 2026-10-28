import React, { createContext, useContext, useState, useCallback } from 'react';

const TimeRangeContext = createContext(null);

export const TIME_RANGE_OPTIONS = [
  { id: '24h', label: '24 Hours', shortLabel: '24h' },
  { id: '7d', label: '7 Days', shortLabel: '7d' },
  { id: '15d', label: '15 Days', shortLabel: '15d' },
  { id: '30d', label: '30 Days', shortLabel: '30d' },
  { id: 'all', label: 'All Records', shortLabel: 'All' },
];

export const TimeRangeProvider = ({ children }) => {
  // Default to '30d' so user immediately sees verified disaster landscape across India,
  // but can smoothly toggle to 24h, 7d, 15d, 30d, or all records.
  const [timeRange, setTimeRangeState] = useState('30d');
  const [customRange, setCustomRangeState] = useState({ startDate: '', endDate: '' });

  const setTimeRange = useCallback((newRange) => {
    setTimeRangeState(newRange);
  }, []);

  const setCustomRange = useCallback((range) => {
    setCustomRangeState(range);
    if (range?.startDate || range?.endDate) {
      setTimeRangeState('custom');
    }
  }, []);

  return (
    <TimeRangeContext.Provider
      value={{
        timeRange,
        setTimeRange,
        customRange,
        setCustomRange,
        availableRanges: TIME_RANGE_OPTIONS,
      }}
    >
      {children}
    </TimeRangeContext.Provider>
  );
};

export const useTimeRange = () => {
  const context = useContext(TimeRangeContext);
  if (!context) {
    throw new Error('useTimeRange must be used within a TimeRangeProvider');
  }
  return context;
};
