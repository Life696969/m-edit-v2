# Sound design

The voice is the hero. Music and effects mark changes the eye also sees.

## Sources (free, licensed)

* Audio files the user put in the folder (music, sound effects); use them first.
* Royalty-free libraries whose licence allows commercial use without attribution, for example the Pixabay Content License.
* CC0 sounds.

Downloads need the user's yes (the permissions question), or `assets.allow_free_licensed_downloads`.

* Only use a source whose terms allow the way you download from it: an official API, direct download links offered for reuse, or CC0 collections.
* Check the current terms. Don't rely on memory.
* Without permission, use the user's audio or none, and say so in the review report.

Record every file in the asset ledger (`edit.json.assets`) with:

* source
* licence or usage basis
* local path
* retrieval date

The audit rejects any cue whose sound is not in the ledger.

## Prepare every effect

Never drop a raw sample in. Prepare each one first:

1. **Onset-align:** trim the leading air at the first sample above about −35 dBFS, so a cue placed at t lands its transient at t.
2. **Trim** to the length the moment needs, with a fade-out.
3. **High-pass** whooshes, slides, UI sounds and typing at about 160 Hz, so they sit around the voice. Impacts stay full-band.
4. **Normalize** the peak, then set the level per cue relative to the measured voice loudness.

## Level ladder (dB under the voice's integrated loudness)

| Role | dB under | Notes |
|---|---|---|
| Anchor hit (the one boom) | 10–12 | `role: "anchor"`, once per video |
| Cutaway whoosh | 13–14 | Starts 40 ms before the picture moves |
| Stamp, punch | 15–16 | Verdict words, FREE stamps |
| Card slide | 17 | Card enters |
| UI, typing, pops | 17–19 | Typing in a prompt box, chips popping |
| Music bed | 21–25 | Lower under dense speech |

## Music arc

* **Intro under the hook:** the quieter section of the track.
* **The drop on the hero moment.** Find the track's drop or impact (its biggest short-time energy step), and place the track so that it lands exactly on the hero word, with the anchor hit.
* **Silence on the pivot.** Stop the music (a 60 ms fade) under one line that needs to land alone: a turn, a punchline, "it's that simple". Bring it back on the grid by letting the track clock keep running under the silence.
* **Out with the last frame:** a 0.3–0.5 s fade.

When the video is delivered as separate files, render the bed once for the whole video. Give each clip the bed from its own start offset, so the music is continuous when the clips are played in order.

## Delivery

* Loudness about −14 to −15 LUFS per clip.
* True peak at most −1 dBTP after encoding. AAC can overshoot, so leave headroom (about −2.5 dBFS).
* Audio trimmed to the exact video duration.
* A/V sync verified within one video frame.
