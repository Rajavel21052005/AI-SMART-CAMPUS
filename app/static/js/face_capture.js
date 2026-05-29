/* ============================================================
   face_capture.js — Webcam capture helper used across
   face registration and live-feed pages.
   Provides: initCapture(), takeSnapshot(), retakeCapture()
   ============================================================ */

let _stream     = null;
let _videoEl    = null;
let _canvasEl   = null;
let _dataInput  = null;

/**
 * Initialise the webcam capture widget.
 * @param {string} videoId    - ID of <video> element
 * @param {string} canvasId   - ID of <canvas> element
 * @param {string} inputId    - ID of hidden <input> for base64 data
 */
async function initCapture(videoId = 'webcamVideo',
                            canvasId = 'snapCanvas',
                            inputId  = 'snapshotData') {
  _videoEl   = document.getElementById(videoId);
  _canvasEl  = document.getElementById(canvasId);
  _dataInput = document.getElementById(inputId);

  if (!_videoEl || !_canvasEl) {
    console.error('face_capture: video or canvas element not found');
    return false;
  }

  try {
    _stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
    });
    _videoEl.srcObject = _stream;
    await _videoEl.play();

    const placeholder = document.getElementById('camPlaceholder');
    if (placeholder) placeholder.style.display = 'none';
    _videoEl.style.display = 'block';

    const guide = document.getElementById('faceGuide');
    if (guide) guide.style.display = 'block';

    return true;
  } catch (err) {
    console.error('Camera access error:', err);
    alert('Could not access camera. Please allow camera permissions in your browser settings.');
    return false;
  }
}

/** Take a snapshot from the live video feed. */
function takeSnapshot() {
  if (!_videoEl || !_canvasEl) return null;

  const ctx = _canvasEl.getContext('2d');
  _canvasEl.width  = _videoEl.videoWidth  || 640;
  _canvasEl.height = _videoEl.videoHeight || 480;
  ctx.drawImage(_videoEl, 0, 0, _canvasEl.width, _canvasEl.height);

  // Mirror horizontally for natural selfie feel
  ctx.save();
  ctx.scale(-1, 1);
  ctx.drawImage(_videoEl, -_canvasEl.width, 0, _canvasEl.width, _canvasEl.height);
  ctx.restore();

  const dataUrl = _canvasEl.toDataURL('image/jpeg', 0.92);

  if (_dataInput) _dataInput.value = dataUrl;

  // Show canvas, hide video
  _videoEl.style.display  = 'none';
  _canvasEl.style.display = 'block';

  // Stop camera stream to free device
  stopCapture();

  return dataUrl;
}

/** Stop camera stream. */
function stopCapture() {
  if (_stream) {
    _stream.getTracks().forEach(track => track.stop());
    _stream = null;
  }
}

/** Reset to allow retake. */
async function retakeCapture() {
  if (_canvasEl)  _canvasEl.style.display = 'none';
  if (_dataInput) _dataInput.value = '';
  return initCapture();
}

/** Send a snapshot to the /face/identify endpoint and return result. */
async function identifySnapshot(dataUrl) {
  const resp = await fetch('/face/identify', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ image: dataUrl }),
  });
  return resp.json();
}
