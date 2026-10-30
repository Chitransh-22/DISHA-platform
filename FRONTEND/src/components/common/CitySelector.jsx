import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, MapPin, X, Check, Globe, ChevronDown, Layers, Building2, Compass } from 'lucide-react';

// All 36 Indian States and Union Territories with canonical names and center coordinates
export const INDIAN_STATES_DATABASE = [
  { name: 'Andhra Pradesh', level: 'state', state: 'Andhra Pradesh', lat: 15.9129, lng: 79.7400 },
  { name: 'Arunachal Pradesh', level: 'state', state: 'Arunachal Pradesh', lat: 28.2180, lng: 94.7278 },
  { name: 'Assam', level: 'state', state: 'Assam', lat: 26.2006, lng: 92.9376 },
  { name: 'Bihar', level: 'state', state: 'Bihar', lat: 25.0961, lng: 85.3131 },
  { name: 'Chhattisgarh', level: 'state', state: 'Chhattisgarh', lat: 21.2787, lng: 81.8661 },
  { name: 'Goa', level: 'state', state: 'Goa', lat: 15.2993, lng: 74.1240 },
  { name: 'Gujarat', level: 'state', state: 'Gujarat', lat: 22.2587, lng: 71.1924 },
  { name: 'Haryana', level: 'state', state: 'Haryana', lat: 29.0588, lng: 76.0856 },
  { name: 'Himachal Pradesh', level: 'state', state: 'Himachal Pradesh', lat: 31.1048, lng: 77.1734 },
  { name: 'Jharkhand', level: 'state', state: 'Jharkhand', lat: 23.6102, lng: 85.2799 },
  { name: 'Karnataka', level: 'state', state: 'Karnataka', lat: 15.3173, lng: 75.7139 },
  { name: 'Kerala', level: 'state', state: 'Kerala', lat: 10.8505, lng: 76.2711 },
  { name: 'Madhya Pradesh', level: 'state', state: 'Madhya Pradesh', lat: 22.9734, lng: 78.6569 },
  { name: 'Maharashtra', level: 'state', state: 'Maharashtra', lat: 19.7515, lng: 75.7139 },
  { name: 'Manipur', level: 'state', state: 'Manipur', lat: 24.6637, lng: 93.9063 },
  { name: 'Meghalaya', level: 'state', state: 'Meghalaya', lat: 25.4670, lng: 91.3662 },
  { name: 'Mizoram', level: 'state', state: 'Mizoram', lat: 23.1645, lng: 92.9376 },
  { name: 'Nagaland', level: 'state', state: 'Nagaland', lat: 26.1584, lng: 94.5624 },
  { name: 'Odisha', level: 'state', state: 'Odisha', lat: 20.9517, lng: 85.0985 },
  { name: 'Punjab', level: 'state', state: 'Punjab', lat: 31.1471, lng: 75.3412 },
  { name: 'Rajasthan', level: 'state', state: 'Rajasthan', lat: 27.0238, lng: 74.2179 },
  { name: 'Sikkim', level: 'state', state: 'Sikkim', lat: 27.5330, lng: 88.5122 },
  { name: 'Tamil Nadu', level: 'state', state: 'Tamil Nadu', lat: 11.1271, lng: 78.6569 },
  { name: 'Telangana', level: 'state', state: 'Telangana', lat: 18.1124, lng: 79.0193 },
  { name: 'Tripura', level: 'state', state: 'Tripura', lat: 23.9408, lng: 91.9882 },
  { name: 'Uttar Pradesh', level: 'state', state: 'Uttar Pradesh', lat: 26.8467, lng: 80.9462 },
  { name: 'Uttarakhand', level: 'state', state: 'Uttarakhand', lat: 30.0668, lng: 79.0193 },
  { name: 'West Bengal', level: 'state', state: 'West Bengal', lat: 22.9868, lng: 87.8550 },
  { name: 'Andaman and Nicobar Islands', level: 'state', state: 'Andaman and Nicobar Islands', lat: 11.7401, lng: 92.6586 },
  { name: 'Chandigarh', level: 'state', state: 'Chandigarh', lat: 30.7333, lng: 76.7794 },
  { name: 'Dadra and Nagar Haveli and Daman and Diu', level: 'state', state: 'Dadra and Nagar Haveli and Daman and Diu', lat: 20.1809, lng: 73.0169 },
  { name: 'Delhi', level: 'state', state: 'Delhi', lat: 28.7041, lng: 77.1025 },
  { name: 'Jammu and Kashmir', level: 'state', state: 'Jammu and Kashmir', lat: 33.7782, lng: 76.5762 },
  { name: 'Ladakh', level: 'state', state: 'Ladakh', lat: 34.1526, lng: 77.5771 },
  { name: 'Lakshadweep', level: 'state', state: 'Lakshadweep', lat: 10.5667, lng: 72.6417 },
  { name: 'Puducherry', level: 'state', state: 'Puducherry', lat: 11.9416, lng: 79.8083 },
];

