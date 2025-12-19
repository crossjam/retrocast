## Implement transcription module

### Overview

We need a module to take podcast audio files and transform them into
transcripts, preferably with speaker diarization (assigning speaker
identifiers to segments of the audio).

More can be read at the following GitHub issue:
https://github.com/crossjam/retrocast/issues/8

Based upon my research the following tools are most appropriate
initially 

- [mlx-whisperer](https://github.com/ml-explore/mlx-examples/tree/main/whisper):
  converts audio to speech (without diarization) at a reasonable speed
  on Apple Silicon machines
- [pyannote.audio](https://github.com/pyannote/pyannote-audio): does
  speaker diarization 

To start off, we would like a new Python module that supports a few
Python mechanisms that implement straight transcription. While
mlx-whisperer is fine for Apple hardware, we would like to be able to
run on Linux CUDA hardware as well. 

Consider two approaches:

- plugin based using pluggy
- class based

Since mlx-whisperer is Apple specific, if additional dependencies are
needed, be sure to properly isolate them using standard Python
packaging mechanisms.

At this stage, assume we will be passing in file paths (pathlib.Path
instances) as the entities to be transcribed. 

Unless specifically provided, the soutput should be
written in a `transcriptions` subdirectory of the user specific
application directory. The directory structure under `transcriptions`
should be similar to what the `download episodes` uses.

Also, we want to eventually surface this as a CLI subgroup named
`process`. It’s okay to stub that out for the moment and provide a
plan. But don’t implement anything until we have the basic
transcription functions working.


