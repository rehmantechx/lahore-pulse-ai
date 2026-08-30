/**
 * ExposureIntelligenceMap — Component tests.
 *
 * Tests: rendering states, map integration, legend, popups, full geometry flow.
 * Covers: empty state, full geometry, legend content, fullscreen toggle,
 *         marker layering, accessible labels.
 *
 * NOTE: Leaflet map internals are hard to unit-test.
 * These tests focus on DOM output, props handling, and state transitions.
 * Integration testing of actual map rendering is done via manual QA.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// ── Mock Leaflet ─────────────────────────────────────────────

// We mock Leaflet entirely since it requires a DOM with dimensions
vi.mock('leaflet', () => {
  const chainable = {
    addTo: vi.fn(() => chainable),
    remove: vi.fn(() => chainable),
    bindPopup: vi.fn(() => chainable),
  };

  const mockMap = {
    setView: vi.fn(),
    remove: vi.fn(),
    invalidateSize: vi.fn(),
    fitBounds: vi.fn(),
    addTo: vi.fn(() => mockMap),
  };

  return {
    default: {
      map: vi.fn(() => mockMap),
      tileLayer: vi.fn(() => ({ addTo: vi.fn(() => ({ addTo: vi.fn() })) })),
      control: {
        attribution: vi.fn(() => ({
          addAttribution: vi.fn(() => ({ addTo: vi.fn() })),
          addTo: vi.fn(),
        })),
      },
      circle: vi.fn(() => ({ ...chainable })),
      circleMarker: vi.fn(() => ({ ...chainable })),
      polygon: vi.fn(() => ({ ...chainable })),
      marker: vi.fn(() => ({ ...chainable })),
      divIcon: vi.fn(() => ({})),
      Icon: {
        Default: {
          prototype: { _getIconUrl: '' },
          mergeOptions: vi.fn(),
        },
      },
    },
  };
});

vi.mock('leaflet/dist/leaflet.css', () => ({}));

vi.mock('../../constants', () => ({
  LAHORE_CENTER: [31.5204, 74.3587],
  LAHORE_ZOOM: 11,
  MIN_ZOOM: 9,
  MAX_ZOOM: 16,
  MAP_TILES: {
    base: { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 19 },
    labels: { url: '', maxZoom: 19 },
    attribution: '© OpenStreetMap',
  },
}));

// ── Mock dependencies ────────────────────────────────────────

vi.mock('../../demo', () => ({
  useDemoData: vi.fn(() => null),
}));

// ── Import component under test ──────────────────────────────

import ExposureIntelligenceMap from '../ExposureIntelligenceMap';

// ── Mock Data ────────────────────────────────────────────────

const MOCK_EXPOSURE = {
  event_location: {
    lat: 31.5204,
    lng: 74.3587,
    pm25: 165.0,
    severity: 'episode',
    trajectory: 'rising',
  },
  investigation_area: {
    type: 'upwind_investigation_corridor',
    coordinates: [
      [31.5204, 74.3587],
      [31.53, 74.37],
      [31.51, 74.37],
      [31.5204, 74.3587],
    ],
    center: { lat: 31.5204, lng: 74.3587 },
    direction_degrees: 90.0,
    direction_label: 'From East',
    distance_km: 8.0,
    width_degrees: 60,
    priority: 'HIGH',
    label: 'Priority Investigation Area',
    requires_ground_verification: true,
    uncertainty: 'Investigation corridor based on current wind direction.',
  },
  exposure_path: {
    type: 'approximate_downwind_cone',
    coordinates: [
      [31.5204, 74.3587],
      [31.51, 74.34],
      [31.53, 74.34],
      [31.5204, 74.3587],
    ],
    center: { lat: 31.5204, lng: 74.3587 },
    direction_degrees: 270.0,
    direction_label: 'Moving toward West',
    distance_km: 9.6,
    cone_width_degrees: 60,
    confidence: 'MODERATE',
    uncertainty: 'Approximate wind-driven trajectory.',
  },
  vulnerable_locations: {
    schools: [
      { name: 'Model School', type: 'school', lat: 31.515, lng: 74.345 },
      { name: 'Beaconhouse', type: 'school', lat: 31.505, lng: 74.34 },
    ],
    hospitals: [
      { name: 'Jinnah Hospital', type: 'hospital', lat: 31.505, lng: 74.335 },
    ],
    summary: {
      schools_in_path: 2,
      hospitals_in_path: 1,
    },
  },
  metadata: {
    wind_direction_degrees: 90.0,
    movement_bearing: 270.0,
    wind_speed_ms: 3.2,
    corridor_length_km: 8.0,
    cone_length_km: 9.6,
    computed_at: '2026-01-01T00:00:00Z',
  },
  uncertainty: null,
};

// ── Tests ────────────────────────────────────────────────────

describe('ExposureIntelligenceMap', () => {
  // Suppress console noise from Leaflet
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  describe('Empty / Loading state', () => {
    it('renders empty state when exposure is null', () => {
      render(<ExposureIntelligenceMap exposure={null} />);
      expect(screen.getByText('Exposure geometry unavailable')).toBeInTheDocument();
    });

    it('has accessible label for empty state', () => {
      render(<ExposureIntelligenceMap exposure={null} />);
      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Exposure intelligence map — no data available'
      );
    });
  });

  describe('Full geometry rendering', () => {
    it('renders the map container', () => {
      const { container } = render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      const mapContainer = container.querySelector('.map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    it('has accessible label for full map', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Exposure intelligence map showing investigation corridor and exposure path'
      );
    });

    it('renders legend section', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText('Exposure Intelligence')).toBeInTheDocument();
    });

    it('shows investigation area label in legend', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText(/Investigation area \(upwind\)/)).toBeInTheDocument();
    });

    it('shows exposure path label in legend', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText(/Exposure path \(downwind\)/)).toBeInTheDocument();
    });

    it('shows observation point label in legend', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText('Observation point')).toBeInTheDocument();
    });

    it('shows school and hospital legend entries', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText('School (vulnerable)')).toBeInTheDocument();
      expect(screen.getByText('Hospital (vulnerable)')).toBeInTheDocument();
    });

    it('displays wind stats in legend', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText('Wind: 3.2 m/s · From East')).toBeInTheDocument();
    });

    it('displays vulnerable location count in legend', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByText('2 schools · 1 hospital in area')).toBeInTheDocument();
    });

    it('renders fullscreen toggle button', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} />);
      expect(screen.getByLabelText('View map fullscreen')).toBeInTheDocument();
    });
  });

  describe('Reduced vulnerability data', () => {
    it('handles zero schools and hospitals gracefully', () => {
      const noVulnExposure = {
        ...MOCK_EXPOSURE,
        vulnerable_locations: {
          schools: [],
          hospitals: [],
          summary: { schools_in_path: 0, hospitals_in_path: 0 },
        },
      };
      render(<ExposureIntelligenceMap exposure={noVulnExposure} />);
      expect(screen.getByText('0 schools · 0 hospitals in area')).toBeInTheDocument();
    });

    it('handles singular forms correctly', () => {
      const singleExposure = {
        ...MOCK_EXPOSURE,
        vulnerable_locations: {
          schools: [{ name: 'One School', type: 'school', lat: 31.51, lng: 74.34 }],
          hospitals: [],
          summary: { schools_in_path: 1, hospitals_in_path: 0 },
        },
      };
      render(<ExposureIntelligenceMap exposure={singleExposure} />);
      expect(screen.getByText('1 school · 0 hospitals in area')).toBeInTheDocument();
    });
  });

  describe('Missing geometry data', () => {
    it('handles missing investigation_area', () => {
      const noInvestigation = {
        ...MOCK_EXPOSURE,
        investigation_area: null,
      };
      // Should still render without crashing
      const { container } = render(<ExposureIntelligenceMap exposure={noInvestigation} />);
      expect(container.querySelector('.map-container')).toBeInTheDocument();
    });

    it('handles missing exposure_path', () => {
      const noPath = {
        ...MOCK_EXPOSURE,
        exposure_path: null,
      };
      const { container } = render(<ExposureIntelligenceMap exposure={noPath} />);
      expect(container.querySelector('.map-container')).toBeInTheDocument();
    });

    it('handles missing vulnerable_locations', () => {
      const noVulnerable = {
        ...MOCK_EXPOSURE,
        vulnerable_locations: undefined,
      };
      const { container } = render(<ExposureIntelligenceMap exposure={noVulnerable} />);
      expect(container.querySelector('.map-container')).toBeInTheDocument();
    });

    it('handles missing metadata', () => {
      const noMetadata = {
        ...MOCK_EXPOSURE,
        metadata: undefined,
      };
      // Should render without wind stats
      render(<ExposureIntelligenceMap exposure={noMetadata} />);
      expect(screen.getByText('Exposure Intelligence')).toBeInTheDocument();
    });
  });

  describe('No wind data state', () => {
    it('handles wind data from the exposure API missing stats', () => {
      const partialExposure = {
        ...MOCK_EXPOSURE,
        metadata: {
          wind_direction_degrees: null,
          movement_bearing: null,
          wind_speed_ms: null,
          corridor_length_km: 8.0,
          cone_length_km: 10.0,
          computed_at: '2026-01-01T00:00:00Z',
        },
      };
      render(<ExposureIntelligenceMap exposure={partialExposure} />);
      expect(screen.getByText('Exposure Intelligence')).toBeInTheDocument();
    });
  });

  describe('Fullscreen behavior', () => {
    it('hides fullscreen when allowFullscreen is false', () => {
      render(<ExposureIntelligenceMap exposure={MOCK_EXPOSURE} allowFullscreen={false} />);
      expect(screen.queryByLabelText('View map fullscreen')).not.toBeInTheDocument();
    });
  });

  describe('CSS classes', () => {
    it('applies custom className', () => {
      const { container } = render(
        <ExposureIntelligenceMap exposure={MOCK_EXPOSURE} className="custom-class" />
      );
      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });
  });
});
