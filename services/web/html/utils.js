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
  console.log('Re-sampled audio to:', targetSampleRate);

  return resampledData;
}

window.getProcessedDataFromFile = getProcessedDataFromFile;

const batchSize = 15360;

const medButtonId = 'medButton';
const mscButtonId = 'mscButton';

/**
 * This function mutates some DOM elements to indicate to the user that there is a loading state.
 *
 * This will occur during a prediction.
 *
 * @param {boolean} shouldBeLoading - Whether or not the loading state should be active.
 * @param {string} buttonId - The id of the button that triggered the loading state
 * @param {boolean} clearBanner - Whether setting the loading state should clear the banner.
 */
function setLoading(shouldBeLoading, buttonId, clearBanner = false) {
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
 * This function shows a banner on the screen containing a message for the user.
 * @param {string} message - The message to display to the user.
 * @param {'info' | 'error'} type - The type of message to display to the user.
 * @param {boolean} clearLoading - Whether or not to clear the loading state.
 */
function showBanner(message, type = 'info', clearLoading = false) {
  const banner = document.getElementById('banner');
  banner.style.display = 'block';

  banner.innerText = message;
  banner.className = `banner ${type}`;

  if (clearLoading) setLoading(false);
}

/**
 * This function clears the banner on the screen.
 */
function clearBanner() {
  const banner = document.getElementById('banner');
  banner.style.display = 'none';
  banner.innerText = '';
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
window.showBanner = showBanner;
window.clearBanner = clearBanner;
