#!/bin/bash
# One-time setup per fresh session: install TTS, download the Kokoro voice model,
# and build the "timed" model copy that reports phoneme timings (for lip sync).
set -e
TTS_DIR=${TTS_DIR:-/home/claude/tts}
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$TTS_DIR"
pip install --break-system-packages -q kokoro-onnx soundfile pillow numpy onnx
[ -s "$TTS_DIR/kokoro.onnx" ] || curl -sL -o "$TTS_DIR/kokoro.onnx" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s "$TTS_DIR/voices.bin" ] || curl -sL -o "$TTS_DIR/voices.bin" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
[ -s "$TTS_DIR/kokoro-timed.onnx" ] || python3 "$HERE/make_timed_model.py" "$TTS_DIR/kokoro.onnx" "$TTS_DIR/kokoro-timed.onnx"
which ffmpeg >/dev/null
echo "setup ok"
