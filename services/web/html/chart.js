function plotPredictions(events, species) {
  const presenceProbability = [];

  events.forEach((event, index) => {
    presenceProbability.push(event[1]);
  });

  renderChart(presenceProbability, species);
}

function renderChart(events, species) {
  renderEvents(events);
  if (species && species.length !== 0) renderSpecies(species);
}

/**
 *
 * @param {number[]} events
 */
function renderEvents(events) {
  // // Destroy previous chart instance if it exists

  const data = events.map((event, index) => ({
    x: (index + 1) * 1.92,
    y: event,
  }));
  data.unshift({ x: 0, y: 0 });

  const ctx = document.getElementById('eventsChart');

  // Create the chart with annotations
  if (window.eventsChart instanceof Chart) {
    window.eventsChart.destroy();
  }

  window.eventsChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Probability of mosquito presence',
          data,
          borderColor: 'rgba(255, 99, 132, 1)',
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Time (seconds)', // Updated label to reflect time
          },
        },
        y: {
          title: {
            display: true,
            text: 'Probability',
          },
          min: 0,
          max: 1,
        },
      },
    },
  });
}

/**
 * @param {{start: number, end: number, species: string, predictions: Record<string, number>}[]} species
 */
function renderSpecies(species) {
  /**
   * @returns {{specie: string, predictions:{x:number, y:number}[]}[]}
   */
  function getSpeciesPredictions() {
    if (!species || species.length === 0) return [];

    const predictions = Object.keys(species[0]['predictions'])
      .flat()
      .map((specie) => ({
        specie: specie,
        predictions: species.map((detectedSpecies) => ({
          x: detectedSpecies.end,
          y: detectedSpecies.predictions[specie],
        })),
      }));

    predictions.unshift({ x: 0, y: 0 });

    return predictions;
  }

  function getSpeciesAnnotations() {
    const combinedSpecies = combineContiguousSpecies(species);

    // Create annotation objects based on detected species data
    return combinedSpecies.map((entry) => {
      return {
        type: 'box',
        xMin: entry.start, // 1.92,
        xMax: entry.end, /// 1.92,
        yMin: 0,
        yMax: 1,
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        label: {
          content: entry.species,
          display: true,
          position: 'center',
          color: 'black',
          font: { weight: 'bold' },
        },
      };
    });
  }

  const detectedSpecies = getSpeciesPredictions();

  const colors = detectedSpecies.map(
    (_) =>
      `#${Math.floor(Math.random() * 16777215)
        .toString(16)
        .padStart(6, '0')}`
  );

  const ctx2 = document.getElementById('speciesChart');

  if (window.speciesChart instanceof Chart) {
    window.speciesChart.destroy();
  }

  window.speciesChart = new Chart(ctx2, {
    type: 'line',
    data: {
      datasets: detectedSpecies.map((detectedSpecie, index) => ({
        label: `Probability for ${detectedSpecie.specie}`,
        data: detectedSpecie.predictions,
        borderColor: colors[index],
        fill: false,
      })),
    },
    options: {
      responsive: true,
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Time (seconds)', // Updated label to reflect time
          },
          min: 0,
        },
        y: {
          title: {
            display: true,
            text: 'Probability',
          },
          min: 0,
          max: 1.1,
        },
      },
      plugins: {
        annotation: {
          annotations: getSpeciesAnnotations(),
        },
      },
    },
  });

  renderSpeciesTable(species);
}
/**
 *
 * @param {{start: number, end: number, species: string, predictions: Record<string, number>}[]} species
 */
function renderSpeciesTable(species) {
  // Aggregate all of the species predictions for the recording.

  const predictions = species.map((e) => e['predictions']);

  const result = predictions.reduce((acc, obj) => {
    for (const key in obj) {
      acc[key] += obj[key]; // Accumulate the values for each key
    }
    return acc;
  }, Object.fromEntries(Object.keys(predictions[0]).map((key) => [key, 0])));

  // Calculate the mean of the predictions
  for (const key in result) {
    result[key] /= predictions.length;
  }

  const table = document.getElementById('speciesTable');

  const tbody = document.createElement('tbody');

  // Transform the result object into a vertical structure
  Object.entries(result).forEach(([species, probability]) => {
    const row = document.createElement('tr');

    // Create the species cell
    const speciesCell = document.createElement('td');
    speciesCell.setAttribute('style', 'font-weight: bold;');
    speciesCell.textContent = species;

    // Create the probability cell
    const probabilityCell = document.createElement('td');
    probabilityCell.textContent = (probability * 100).toFixed(2).toString() + '%'; // Format to 2 decimal places

    // Append cells to the row
    row.appendChild(speciesCell);
    row.appendChild(probabilityCell);

    // Append the row to the table body
    tbody.appendChild(row);
  });

  // Append the body to the table
  table.appendChild(tbody);
}

function combineContiguousSpecies(detectedSpecies) {
  const combinedSpecies = [];
  let currentEntry = null;
  let totalPresence = 0; // To accumulate the probabilities for mean calculation
  let segmentCount = 0; // Count of contiguous segments for calculating the mean

  detectedSpecies.forEach((entry) => {
    if (currentEntry && currentEntry.species === entry.species && currentEntry.end === entry.start) {
      // Extend the current entry if species matches and they are contiguous
      currentEntry.end = entry.end;

      // Update predictions by keeping the maximum probability for each species
      Object.keys(entry.predictions).forEach((key) => {
        currentEntry.predictions[key] = Math.max(currentEntry.predictions[key] || 0, entry.predictions[key]);
      });

      // Accumulate the probability for the mean presence calculation of the specific species
      totalPresence += entry.predictions[entry.species];
      segmentCount += 1;
    } else {
      // Finalize the mean presence for the last contiguous block if one exists
      if (currentEntry) {
        currentEntry.meanPresence = totalPresence / segmentCount;
        combinedSpecies.push(currentEntry);
      }

      // Start a new entry
      currentEntry = {
        start: entry.start,
        end: entry.end,
        species: entry.species,
        predictions: { ...entry.predictions }, // Shallow copy of predictions
        meanPresence: entry.predictions[entry.species], // Initialize mean with current entry's probability
      };

      // Reset the total presence and segment count
      totalPresence = entry.predictions[entry.species];
      segmentCount = 1;
    }
  });

  // Add the last contiguous block if it exists
  if (currentEntry) {
    currentEntry.meanPresence = totalPresence / segmentCount;
    combinedSpecies.push(currentEntry);
  }

  return combinedSpecies;
}

window.plotPredictions = plotPredictions;
