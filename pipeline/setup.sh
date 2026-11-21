#!/bin/bash
# One-time setup per fresh session: install TTS + download Kokoro voice model.
set -e
TTS_DIR=${TTS_DIR:-/home/claude/tts}
mkdir -p "$TTS_DIR"
pip install --break-system-packages -q kokoro-onnx soundfile pillow numpy
[ -s "$TTS_DIR/kokoro.onnx" ] || curl -sL -o "$TTS_DIR/kokoro.onnx" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s "$TTS_DIR/voices.bin" ] || curl -sL -o "$TTS_DIR/voices.bin" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
which ffmpeg >/dev/null
echo "setup ok"
