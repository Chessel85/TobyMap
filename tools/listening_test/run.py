r"""The listening test's flow, without a window (P1-T13).

`ListeningTest` walks through the blocks. The window (app.py) shows what `ListeningTest` says and
passes it the keys, so the flow is tested without a window or a sound device.

States: "ready" (press Space to hear the next sound), "hour" (type the clock
hour, then Enter), "level" (type the distance level, then Enter), "done".
"""
from __future__ import annotations

import numpy as np

from desktop.audio import spatial
from tools.listening_test import model

TONE_FRACTION = 0.5   # the fixed tone alternative for beyond the view (DP80) is heard at a steady middle loudness


def tone_bursts(count: int = 3, hz: float = 600.0) -> np.ndarray:
    rate = spatial.RATE
    out = []
    for _ in range(count):
        t = np.arange(int(rate * 0.18)) / rate
        burst = (0.6 * np.sin(2 * np.pi * hz * t)).astype(np.float32)
        ramp = np.linspace(0, 1, int(rate * 0.01), dtype=np.float32)
        burst[:len(ramp)] *= ramp
        burst[-len(ramp):] *= ramp[::-1]
        out += [burst, np.zeros(int(rate * 0.09), np.float32)]
    return np.concatenate(out)


LABELS = ["Berlin", "Bay of Biscay", "Isle of Skye", "River Thames", "Kilimanjaro", "Saint Petersburg"]


def label_tone() -> np.ndarray:
    """The short tone that may come before a label (AD-10)."""
    t = np.arange(int(spatial.RATE * 0.12)) / spatial.RATE
    tone = (0.5 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
    ramp = np.linspace(0, 1, int(spatial.RATE * 0.01), dtype=np.float32)
    tone[:len(ramp)] *= ramp
    tone[-len(ramp):] *= ramp[::-1]
    return np.concatenate([tone, np.zeros(int(spatial.RATE * 0.06), np.float32)])


def render_label(trial: model.Trial) -> np.ndarray:
    """A spoken label from behind: no pitch change, a lower pitch, or a short tone first (AD-10)."""
    from desktop.audio import voice

    mono = voice.speak(LABELS[(trial.number - 1) % len(LABELS)])
    if trial.style == "tone":
        mono = np.concatenate([label_tone(), mono])
    return spatial.stereo(mono, trial.bearing, trial.fraction, pitch=trial.style == "lower")


def render_trial(trial: model.Trial, mode: str) -> np.ndarray:
    """The stereo samples for a trial."""
    if trial.kind == "labels":
        return render_label(trial)
    if trial.kind == "beyond" and trial.style == "tone":
        return spatial.render(mode, tone_bursts(), trial.bearing, TONE_FRACTION)
    mono = spatial.noise_bursts(seed=trial.number)
    if trial.kind == "moving":
        return spatial.render_moving(mode, mono, trial.start_bearing, trial.bearing, trial.fraction)
    return spatial.render(mode, mono, trial.bearing, trial.fraction)


class ListeningTest:
    def __init__(self, participant: str, folder, seed: int = 1, hrtf: bool | None = None, voice: bool | None = None):
        self.results = model.Results(participant, folder)
        self.seed = seed
        self.hrtf = spatial.hrtf_available() if hrtf is None else hrtf
        if voice is None:
            from desktop.audio import voice as voice_module

            voice = voice_module.available()
        self.voice = voice          # the Piper voice is installed (spike S6)
        self.block_index = -1
        self.trials: list[model.Trial] = []
        self.trial_index = 0
        self.state = "done"
        self.last_played: model.Trial | None = None

    # Which blocks can run on this computer.
    def usable(self, block: dict) -> tuple[bool, str]:
        if block["mode"].startswith("hrtf") and not self.hrtf:
            return False, "The head-related sound files are not on this computer, so this block is skipped."
        if block["kind"] == "labels" and not self.voice:
            return False, "The spoken labels need the Piper voice, which is not installed here (voices/piper), so this block is skipped."
        return True, ""

    def start(self) -> list[str]:
        self.block_index = -1
        return self.next_block()

    def next_block(self) -> list[str]:
        """Say what the next usable block is, or that the test is over."""
        said: list[str] = []
        while True:
            self.block_index += 1
            if self.block_index >= len(model.BLOCKS):
                self.state = "done"
                return said + [f"The listening test is finished. Your answers are in {self.results.write()}. Press the Close button."]
            block = model.BLOCKS[self.block_index]
            ok, why = self.usable(block)
            if not ok:
                said.append(f"Block {block['id']}. {why}")
                continue
            if block["kind"] == "labels":
                from desktop.audio import voice

                voice.load()      # takes a few seconds the first time
            self.trials = model.make_trials(block, self.seed)
            self.trial_index = 0
            self.state = "ready"
            return said + [block["words"]]

    @property
    def block(self) -> dict:
        return model.BLOCKS[self.block_index]

    @property
    def trial(self) -> model.Trial:
        return self.trials[self.trial_index]

    def play(self) -> tuple[model.Trial, np.ndarray] | None:
        """Space: hear the next sound. R: hear the same one again (counted)."""
        if self.state == "ready":
            self.state = "hour"
        elif self.state not in ("hour", "level"):
            return None
        else:
            self.trial.plays += 1
        self.last_played = self.trial
        return self.trial, render_trial(self.trial, self.block["mode"])

    def submit(self, text: str) -> list[str]:
        """The listener pressed Enter on some text. Returns what to say next."""
        if self.state == "hour":
            hour = model.parse_hour(text)
            if hour is None:
                return ["Type an hour from 1 to 12, or 0 if you can't tell, then press Enter."]
            self.trial.heard_hour = hour
            self.state = "level"
            return ["Now the distance, from 1, very near, to 5, beyond the view, then Enter."]
        if self.state == "level":
            level = model.parse_level(text)
            if level is None:
                return ["Type a distance from 1 to 5, then press Enter."]
            self.trial.heard_level = level
            self.results.add(self.trial, self.block["mode"], self.block["key"])
            self.trial_index += 1
            if self.trial_index >= len(self.trials):
                return ["That is the end of the block."] + self.next_block()
            self.state = "ready"
            return [f"Trial {self.trial_index + 1} of {len(self.trials)}. Press Space."]
        return []
