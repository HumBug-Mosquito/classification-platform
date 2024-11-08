async function getProcessedDataFromFile(file) {
  const arrayBuffer = await file.arrayBuffer();

  // Step 2: Decode the audio data
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // Step 3: Convert to mono if it's a stereo file
  const numberOfChannels = audioBuffer.numberOfChannels;
  const originalLength = audioBuffer.length;
  const originalSampleRate = audioBuffer.sampleRate;

  let monoData = new Float32Array(originalLength);
  if (numberOfChannels > 1) {
    // Average all channels to get mono audio data
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const channelData = audioBuffer.getChannelData(channel);
      for (let i = 0; i < originalLength; i++) {
        monoData[i] += channelData[i] / numberOfChannels;
      }
    }
  } else {
    // If it's already mono, just use the channel data directly
    monoData = audioBuffer.getChannelData(0);
  }

  // Step 4: Resample to 8000 Hz
  const targetSampleRate = 8000;
  const resampleFactor = targetSampleRate / originalSampleRate;
  const newLength = Math.round(originalLength * resampleFactor);
  const resampledData = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const originalIndex = i / resampleFactor;
    const lowerIndex = Math.floor(originalIndex);
    const upperIndex = Math.ceil(originalIndex);
    const weight = originalIndex - lowerIndex;

    // Linear interpolation
    const lowerValue = monoData[lowerIndex] || 0;
    const upperValue = monoData[upperIndex] || 0;
    resampledData[i] = lowerValue * (1 - weight) + upperValue * weight;
  }

  // Logging for inspection
  // console.log('Resampled Audio Samples (8000 Hz):', resampledData);
  console.log('Re-sampled audio to:', targetSampleRate);
  // console.log('Length:', newLength);

  return resampledData;
}

window.getProcessedDataFromFile = getProcessedDataFromFile;

const batchSize = 15360;
/**
 *
 * @param {Float32Array} signal
 * @returns
 */
function prepare(signal) {
  if (signal.length < batchSize) signal = ensureMinimumLength(signal);

  return padAndStepSignal(signal);
}

window.prepare = prepare;

/**
 *
 * @param {Float32Array} signal
 * @returns {Float32Array}
 */
function ensureMinimumLength(signal) {
  const desiredLength = Math.floor(batchSize);

  const xMean = signal.reduce((a, b) => a + b) / signal.length;

  const leftPadAmt = Math.floor((desiredLength - signal.length) / 2);
  const leftPadMeanAdd = Array(leftPadAmt).fill(xMean);

  const rightPadAmt = desiredLength - signal.length - leftPadAmt;
  const rightPadMeanAdd = Array(rightPadAmt).fill(xMean);

  return Array.from(new Float32Array([...leftPadMeanAdd, ...signal, ...rightPadMeanAdd]));
}

/**
 *
 * @param {Float32Array} paddedAudioBytes
 * @returns {Float32Array[]}
 */
function padAndStepSignal(signal) {
  const batches = [];
  for (let i = 0; i < signal.length; i += batchSize) {
    let batch = signal.slice(i, i + batchSize); // Slice signal into chunks of batchSize
    if (batch.length < batchSize) {
      batch = ensureMinimumLength(batch);
    }

    batches.push(batch);
  }
  return batches;
}

const medButtonId = 'medButton';
const mscButtonId = 'mscButton';

/**
 * This function mutates some DOM elements to indicate to the user that there is a loading state.
 *
 * This will occur during a prediction.
 *
 * @param {boolean} shouldBeLoading - Whether or not the loading state should be active.
 * @param {string} buttonId - The id of the button that triggered the loading state
 */
function setLoading(shouldBeLoading, buttonId) {
  //  If the loading state is already active, do nothing.
  if (shouldBeLoading === getIsLoading()) return;

  // Get the buttons that we want to mutate.
  const mscButton = document.getElementById(mscButtonId);
  const medButton = document.getElementById(medButtonId);

  // Make the buttons disabled if we are entering a loading state.
  if (shouldBeLoading) {
    mscButton.disabled = true;
    medButton.disabled = true;
    document.getElementById(buttonId).innerText = 'Loading...';
    return;
  }

  // Make the buttons enabled if we are exiting a loading state.
  mscButton.disabled = false;
  medButton.disabled = false;

  medButton.innerText = 'Predict Mosquito Events';
  mscButton.innerText = 'Predict Mosquito Species';
}

/**
 * This function gets an element that is mutated when we enter a loading state and check
 * if the properties set during a loading state are present.
 */
function getIsLoading() {
  // Get the buttons that we want to mutate.
  const mscButton = document.getElementById(mscButtonId);
  const medButton = document.getElementById(medButtonId);

  return mscButton.disabled || medButton.disabled;
}

window.setIsLoading = setLoading;
window.getIsLoading = getIsLoading;
