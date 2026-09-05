# Perceptual volume slider over a unity-gain ceiling

Volume everywhere in Harpi means one thing: linear gain applied to the source, and 1.0 is the ceiling (unity — the panel and the `!volume` command can never amplify above the source; the old 0–2 range was too loud at the top). The panel slider, however, is a perceptual input device: it speaks position 0–1 and the session speaks gain via `gain = pos²`. Perceived loudness grows roughly with the square of amplitude, so a linear ruler put the everyday listening range (gain ≈ 0.05–0.3) into a sliver of the track; squaring hands that region ~25% of the travel. The curve lives only at the input device — the stored value, the Discord command, the readout, and the session clamps (`MAX_VOLUME` in `session.py`) all keep speaking linear gain, so `!volume 0.08` and a slider readout of `0.08` name the same state.

## Considered options

- **Position canonical everywhere** (command and storage speak 0–100%, gain derived at the audio boundary): rejected — it changes what the existing `!volume <gain>` command means and spreads the mapping across command parser, docs, and defaults.
- **Steeper curve (pos³) or linear**: pos³ makes the top third of the track jump loudly under the 1.0 ceiling; linear is what we are escaping. pos² is the standard perceptual approximation.

## Consequences

- The slider renders `√gain` server-side and squares position client-side before posting (volume-slider script in `templates/pages/music.html`); the layer dialog slider follows the same mapping.
- Slider max 100% = gain 1.0 = source loudness, unmodified. A genuinely quiet source stays quiet — that is a source problem, and the Probe already measures stream loudness.
