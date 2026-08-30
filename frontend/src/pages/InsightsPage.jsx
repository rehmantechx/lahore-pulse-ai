/**
 * InsightsPage — Trends, patterns, and analysis.
 *
 * Citizen-friendly. Shows historical trends, seasonal patterns,
 * and comparative data. No technical jargon.
 */

import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useHistoricalAnalogs } from '../hooks/useHistoricalAnalogs';
import HistoricalTrendChart from '../components/forecast/HistoricalTrendChart';
import { BarChart3 } from 'lucide-react';
import { CheckCircle, AlertTriangle, TrendingUp, Search, CloudRain, Building2, Clock, TreePine, Calendar, Brain } from 'lucide-react';

function getAirQualityInfo(value) {
  if (value == null || isNaN(value))
    return { label: 'No Data', color: '#A09A93', bg: '#F8F7F5' };
  if (value <= 12) return { label: 'Excellent', color: '#22C55E', bg: '#F0FDF4' };
  if (value <= 25) return { label: 'Good', color: '#84CC16', bg: '#F7FEE7' };
  if (value <= 35) return { label: 'Fair', color: '#EAB308', bg: '#FEFCE8' };
  if (value <= 55) return { label: 'Moderate', color: '#F97316', bg: '#FFF7ED' };
  if (value <= 90) return { label: 'Poor', color: '#EF4444', bg: '#FEF2F2' };
  if (value <= 150) return { label: 'Very Poor', color: '#DC2626', bg: '#FEF2F2' };
  return { label: 'Hazardous', color: '#7F1D1D', bg: '#FEF2F2' };
}

const SEASONAL_FACTS = [
  {
    season: 'Winter (Nov–Feb)',
    icon: <CloudRain size={18} />,
    fact: 'Smog season. Air quality is typically at its worst due to temperature inversions, crop burning, and vehicle emissions trapped near the ground.',
    color: '#EF4444',
    bg: '#FEF2F2',
  },
  {
    season: 'Spring (Mar–Apr)',
    icon: <TrendingUp size={18} />,
    fact: 'Transitional period. Air quality improves as temperatures rise and weather patterns shift.',
    color: '#EAB308',
    bg: '#FEFCE8',
  },
  {
    season: 'Summer (May–Aug)',
    icon: <CloudRain size={18} />,
    fact: 'Generally better air quality. Monsoon rains help wash pollutants out of the air.',
    color: '#22C55E',
    bg: '#F0FDF4',
  },
  {
    season: 'Autumn (Sep–Oct)',
    icon: <AlertTriangle size={18} />,
    fact: 'Pre-smog period. Air quality starts declining as cooler weather approaches and crop burning begins.',
    color: '#F97316',
    bg: '#FFF7ED',
  },
];

const KEY_FACTS = [
  { icon: <Building2 size={16} />, fact: 'Lahore is one of the most populated cities in Pakistan with over 11 million residents.' },
  { icon: <BarChart3 size={16} />, fact: 'Air quality can vary dramatically between neighborhoods — up to 3× difference within a few kilometers.' },
  { icon: <Clock size={16} />, fact: 'Morning rush hours (7–9 AM) and evening hours (6–9 PM) typically see the worst conditions.' },
  { icon: <CloudRain size={16} />, fact: 'Rain significantly improves air quality by washing pollutants out of the atmosphere.' },
  { icon: <Building2 size={16} />, fact: 'Construction dust, vehicle emissions, and industrial activity are major contributors.' },
  { icon: <TreePine size={16} />, fact: 'Parks and green areas tend to have better air quality than busy roads and industrial zones.' },
];

