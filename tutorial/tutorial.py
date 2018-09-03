from omegaconf import OmegaConf
import io
import sys


def initialization():
    # You can initialize the config in various ways, regardless of how you created it the features are the same:

    # Empty configuration
    empty = OmegaConf.empty()

    # initialize from a string containing valid yaml
    c1 = OmegaConf.from_string('yaml_string')

    # Initialize from a file name
    c2 = OmegaConf.from_filename('config.yaml')

    # from a file object
    c3 = OmegaConf.from_file(io.open('config.yaml', 'r'))

    # From command line arguments in sys.argv
    c4 = OmegaConf.from_cli()

    # From environment variables
    c5 = OmegaConf.from_env()


def access():
    # For simplicity, I am inlining the yaml content here.
    yaml = '''
key: value
list: [1, 2, 3]
nested:
  nested:
    key:
      value
'''

    cfg = OmegaConf.from_string(yaml)
    # Pretty print the config:
    print("print 1:\n", cfg.pretty())

    # Object style read access:
    assert cfg.key == 'value'
    assert cfg.nested.nested.key == 'value'
    assert cfg.list[0] == 1

    # Map style read access:
    assert cfg['key'] == 'value'
    assert cfg['nested']['nested']['key'] == 'value'
    assert cfg['list'][0] == 1

    # write access as well:
    cfg.key = 'new value'
    cfg.nested.nested.key = 'new value 2'
    cfg['nested1'] = {}
    cfg.nested1.key = 'value'
    # print again to see what changed:
    print("print 2:\n", cfg.pretty())

    # constructing a config in python:
    # Let's say we want this config:
    target = {'a': {
        'b': {
            'c': 1,
            'd': 2
        }
    }}
    cfg = OmegaConf.empty()
    cfg.a = {}
    cfg.a.b = {}
    cfg.a.b.c = 1
    cfg.a.b.d = 2
    assert target == cfg

    # We can also use cfg.update() to make it a bit more concise:
    cfg = OmegaConf.empty()
    cfg.update("a.b.c", 1)
    cfg.update("a.b.d", 2)
    assert target == cfg


def merging_configs():
    # Configs can be merges in a specific order.
    # Variables that appears in both will be overridden by the config mentioned last.
    c1 = OmegaConf.from_string('a : {b: 1}')
    c2 = OmegaConf.from_string('a : {b: 2}')
    c3 = OmegaConf.merge(c1, c2)
    assert c3.a.b == 2

    # In this case, both configs got a map under a, but with different content.
    # The resulting map contains both because there is no conflict
    c1 = OmegaConf.from_string('a : {b: 1}')
    c2 = OmegaConf.from_string('a : {c: 2}')
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == {'a': {'b': 1, 'c': 2}}

    # Typical usage is to load a file, and to override with with command line arguments:
    c1 = OmegaConf.from_string('a : {b: 1}')
    # usually this will actually come from the command line, but we wan simulate it here to simplify:
    sys.argv = ['program.py', 'a.b=10']
    cli = OmegaConf.from_cli()
    c3 = OmegaConf.merge(c1, cli)
    assert c3 == {'a': {'b': 10}}


if __name__ == '__main__':
    initialization()
    access()
    merging_configs()
