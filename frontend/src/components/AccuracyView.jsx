import { useState, useEffect } from 'react';
import { format, parseISO } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { api } from '../services/api';
import './AccuracyView.css';

const TOOLTIP_CONTENT = {
  mae: 'Mean Absolute Error: Average magnitude of forecast errors, regardless of direction',
  rmse: 'Root Mean Square Error: Emphasizes larger errors more than MAE',
  bias: 'Systematic tendency to over-forecast (positive) or under-forecast (negative)',
  p90: '90th percentile error: 90% of errors are smaller than this value'
};

export default function AccuracyView() {
  const [startDate, setStartDate] = useState('2026-01-02');
  const [endDate, setEndDate] = useState('2026-02-01');
  const [metrics, setMetrics] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [errorsByHour, setErrorsByHour] = useState(null);
  const [distribution, setDistribution] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const minDate = '2026-01-02';
  const maxDate = '2026-02-01';

  useEffect(() => {
    loadAllData();
  }, [startDate, endDate]);

  async function loadAllData() {
    setLoading(true);
    setError(null);

    try {
      const [metricsData, comparisonData, hourlyData, distData] = await Promise.all([
        api.getMetrics(startDate, endDate),
        api.getComparison(startDate, endDate),
        api.getErrorsByHour(startDate, endDate),
        api.getErrorsDistribution(startDate, endDate)
      ]);

      setMetrics(metricsData);
      setComparison(comparisonData);
      setErrorsByHour(hourlyData);
      setDistribution(distData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function formatNumber(value, decimals = 0) {
    return new Intl.NumberFormat('en-GB', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value);
  }

  function prepareComparisonData() {
    if (!comparison || !comparison.data) return [];
    
    // Sort by startTime
    const sorted = [...comparison.data].sort((a, b) => 
      a.startTime.localeCompare(b.startTime)
    );
    
    return sorted.map(point => ({
      time: point.startTime,
      fullTime: point.startTime,
      forecast: point.forecast,
      actual: point.actual
    }));
  }

  function prepareErrorOverTimeData() {
    if (!comparison || !comparison.data) return [];
    
    // Sort by startTime
    const sorted = [...comparison.data].sort((a, b) => 
      a.startTime.localeCompare(b.startTime)
    );
    
    return sorted.map(point => ({
      time: point.startTime,
      fullTime: point.startTime,
      error: point.forecast - point.actual
    }));
  }

  function prepareHourlyErrorData() {
    if (!errorsByHour || !errorsByHour.hourly_errors) return [];
    
    return errorsByHour.hourly_errors.map(item => ({
      hour: `${String(item.hour).padStart(2, '0')}:00`,
      mae: item.mae,
      count: item.count
    }));
  }

  function prepareDistributionData() {
    if (!distribution || !distribution.bins) return [];
    
    return distribution.bins.map(bin => ({
      range: `${Math.round(bin.bin_start)} to ${Math.round(bin.bin_end)}`,
      midpoint: (bin.bin_start + bin.bin_end) / 2,
      count: bin.count,
      percentage: bin.percentage
    }));
  }

  const comparisonData = prepareComparisonData();
  const errorTimeData = prepareErrorOverTimeData();
  const hourlyData = prepareHourlyErrorData();
  const distData = prepareDistributionData();
  const midnightTicks = comparisonData.filter(point => new Date(point.fullTime).getUTCHours() === 0).map(point => point.fullTime);
  const formatDayTick = value => formatInTimeZone(parseISO(value), 'UTC', 'dd MMM');

  return (
    <div className="accuracy-view">
      <div className="view-header">
        <h1>Forecast Accuracy Analysis</h1>
        <p className="view-description">
          Comprehensive metrics and visualizations of forecast performance
        </p>
      </div>

      <div className="date-range-controls">
        <div className="date-input-group">
          <label htmlFor="start-date">Start Date:</label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            min={minDate}
            max={endDate}
            className="date-picker"
          />
        </div>

        <div className="date-input-group">
          <label htmlFor="end-date">End Date:</label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            min={startDate}
            max={maxDate}
            className="date-picker"
          />
        </div>
      </div>

      {loading && (
        <div className="state-message loading">
          <div className="spinner"></div>
          <p>Loading accuracy data...</p>
        </div>
      )}

      {error && (
        <div className="state-message error">
          <p>⚠️ {error}</p>
        </div>
      )}

      {!loading && !error && metrics && (
        <>
          <div className="kpi-cards">
            <div className="kpi-card" title={TOOLTIP_CONTENT.mae}>
              <div className="kpi-label">Mean Absolute Error</div>
              <div className="kpi-value">{formatNumber(metrics.mae, 1)} MW</div>
              <div className="kpi-detail">
                {formatNumber(metrics.normalised_mae * 100, 1)}% of mean generation ({formatNumber(metrics.mean_actual, 0)} MW)
              </div>
            </div>

            <div className="kpi-card" title={TOOLTIP_CONTENT.rmse}>
              <div className="kpi-label">Root Mean Square Error</div>
              <div className="kpi-value">{formatNumber(metrics.rmse, 1)} MW</div>
              <div className="kpi-detail">
                {metrics.rmse > metrics.mae 
                  ? `${formatNumber((metrics.rmse / metrics.mae - 1) * 100, 0)}% larger than MAE` 
                  : 'Similar to MAE'}
              </div>
            </div>

            <div className="kpi-card" title={TOOLTIP_CONTENT.bias}>
              <div className="kpi-label">Bias</div>
              <div className="kpi-value">
                {metrics.bias > 0 ? '+' : ''}{formatNumber(metrics.bias, 1)} MW
              </div>
              <div className="kpi-detail">
                {Math.abs(metrics.bias) < 100 
                  ? 'Nearly unbiased' 
                  : metrics.bias > 0 
                    ? `Over-forecasting by ${formatNumber((metrics.bias / metrics.mean_actual) * 100, 1)}%`
                    : `Under-forecasting by ${formatNumber((Math.abs(metrics.bias) / metrics.mean_actual) * 100, 1)}%`}
              </div>
            </div>

            <div className="kpi-card" title={TOOLTIP_CONTENT.p90}>
              <div className="kpi-label">P90 Error</div>
              <div className="kpi-value">{formatNumber(metrics.percentiles.p90_absolute_error, 0)} MW</div>
              <div className="kpi-detail">
                90% of {metrics.record_count} periods below this
              </div>
            </div>
          </div>

          {metrics.summary && (
            <div className="insight-box">
              <h3>📊 Key Insights</h3>
              <p>{metrics.summary}</p>
            </div>
          )}

          <div className="charts-grid">
            {comparisonData.length > 0 && (
              <div className="chart-section">
                <h3>Forecast vs Actual Generation</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={comparisonData} margin={{ top: 10, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="fullTime"
                      ticks={midnightTicks}
                      tickFormatter={formatDayTick}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                    />
                    <YAxis label={{ value: 'Generation (MW)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip
                      formatter={(value) => `${Math.round(value)} MW`}
                      labelFormatter={value => formatInTimeZone(parseISO(value), 'UTC', 'dd MMM HH:mm')}
                    />
                    <Legend verticalAlign="top" height={36} />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={false}
                      name="Forecast"
                    />
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#16a34a"
                      strokeWidth={2}
                      dot={false}
                      name="Actual"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {errorTimeData.length > 0 && (
              <div className="chart-section">
                <h3>Error Over Time</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={errorTimeData} margin={{ top: 10, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="fullTime"
                      ticks={midnightTicks}
                      tickFormatter={formatDayTick}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                    />
                    <YAxis label={{ value: 'Error (MW)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip
                      formatter={(value) => `${Math.round(value)} MW`}
                      labelFormatter={value => formatInTimeZone(parseISO(value), 'UTC', 'dd MMM HH:mm')}
                    />
                    <Legend verticalAlign="top" height={36} />
                    <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />
                    <Line
                      type="monotone"
                      dataKey="error"
                      stroke="#dc2626"
                      strokeWidth={2}
                      dot={false}
                      name="Forecast Error"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {hourlyData.length > 0 && (
              <div className="chart-section">
                <h3>Mean Absolute Error by Hour of Day</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={hourlyData} margin={{ top: 10, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="hour"
                      label={{ value: 'Hour (UTC)', position: 'insideBottom', offset: -10 }}
                    />
                    <YAxis label={{ value: 'MAE (MW)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(value) => `${Math.round(value)} MW`} />
                    <Bar dataKey="mae" fill="#2563eb" name="Mean Absolute Error" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {distData.length > 0 && (
              <div className="chart-section">
                <h3>Error Distribution</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={distData} margin={{ top: 10, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="range"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                    />
                    <YAxis label={{ value: 'Count', angle: -90, position: 'insideLeft' }} />
                    <Tooltip
                      formatter={(value, name) => {
                        if (name === 'count') return value;
                        return `${value.toFixed(1)}%`;
                      }}
                    />
                    <Bar dataKey="count" fill="#16a34a" name="Frequency" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
