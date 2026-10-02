# Transcription providers

m-edit supports four paths without making a remote call mandatory.

## Existing captions

Place a caption file beside a clip with the same stem:

```text
clip1.mp4
clip1.srt
```

Supported inputs: SRT, WebVTT, and compatible JSON.

## OpenAI Whisper CLI

Install the `whisper` CLI separately. m-edit detects it and can create canonical JSON. Whisper may download models; authorize network access or configure a local model cache before use.

## faster-whisper

Install `faster-whisper` separately and set `transcription.model_path` to a local model directory. m-edit deliberately refuses implicit model downloads in the network-safe path.

## whisper.cpp

Install `whisper-cli` and set `transcription.model_path` to a local GGML/GGUF model.

## Host-agent transcription

A host that can genuinely inspect audio may write the transcript directly. If it cannot hear the clip, it must disclose the limitation rather than inventing words.
