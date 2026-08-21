import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, MapPin, X, Check, ChevronDown } from 'lucide-react';

// Comprehensive Indian cities & districts database with real geographical coordinates
export const INDIAN_CITIES_DATABASE = [
  // Metro & Major Urban Centers
  { name: 'Delhi NCR', state: 'Delhi', lat: 28.6139, lng: 77.2090 },
  { name: 'New Delhi', state: 'Delhi', lat: 28.6139, lng: 77.2090 },
  { name: 'Mumbai', state: 'Maharashtra', lat: 19.0760, lng: 72.8777 },
  { name: 'Pune', state: 'Maharashtra', lat: 18.5204, lng: 73.8567 },
  { name: 'Nagpur', state: 'Maharashtra', lat: 21.1458, lng: 79.0882 },
  { name: 'Thane', state: 'Maharashtra', lat: 19.2183, lng: 72.9781 },
  { name: 'Nashik', state: 'Maharashtra', lat: 19.9975, lng: 73.7898 },
  { name: 'Kolhapur', state: 'Maharashtra', lat: 16.7050, lng: 74.2433 },
  { name: 'Kolkata', state: 'West Bengal', lat: 22.5726, lng: 88.3639 },
  { name: 'Howrah', state: 'West Bengal', lat: 22.5958, lng: 88.2636 },
  { name: 'Siliguri', state: 'West Bengal', lat: 26.7271, lng: 88.3953 },
  { name: 'Darjeeling', state: 'West Bengal', lat: 27.0410, lng: 88.2663 },
  { name: 'Durgapur', state: 'West Bengal', lat: 23.5204, lng: 87.3119 },
  { name: 'Asansol', state: 'West Bengal', lat: 23.6889, lng: 86.9661 },
  { name: 'Chennai', state: 'Tamil Nadu', lat: 13.0827, lng: 80.2707 },
  { name: 'Coimbatore', state: 'Tamil Nadu', lat: 11.0168, lng: 76.9558 },
  { name: 'Madurai', state: 'Tamil Nadu', lat: 9.9252, lng: 78.1198 },
  { name: 'Tiruchirappalli', state: 'Tamil Nadu', lat: 10.7905, lng: 78.7047 },
  { name: 'Salem', state: 'Tamil Nadu', lat: 11.6643, lng: 78.1460 },
  { name: 'Bengaluru', state: 'Karnataka', lat: 12.9716, lng: 77.5946 },
  { name: 'Mysuru', state: 'Karnataka', lat: 12.2958, lng: 76.6394 },
  { name: 'Hubli-Dharwad', state: 'Karnataka', lat: 15.3647, lng: 75.1240 },
  { name: 'Mangaluru', state: 'Karnataka', lat: 12.9141, lng: 74.8560 },
  { name: 'Belagavi', state: 'Karnataka', lat: 15.8497, lng: 74.4977 },
  { name: 'Hyderabad', state: 'Telangana', lat: 17.3850, lng: 78.4867 },
  { name: 'Warangal', state: 'Telangana', lat: 17.9689, lng: 79.5941 },
  { name: 'Nizamabad', state: 'Telangana', lat: 18.6725, lng: 78.0941 },
  { name: 'Karimnagar', state: 'Telangana', lat: 18.4386, lng: 79.1288 },
  { name: 'Ahmedabad', state: 'Gujarat', lat: 23.0225, lng: 72.5714 },
  { name: 'Surat', state: 'Gujarat', lat: 21.1702, lng: 72.8311 },
  { name: 'Vadodara', state: 'Gujarat', lat: 22.3072, lng: 73.1812 },
  { name: 'Rajkot', state: 'Gujarat', lat: 22.3039, lng: 70.8022 },
  { name: 'Gandhinagar', state: 'Gujarat', lat: 23.2156, lng: 72.6369 },
  { name: 'Bhavnagar', state: 'Gujarat', lat: 21.7645, lng: 72.1519 },
  { name: 'Bhuj', state: 'Gujarat', lat: 23.2420, lng: 69.6669 },
  { name: 'Jaipur', state: 'Rajasthan', lat: 26.9124, lng: 75.7873 },
  { name: 'Jodhpur', state: 'Rajasthan', lat: 26.2389, lng: 73.0243 },
  { name: 'Udaipur', state: 'Rajasthan', lat: 24.5854, lng: 73.7125 },
  { name: 'Kota', state: 'Rajasthan', lat: 25.2138, lng: 75.8648 },
  { name: 'Bikaner', state: 'Rajasthan', lat: 28.0229, lng: 73.3119 },
  { name: 'Ajmer', state: 'Rajasthan', lat: 26.4499, lng: 74.6399 },
  { name: 'Lucknow', state: 'Uttar Pradesh', lat: 26.8467, lng: 80.9462 },
  { name: 'Kanpur', state: 'Uttar Pradesh', lat: 26.4499, lng: 80.3319 },
  { name: 'Varanasi', state: 'Uttar Pradesh', lat: 25.3176, lng: 82.9739 },
  { name: 'Agra', state: 'Uttar Pradesh', lat: 27.1767, lng: 78.0081 },
  { name: 'Noida', state: 'Uttar Pradesh', lat: 28.5355, lng: 77.3910 },
  { name: 'Ghaziabad', state: 'Uttar Pradesh', lat: 28.6692, lng: 77.4538 },
  { name: 'Prayagraj', state: 'Uttar Pradesh', lat: 25.4358, lng: 81.8463 },
  { name: 'Meerut', state: 'Uttar Pradesh', lat: 28.9845, lng: 77.7064 },
  { name: 'Gorakhpur', state: 'Uttar Pradesh', lat: 26.7606, lng: 83.3732 },
  { name: 'Bareilly', state: 'Uttar Pradesh', lat: 28.3670, lng: 79.4304 },
  { name: 'Aligarh', state: 'Uttar Pradesh', lat: 27.8974, lng: 78.0880 },
  { name: 'Bhopal', state: 'Madhya Pradesh', lat: 23.2599, lng: 77.4126 },
  { name: 'Indore', state: 'Madhya Pradesh', lat: 22.7196, lng: 75.8577 },
  { name: 'Gwalior', state: 'Madhya Pradesh', lat: 26.2183, lng: 78.1828 },
  { name: 'Jabalpur', state: 'Madhya Pradesh', lat: 23.1815, lng: 79.9864 },
  { name: 'Ujjain', state: 'Madhya Pradesh', lat: 23.1765, lng: 75.7885 },
  { name: 'Patna', state: 'Bihar', lat: 25.5941, lng: 85.1376 },
  { name: 'Gaya', state: 'Bihar', lat: 24.7914, lng: 85.0002 },
  { name: 'Bhagalpur', state: 'Bihar', lat: 25.2425, lng: 86.9842 },
  { name: 'Muzaffarpur', state: 'Bihar', lat: 26.1209, lng: 85.3647 },
  { name: 'Bhubaneswar', state: 'Odisha', lat: 20.2961, lng: 85.8245 },
  { name: 'Cuttack', state: 'Odisha', lat: 20.4625, lng: 85.8828 },
  { name: 'Puri', state: 'Odisha', lat: 19.8135, lng: 85.8312 },
  { name: 'Rourkela', state: 'Odisha', lat: 22.2604, lng: 84.8536 },
  { name: 'Balasore', state: 'Odisha', lat: 21.4934, lng: 86.9135 },
  { name: 'Sambalpur', state: 'Odisha', lat: 21.4669, lng: 83.9812 },
  { name: 'Kochi', state: 'Kerala', lat: 9.9312, lng: 76.2673 },
  { name: 'Thiruvananthapuram', state: 'Kerala', lat: 8.5241, lng: 76.9366 },
  { name: 'Kozhikode', state: 'Kerala', lat: 11.2588, lng: 75.7804 },
  { name: 'Thrissur', state: 'Kerala', lat: 10.5276, lng: 76.2144 },
  { name: 'Wayanad', state: 'Kerala', lat: 11.6854, lng: 76.1320 },
  { name: 'Idukki', state: 'Kerala', lat: 9.8494, lng: 76.9810 },
  { name: 'Alappuzha', state: 'Kerala', lat: 9.4981, lng: 76.3388 },
  { name: 'Visakhapatnam', state: 'Andhra Pradesh', lat: 17.6868, lng: 83.2185 },
  { name: 'Vijayawada', state: 'Andhra Pradesh', lat: 16.5062, lng: 80.6480 },
  { name: 'Guntur', state: 'Andhra Pradesh', lat: 16.3067, lng: 80.4365 },
  { name: 'Tirupati', state: 'Andhra Pradesh', lat: 13.6288, lng: 79.4192 },
  { name: 'Kurnool', state: 'Andhra Pradesh', lat: 15.8281, lng: 78.0373 },
  { name: 'Guwahati', state: 'Assam', lat: 26.1445, lng: 91.7362 },
  { name: 'Silchar', state: 'Assam', lat: 24.8333, lng: 92.7789 },
  { name: 'Dibrugarh', state: 'Assam', lat: 27.4728, lng: 94.9120 },
  { name: 'Jorhat', state: 'Assam', lat: 26.7509, lng: 94.2037 },
  { name: 'Tezpur', state: 'Assam', lat: 26.6528, lng: 92.7926 },
  { name: 'Dehradun', state: 'Uttarakhand', lat: 30.3165, lng: 78.0322 },
  { name: 'Haridwar', state: 'Uttarakhand', lat: 29.9457, lng: 78.1642 },
  { name: 'Rishikesh', state: 'Uttarakhand', lat: 30.0869, lng: 78.2676 },
  { name: 'Nainital', state: 'Uttarakhand', lat: 29.3919, lng: 79.4542 },
  { name: 'Chamoli', state: 'Uttarakhand', lat: 30.4000, lng: 79.3333 },
  { name: 'Shimla', state: 'Himachal Pradesh', lat: 31.1048, lng: 77.1734 },
  { name: 'Manali', state: 'Himachal Pradesh', lat: 32.2432, lng: 77.1892 },
  { name: 'Dharamshala', state: 'Himachal Pradesh', lat: 32.2190, lng: 76.3234 },
  { name: 'Kullu', state: 'Himachal Pradesh', lat: 31.9579, lng: 77.1095 },
  { name: 'Mandi', state: 'Himachal Pradesh', lat: 31.7087, lng: 76.9320 },
  { name: 'Ranchi', state: 'Jharkhand', lat: 23.3441, lng: 85.3096 },
  { name: 'Jamshedpur', state: 'Jharkhand', lat: 22.8046, lng: 86.2029 },
  { name: 'Dhanbad', state: 'Jharkhand', lat: 23.7957, lng: 86.4304 },
  { name: 'Bokaro', state: 'Jharkhand', lat: 23.6693, lng: 86.1511 },
  { name: 'Raipur', state: 'Chhattisgarh', lat: 21.2514, lng: 81.6296 },
  { name: 'Bilaspur', state: 'Chhattisgarh', lat: 22.0797, lng: 82.1391 },
  { name: 'Durg-Bhilai', state: 'Chhattisgarh', lat: 21.1904, lng: 81.2849 },
  { name: 'Ludhiana', state: 'Punjab', lat: 30.9010, lng: 75.8573 },
  { name: 'Amritsar', state: 'Punjab', lat: 31.6340, lng: 74.8723 },
  { name: 'Jalandhar', state: 'Punjab', lat: 31.3260, lng: 75.5762 },
  { name: 'Patiala', state: 'Punjab', lat: 30.3398, lng: 76.3869 },
  { name: 'Chandigarh', state: 'Chandigarh', lat: 30.7333, lng: 76.7794 },
  { name: 'Gurugram', state: 'Haryana', lat: 28.4595, lng: 77.0266 },
  { name: 'Faridabad', state: 'Haryana', lat: 28.4089, lng: 77.3178 },
  { name: 'Panipat', state: 'Haryana', lat: 29.3909, lng: 76.9635 },
  { name: 'Srinagar', state: 'Jammu and Kashmir', lat: 34.0837, lng: 74.7973 },
  { name: 'Jammu', state: 'Jammu and Kashmir', lat: 32.7266, lng: 74.8570 },
  { name: 'Leh', state: 'Ladakh', lat: 34.1526, lng: 77.5771 },
  { name: 'Kargil', state: 'Ladakh', lat: 34.5539, lng: 76.1349 },
  { name: 'Gangtok', state: 'Sikkim', lat: 27.3389, lng: 88.6065 },
  { name: 'Shillong', state: 'Meghalaya', lat: 25.5788, lng: 91.8933 },
  { name: 'Cherrapunji', state: 'Meghalaya', lat: 25.2986, lng: 91.7324 },
  { name: 'Imphal', state: 'Manipur', lat: 24.8170, lng: 93.9368 },
  { name: 'Aizawl', state: 'Mizoram', lat: 23.7271, lng: 92.7176 },
  { name: 'Kohima', state: 'Nagaland', lat: 25.6751, lng: 94.1086 },
  { name: 'Dimapur', state: 'Nagaland', lat: 25.9068, lng: 93.7273 },
  { name: 'Agartala', state: 'Tripura', lat: 23.8315, lng: 91.2868 },
  { name: 'Itanagar', state: 'Arunachal Pradesh', lat: 27.0844, lng: 93.6053 },
  { name: 'Panaji', state: 'Goa', lat: 15.4909, lng: 73.8278 },
  { name: 'Margao', state: 'Goa', lat: 15.2832, lng: 73.9862 },
  { name: 'Puducherry', state: 'Puducherry', lat: 11.9416, lng: 79.8083 },
  { name: 'Port Blair', state: 'Andaman and Nicobar', lat: 11.6234, lng: 92.7265 },
];

