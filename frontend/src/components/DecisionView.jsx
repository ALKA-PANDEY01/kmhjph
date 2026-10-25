import { useState, useEffect } from 'react';
import { format, parseISO } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { api } from '../services/api';
import './DecisionView.css';

export default function DecisionView() {
  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showActuals, setShowActuals] = useState(false);
  const [showUncertainty, setShowUncertainty] = useState(false);
  const [signedErrorBounds, setSignedErrorBounds] = useState(null);

  const minDate = '2026-01-02';
  const maxDate = '2026-02-01';

  // Load P90 error once on mount
  useEffect(() => {
    loadP90Error();
  }, []);

  // Load forecast when date changes
  useEffect(() => {
    loadForecast();
  }, [selectedDate]);

  async function loadP90Error() {
    try {
      const metrics = await api.getMetrics();
      setSignedErrorBounds({ p5: metrics.percentiles.p5_signed_error, p95: metrics.percentiles.p95_signed_error });
    } catch (err) {
      console.error('Failed to load P90 error:', err);
    }
  }

  async function loadForecast() {
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getForecast(selectedDate);
      setForecastData(data);
    } catch (err) {
      setError(err.message);
      setForecastData(null);
    } finally {
      setLoading(false);
    }
  }

  function prepareChartData() {
    if (!forecastData || !forecastData.data_points || forecastData.data_points.length === 0) {
      return [];
    }

    // Sort by startTime to ensure chronological order
    const sortedPoints = [...forecastData.data_points].sort((a, b) => 
      a.startTime.localeCompare(b.startTime)
    );

    return sortedPoints.map(point => {
      const chartPoint = {
        time: point.startTime,
        fullTime: point.startTime,
        forecast: point.forecast,
      };

      if (showActuals && point.actual !== null) {
        chartPoint.actual = point.actual;
      }

      if (showUncertainty && signedErrorBounds) {
        chartPoint.upperBound = point.forecast - signedErrorBounds.p5;
        chartPoint.lowerBound = point.forecast - signedErrorBounds.p95;
      }

      return chartPoint;
    });
  }

  const chartData = prepareChartData();
  
  // Get publishTime from first data point
  const publishTime = forecastData?.data_points?.[0]?.publishTime;

  return (
    <div className="decision-view">
      <div className="view-header">
        <h1>Wind Forecast Decision View</h1>
        <p className="view-description">
          Review the forecast available at your 09:00 London decision cutoff
        </p>
      </div>

      <div className="controls">
        <div className="date-picker-group">
          <label htmlFor="date-picker">Delivery Date:</label>
          <input
            id="date-picker"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            min={minDate}
            max={maxDate}
            className="date-picker"
          />
        </div>

        <div className="toggle-group">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showActuals}
              onChange={(e) => setShowActuals(e.target.checked)}
            />
            <span>Show Actuals</span>
          </label>

          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showUncertainty}
              onChange={(e) => setShowUncertainty(e.target.checked)}
            />
            <span>90% of actuals fall in this range</span>
          </label>
        </div>
      </div>

      {loading && (
        <div className="state-message loading">
          <div className="spinner"></div>
          <p>Loading forecast data...</p>
        </div>
      )}

      {error && (
        <div className="state-message error">
          <p>⚠️ {error}</p>
        </div>
      )}

      {!loading && !error && forecastData && (
        <>
          <div className="forecast-banner">
            <p>
              <strong>Forecast as of {publishTime ? formatInTimeZone(parseISO(publishTime), 'UTC', 'dd MMM yyyy HH:mm') : 'N/A'} UTC</strong>
              <br />
              <span className="banner-detail">
                The latest forecast available before your 09:00 cutoff on{' '}
                {formatInTimeZone(parseISO(forecastData.decision_cutoff), 'UTC', 'dd MMM yyyy')}
              </span>
            </p>
          </div>

          {chartData.length === 0 ? (
            <div className="state-message empty">
              <p>No forecast data available for this date</p>
            </div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={500}>
                <LineChart data={chartData} margin={{ top: 20, right: 30, left: 55, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis
                    dataKey="time"
                    tickFormatter={value => formatInTimeZone(parseISO(value), 'UTC', 'HH:mm')}
                    label={{ value: 'Hour of Day (UTC)', position: 'insideBottom', offset: -10 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis
                    width={60}
                    label={{ value: 'Wind Generation (MW)', angle: -90, position: 'left', offset: 0 }}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
                    formatter={(value) => `${Math.round(value)} MW`}
                    labelFormatter={value => formatInTimeZone(parseISO(value), 'UTC', 'dd MMM HH:mm')}
                  />
                  <Legend
                    verticalAlign="top"
                    height={36}
                    wrapperStyle={{ paddingBottom: '20px' }}
                  />
                  
                  {showUncertainty && (
                    <>
                      <Line
                        type="monotone"
                        dataKey="upperBound"
                        stroke="#ffa500"
                        strokeDasharray="3 3"
                        strokeWidth={1}
                        dot={false}
                        name="90% range: high"
                        connectNulls
                      />
                      <Line
                        type="monotone"
                        dataKey="lowerBound"
                        stroke="#ffa500"
                        strokeDasharray="3 3"
                        strokeWidth={1}
                        dot={false}
                        name="90% range: low"
                        connectNulls
                      />
                    </>
                  )}
                  
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Forecast"
                    connectNulls
                  />
                  
                  {showActuals && (
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#16a34a"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Actual"
                      connectNulls
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
