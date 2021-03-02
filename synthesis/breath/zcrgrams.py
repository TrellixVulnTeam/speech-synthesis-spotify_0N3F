from pathlib import Path

import numpy as np
from scipy import signal
from scipy import io
from scipy.io import wavfile

import soundfile
from PIL import Image

import manydo
from tqdm.auto import tqdm

from .helpers import (
    load_wav,
    create_melspec,
    zcr_rate,
    colorvec,
    colorvec2,
)


num_threads = 8


def process_file(path: Path):
    sample_rate = 44100

    # load input wav and split into two second samples
    seconds_per_split = 2
    read_filename, wav_out, num_samples, sample_freq = load_wav(
        path.as_posix(), sr=sample_rate
    )
    num_splits = num_samples // (seconds_per_split * sample_rate)
    one_channel_out = wav_out[:, 0]  # only use left channel
    wav_in = np.reshape(
        one_channel_out[: seconds_per_split * sample_rate * num_splits],
        (num_splits, seconds_per_split * sample_rate),
    )

    # create mel-spectrogram
    ins = [wav_in[r, :] for r in range(num_splits)]
    melspecs = manydo.map(
        function=create_melspec, iterable=ins, num_jobs=num_threads, loading_bar=False
    )

    # use zero crossing rate to create zcr-colored melspectrograms
    zrates = manydo.map(
        function=zcr_rate, iterable=ins, num_jobs=num_threads, loading_bar=False
    )
    x_complete = np.asarray(
        manydo.map(
            function=colorvec2,
            iterable=zip(melspecs, zrates),
            num_jobs=num_threads,
            loading_bar=False,
        ),
        dtype=np.float32,
    )

    # save the zcr-coloured melspectrograms
    zcr_path = Path(path.stem)
    zcr_path.mkdir(parents=True)

    for n in range(0, np.shape(x_complete)[0]):
        imout = np.floor(255 * x_complete[n, ::-1, :, :])
        imout = imout.astype(np.uint8)
        img = Image.fromarray(imout, "RGB")
        img.save(
            zcr_path / ("zcr" + f"{n:04d}" + ".png"),
            "PNG",
        )


if __name__ == "__main__":
    for file_path in tqdm(sorted(Path(f"./audio").iterdir())):
        process_file(file_path)
