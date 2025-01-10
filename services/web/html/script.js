const classificationDomain = 'wss://classification.humbug.ac.uk';

function showToast(message) {
  window.showBanner(message, 'info', false);

  return;
}

// Respond to file selection
document.getElementById('dropzone-file').addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file) {
    window.showBanner(`File selected: ${file.name}`);
    document.getElementById('upload-text').innerText = file.name;
  }
});

// Handle drag and drop events
const dropzoneLabel = document.getElementById('dropzone-label');
dropzoneLabel.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropzoneLabel.classList.add('bg-gray-200');
});

dropzoneLabel.addEventListener('dragleave', () => {
  dropzoneLabel.classList.remove('bg-gray-200');
});

dropzoneLabel.addEventListener('drop', (event) => {
  event.preventDefault();
  dropzoneLabel.classList.remove('bg-gray-200');
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    const fileInput = document.getElementById('dropzone-file');
    fileInput.files = files;
    const file = files[0];
    window.showBanner(`File selected: ${file.name}`);
    document.getElementById('upload-text').innerText = file.name;
  }
});

document.getElementById('mscButton').addEventListener('click', async () => {
  showToast('Processing file...');

  const fileInput = document.getElementById('dropzone-file');
  if (fileInput.files.length === 0) {
    window.showBanner('Please select a WAV file first.', 'error');
    return;
  }

  const file = fileInput.files[0];
  window.showBanner('Reading file...');

  setIsLoading(true, 'mscButton');
  const data = await getProcessedDataFromFile(file);

  await performMsc(data);
});

document.getElementById('medButton').addEventListener('click', async () => {
  window.showBanner('Processing file...');

  const fileInput = document.getElementById('dropzone-file');
  if (fileInput.files.length === 0) {
    window.showBanner('Please select a WAV file first.', 'error');
    return;
  }

  const file = fileInput.files[0];
  window.showBanner('Ensuring correct sampling...');
  setIsLoading(true, 'medButton');
  const data = await getProcessedDataFromFile(file);

  await performMed(data);
});

/**
 *
 * @param {Float32Array} input
 */
async function performMed(input) {
  // Establish a WebSocket connection
  const socket = new WebSocket(`${classificationDomain}/med`);
  // On connection open, send the file bytes
  socket.addEventListener('open', async () => {
    window.showBanner('Connection established. Sending file...');
    setIsLoading(true, 'medButton');
    socket.send(JSON.stringify(Array.from(input)));
    showToast('File sent. Waiting for response...');
  });

  // Handle messages received from the server
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message['type'] === 'complete') {
      setIsLoading(false, undefined);
      const predictions = message['data']['predictions'];
      plotPredictions(predictions, []);
    } else {
      showToast('Message from server: ' + event.data);
    }
  });

  // Handle errors
  socket.addEventListener('error', (error) => {
    showToast('WebSocket error occurred.', 'error', true);
    console.dir(error);
    console.error('WebSocket error:', error);
  });

  // Handle connection close
  socket.addEventListener('close', () => {
    window.showBanner('WebSocket connection closed.', 'error', true);
  });
}

async function performMsc(input) {
  // Establish a WebSocket connection
  const socket = new WebSocket(`${classificationDomain}/msc`);
  // On connection open, send the file bytes
  socket.addEventListener('open', () => {
    showToast('WebSocket connection established. Sending file...');
    setIsLoading(true, 'mscButton');
    socket.send(JSON.stringify(Array.from(input)));
  });

  // Handle messages received from the server
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    console.log(message);
    if (message['type'] === 'complete') {
      const predictions = message['data']['events']['predictions'];
      const speciesAnnotations = message['data']['species']['detected_species'];
      window.showBanner('Processing complete.', 'info', true);
      setTimeout(() => {
        window.clearBanner();
      }, 3000);
      plotPredictions(predictions, speciesAnnotations);
    } else if (message['type'] === 'progress') {
      showToast('Progress: ' + message['data']['message']);
    } else {
      showToast('Message from server: ' + event.data);
    }
  });

  // Handle errors
  socket.addEventListener('error', (error) => {
    window.showBanner('WebSocket error occurred.', 'error', true);
    console.dir(error);
    console.error('WebSocket error:', error);
  });

  // Handle connection close
  socket.addEventListener('close', () => {
    setIsLoading(false, undefined);
    window.clearBanner();
    showToast('WebSocket connection closed.');
  });
}
