/**
 * Preset feature vectors (165 local and aggregate features) for Elliptic Bitcoin Anomaly Detection.
 * Note: When sent to the backend, the selected timestep (1-49) is prepended to form the 166-feature tensor.
 */

// Helper to generate normalized float array with controlled mean & variance
function generateVector(length, baseMean, variance, spikes = []) {
  const arr = [];
  for (let i = 0; i < length; i++) {
    let val = baseMean + (Math.sin(i * 1.3) * variance) + (Math.cos(i * 0.7) * (variance / 2));
    // Apply spikes for specific characteristic features (e.g. fee ratio, degree)
    if (spikes.includes(i)) {
      val += variance * 4.5;
    }
    arr.push(parseFloat(val.toFixed(6)));
  }
  return arr;
}

// 1. Licit Exchange Inflow: Typical compliant exchange transaction
// Modest transaction volume, low fan-out, standard fee ratio
export const LICIT_EXCHANGE_PRESET = generateVector(
  165,
  -0.125,
  0.085,
  [2, 8, 14, 25] // normal exchange routing signatures
);

// 2. Darknet Mixer Flow: Peeling chains, tumbler hops, extreme fee evasion / rush
// High variance, high fan-out, rapid hop signature
export const DARKNET_MIXER_PRESET = generateVector(
  165,
  1.450,
  0.920,
  [0, 1, 3, 5, 9, 11, 16, 22, 33, 45, 60, 78, 102, 140] // characteristic anomaly spikes
);

/**
 * Generates an array of exactly 165 pseudo-random float features.
 */
export function generateRandomFeatures(illicitBias = false) {
  const mean = illicitBias ? 1.2 : -0.1;
  const spread = illicitBias ? 0.8 : 0.2;
  const arr = [];
  for (let i = 0; i < 165; i++) {
    const val = mean + (Math.random() * 2 - 1) * spread;
    arr.push(parseFloat(val.toFixed(5)));
  }
  return arr;
}
