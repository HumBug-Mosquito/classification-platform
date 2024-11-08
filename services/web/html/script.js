function showToast(message) {
  const toast = document.getElementById('toast');
  toast.innerText = message;
  toast.classList.remove('hidden');
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 3000);

  return;
}

// Respond to file selection
document.getElementById('dropzone-file').addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file) {
    showToast(`File selected: ${file.name}`);
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
    showToast(`File selected: ${file.name}`);
    document.getElementById('upload-text').innerText = file.name;
  }
});

document.getElementById('mscButton').addEventListener('click', async () => {
  showToast('Processing file...');

  const fileInput = document.getElementById('dropzone-file');
  if (fileInput.files.length === 0) {
    showToast('Please select a WAV file first.');
    return;
  }

  const file = fileInput.files[0];
  showToast('Reading file...');
  const data = await getProcessedDataFromFile(file);

  await performMsc(data);
});

document.getElementById('medButton').addEventListener('click', async () => {
  showToast('Processing file...');

  const fileInput = document.getElementById('dropzone-file');
  if (fileInput.files.length === 0) {
    showToast('Please select a WAV file first.');
    return;
  }

  const file = fileInput.files[0];
  showToast('Reading file...');
  const data = await getProcessedDataFromFile(file);

  await performMed(data);
});

/**
 *
 * @param {Float32Array} input
 */
async function performMed(input) {
  // Establish a WebSocket connection
  const socket = new WebSocket('ws://live.localhost/med');
  // On connection open, send the file bytes
  socket.addEventListener('open', async () => {
    showToast('WebSocket connection established. Sending file...');
    setIsLoading(true, 'medButton');
    socket.send(JSON.stringify(Array.from(input)));
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
    setIsLoading(false, undefined);
    showToast('WebSocket error occurred.');
    console.dir(error);
    console.error('WebSocket error:', error);
  });

  // Handle connection close
  socket.addEventListener('close', () => {
    setIsLoading(false, undefined);
    showToast('WebSocket connection closed.');
  });
}

async function performMsc(input) {
  // Establish a WebSocket connection
  const socket = new WebSocket('ws://live.localhost/msc');
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
      setIsLoading(false, undefined);
      plotPredictions(predictions, speciesAnnotations);
    } else {
      showToast('Message from server: ' + event.data);
    }
  });

  // Handle errors
  socket.addEventListener('error', (error) => {
    setIsLoading(false, undefined);
    showToast('WebSocket error occurred.');
    console.dir(error);
    console.error('WebSocket error:', error);
  });

  // Handle connection close
  socket.addEventListener('close', () => {
    setIsLoading(false, undefined);
    showToast('WebSocket connection closed.');
  });
}