export const COUNTRY_OPTION = {
  name: 'All India',
  level: 'country',
  state: null,
  district: null,
  lat: 22.5937,
  lng: 78.9629,
};

// Comprehensive Indian cities & districts database with real geographical coordinates
export const INDIAN_CITIES_DATABASE = [
  // Metro & Major Urban Centers
  { name: 'Delhi NCR', state: 'Delhi', district: 'New Delhi', level: 'city', lat: 28.6139, lng: 77.2090 },
  { name: 'New Delhi', state: 'Delhi', district: 'New Delhi', level: 'city', lat: 28.6139, lng: 77.2090 },
  { name: 'Mumbai', state: 'Maharashtra', district: 'Mumbai', level: 'city', lat: 19.0760, lng: 72.8777 },
  { name: 'Pune', state: 'Maharashtra', district: 'Pune', level: 'district', lat: 18.5204, lng: 73.8567 },
  { name: 'Nagpur', state: 'Maharashtra', district: 'Nagpur', level: 'district', lat: 21.1458, lng: 79.0882 },
  { name: 'Thane', state: 'Maharashtra', district: 'Thane', level: 'district', lat: 19.2183, lng: 72.9781 },
  { name: 'Nashik', state: 'Maharashtra', district: 'Nashik', level: 'district', lat: 19.9975, lng: 73.7898 },
  { name: 'Kolhapur', state: 'Maharashtra', district: 'Kolhapur', level: 'district', lat: 16.7050, lng: 74.2433 },
  { name: 'Chhatrapati Sambhaji Nagar', state: 'Maharashtra', district: 'Aurangabad', level: 'district', lat: 19.8762, lng: 75.3433 },
  { name: 'Kolkata', state: 'West Bengal', district: 'Kolkata', level: 'city', lat: 22.5726, lng: 88.3639 },
  { name: 'Howrah', state: 'West Bengal', district: 'Howrah', level: 'district', lat: 22.5958, lng: 88.2636 },
  { name: 'Siliguri', state: 'West Bengal', district: 'Darjeeling', level: 'city', lat: 26.7271, lng: 88.3953 },
  { name: 'Darjeeling', state: 'West Bengal', district: 'Darjeeling', level: 'district', lat: 27.0410, lng: 88.2663 },
  { name: 'Durgapur', state: 'West Bengal', district: 'Paschim Bardhaman', level: 'city', lat: 23.5204, lng: 87.3119 },
  { name: 'Asansol', state: 'West Bengal', district: 'Paschim Bardhaman', level: 'city', lat: 23.6889, lng: 86.9661 },
  { name: 'Chennai', state: 'Tamil Nadu', district: 'Chennai', level: 'city', lat: 13.0827, lng: 80.2707 },
  { name: 'Coimbatore', state: 'Tamil Nadu', district: 'Coimbatore', level: 'district', lat: 11.0168, lng: 76.9558 },
  { name: 'Madurai', state: 'Tamil Nadu', district: 'Madurai', level: 'district', lat: 9.9252, lng: 78.1198 },
  { name: 'Tiruchirappalli', state: 'Tamil Nadu', district: 'Tiruchirappalli', level: 'district', lat: 10.7905, lng: 78.7047 },
  { name: 'Salem', state: 'Tamil Nadu', district: 'Salem', level: 'district', lat: 11.6643, lng: 78.1460 },
  { name: 'Bengaluru', state: 'Karnataka', district: 'Bengaluru Urban', level: 'city', lat: 12.9716, lng: 77.5946 },
  { name: 'Mysuru', state: 'Karnataka', district: 'Mysuru', level: 'district', lat: 12.2958, lng: 76.6394 },
  { name: 'Hubli-Dharwad', state: 'Karnataka', district: 'Dharwad', level: 'district', lat: 15.3647, lng: 75.1240 },
  { name: 'Mangaluru', state: 'Karnataka', district: 'Dakshina Kannada', level: 'district', lat: 12.9141, lng: 74.8560 },
  { name: 'Belagavi', state: 'Karnataka', district: 'Belagavi', level: 'district', lat: 15.8497, lng: 74.4977 },
  { name: 'Hyderabad', state: 'Telangana', district: 'Hyderabad', level: 'city', lat: 17.3850, lng: 78.4867 },
  { name: 'Warangal', state: 'Telangana', district: 'Warangal', level: 'district', lat: 17.9689, lng: 79.5941 },
  { name: 'Nizamabad', state: 'Telangana', district: 'Nizamabad', level: 'district', lat: 18.6725, lng: 78.0941 },
  { name: 'Karimnagar', state: 'Telangana', district: 'Karimnagar', level: 'district', lat: 18.4386, lng: 79.1288 },
  // Gujarat Centers
  { name: 'Ahmedabad', state: 'Gujarat', district: 'Ahmedabad', level: 'district', lat: 23.0225, lng: 72.5714 },
  { name: 'Surat', state: 'Gujarat', district: 'Surat', level: 'district', lat: 21.1702, lng: 72.8311 },
  { name: 'Vadodara', state: 'Gujarat', district: 'Vadodara', level: 'district', lat: 22.3072, lng: 73.1812 },
  { name: 'Rajkot', state: 'Gujarat', district: 'Rajkot', level: 'district', lat: 22.3039, lng: 70.8022 },
  { name: 'Gandhinagar', state: 'Gujarat', district: 'Gandhinagar', level: 'district', lat: 23.2156, lng: 72.6369 },
  { name: 'Bhavnagar', state: 'Gujarat', district: 'Bhavnagar', level: 'district', lat: 21.7645, lng: 72.1519 },
  { name: 'Jamnagar', state: 'Gujarat', district: 'Jamnagar', level: 'district', lat: 22.4707, lng: 70.0577 },
  { name: 'Junagadh', state: 'Gujarat', district: 'Junagadh', level: 'district', lat: 21.5222, lng: 70.4579 },
  { name: 'Bhuj', state: 'Gujarat', district: 'Kutch', level: 'district', lat: 23.2420, lng: 69.6669 },
  { name: 'Anand', state: 'Gujarat', district: 'Anand', level: 'district', lat: 22.5645, lng: 72.9289 },
  { name: 'Bharuch', state: 'Gujarat', district: 'Bharuch', level: 'district', lat: 21.7051, lng: 72.9959 },
  { name: 'Morbi', state: 'Gujarat', district: 'Morbi', level: 'district', lat: 22.8120, lng: 70.8377 },
  // Assam Centers
  { name: 'Guwahati', state: 'Assam', district: 'Kamrup Metropolitan', level: 'city', lat: 26.1445, lng: 91.7362 },
  { name: 'Kamrup', state: 'Assam', district: 'Kamrup', level: 'district', lat: 26.3167, lng: 91.5833 },
  { name: 'Silchar', state: 'Assam', district: 'Cachar', level: 'district', lat: 24.8333, lng: 92.7789 },
  { name: 'Cachar', state: 'Assam', district: 'Cachar', level: 'district', lat: 24.8333, lng: 92.7789 },
  { name: 'Dibrugarh', state: 'Assam', district: 'Dibrugarh', level: 'district', lat: 27.4728, lng: 94.9120 },
  { name: 'Jorhat', state: 'Assam', district: 'Jorhat', level: 'district', lat: 26.7509, lng: 94.2037 },
  { name: 'Tezpur', state: 'Assam', district: 'Sonitpur', level: 'district', lat: 26.6528, lng: 92.7926 },
  { name: 'Nagaon', state: 'Assam', district: 'Nagaon', level: 'district', lat: 26.3464, lng: 92.6840 },
  { name: 'Tinsukia', state: 'Assam', district: 'Tinsukia', level: 'district', lat: 27.4922, lng: 95.3468 },
  { name: 'Dhemaji', state: 'Assam', district: 'Dhemaji', level: 'district', lat: 27.4833, lng: 94.5833 },
  // Rajasthan Centers
  { name: 'Jaipur', state: 'Rajasthan', district: 'Jaipur', level: 'district', lat: 26.9124, lng: 75.7873 },
  { name: 'Jodhpur', state: 'Rajasthan', district: 'Jodhpur', level: 'district', lat: 26.2389, lng: 73.0243 },
  { name: 'Udaipur', state: 'Rajasthan', district: 'Udaipur', level: 'district', lat: 24.5854, lng: 73.7125 },
  { name: 'Kota', state: 'Rajasthan', district: 'Kota', level: 'district', lat: 25.2138, lng: 75.8648 },
  { name: 'Bikaner', state: 'Rajasthan', district: 'Bikaner', level: 'district', lat: 28.0229, lng: 73.3119 },
  { name: 'Ajmer', state: 'Rajasthan', district: 'Ajmer', level: 'district', lat: 26.4499, lng: 74.6399 },
  // Uttar Pradesh Centers
  { name: 'Lucknow', state: 'Uttar Pradesh', district: 'Lucknow', level: 'city', lat: 26.8467, lng: 80.9462 },
  { name: 'Kanpur', state: 'Uttar Pradesh', district: 'Kanpur Nagar', level: 'district', lat: 26.4499, lng: 80.3319 },
  { name: 'Varanasi', state: 'Uttar Pradesh', district: 'Varanasi', level: 'district', lat: 25.3176, lng: 82.9739 },
  { name: 'Agra', state: 'Uttar Pradesh', district: 'Agra', level: 'district', lat: 27.1767, lng: 78.0081 },
  { name: 'Noida', state: 'Uttar Pradesh', district: 'Gautam Buddha Nagar', level: 'city', lat: 28.5355, lng: 77.3910 },
  { name: 'Ghaziabad', state: 'Uttar Pradesh', district: 'Ghaziabad', level: 'district', lat: 28.6692, lng: 77.4538 },
  { name: 'Prayagraj', state: 'Uttar Pradesh', district: 'Prayagraj', level: 'district', lat: 25.4358, lng: 81.8463 },
  { name: 'Meerut', state: 'Uttar Pradesh', district: 'Meerut', level: 'district', lat: 28.9845, lng: 77.7064 },
  { name: 'Gorakhpur', state: 'Uttar Pradesh', district: 'Gorakhpur', level: 'district', lat: 26.7606, lng: 83.3732 },
  { name: 'Bareilly', state: 'Uttar Pradesh', district: 'Bareilly', level: 'district', lat: 28.3670, lng: 79.4304 },
  { name: 'Aligarh', state: 'Uttar Pradesh', district: 'Aligarh', level: 'district', lat: 27.8974, lng: 78.0880 },
  // Madhya Pradesh Centers
  { name: 'Bhopal', state: 'Madhya Pradesh', district: 'Bhopal', level: 'district', lat: 23.2599, lng: 77.4126 },
  { name: 'Indore', state: 'Madhya Pradesh', district: 'Indore', level: 'district', lat: 22.7196, lng: 75.8577 },
  { name: 'Gwalior', state: 'Madhya Pradesh', district: 'Gwalior', level: 'district', lat: 26.2183, lng: 78.1828 },
  { name: 'Jabalpur', state: 'Madhya Pradesh', district: 'Jabalpur', level: 'district', lat: 23.1815, lng: 79.9864 },
  { name: 'Ujjain', state: 'Madhya Pradesh', district: 'Ujjain', level: 'district', lat: 23.1765, lng: 75.7885 },
  // Bihar Centers
  { name: 'Patna', state: 'Bihar', district: 'Patna', level: 'district', lat: 25.5941, lng: 85.1376 },
  { name: 'Gaya', state: 'Bihar', district: 'Gaya', level: 'district', lat: 24.7914, lng: 85.0002 },
  { name: 'Bhagalpur', state: 'Bihar', district: 'Bhagalpur', level: 'district', lat: 25.2425, lng: 86.9842 },
  { name: 'Muzaffarpur', state: 'Bihar', district: 'Muzaffarpur', level: 'district', lat: 26.1209, lng: 85.3647 },
  // Odisha Centers
  { name: 'Bhubaneswar', state: 'Odisha', district: 'Khordha', level: 'city', lat: 20.2961, lng: 85.8245 },
  { name: 'Cuttack', state: 'Odisha', district: 'Cuttack', level: 'district', lat: 20.4625, lng: 85.8828 },
  { name: 'Puri', state: 'Odisha', district: 'Puri', level: 'district', lat: 19.8135, lng: 85.8312 },
  { name: 'Rourkela', state: 'Odisha', district: 'Sundargarh', level: 'city', lat: 22.2604, lng: 84.8536 },
  { name: 'Balasore', state: 'Odisha', district: 'Balasore', level: 'district', lat: 21.4934, lng: 86.9135 },
  { name: 'Sambalpur', state: 'Odisha', district: 'Sambalpur', level: 'district', lat: 21.4669, lng: 83.9812 },
  // Kerala Centers
  { name: 'Kochi', state: 'Kerala', district: 'Ernakulam', level: 'city', lat: 9.9312, lng: 76.2673 },
  { name: 'Thiruvananthapuram', state: 'Kerala', district: 'Thiruvananthapuram', level: 'district', lat: 8.5241, lng: 76.9366 },
  { name: 'Kozhikode', state: 'Kerala', district: 'Kozhikode', level: 'district', lat: 11.2588, lng: 75.7804 },
  { name: 'Thrissur', state: 'Kerala', district: 'Thrissur', level: 'district', lat: 10.5276, lng: 76.2144 },
  { name: 'Wayanad', state: 'Kerala', district: 'Wayanad', level: 'district', lat: 11.6854, lng: 76.1320 },
  { name: 'Idukki', state: 'Kerala', district: 'Idukki', level: 'district', lat: 9.8494, lng: 76.9810 },
  { name: 'Alappuzha', state: 'Kerala', district: 'Alappuzha', level: 'district', lat: 9.4981, lng: 76.3388 },
  // Andhra Pradesh Centers
  { name: 'Visakhapatnam', state: 'Andhra Pradesh', district: 'Visakhapatnam', level: 'district', lat: 17.6868, lng: 83.2185 },
  { name: 'Vijayawada', state: 'Andhra Pradesh', district: 'NTR', level: 'district', lat: 16.5062, lng: 80.6480 },
  { name: 'Guntur', state: 'Andhra Pradesh', district: 'Guntur', level: 'district', lat: 16.3067, lng: 80.4365 },
  { name: 'Tirupati', state: 'Andhra Pradesh', district: 'Tirupati', level: 'district', lat: 13.6288, lng: 79.4192 },
  { name: 'Kurnool', state: 'Andhra Pradesh', district: 'Kurnool', level: 'district', lat: 15.8281, lng: 78.0373 },
  // Uttarakhand Centers
  { name: 'Dehradun', state: 'Uttarakhand', district: 'Dehradun', level: 'district', lat: 30.3165, lng: 78.0322 },
  { name: 'Haridwar', state: 'Uttarakhand', district: 'Haridwar', level: 'district', lat: 29.9457, lng: 78.1642 },
  { name: 'Rishikesh', state: 'Uttarakhand', district: 'Dehradun', level: 'city', lat: 30.0869, lng: 78.2676 },
  { name: 'Nainital', state: 'Uttarakhand', district: 'Nainital', level: 'district', lat: 29.3919, lng: 79.4542 },
  { name: 'Chamoli', state: 'Uttarakhand', district: 'Chamoli', level: 'district', lat: 30.4000, lng: 79.3333 },
  { name: 'Uttarkashi', state: 'Uttarakhand', district: 'Uttarkashi', level: 'district', lat: 30.7300, lng: 78.4400 },
  // Himachal Pradesh Centers
  { name: 'Shimla', state: 'Himachal Pradesh', district: 'Shimla', level: 'district', lat: 31.1048, lng: 77.1734 },
  { name: 'Manali', state: 'Himachal Pradesh', district: 'Kullu', level: 'city', lat: 32.2432, lng: 77.1892 },
  { name: 'Dharamshala', state: 'Himachal Pradesh', district: 'Kangra', level: 'district', lat: 32.2190, lng: 76.3234 },
  { name: 'Kullu', state: 'Himachal Pradesh', district: 'Kullu', level: 'district', lat: 31.9579, lng: 77.1095 },
  { name: 'Mandi', state: 'Himachal Pradesh', district: 'Mandi', level: 'district', lat: 31.7087, lng: 76.9320 },
  // Jharkhand Centers
  { name: 'Ranchi', state: 'Jharkhand', district: 'Ranchi', level: 'district', lat: 23.3441, lng: 85.3096 },
  { name: 'Jamshedpur', state: 'Jharkhand', district: 'East Singhbhum', level: 'city', lat: 22.8046, lng: 86.2029 },
  { name: 'Dhanbad', state: 'Jharkhand', district: 'Dhanbad', level: 'district', lat: 23.7957, lng: 86.4304 },
  { name: 'Bokaro', state: 'Jharkhand', district: 'Bokaro', level: 'district', lat: 23.6693, lng: 86.1511 },
  // Chhattisgarh Centers
  { name: 'Raipur', state: 'Chhattisgarh', district: 'Raipur', level: 'district', lat: 21.2514, lng: 81.6296 },
  { name: 'Bilaspur', state: 'Chhattisgarh', district: 'Bilaspur', level: 'district', lat: 22.0797, lng: 82.1391 },
  { name: 'Durg-Bhilai', state: 'Chhattisgarh', district: 'Durg', level: 'district', lat: 21.1904, lng: 81.2849 },
  // Punjab & Haryana Centers
  { name: 'Ludhiana', state: 'Punjab', district: 'Ludhiana', level: 'district', lat: 30.9010, lng: 75.8573 },
  { name: 'Amritsar', state: 'Punjab', district: 'Amritsar', level: 'district', lat: 31.6340, lng: 74.8723 },
  { name: 'Jalandhar', state: 'Punjab', district: 'Jalandhar', level: 'district', lat: 31.3260, lng: 75.5762 },
  { name: 'Patiala', state: 'Punjab', district: 'Patiala', level: 'district', lat: 30.3398, lng: 76.3869 },
  { name: 'Chandigarh', state: 'Chandigarh', district: 'Chandigarh', level: 'city', lat: 30.7333, lng: 76.7794 },
  { name: 'Gurugram', state: 'Haryana', district: 'Gurugram', level: 'district', lat: 28.4595, lng: 77.0266 },
  { name: 'Faridabad', state: 'Haryana', district: 'Faridabad', level: 'district', lat: 28.4089, lng: 77.3178 },
  { name: 'Panipat', state: 'Haryana', district: 'Panipat', level: 'district', lat: 29.3909, lng: 76.9635 },
  // Jammu & Kashmir & Ladakh
  { name: 'Srinagar', state: 'Jammu and Kashmir', district: 'Srinagar', level: 'district', lat: 34.0837, lng: 74.7973 },
  { name: 'Jammu', state: 'Jammu and Kashmir', district: 'Jammu', level: 'district', lat: 32.7266, lng: 74.8570 },
  { name: 'Anantnag', state: 'Jammu and Kashmir', district: 'Anantnag', level: 'district', lat: 33.7311, lng: 75.1522 },
  { name: 'Baramulla', state: 'Jammu and Kashmir', district: 'Baramulla', level: 'district', lat: 34.2000, lng: 74.3400 },
  { name: 'Leh', state: 'Ladakh', district: 'Leh', level: 'district', lat: 34.1526, lng: 77.5771 },
  { name: 'Kargil', state: 'Ladakh', district: 'Kargil', level: 'district', lat: 34.5539, lng: 76.1349 },
  // Northeast States Centers
  { name: 'Gangtok', state: 'Sikkim', district: 'East Sikkim', level: 'district', lat: 27.3389, lng: 88.6065 },
  { name: 'Shillong', state: 'Meghalaya', district: 'East Khasi Hills', level: 'district', lat: 25.5788, lng: 91.8933 },
  { name: 'Cherrapunji', state: 'Meghalaya', district: 'East Khasi Hills', level: 'city', lat: 25.2986, lng: 91.7324 },
  { name: 'Imphal', state: 'Manipur', district: 'Imphal West', level: 'district', lat: 24.8170, lng: 93.9368 },
  { name: 'Aizawl', state: 'Mizoram', district: 'Aizawl', level: 'district', lat: 23.7271, lng: 92.7176 },
  { name: 'Kohima', state: 'Nagaland', district: 'Kohima', level: 'district', lat: 25.6751, lng: 94.1086 },
  { name: 'Dimapur', state: 'Nagaland', district: 'Dimapur', level: 'district', lat: 25.9068, lng: 93.7273 },
  { name: 'Agartala', state: 'Tripura', district: 'West Tripura', level: 'district', lat: 23.8315, lng: 91.2868 },
  { name: 'Itanagar', state: 'Arunachal Pradesh', district: 'Papum Pare', level: 'district', lat: 27.0844, lng: 93.6053 },
  // Goa & UTs
  { name: 'Panaji', state: 'Goa', district: 'North Goa', level: 'city', lat: 15.4909, lng: 73.8278 },
  { name: 'Margao', state: 'Goa', district: 'South Goa', level: 'city', lat: 15.2832, lng: 73.9862 },
  { name: 'Puducherry', state: 'Puducherry', district: 'Puducherry', level: 'city', lat: 11.9416, lng: 79.8083 },
  { name: 'Port Blair', state: 'Andaman and Nicobar Islands', district: 'South Andaman', level: 'city', lat: 11.6234, lng: 92.7265 },
];

