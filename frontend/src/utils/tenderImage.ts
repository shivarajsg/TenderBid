export type TenderCategoryKey =
  | 'automotive-machinery'
  | 'medical-biomedical'
  | 'laboratory-furniture'
  | 'computers-electronics'
  | 'solar-electrical'
  | 'construction-infrastructure'
  | 'cleaning-housekeeping'
  | 'vehicles-transportation'
  | 'industrial-tools'
  | 'agriculture-food'
  | 'office-stationery'
  | 'logistics-maintenance'
  | 'professional-training'
  | 'general-procurement';

const CATEGORY_MAP: Array<{ key: TenderCategoryKey; keywords: string[] }> = [
  {
    key: 'automotive-machinery',
    keywords: ['wheel', 'hub', 'brake', 'axle', 'engine', 'transmission', 'tatra', 'beml', 'chassis', 'bearing', 'machinery', 'automotive', 'motor', 'clutch', 'radiator', 'suspension'],
  },
  {
    key: 'medical-biomedical',
    keywords: ['medical', 'ultrasound', 'biomedical', 'patient', 'diagnostic', 'hospital', 'cardiac', 'surgical', 'ventilator', 'ecg', 'gloves', 'urine', 'mask', 'stethoscope', 'pharma', 'medicines', 'oxygen'],
  },
  {
    key: 'laboratory-furniture',
    keywords: ['laboratory', 'workbench', 'cleanroom', 'centrifuge', 'balance', 'pipette', 'fume hood', 'spectrophotometer', 'microscope', 'incubator', 'autoclave', 'lab equipment'],
  },
  {
    key: 'computers-electronics',
    keywords: ['laptop', 'computer', 'server', 'iot', 'gateway', 'processor', 'desktop', 'cctv', 'camera', 'microcontroller', 'switch', 'router', 'networking', 'workstation', 'ups', 'monitor', 'display'],
  },
  {
    key: 'solar-electrical',
    keywords: ['solar', 'photovoltaic', 'switchgear', 'transformer', 'inverter', 'substation', 'generator', 'rectifier', 'battery', 'cable', 'electrical', 'high-voltage', 'lighting', 'street light'],
  },
  {
    key: 'construction-infrastructure',
    keywords: ['construction', 'excavator', 'crane', 'infrastructure', 'civil', 'bridge', 'road', 'cement', 'concrete', 'steel', 'scaffolding', 'building', 'earthmoving', 'pipe', 'pipeline'],
  },
  {
    key: 'cleaning-housekeeping',
    keywords: ['cleaning', 'housekeeping', 'scrubber', 'sweeper', 'sanitation', 'waste', 'janitorial', 'disinfectant', 'vacuum', 'polythe'],
  },
  {
    key: 'vehicles-transportation',
    keywords: ['truck', 'vehicle', 'bus', 'transportation', 'ambulance', 'car', 'fleet', 'trailer', 'railway', 'wagon', 'locomotive'],
  },
  {
    key: 'industrial-tools',
    keywords: ['lathe', 'cnc', 'tool', 'milling', 'drilling', 'welding', 'micrometer', 'caliper', 'abrasive', 'cutting tool', 'grinding', 'workshop'],
  },
  {
    key: 'agriculture-food',
    keywords: ['agriculture', 'meat', 'grain', 'cold storage', 'harvest', 'fertilizer', 'food', 'dairy', 'irrigation', 'poultry'],
  },
  {
    key: 'office-stationery',
    keywords: ['office', 'furniture', 'printer', 'copier', 'stationery', 'paper', 'chair', 'desk', 'filing', 'cabin'],
  },
  {
    key: 'logistics-maintenance',
    keywords: ['logistics', 'maintenance', 'forklift', 'overhaul', 'repair', 'pallet', 'warehouse', 'depot', 'handling'],
  },
  {
    key: 'professional-training',
    keywords: ['training', 'education', 'course', 'symposium', 'workshop', 'consultancy', 'instructor', 'teaching'],
  },
];

/**
 * Determine best matching category key from tender title and sector.
 * Title takes precedence over generic sector.
 */
export function getTenderCategoryKey(title: string, sector?: string | null): TenderCategoryKey {
  const titleLower = (title || '').toLowerCase();
  const sectorLower = (sector || '').toLowerCase();

  // Priority 1: Check title
  for (const item of CATEGORY_MAP) {
    if (item.keywords.some((kw) => new RegExp(`\\b${kw}(?:s|es|ing)?\\b`, 'i').test(titleLower))) {
      return item.key;
    }
  }

  // Priority 2: Check sector
  if (sectorLower) {
    for (const item of CATEGORY_MAP) {
      if (item.keywords.some((kw) => new RegExp(`\\b${kw}(?:s|es|ing)?\\b`, 'i').test(sectorLower))) {
        return item.key;
      }
    }
  }

  return 'general-procurement';
}

/**
 * Return human-readable category title
 */
export function getCategoryDisplayName(key: TenderCategoryKey): string {
  switch (key) {
    case 'automotive-machinery':
      return 'Automotive & Industrial Machinery';
    case 'medical-biomedical':
      return 'Medical & Biomedical Equipment';
    case 'laboratory-furniture':
      return 'Laboratory Equipment & Furniture';
    case 'computers-electronics':
      return 'Computers & Electronics';
    case 'solar-electrical':
      return 'Solar & Electrical Equipment';
    case 'construction-infrastructure':
      return 'Construction & Infrastructure';
    case 'cleaning-housekeeping':
      return 'Cleaning & Housekeeping Equipment';
    case 'vehicles-transportation':
      return 'Vehicles & Transportation Fleet';
    case 'industrial-tools':
      return 'Industrial Tools & Metrology';
    case 'agriculture-food':
      return 'Agriculture & Food Supplies';
    case 'office-stationery':
      return 'Office Furniture & Stationery';
    case 'logistics-maintenance':
      return 'Logistics & Maintenance Services';
    case 'professional-training':
      return 'Professional Training Services';
    default:
      return 'Public Procurement & Supplies';
  }
}

/**
 * Get primary image URL for tender
 */
export function getTenderImageUrl(title: string, sector?: string | null, customImageUrl?: string | null): string {
  if (customImageUrl && customImageUrl.trim().length > 0) {
    return customImageUrl;
  }
  const categoryKey = getTenderCategoryKey(title, sector);
  return `/images/tender-categories/${categoryKey}.svg`;
}
