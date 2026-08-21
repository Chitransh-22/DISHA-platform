/**
 * DISHA Platform - Centralized Disaster Event & Hazard Configuration
 * 
 * Single Source of Truth for:
 * 1. Hazard Categories, Slugs, Labels, Colors, and Distinct Icons
 * 2. Case normalization & alias resolution (e.g. 'eq', 'seismic' -> 'Earthquake')
 * 3. Official Disaster Safety Guidance (DOs and DON'Ts)
 */

export const EVENT_CONFIG = {
  Earthquake: {
    id: 'earthquake',
    label: 'Earthquake',
    icon: '📉', // Seismic tremor / faultline vibration
    symbol: 'seismic',
    color: '#ef4444',
    bg: 'bg-red-500',
    border: 'border-red-500',
    lightBg: 'bg-red-50 text-red-700 border-red-200',
    badge: 'bg-red-50 text-red-700 border-red-200',
    aliases: ['earthquake', 'eq', 'seismic', 'tremor', 'earth quake', 'temblor', 'aftershock'],
    dos: [
      'Drop, Cover, and Hold On under a sturdy desk or table.',
      'Stay away from glass windows, mirrors, exterior walls, and heavy light fixtures.',
      'If outdoors, move to an open area away from buildings, power lines, and trees.',
      'If in a moving vehicle, stop safely away from overpasses and stay inside until shaking stops.',
    ],
    donts: [
      'Do NOT use elevators during or immediately after an earthquake.',
      'Do NOT run outside while building structures are actively shaking.',
      'Do NOT light matches, lighters, or operate electrical switches if gas leaks are suspected.',
      'Do NOT stand in doorways or near tall unanchored furniture.',
    ],
  },
  Flood: {
    id: 'flood',
    label: 'Flood',
    icon: '🌊',
    symbol: 'waves',
    color: '#0284c7',
    bg: 'bg-sky-600',
    border: 'border-sky-600',
    lightBg: 'bg-sky-50 text-sky-700 border-sky-200',
    badge: 'bg-sky-50 text-sky-700 border-sky-200',
    aliases: ['flood', 'inundation', 'flash_flood', 'flash flood', 'waterlogging', 'overflow'],
    dos: [
      'Move immediately to higher ground or upper floors of stable buildings.',
      'Follow official evacuation orders and route advisories from NDRF/SDMA.',
      'Turn off main power switches and gas valves before evacuating.',
      'Keep emergency survival kits, dry food, clean drinking water, and medications ready.',
    ],
    donts: [
      'Do NOT walk, swim, or drive through moving floodwaters (6 inches of moving water can knock you down).',
      'Do NOT touch electrical equipment or wires if you are wet or standing in water.',
      'Do NOT eat food or drink tap water that has come into contact with floodwater.',
      'Do NOT ignore official evacuation notices or barricades.',
    ],
  },
  'Heavy Rain': {
    id: 'heavy_rain',
    label: 'Heavy Rain',
    icon: '🌧️',
    symbol: 'cloud-rain',
    color: '#3b82f6',
    bg: 'bg-blue-500',
    border: 'border-blue-500',
    lightBg: 'bg-blue-50 text-blue-700 border-blue-200',
    badge: 'bg-blue-50 text-blue-700 border-blue-200',
    aliases: ['heavy_rain', 'heavy rain', 'rain', 'downpour', 'thunderstorm', 'very heavy rain', 'incessant rain'],
    dos: [
      'Stay indoors and monitor local IMD weather bulletins.',
      'Keep drainage outlets around your home clear of debris.',
      'Check tires, wipers, and brakes before essential travel; drive at reduced speeds.',
      'Charge mobile phones and power banks in advance of potential outages.',
    ],
    donts: [
      'Do NOT venture near open drains, culverts, or waterlogged subways.',
      'Do NOT park vehicles under dilapidated structures or large trees.',
      'Do NOT wade through stagnated water pools where electric cables may be submerged.',
      'Do NOT spread unverified social media weather rumors.',
    ],
  },
  Landslide: {
    id: 'landslide',
    label: 'Landslide',
    icon: '⛰️',
    symbol: 'mountain',
    color: '#a855f7',
    bg: 'bg-purple-500',
    border: 'border-purple-500',
    lightBg: 'bg-purple-50 text-purple-700 border-purple-200',
    badge: 'bg-purple-50 text-purple-700 border-purple-200',
    aliases: ['landslide', 'mudslide', 'rockslide', 'debris_flow', 'slope_failure', 'hill_collapse'],
    dos: [
      'Evacuate immediately if you notice unusual sounds like trees cracking or boulders knocking.',
      'Stay alert for sudden increases or decreases in water flow in local mountain streams.',
      'Move away from the path of a landslide or debris flow to stable high ground.',
      'Report broken utility lines and damaged road sections to local authorities.',
    ],
    donts: [
      'Do NOT stay in low-lying mountain valleys or direct slope runout zones during heavy rains.',
      'Do NOT cross fresh landslide debris paths until certified safe by Border Roads / PWD.',
      'Do NOT build or sleep in rooms directly adjacent to steep unsupported slopes.',
      'Do NOT ignore landslide warning sirens or evacuation orders.',
    ],
  },
  Lightning: {
    id: 'lightning',
    label: 'Lightning',
    icon: '⚡',
    symbol: 'zap',
    color: '#eab308',
    bg: 'bg-yellow-500',
    border: 'border-yellow-500',
    lightBg: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    badge: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    aliases: ['lightning', 'thunderbolt', 'cloud_to_ground', 'electrical_storm'],
    dos: [
      'Seek shelter inside a substantial, enclosed building or metal-topped vehicle immediately.',
      'Follow the 30-30 Rule: If time between lightning flash and thunder is < 30 seconds, take shelter.',
      'Unplug sensitive electronics and appliances before storms begin.',
      'Stay inside for at least 30 minutes after the last clap of thunder.',
    ],
    donts: [
      'Do NOT take shelter under tall, isolated trees or open sheds in fields.',
      'Do NOT stay in open fields, hilltops, rooftops, or bodies of water.',
      'Do NOT hold metal objects like umbrellas with metal tips, farming tools, or fishing rods.',
      'Do NOT use corded phones, take showers, or wash dishes during a thunderstorm.',
    ],
  },
  Cyclone: {
    id: 'cyclone',
    label: 'Cyclone',
    icon: '🌀',
    symbol: 'wind',
    color: '#10b981',
    bg: 'bg-emerald-500',
    border: 'border-emerald-500',
    lightBg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    aliases: ['cyclone', 'storm', 'hurricane', 'typhoon', 'squall', 'gale', 'deep_depression'],
    dos: [
      'Board up glass windows or put storm shutters in place; secure loose outdoor items.',
      'Evacuate immediately to designated pucca cyclone shelters if advised by authorities.',
      'Keep an emergency bag with documents in waterproof bags, torches, batteries, and first-aid.',
      'Anchor small boats and marine vessels safely away from the surf zone.',
    ],
    donts: [
      'Do NOT venture out to sea or stay in kutchha thatched houses during cyclone landfall.',
      'Do NOT go outside when the "eye" (calm center) passes over—fierce winds resume suddenly.',
      'Do NOT touch fallen electric poles, dangling wires, or sharp metal debris.',
      'Do NOT enter damaged buildings until structural integrity is verified.',
    ],
  },
  Fire: {
    id: 'fire',
    label: 'Fire',
    icon: '🔥',
    symbol: 'flame',
    color: '#f97316',
    bg: 'bg-orange-500',
    border: 'border-orange-500',
    lightBg: 'bg-orange-50 text-orange-700 border-orange-200',
    badge: 'bg-orange-50 text-orange-700 border-orange-200',
    aliases: ['fire', 'fire_accident', 'wildfire', 'forest_fire', 'blaze', 'inferno', 'factory_fire'],
    dos: [
      'Crawl low under smoke toward the nearest marked emergency fire exit.',
      'Feel closed doors with the back of your hand before opening—if hot, use an alternate exit.',
      'Call National Emergency Services (112 / 101) immediately with exact location details.',
      'If clothing catches fire: STOP, DROP, and ROLL until flames are extinguished.',
    ],
    donts: [
      'Do NOT use elevators in a burning building; always use fire exit stairwells.',
      'Do NOT re-enter a burning building to retrieve belongings or pets.',
      'Do NOT throw water on electrical fires or grease/oil fires.',
      'Do NOT inhale heavy smoke—cover your mouth and nose with a damp cloth.',
    ],
  },
  Cloudburst: {
    id: 'cloudburst',
    label: 'Cloudburst',
    icon: '⛈️',
    symbol: 'cloud-lightning',
    color: '#06b6d4',
    bg: 'bg-cyan-500',
    border: 'border-cyan-500',
    lightBg: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    badge: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    aliases: ['cloudburst', 'torrential_burst', 'intense_precipitation'],
    dos: [
      'Move uphill immediately away from mountain streams and natural drainage gorges.',
      'Alert neighbors in downstream areas using whistles or sirens if flash flooding begins.',
      'Stay away from culverts and temporary mountain road bridges.',
      'Keep emergency communication radios tuned to SDRF emergency frequencies.',
    ],
    donts: [
      'Do NOT camp, park vehicles, or build structures in dry mountain riverbeds.',
      'Do NOT attempt to drive vehicles through surging mud and debris flows.',
      'Do NOT delay evacuation to collect non-essential personal items.',
      'Do NOT cross flooded footbridges under torrential flow.',
    ],
  },
  'Building Collapse': {
    id: 'building_collapse',
    label: 'Building Collapse',
    icon: '🏚️',
    symbol: 'building',
    color: '#e11d48',
    bg: 'bg-rose-600',
    border: 'border-rose-600',
    lightBg: 'bg-rose-50 text-rose-700 border-rose-200',
    badge: 'bg-rose-50 text-rose-700 border-rose-200',
    aliases: ['building_collapse', 'structure_collapse', 'tunnel_collapse', 'bridge_collapse', 'roof_collapse'],
    dos: [
      'If trapped under debris, cover your mouth with a cloth to protect your lungs from dust.',
      'Tap on a pipe, wall, or whistle so rescuers can locate you acoustically.',
      'Shout only as a last resort to prevent inhaling dangerous quantities of dust.',
      'Keep calm and conserve energy and oxygen while awaiting NDRF rescue teams.',
    ],
    donts: [
      'Do NOT light matches or lighters due to possible ruptured gas lines in rubble.',
      'Do NOT make unnecessary movements that could trigger further debris shifting.',
      'Do NOT crowd rescue zones; keep access roads clear for emergency heavy machinery.',
      'Do NOT enter partially collapsed adjacent structures.',
    ],
  },
  'Industrial Accident': {
    id: 'industrial_accident',
    label: 'Industrial Accident',
    icon: '⚠️',
    symbol: 'alert-triangle',
    color: '#d97706',
    bg: 'bg-amber-600',
    border: 'border-amber-600',
    lightBg: 'bg-amber-50 text-amber-700 border-amber-200',
    badge: 'bg-amber-50 text-amber-700 border-amber-200',
    aliases: ['industrial_accident', 'gas_leak', 'chemical_spill', 'toxic_leak', 'boiler_blast'],
    dos: [
      'Evacuate crosswind or upwind away from the direction of chemical or gas plume movement.',
      'Cover nose and mouth with a wet handkerchief or mask to filter airborne particles.',
      'Close and seal all windows and doors with wet towels if sheltering in place is advised.',
      'Seek medical evaluation immediately if experiencing eye burning, nausea, or breathing issues.',
    ],
    donts: [
      'Do NOT light open flames or operate electrical switches near potential gas leaks.',
      'Do NOT touch spilled unidentified chemicals, liquids, or leaking containers.',
      'Do NOT travel downwind of an active chemical vapor release.',
      'Do NOT consume uncovered food or open water in affected industrial zones.',
    ],
  },
  Explosion: {
    id: 'explosion',
    label: 'Explosion',
    icon: '💥',
    symbol: 'bomb',
    color: '#dc2626',
    bg: 'bg-red-600',
    border: 'border-red-600',
    lightBg: 'bg-red-50 text-red-700 border-red-200',
    badge: 'bg-red-50 text-red-700 border-red-200',
    aliases: ['explosion', 'blast', 'detonation', 'cylinder_blast'],
    dos: [
      'Take cover under a sturdy table or desk to protect against falling glass and debris.',
      'Evacuate the area quickly and check for secondary hazard devices or compromised structures.',
      'Help injured individuals if you can do so without placing yourself in immediate danger.',
      'Cooperate fully with police, bomb disposal, and forensic investigation units.',
    ],
    donts: [
      'Do NOT touch suspicious bags, wires, or unattended packages near the blast site.',
      'Do NOT use elevators during evacuation from damaged multi-story buildings.',
      'Do NOT crowd incident perimeters; keep emergency ambulance routes clear.',
      'Do NOT stand near large glass facades or window panes.',
    ],
  },
  Heatwave: {
    id: 'heatwave',
    label: 'Heatwave',
    icon: '🌡️',
    symbol: 'sun',
    color: '#ea580c',
    bg: 'bg-orange-600',
    border: 'border-orange-600',
    lightBg: 'bg-orange-50 text-orange-700 border-orange-200',
    badge: 'bg-orange-50 text-orange-700 border-orange-200',
    aliases: ['heatwave', 'heat_wave', 'severe_heat', 'loo', 'extreme_temperature'],
    dos: [
      'Drink plenty of water, ORS, lassi, lemon water, or coconut water frequently even if not thirsty.',
      'Wear lightweight, loose-fitting, light-colored cotton clothing.',
      'Cover your head with a cloth, hat, or umbrella when stepping outdoors.',
      'Keep pets in shaded areas with access to plenty of fresh water.',
    ],
    donts: [
      'Do NOT go out in direct sunlight between 12:00 PM and 3:30 PM.',
      'Do NOT leave children or pets inside parked vehicles even for a few minutes.',
      'Do NOT consume alcohol, tea, coffee, or carbonated soft drinks which dehydrate the body.',
      'Do NOT engage in strenuous outdoor labor during peak afternoon heat.',
    ],
  },
  Other: {
    id: 'other',
    label: 'Advisory / Other',
    icon: '📢',
    symbol: 'shield-alert',
    color: '#64748b',
    bg: 'bg-slate-500',
    border: 'border-slate-500',
    lightBg: 'bg-slate-50 text-slate-700 border-slate-200',
    badge: 'bg-slate-50 text-slate-700 border-slate-200',
    aliases: ['other', 'advisory', 'sdma_alert', 'bulletin', 'general_alert', 'hazard'],
    dos: [
      'Monitor official DISHA, NDMA, and State Disaster Management Authority alerts.',
      'Maintain an updated family emergency contact list and first-aid kit.',
      'Follow localized advisories issued by district administration and emergency responders.',
    ],
    donts: [
      'Do NOT spread unverified rumors or panicked messages on social networks.',
      'Do NOT ignore official emergency warnings or public address announcements.',
    ],
  },
};

