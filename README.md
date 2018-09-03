# OmegaConf
OmegaConf is a flexible yaml based configuration library, supporting dot access, deep updates and more.

### Loading from a string:
```
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    assert c == {'hello': 'world'}
```

### Loading from a file
Given the file *config.yaml* with this content:
```
env_name: '???' # '???' denotes mandatory variables, see below
num_trials: 1
train_timesteps: 200
render: False

training:
  batch_size: 128
```

To load config.yaml: 
 
```conf = OmegaConf.from_filename('config.yaml')```

### Access
You can read and write variables using dot and dictionary notations:
```
assert conf.training.batch_size == 128
assert conf.train_timesteps == 200
assert conf['training'] == 128
assert conf['training']['batch_size'] == 128
```

### Overriding values 
You can override configuration values, even with dot notation
```
conf.env_name = 'NewEnv-v2'
conf.training.batch_size = 256

# Which are (almost) equivalent to
conf.update('env_name', 'NewEnv-v2')
conf.update('training.batch_size', 256)
```
update() will allow you to automatically create subtree if a node is missing.


### Mandatory variables
Accessing variables with the string value ??? will throw an exception, those variables mut be overridden before accessing
In the above example, such a variable is env_name


### CLI based configuration
To access the CLI arguments (sys.argv), you can get a cli_config:
```conf = OmegaConf.from_cli()```
For example, if your CLI arguments are:

```python prog.py a=1 b=2 c.a = 3 c.b = 4```

Although CLI only allow simple key=value pairs, you can use dot notation to create more complex configurations.
The arguments above will contain the config:
```
a: 1
b: 2
c: {
    a: 3
    b: 4
}
```

### Environment based configuration
Similarly to CLI config, you can have a config that is based on your system environment:
```conf = OmegaConf.from_env()```

### Merging configurations
A powerful feature of OmegaConf is the ability to layer configurations in a specific order.
Any number of configurations can be merged into a single tree in a specific order:
you could do something like:
```
file1conf = OmegaConf.from_filename('conf1.yaml')
file2conf = OmegaConf.from_filename('conf2.yaml')
envconf = OmegaConf.from_env()
cliconf = OmegaConf.from_cli()
conf = OmegaConf.merge(file1econf, file2econf, envconf, cliconf)
```

Merged ```conf``` would contain the merge of all four configurations, if a value exist in two config, 
the one mentioned later in the merge will win over.