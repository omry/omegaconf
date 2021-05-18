import pickle
import sys

from omegaconf import OmegaConf

with open(f"{sys.argv[1]}.pickle", mode="rb") as fp:
    cfg = pickle.load(fp)
    assert cfg == OmegaConf.create({"a": [{"b": 10}]})