/**
 * Normalizes raw category/disaster_type strings into standardized event configuration.
 * Performs lowercase, trimming, punctuation removal, and alias lookup.
 */
export function getCategoryConfig(rawCategory) {
  if (!rawCategory) return EVENT_CONFIG.Other;

  const normalized = String(rawCategory)
    .trim()
    .toLowerCase()
    .replace(/[-–—]/g, '_')
    .replace(/\s+/g, '_');

  // Direct key lookup
  for (const [key, config] of Object.entries(EVENT_CONFIG)) {
    if (key.toLowerCase() === normalized || config.id === normalized) {
      return config;
    }
  }

  // Alias lookup
  for (const config of Object.values(EVENT_CONFIG)) {
    if (config.aliases.some((alias) => normalized.includes(alias) || alias.includes(normalized))) {
      return config;
    }
  }

  // Partial keyword matching
  if (normalized.includes('earthquake') || normalized.includes('seismic') || normalized.includes('tremor')) {
    return EVENT_CONFIG.Earthquake;
  }
  if (normalized.includes('flood') || normalized.includes('inundat')) {
    return EVENT_CONFIG.Flood;
  }
  if (normalized.includes('rain') || normalized.includes('downpour') || normalized.includes('storm')) {
    return EVENT_CONFIG['Heavy Rain'];
  }
  if (normalized.includes('landslide') || normalized.includes('mudslide') || normalized.includes('rockslide')) {
    return EVENT_CONFIG.Landslide;
  }
  if (normalized.includes('lightning') || normalized.includes('thunder')) {
    return EVENT_CONFIG.Lightning;
  }
  if (normalized.includes('cyclone') || normalized.includes('typhoon') || normalized.includes('hurricane')) {
    return EVENT_CONFIG.Cyclone;
  }
  if (normalized.includes('fire') || normalized.includes('blaze')) {
    return EVENT_CONFIG.Fire;
  }
  if (normalized.includes('cloudburst')) {
    return EVENT_CONFIG.Cloudburst;
  }
  if (normalized.includes('collapse')) {
    return EVENT_CONFIG['Building Collapse'];
  }
  if (normalized.includes('industrial') || normalized.includes('chemical') || normalized.includes('gas_leak')) {
    return EVENT_CONFIG['Industrial Accident'];
  }
  if (normalized.includes('explosion') || normalized.includes('blast')) {
    return EVENT_CONFIG.Explosion;
  }
  if (normalized.includes('heat')) {
    return EVENT_CONFIG.Heatwave;
  }

  return EVENT_CONFIG.Other;
}

/**
 * Standardizes severity into color badges.
 */
export const SEVERITY_CONFIG = {
  Critical: {
    label: 'Critical',
    bg: 'bg-red-600',
    badge: 'bg-red-600 text-white border-red-600',
    lightBadge: 'bg-red-50 text-red-700 border-red-200',
    color: '#dc2626',
  },
  Severe: {
    label: 'Severe',
    bg: 'bg-orange-500',
    badge: 'bg-orange-500 text-white border-orange-500',
    lightBadge: 'bg-orange-50 text-orange-700 border-orange-200',
    color: '#ea580c',
  },
  Moderate: {
    label: 'Moderate',
    bg: 'bg-amber-500',
    badge: 'bg-amber-500 text-white border-amber-500',
    lightBadge: 'bg-amber-50 text-amber-700 border-amber-200',
    color: '#f59e0b',
  },
  Low: {
    label: 'Low',
    bg: 'bg-emerald-600',
    badge: 'bg-emerald-600 text-white border-emerald-600',
    lightBadge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    color: '#059669',
  },
};
