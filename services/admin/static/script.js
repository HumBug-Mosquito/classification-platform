function handleSockets() {
  console.log('Connecting to socket');
  let socket = new WebSocket('ws://localhost:8000/updates');
  socket.onopen = () => {
    console.log('Socket is open');
  };

  socket.onmessage = (event) => {
    console.log('Received event:', event);
    console.log('Received message:', event.data);

    try {
      const parsedData = JSON.parse(event.data);
      handleUpdate(parsedData);
    } catch (error) {
      console.error('Error parsing message:', error);
      console.log('Raw message:', event.data);
    }
  };

  socket.onclose = function (e) {
    console.log(
      'Socket is closed. Reconnect will be attempted in 1 second.',
      e.reason
    );
    setTimeout(function () {
      handleSockets();
    }, 1000);
  };

  socket.onerror = function (err) {
    console.error(
      'Socket encountered error: ',
      err.message,
      'Closing socket'
    );
    socket.close();
  };
}

/**
 * Update the state of the application.
 * @param {Object} state - The new state of the application.
 *
 * {
 *  current_recording: {
 *    recording_id: 1234,
 *    progress: 0,
 *    status: 'Not started'
 *  },
 *  queue:[
 *    {
 *      recording_id: 1234,
 *      type: 'med'
 *    },
 *  {
 *      recording_id: 124,
 *      type: 'med'
 *    },
 *  ],
 * }
 */
function handleUpdate(state) {
  updateCurrentRecording(state.processing);
  updateQueue(state.queue);
}

function updateCurrentRecording(recording) {
  if (!recording) {
    // show some text
    document.getElementById('current-recording-info').textContent =
      'No recording is currently being processed';

    document.getElementById('current-recording-table').style.display =
      'none';
    return;
  }

  document.getElementById('current-recording-info').style.display =
    'none';

  let table = document.getElementById('current-recording-table');
  table.style.display = 'table';
  table.innerHTML = `
   <thead>
            <tr>
              <th>Recording ID</th>
              <th>Type</th>
              <th>Progress</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="current-recording-list">
              <tr>
                <td>${recording.recording_id}</td>
                <td>${recording.type}</td>
                <td>${recording.progress}</td>
                <td>${recording.status}</td>
              </tr>
          </tbody>
   
  `;
}
function updateQueue(queue) {
  const queueList = document.getElementById('queue-list');
  queueList.innerHTML = ''; // Clear existing items

  if (queue && queue.length > 0) {
    queue.forEach((item) => {
      const row = document.createElement('tr');
      row.innerHTML = `
          <td>${item.recording_id}</td>
          <td>${item.type}</td>
      `;
      queueList.appendChild(row);
    });
  } else {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="2">Queue is empty</td>';
    queueList.appendChild(row);
  }
}

handleSockets();