/**
 * Searches the hierarchical database across Country, States, Districts, and Cities.
 */
export function findMatchingAreas(query) {
  if (!query || !query.trim()) {
    // Return Country + top states + top cities
    return [
      COUNTRY_OPTION,
      ...INDIAN_STATES_DATABASE.slice(0, 6),
      ...INDIAN_CITIES_DATABASE.slice(0, 10),
    ];
  }

  const q = query.toLowerCase().trim();
  const results = [];

  // Match Country
  if ('all india'.includes(q) || 'india'.includes(q) || 'country'.includes(q)) {
    results.push(COUNTRY_OPTION);
  }

  // Match States
  const matchedStates = INDIAN_STATES_DATABASE.filter(
    (s) => s.name.toLowerCase().includes(q) || s.state.toLowerCase().includes(q)
  );
  results.push(...matchedStates);

  // Match Cities / Districts
  const matchedCities = INDIAN_CITIES_DATABASE.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.state.toLowerCase().includes(q) ||
      (c.district && c.district.toLowerCase().includes(q))
  );
  results.push(...matchedCities);

  return results.slice(0, 25);
}

// Backwards compatibility alias
export const findMatchingCities = findMatchingAreas;

/**
 * Resolves an area name to coordinates and metadata.
 */
export function resolveAreaCoordinates(areaName) {
  if (!areaName) return null;
  const q = areaName.toLowerCase().trim();

  if (q === 'all india' || q === 'india') {
    return { ...COUNTRY_OPTION };
  }

  // Check state match
  const stateMatch = INDIAN_STATES_DATABASE.find(
    (s) => s.name.toLowerCase() === q
  );
  if (stateMatch) {
    return {
      name: stateMatch.name,
      level: 'state',
      state: stateMatch.name,
      district: null,
      lat: stateMatch.lat,
      lng: stateMatch.lng,
    };
  }

  // Check city exact match
  const cityMatch = INDIAN_CITIES_DATABASE.find(
    (c) => c.name.toLowerCase() === q || `${c.name}, ${c.state}`.toLowerCase() === q
  );
  if (cityMatch) {
    return {
      name: `${cityMatch.name}, ${cityMatch.state}`,
      level: cityMatch.level || 'district',
      state: cityMatch.state,
      district: cityMatch.district || cityMatch.name,
      lat: cityMatch.lat,
      lng: cityMatch.lng,
    };
  }

  // Check city partial match
  const partialCity = INDIAN_CITIES_DATABASE.find(
    (c) => c.name.toLowerCase().includes(q) || q.includes(c.name.toLowerCase())
  );
  if (partialCity) {
    return {
      name: `${partialCity.name}, ${partialCity.state}`,
      level: partialCity.level || 'district',
      state: partialCity.state,
      district: partialCity.district || partialCity.name,
      lat: partialCity.lat,
      lng: partialCity.lng,
    };
  }

  return null;
}

