// Update video feed
function updateVideoFeed() {
    const videoFeed = document.getElementById('videoFeed');
    videoFeed.src = '/video_feed?' + new Date().getTime();
}

// Update status
function updateStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = `Status: ${data.connected ? 'Connected' : 'Disconnected'}`;
            if (data.error) {
                statusDiv.textContent += ` (Error: ${data.error})`;
            }
        })
        .catch(error => console.error('Error:', error));
}

// Capture photo
function capturePhoto() {
    fetch('/capture_photo', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Photo captured successfully!');
                refreshLibrary();
            } else {
                alert('Failed to capture photo: ' + data.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

// Load photo library
function loadLibrary() {
    fetch('/library')
        .then(response => response.json())
        .then(data => {
            const photoGrid = document.getElementById('photoGrid');
            photoGrid.innerHTML = '';
            
            data.photos.forEach(photo => {
                const photoItem = document.createElement('div');
                photoItem.className = 'photo-item';
                photoItem.innerHTML = `
                    <img src="/photos/${photo.filename}" alt="Captured photo">
                    <div class="timestamp">${photo.timestamp}</div>
                    <div class="actions">
                        <button class="button" onclick="deletePhoto('${photo.filename}')">Delete</button>
                        <button class="button" onclick="sendToTelegram('${photo.filename}')">Send to Telegram</button>
                    </div>
                `;
                photoGrid.appendChild(photoItem);
            });
        })
        .catch(error => console.error('Error:', error));
}

// Delete photo
function deletePhoto(filename) {
    if (confirm('Are you sure you want to delete this photo?')) {
        fetch('/delete_photo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshLibrary();
            } else {
                alert('Failed to delete photo: ' + data.error);
            }
        })
        .catch(error => console.error('Error:', error));
    }
}

// Send photo to Telegram
function sendToTelegram(filename) {
    fetch('/send_to_telegram', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Photo sent to Telegram successfully!');
        } else {
            alert('Failed to send photo to Telegram: ' + data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Refresh library
function refreshLibrary() {
    loadLibrary();
}

// Start periodic updates
setInterval(updateVideoFeed, 1000);
setInterval(updateStatus, 5000);

// Initial load
updateStatus();
loadLibrary(); 