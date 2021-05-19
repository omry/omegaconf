import pickle

from omegaconf import OmegaConf, __version__

cfg = OmegaConf.create({"a": [{"b": 10}]})

with open(f"{__version__}.pickle", mode="wb") as fp:
    pickle.dump(cfg, fp)