export default function InsightsPage() {
  const { forecasts, loading: forecastLoading } = useForecast();
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const { analogs, loading: analogsLoading } = useHistoricalAnalogs();

  const currentPM25 = forecasts?.['1']?.predicted_pm25;
  const airInfo = getAirQualityInfo(currentPM25);
  const loading = forecastLoading || episodeLoading;

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="page">
      {/* Header with Lahore Skyline */}
      <div style={{ position: 'relative', overflow: 'hidden', borderRadius: 12, marginBottom: 'var(--sp-4)' }}>
        <h1 className="page__title" style={{ position: 'relative', zIndex: 1 }}>Insights</h1>
        <p className="page__subtitle" style={{ position: 'relative', zIndex: 1 }}>
          Understand Lahore's air quality patterns and what drives them
        </p>
        <div className="lh-skyline" aria-hidden="true" />
      </div>

      {/* Current Summary */}
      <div
        style={{
          marginTop: 'var(--sp-6)',
          padding: 'var(--sp-4)',
          borderRadius: 12,
          background: airInfo.bg,
          border: `1px solid ${airInfo.color}20`,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <span style={{ fontSize: 24 }}>
          {airInfo.color === '#22C55E' ? <CheckCircle size={24} color="#22C55E" /> : airInfo.color === '#F97316' ? <AlertTriangle size={24} color="#F97316" /> : <AlertTriangle size={24} color="#EF4444" />}
        </span>
        <div>
          <span style={{ fontWeight: 600, color: airInfo.color }}>
            {loading ? 'Loading...' : `Currently ${airInfo.label}`}
          </span>
          <span
            style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--lp-text-secondary)',
              marginLeft: 8,
            }}
          >
            {today}
          </span>
        </div>
      </div>

      {/* Historical Trend Chart */}
      <div className="premium-section" style={{ marginTop: 'var(--sp-6)' }}>
        <div className="premium-section__header">
          <div className="premium-section__icon"><TrendingUp size={20} /></div>
          <span className="premium-section__title">Historical Trend</span>
          <span className="premium-section__subtitle">
            How air quality has changed over time
          </span>
        </div>

        <div style={{ marginTop: 'var(--sp-3)' }}>
          <HistoricalTrendChart />
        </div>
      </div>

      {/* How Today Compares */}
      {!analogsLoading && analogs && analogs.length > 0 && (
        <div className="premium-section" style={{ marginTop: 'var(--sp-6)' }}>
          <div className="premium-section__header">
            <div className="premium-section__icon"><Search size={20} /></div>
            <span className="premium-section__title">How Today Compares</span>
            <span className="premium-section__subtitle">
              Similar days in Lahore's history
            </span>
          </div>

          <div className="surface">
            <div className="surface__body">
              <p
                style={{
                  margin: '0 0 var(--sp-3) 0',
                  fontSize: 'var(--text-sm)',
                  color: 'var(--lp-text-secondary)',
                  lineHeight: 1.6,
                }}
              >
                Based on weather patterns and air quality data, today's conditions
                are similar to historical episodes. Here's how those played out:
              </p>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
              >
                {analogs.slice(0, 3).map((analogy, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 14px',
                      borderRadius: 10,
                      background: 'var(--lp-bg-secondary)',
                    }}
                  >
                    <span
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: '50%',
                        background: 'var(--lp-bg-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--lp-text-secondary)',
                        flexShrink: 0,
                      }}
                    >
                      {idx + 1}
                    </span>
                    <span
                      style={{
                        fontSize: 'var(--text-sm)',
                        color: 'var(--lp-text-secondary)',
                      }}
                    >
                      {analogy.date || `Similar episode #${idx + 1}`}
                      {analogy.pm25 && (
                        <span style={{ color: getAirQualityInfo(analogy.pm25).color, fontWeight: 600, marginLeft: 8 }}>
                          {getAirQualityInfo(analogy.pm25).label}
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Seasonal Patterns */}
      <div className="premium-section" style={{ marginTop: 'var(--sp-6)' }}>
        <div className="premium-section__header">
          <div className="premium-section__icon"><Calendar size={20} /></div>
          <span className="premium-section__title">Seasonal Patterns</span>
          <span className="premium-section__subtitle">
            How air quality changes through the year
          </span>
        </div>

        <div className="premium-metrics">
          {SEASONAL_FACTS.map((item) => (
            <div key={item.season} className="premium-metric">
              <div className="premium-metric__icon" style={{ background: item.bg }}>
                {item.icon}
              </div>
              <div className="premium-metric__text">
                <span className="premium-metric__label">{item.season}</span>
                <span
                  className="premium-metric__value"
                  style={{ color: item.color, fontSize: 'var(--text-sm)' }}
                >
                  {item.season.includes('Winter')
                    ? 'Worst Season'
                    : item.season.includes('Summer')
                      ? 'Best Season'
                      : 'Transition'}
                </span>
                <span
                  className="premium-metric__sub"
                  style={{ lineHeight: 1.5 }}
                >
                  {item.fact}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Key Facts */}
      <div className="premium-section" style={{ marginTop: 'var(--sp-6)' }}>
        <div className="premium-section__header">
          <div className="premium-section__icon"><Brain size={20} /></div>
          <span className="premium-section__title">Key Facts About Lahore's Air</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {KEY_FACTS.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                padding: '12px 16px',
                borderRadius: 10,
                background: 'var(--lp-bg-primary)',
                border: '1px solid var(--lp-border)',
              }}
            >
              <span style={{ fontSize: 18, marginTop: 2, flexShrink: 0 }}>
                {item.icon}
              </span>
              <span
                style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--lp-text-secondary)',
                  lineHeight: 1.6,
                }}
              >
                {item.fact}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Data Note */}
      <div
        style={{
          marginTop: 'var(--sp-6)',
          padding: 'var(--sp-4)',
          borderRadius: 12,
          background: 'var(--lp-bg-secondary)',
          fontSize: 'var(--text-sm)',
          color: 'var(--lp-text-tertiary)',
          lineHeight: 1.6,
        }}
      >
        <strong>About this data:</strong> Insights are generated from Lahore's air
        quality monitoring network and historical records. Patterns and trends
        reflect general conditions — specific locations may vary.
      </div>
    </div>
  );
}