export const resolveCityCoordinates = resolveAreaCoordinates;

export const CitySelector = ({
  value,
  onSelectCity,
  placeholder = 'Search Country, State, District, or City...',
  showCountryOption = true,
}) => {
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

  const matches = useMemo(() => findMatchingAreas(search), [search]);

  const handleSelect = (item) => {
    const isCountry = item.level === 'country' || item.name === 'All India';
    const isState = item.level === 'state';

    const displayName = isCountry
      ? 'All India'
      : isState
      ? item.name
      : `${item.name}, ${item.state}`;

    setSearch(displayName);
    setIsOpen(false);

    onSelectCity({
      name: displayName,
      level: item.level || (isCountry ? 'country' : isState ? 'state' : 'district'),
      state: isCountry ? null : item.state || (isState ? item.name : null),
      district: isCountry || isState ? null : (item.district || item.name),
      lat: item.lat,
      lng: item.lng,
      isGps: false,
      unresolved: false,
    });
  };

  const handleCustomSubmit = () => {
    if (!search.trim()) return;
    const resolved = resolveAreaCoordinates(search);
    if (resolved) {
      onSelectCity({
        ...resolved,
        isGps: false,
        unresolved: false,
      });
      setSearch(resolved.name);
    } else {
      // User entered an area not in the offline database
      onSelectCity({
        name: search.trim(),
        level: 'custom',
        state: search.trim(),
        district: search.trim(),
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
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl z-50 max-h-72 overflow-y-auto divide-y divide-slate-100 animate-in fade-in zoom-in-95 duration-150">
          {matches.length > 0 ? (
            matches.map((item, idx) => {
              const isCountry = item.level === 'country' || item.name === 'All India';
              const isState = item.level === 'state';

              return (
                <button
                  key={`${item.name}-${item.state || 'all'}-${idx}`}
                  type="button"
                  onClick={() => handleSelect(item)}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-orange-50/70 transition-colors flex items-center justify-between text-xs cursor-pointer group"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isCountry ? (
                      <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                    ) : isState ? (
                      <Layers className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    ) : (
                      <MapPin className="w-3.5 h-3.5 text-slate-400 group-hover:text-orange-500 shrink-0" />
                    )}

                    <span className="font-bold text-slate-800 truncate">{item.name}</span>

                    {item.state && !isState && (
                      <span className="text-slate-400 shrink-0">({item.state})</span>
                    )}

                    {/* Level Pill */}
                    <span
                      className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded shrink-0 ${
                        isCountry
                          ? 'bg-blue-100 text-blue-800 border border-blue-200'
                          : isState
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {isCountry ? 'Nation' : isState ? 'State' : item.level === 'district' ? 'District' : 'City'}
                    </span>
                  </div>

                  {item.lat != null && item.lng != null && (
                    <span className="text-[10px] font-mono text-slate-400 group-hover:text-orange-600 shrink-0 ml-2">
                      {item.lat.toFixed(2)}°N, {item.lng.toFixed(2)}°E
                    </span>
                  )}
                </button>
              );
            })
          ) : (
            <div className="p-3 text-center space-y-2">
              <p className="text-xs text-slate-500">No pre-indexed area matches "{search}".</p>
              <button
                type="button"
                onClick={handleCustomSubmit}
                className="w-full py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
              >
                Filter by Area Name: "{search}"
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