/**
 * Searches the city database or performs fuzzy matching.
 */
export function findMatchingCities(query) {
  if (!query || !query.trim()) return INDIAN_CITIES_DATABASE.slice(0, 15);
  const q = query.toLowerCase().trim();

  return INDIAN_CITIES_DATABASE.filter(
    (c) => c.name.toLowerCase().includes(q) || c.state.toLowerCase().includes(q)
  );
}

/**
 * Resolves a city name to coordinates.
 */
export function resolveCityCoordinates(cityName) {
  if (!cityName) return null;
  const q = cityName.toLowerCase().trim();

  const exact = INDIAN_CITIES_DATABASE.find(
    (c) => c.name.toLowerCase() === q || `${c.name}, ${c.state}`.toLowerCase() === q
  );
  if (exact) return { lat: exact.lat, lng: exact.lng, name: `${exact.name}, ${exact.state}` };

  const partial = INDIAN_CITIES_DATABASE.find(
    (c) => c.name.toLowerCase().includes(q) || q.includes(c.name.toLowerCase())
  );
  if (partial) return { lat: partial.lat, lng: partial.lng, name: `${partial.name}, ${partial.state}` };

  return null;
}

export const CitySelector = ({ value, onSelectCity, placeholder = 'Search or enter city...' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState(value?.name || '');
  const containerRef = useRef(null);

  useEffect(() => {
    if (value?.name) {
      setSearch(value.name);
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const matches = useMemo(() => findMatchingCities(search), [search]);

  const handleSelect = (city) => {
    setSearch(`${city.name}, ${city.state}`);
    setIsOpen(false);
    onSelectCity({
      name: `${city.name}, ${city.state}`,
      lat: city.lat,
      lng: city.lng,
      isGps: false,
    });
  };

  const handleCustomSubmit = () => {
    if (!search.trim()) return;
    const resolved = resolveCityCoordinates(search);
    if (resolved) {
      onSelectCity({
        name: resolved.name,
        lat: resolved.lat,
        lng: resolved.lng,
        isGps: false,
      });
    } else {
      // User entered a city not in the offline database
      onSelectCity({
        name: search.trim(),
        lat: null,
        lng: null,
        isGps: false,
        unresolved: true,
      });
    }
    setIsOpen(false);
  };

  return (
    <div className="relative w-full min-w-[240px]" ref={containerRef}>
      <div className="relative flex items-center">
        <MapPin className="w-4 h-4 text-orange-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (matches.length > 0) {
                handleSelect(matches[0]);
              } else {
                handleCustomSubmit();
              }
            }
          }}
          placeholder={placeholder}
          className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-8 py-2 text-xs sm:text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 transition-all shadow-xs"
        />

        {search && (
          <button
            onClick={() => {
              setSearch('');
              setIsOpen(true);
            }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl z-50 max-h-60 overflow-y-auto divide-y divide-slate-100 animate-in fade-in zoom-in-95 duration-150">
          {matches.length > 0 ? (
            matches.map((city) => (
              <button
                key={`${city.name}-${city.state}`}
                type="button"
                onClick={() => handleSelect(city)}
                className="w-full text-left px-3.5 py-2.5 hover:bg-orange-50/70 transition-colors flex items-center justify-between text-xs cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 group-hover:text-orange-500" />
                  <span className="font-bold text-slate-800">{city.name}</span>
                  <span className="text-slate-400">({city.state})</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 group-hover:text-orange-600">
                  {city.lat.toFixed(2)}°N, {city.lng.toFixed(2)}°E
                </span>
              </button>
            ))
          ) : (
            <div className="p-3 text-center space-y-2">
              <p className="text-xs text-slate-500">No exact match found in index.</p>
              <button
                type="button"
                onClick={handleCustomSubmit}
                className="w-full py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
              >
                Use "{search}" as Custom City
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
