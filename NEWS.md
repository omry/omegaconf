## 2.1.0.rc1 (2021-05-12)
OmegaConf 2.1 is a major release introducing substantial new features, and introducing some incompatible changes.
The biggest area of improvement in 2.1 is interpolations and resolvers. In addition - OmegaConf containers are now
much more compatible with their plain Python container counterparts (dict and list).

### Features
#### API Enhancements
- OmegaConf.select() now takes an optional default value to return if a key is not found ([#228](https://github.com/omry/omegaconf/issues/228))
- flag_override can now override multiple flags at the same time ([#400](https://github.com/omry/omegaconf/issues/400))
- Add the OmegaConf.to_object method, which converts Structured Configs to native instances of the underlying `@dataclass` or `@attr.s` class. ([#472](https://github.com/omry/omegaconf/issues/472))
- Add OmegaConf.unsafe_merge(), a fast merge variant that destroys the input configs ([#482](https://github.com/omry/omegaconf/issues/482))
- New function `OmegaConf.has_resolver()` allows checking whether a resolver has already been registered. ([#608](https://github.com/omry/omegaconf/issues/608))
- Adds OmegaConf.resolve(cfg) for in-place interpolation resolution on cfg ([#640](https://github.com/omry/omegaconf/issues/640))
- force_add flag added to OmegaConf.update(), ensuring that the path is created even if it will result in insertion of new values into struct nodes. ([#664](https://github.com/omry/omegaconf/issues/664))
- Add DictConfig support for keys of type int, float and bool ([#149](https://github.com/omry/omegaconf/issues/149)), ([#483](https://github.com/omry/omegaconf/issues/483))
- Structured Configs fields without a value are now automatically treated as `OmegaConf.MISSING` ([#390](https://github.com/omry/omegaconf/issues/390))
- Add minimal support for typing.TypedDict ([#473](https://github.com/omry/omegaconf/issues/473))
- OmegaConf.to_container now takes a `structured_config_mode` keyword argument. Setting `structured_config_mode=SCMode.DICT_CONFIG` causes `to_container` to not convert Structured Config objects to python dicts (it leaves them as DictConfig objects). ([#548](https://github.com/omry/omegaconf/issues/548))
#### Interpolation and resolvers
- Support for relative interpolation ([#48](https://github.com/omry/omegaconf/issues/48))
- Add ability to nest interpolations, e.g. ${foo.${bar}}}, ${oc.env:{$var1},${var2}}, or ${${func}:x1,x2} ([#445](https://github.com/omry/omegaconf/issues/445))
- Custom resolvers can now access the parent and the root config nodes ([#266](https://github.com/omry/omegaconf/issues/266))
- For `OmegaConf.{update, select}` and in interpolations, bracketed keys may be used as an alternative form to dot notation,
  e.g. foo.1 is equivalent to foo[1], [foo].1 and [foo][1]. ([#179](https://github.com/omry/omegaconf/issues/179))
- Custom resolvers may take non string arguments as input, and control whether to use the cache. ([#445](https://github.com/omry/omegaconf/issues/445))
- Dots may now be used in resolver names to denote namespaces (e.g: `${namespace.my_func:123}`) ([#539](https://github.com/omry/omegaconf/issues/539))
- New resolver `oc.select`, enabling node selection with a default value to use if the node cannot be selected ([#541](https://github.com/omry/omegaconf/issues/541))
- New resolver `oc.decode` that can be used to automatically convert a string to bool, int, float, dict, list, etc. ([#574](https://github.com/omry/omegaconf/issues/574))
- New resolvers `oc.dict.keys` and `oc.dict.values` provide a list view of the keys or values of a DictConfig node. ([#643](https://github.com/omry/omegaconf/issues/643))
- New resolver `oc.create` can be used to dynamically generate config nodes ([#645](https://github.com/omry/omegaconf/issues/645))
- New resolver `oc.deprecated`, that enables deprecating config nodes ([#681](https://github.com/omry/omegaconf/issues/681))
- The dollar character `$` is now allowed in interpolated key names, e.g. `${$var}` ([#600](https://github.com/omry/omegaconf/issues/600))
#### Misc
- New PyDev.Debugger resolver plugin for easier debugging in PyCharm and VSCode ([#214](https://github.com/omry/omegaconf/issues/214))
- OmegaConf now supports Python 3.9 ([#447](https://github.com/omry/omegaconf/issues/447))
- Support for Python 3.10 postponed annotation evaluation ([#303](https://github.com/omry/omegaconf/issues/303))
- Experimental support for enabling objects in config via "allow_objects" flag ([#382](https://github.com/omry/omegaconf/issues/382))

### Bug Fixes

- Fix support for forward declarations in Dict and Lists ([#378](https://github.com/omry/omegaconf/issues/378))
- Fix bug that allowed instances of Structured Configs to be assigned to DictConfig with different element type. ([#386](https://github.com/omry/omegaconf/issues/386))
- Fix exception raised when checking for the existence of a key with an incompatible type in DictConfig ([#394](https://github.com/omry/omegaconf/issues/394))
- Fix loading of an empty file via a file-pointer to return an empty dictionary ([#403](https://github.com/omry/omegaconf/issues/403))
- Fix pickling of Structured Configs with fields annotated as Dict[KT, VT] or List[T] on Python 3.6. ([#407](https://github.com/omry/omegaconf/issues/407))
- Assigning a primitive type to a Subscripted Dict now raises a descriptive message. ([#409](https://github.com/omry/omegaconf/issues/409))
- Fix assignment of an invalid value to a DictConfig to raise an exception without modifying the config object ([#409](https://github.com/omry/omegaconf/issues/409))
- Assigning a Structured Config to a Dict annotation now raises a descriptive error message. ([#410](https://github.com/omry/omegaconf/issues/410))
- OmegaConf.to_container() raises a ValueError on invalid input ([#418](https://github.com/omry/omegaconf/issues/418))
- Fix ConfigKeyError in some cases when merging lists containing interpolation values ([#422](https://github.com/omry/omegaconf/issues/442))
- DictConfig.get() in struct mode return None like standard Dict for non-existing keys ([#425](https://github.com/omry/omegaconf/issues/425))
- Fix bug where interpolations were unnecessarily resolved during merge ([#431](https://github.com/omry/omegaconf/issues/431))
- Fix bug where assignment of an invalid value to a ListConfig raised an exception but left the object modified. ([#433](https://github.com/omry/omegaconf/issues/433))
- When initializing a Structured Config with an incorrectly-typed value, the resulting ValidationError now properly reports the offending value in its error message. ([#435](https://github.com/omry/omegaconf/issues/435))
- Fix assignment of a Container to itself causing it to clear its content ([#449](https://github.com/omry/omegaconf/issues/449))
- Fix bug where DictConfig's shallow copy didn't work properly in some cases. ([#450](https://github.com/omry/omegaconf/issues/450))
- Fix support for merge tags in YAML files ([#470](https://github.com/omry/omegaconf/issues/470))
- Fix merge into a custom resolver node that raises an exception ([#486](https://github.com/omry/omegaconf/issues/486))
- Fix merge when element type is a Structured Config ([#496](https://github.com/omry/omegaconf/issues/496))
- Fix ValidationError when setting to None an optional field currently interpolated to a non-optional one ([#524](https://github.com/omry/omegaconf/issues/524))
- Fix OmegaConf.to_yaml(cfg) when keys are of Enum type ([#531](https://github.com/omry/omegaconf/issues/531))
- When a DictConfig has enum-typed keys, `__delitem__` can now be called with a string naming the enum member to be deleted. ([#554](https://github.com/omry/omegaconf/issues/554))
- `OmegaConf.select()` of a missing (`???`) node from a ListConfig with `throw_on_missing` set to True now raises the intended exception. ([#563](https://github.com/omry/omegaconf/issues/563))
- `DictConfig.{get(),pop()}` now return `None` when the accessed key evaluates to `None`, instead of the specified default value (for consistency with regular Python dictionaries). ([#583](https://github.com/omry/omegaconf/issues/583))
- `ListConfig.get()` now return `None` when the accessed key evaluates to `None`, instead of the specified default value (for consistency with DictConfig). ([#583](https://github.com/omry/omegaconf/issues/583))
- Fix creation of structured config from a dict subclass: data from the dict is no longer thrown away. ([#584](https://github.com/omry/omegaconf/issues/584))
- Assignment of a dict/list to an existing node in a parent in struct mode no longer raises ValidationError ([#586](https://github.com/omry/omegaconf/issues/586))
- Nested flag_override now properly restore the original state ([#589](https://github.com/omry/omegaconf/issues/589))
- Fix OmegaConf.create() to set the provided `parent` when creating a config from a YAML string. ([#648](https://github.com/omry/omegaconf/issues/648))
- OmegaConf.select now returns None when attempting to select a child of a value or None node ([#678](https://github.com/omry/omegaconf/issues/678))
- Improve error message when creating a config from a Structured Config that fails type validation ([#697](https://github.com/omry/omegaconf/issues/697))

### API changes and deprecations

- DictConfig `__getattr__` access, e.g. `cfg.foo`, is now raising a AttributeError if the key "foo" does not exist ([#515](https://github.com/omry/omegaconf/issues/515))
- DictConfig `__getitem__` access, e.g. `cfg["foo"]`, is now raising a KeyError if the key "foo" does not exist ([#515](https://github.com/omry/omegaconf/issues/515))
- DictConfig get access, e.g. `cfg.get("foo")`, now returns `None` if the key "foo" does not exist ([#527](https://github.com/omry/omegaconf/issues/527))
- `Omegaconf.select(cfg, key, default, throw_on_missing)` now requires keyword arguments for everything after `key` ([#228](https://github.com/omry/omegaconf/issues/228))
- Structured Configs with nested Structured config field that does not specify a default value are now interpreted as MISSING (`???`) instead of auto-expanding ([#411](https://github.com/omry/omegaconf/issues/411))
- OmegaConf.update() is now merging dict/list values into the destination node by default. Call with merge=False to replace instead. ([#667](https://github.com/omry/omegaconf/issues/667))
- `register_resolver()` is deprecated in favor of `register_new_resolver()`, allowing resolvers to (i) take non-string arguments like int, float, dict, interpolations, etc. and (ii) control the cache behavior (now disabled by default) ([#426](https://github.com/omry/omegaconf/issues/426))
- Merging a MISSING value onto an existing value no longer changes the target value to MISSING. ([#462](https://github.com/omry/omegaconf/issues/462))
- When resolving an interpolation of a config value with a primitive type, the interpolated value is validated and possibly converted based on the node's type. ([#488](https://github.com/omry/omegaconf/issues/488))
- DictConfig and ListConfig shallow copy is now performing a deepcopy ([#492](https://github.com/omry/omegaconf/issues/492))
- `OmegaConf.select()`, `DictConfig.{get(),pop()}`, `ListConfig.{get(),pop()}` no longer return the specified default value when the accessed key is an interpolation that cannot be resolved: instead, an exception is raised. ([#543](https://github.com/omry/omegaconf/issues/543))
- OmegaConf.{merge, unsafe_merge, to_yaml} now raises a ValueError when called on a str input. Previously an AssertionError was raised. ([#560](https://github.com/omry/omegaconf/issues/560))
- All exceptions raised during the resolution of an interpolation are either `InterpolationResolutionError` or a subclass of it. ([#561](https://github.com/omry/omegaconf/issues/561))
- `key in cfg` now returns True when `key` is an interpolation even if the interpolation target is a missing ("???") value. ([#562](https://github.com/omry/omegaconf/issues/562))
- `OmegaConf.select()` as well as container methods `get()` and `pop()` do not return their default value anymore when the accessed key is an interpolation that cannot be resolved: instead, an exception is raised. ([#565](https://github.com/omry/omegaconf/issues/565))
- Implicitly empty resolver arguments (e.g., `${foo:a,}`) are deprecated in favor of explicit quoted strings (e.g., `${foo:a,""}`) ([#572](https://github.com/omry/omegaconf/issues/572))
- The `env` resolver is deprecated in favor of `oc.env`, which keeps the string representation of environment variables, does not cache the resulting value, and handles "null" as default value. ([#573](https://github.com/omry/omegaconf/issues/573))
- `OmegaConf.get_resolver()` is deprecated: use the new `OmegaConf.has_resolver()` to check for the existence of a resolver. ([#608](https://github.com/omry/omegaconf/issues/608))
- Interpolation cycles are now forbidden and will trigger an InterpolationResolutionError on access. ([#662](https://github.com/omry/omegaconf/issues/662))
- Support for Structured Configs that subclass `typing.Dict` is now deprecated. ([#663](https://github.com/omry/omegaconf/issues/663))
- Remove BaseContainer.{pretty,select,update_node} that have been deprecated since OmegaConf 2.0. ([#671](https://github.com/omry/omegaconf/issues/671))

### Miscellaneous changes

- Optimized config creation time. Faster by 1.25x to 4x in benchmarks ([#477](https://github.com/omry/omegaconf/issues/477))
- ListConfig.__contains__ optimized, about 15x faster in a benchmark ([#529](https://github.com/omry/omegaconf/issues/529))
- Optimized ListConfig iteration by 12x in a benchmark ([#532](https://github.com/omry/omegaconf/issues/532))


## 2.0.6 (2021-01-19)
### Bug Fixes

- Fix bug where DictConfig's shallow copy didn't work properly in some cases. ([#450](https://github.com/omry/omegaconf/issues/450))

## 2.0.5 (2020-11-11)
### Bug Fixes

- Fix bug where interpolations were unnecessarily resolved during merge ([#431](https://github.com/omry/omegaconf/issues/431))

## 2.0.4 (2020-11-03)
### Bug Fixes

- Fix a bug merging into a field annotated as Optional[List[int]] = None ([#428](https://github.com/omry/omegaconf/issues/428))


## 2.0.3 (2020-10-19)
### Deprecations and Removals

- Automatic expansion of nested dataclasses without a default value is deprecated ([#412](https://github.com/omry/omegaconf/issues/412))


## 2.0.2 (2020-09-10)
### Features

- OmegaConf.update() now takes a merge flag to indicate merge or set for config values ([#363](https://github.com/omry/omegaconf/issues/363))

### Bug Fixes

- Fix cfg.pretty() deprecation warning ([#358](https://github.com/omry/omegaconf/issues/358))
- Properly crash when accessing `${foo.bar}` if `foo` is a value node (instead of silently returning `${foo}`) ([#364](https://github.com/omry/omegaconf/issues/364))

### Deprecations and Removals

- OmegaConf.update() now warns if the merge flag is not specified ([#367](https://github.com/omry/omegaconf/issues/367))


## 2.0.1 (2020-09-01)
This is mostly a bugfix release.
The notable change is the config.pretty() is now deprecated in favor of OmegaConf.to_yaml().

### Bug Fixes

- Fixes merging of dict into a Dict[str, str] ([#246](https://github.com/omry/omegaconf/issues/246))
- Fix DictConfig created from another DictConfig drops node types ([#252](https://github.com/omry/omegaconf/issues/252))
- Relax save and load APIs to accept IO[Any] ([#253](https://github.com/omry/omegaconf/issues/253))
- Report errors when loading YAML files with duplicate keys ([#257](https://github.com/omry/omegaconf/issues/257))
- Fix a bug initializing config with field typed as Any with Structured Config object ([#260](https://github.com/omry/omegaconf/issues/260))
- Merging into a MISSING Structured config node expands the node first to ensure the result is legal ([#269](https://github.com/omry/omegaconf/issues/269))
- Fix merging into a config with a read only node if merge is not mutating that node ([#271](https://github.com/omry/omegaconf/issues/271))
- Fix OmegaConf.to_container() failing in some cases when the config is read-only ([#275](https://github.com/omry/omegaconf/issues/275))
- Optional[Tuple] types are now supported as type annotation in Structured Configs. ([#279](https://github.com/omry/omegaconf/issues/279))
- Support indirect interpolation ([#283](https://github.com/omry/omegaconf/issues/283))
- OmegaConf.save() can now save dataclass and attr classes and instances ([#287](https://github.com/omry/omegaconf/issues/287))
- OmegaConf.create() doesn't modify yaml.loader.SafeLoader ([#289](https://github.com/omry/omegaconf/issues/289))
- Fix merging a sublcass Structured Config that adds a field ([#291](https://github.com/omry/omegaconf/issues/291))
- strings containing valid ints and floats represented are converted to quoted strings instead of the primitives in pretty() ([#296](https://github.com/omry/omegaconf/issues/296))
- Loading an empty YAML file now returns an empty DictConfig ([#297](https://github.com/omry/omegaconf/issues/297))
- Fix bug that allowed an annotated List and Dict field in a Structured Config to be assigned a value of a different type. ([#300](https://github.com/omry/omegaconf/issues/300))
- merge_with() now copied flags (readonly, struct) into target config ([#301](https://github.com/omry/omegaconf/issues/301))
- Fix DictConfig setdefault method to behave as it should ([#304](https://github.com/omry/omegaconf/issues/304))
- Merging a missing list onto an existing one makes the target missing ([#306](https://github.com/omry/omegaconf/issues/306))
- Fix error when merging a structured config into a field with None value ([#310](https://github.com/omry/omegaconf/issues/310))
- Fix a bug that allowed the assignment of containers onto fields annotated as primitive types ([#324](https://github.com/omry/omegaconf/issues/324))
- Merging a List of a structured with a different type now raises an error. ([#327](https://github.com/omry/omegaconf/issues/327))
- Remove dot-keys usage warning ([#332](https://github.com/omry/omegaconf/issues/332))
- Fix merging into an Optional[List[Any]] = None ([#336](https://github.com/omry/omegaconf/issues/336))
- Fix to properly merge list of dicts into a list of dataclasses ([#348](https://github.com/omry/omegaconf/issues/348))
- OmegaConf.to_yaml() now properly support Structured Configs ([#350](https://github.com/omry/omegaconf/issues/350))

### Deprecations and Removals

- cfg.pretty() is deprecated in favor of OmegaConf.to_yaml(config). ([#263](https://github.com/omry/omegaconf/issues/263))

### Improved Documentation

- Document serialization APIs ([#278](https://github.com/omry/omegaconf/issues/278))
- Document OmegaConf.is_interpolation and OmegaConf.is_none ([#286](https://github.com/omry/omegaconf/issues/286))
- Document OmegaConf.get_type() ([#343](https://github.com/omry/omegaconf/issues/343))


## 2.0.0 (2020-05-04)

OmegaConf 2.0 is a major release introducing substantial new features, and introducing some incompatible changes.
The biggest new feature is Structured Configs, which extends OmegaConf into a schema validation system
as well as a configuration system.
With Structured Configs you can create OmegaConf objects from standard dataclasses or attr classes (or objects).
OmegaConf will retain the type information from the source object/class and validate that config mutations are legal.

This is the biggest OmegaConf release ever, the number of unit tests more than tripled (485 to 1571).

### Features

- Add support for initializing OmegaConf from typed objects and classes ([#87](https://github.com/omry/omegaconf/issues/87))
- DictConfig and ListConfig now implements typing.MutableMapping and typing.MutableSequence. ([#114](https://github.com/omry/omegaconf/issues/114))
- Enums can now be used as values and keys  ([#87](https://github.com/omry/omegaconf/issues/87)),([#137](https://github.com/omry/omegaconf/issues/137))
- Standardize exception messages ([#186](https://github.com/omry/omegaconf/issues/186))
- In struct mode, exceptions raised on invalid access are now consistent with Python ([#138](https://github.com/omry/omegaconf/issues/138)),([#94](https://github.com/omry/omegaconf/issues/94))
    * KeyError is raised when using dictionary access style for a missing key: cfg["foo"]
    * AttributeError is raised when using attribute access style for a missing attribute: cfg.foo
- Structured configs can now inherit from Dict, making them open to arbitrary fields ([#134](https://github.com/omry/omegaconf/issues/134))
- Container.pretty() now preserves insertion order by default. override with sort_keys=True ([#161](https://github.com/omry/omegaconf/issues/161))
- Merge into node interpolation is now by value (copying target node) ([#184](https://github.com/omry/omegaconf/issues/184))
- Add OmegaConf.{is_config, is_list, is_dict} to test if an Object is an OmegaConf object, and if it's a list or a dict ([#101](https://github.com/omry/omegaconf/issues/101))
- Add OmegaConf.is_missing(cfg, key) to test if a key is missing ('???') in a config ([#102](https://github.com/omry/omegaconf/issues/102))
- OmegaConf.is_interpolation queries if a node is an interpolation ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_missing queries if a node is missing (has the value '???') ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_optional queries if a node in the config is optional (can take None) ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_none queries if a node represents None ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf now passes strict mypy tests ([#105](https://github.com/omry/omegaconf/issues/105))
- Add isort to ensure imports are kept sorted ([#107](https://github.com/omry/omegaconf/issues/107))

### Bug Fixes

- Disable automatic conversion of date strings in yaml decoding ([#95](https://github.com/omry/omegaconf/issues/95))
- Fixed pretty to handle strings with unicode characters correctly ([#111](https://github.com/omry/omegaconf/issues/111))
- Fix eq fails if object contains unresolveable values ([#124](https://github.com/omry/omegaconf/issues/124))
- Correctly throw MissingMandatoryValue on indirect access of missing value ([#99](https://github.com/omry/omegaconf/issues/99))
- DictConfig pop now returns the underlying value and not ValueNode ([#127](https://github.com/omry/omegaconf/issues/127))
- OmegaConf.select(key) now returns the root node when key is "" ([#135](https://github.com/omry/omegaconf/issues/135))
- Add support for loading/saving config files by using pathlib.Path objects ([#159](https://github.com/omry/omegaconf/issues/159))
- Fix AttributeError when accessing config in struct-mode with get() while providing None as default ([#174](https://github.com/omry/omegaconf/issues/174))


### Deprecations and Removals

- Renamed omegaconf.Config to omegaconf.Container ([#103](https://github.com/omry/omegaconf/issues/103))
- Dropped support Python 2.7 and 3.5 ([#88](https://github.com/omry/omegaconf/issues/88))
- cfg.select(key) deprecated in favor of OmegaConf.select(cfg, key) ([#116](https://github.com/omry/omegaconf/issues/116))
- cfg.update(key, value) deprecated in favor of OmegaConf.update(cfg, key, value) ([#116](https://github.com/omry/omegaconf/issues/116))
- Container.pretty() behavior change: sorted keys -> unsorted keys by default. override with sort_keys=True. ([#161](https://github.com/omry/omegaconf/issues/161))
- cfg.to_container() is removed, deprecated since 1.4.0. Use OmegaConf.to_container() ([#188](https://github.com/omry/omegaconf/issues/188))
- cfg.save() is removed, deprecated since 1.4.0, use OmegaConf.save() ([#188](https://github.com/omry/omegaconf/issues/188))
- DictConfig item deletion now throws ConfigTypeError if the config is in struct mode ([#225](https://github.com/omry/omegaconf/issues/225))
- DictConfig.pop() now throws ConfigTypeError if the config is in struct mode ([#225](https://github.com/omry/omegaconf/issues/225))


## 1.4.0 (2019-11-19)

### Features

- ListConfig now implements + operator (Allowing concatenation with other ListConfigs) ([#36](https://github.com/omry/omegaconf/issues/36))
- OmegaConf.save() now takes a resolve flag (defaults False) ([#37](https://github.com/omry/omegaconf/issues/37))
- Add OmegaConf.masked_copy(keys) function that returns a copy of a config with a subset of the keys ([#42](https://github.com/omry/omegaconf/issues/42))
- Improve built-in env resolver to return properly typed values ("1" -> int, "1.0" -> float etc) ([#44](https://github.com/omry/omegaconf/issues/44))
- Resolvers can now accept a list of zero or more arguments, for example: "${foo:a,b,..,n}" ([#46](https://github.com/omry/omegaconf/issues/46))
- Change semantics of contains check ('x' in conf): Missing mandatory values ('???') are now considered not included and contains test returns false for them ([#49](https://github.com/omry/omegaconf/issues/49))
- Allow assignment of a tuple value into a Config ([#74](https://github.com/omry/omegaconf/issues/74))

### Bug Fixes

- Read-only list can no longer be replaced with command line override ([#39](https://github.com/omry/omegaconf/issues/39))
- Fix an error when expanding an empty dictionary in PyCharm debugger ([#40](https://github.com/omry/omegaconf/issues/40))
- Fix a bug in open_dict causing improper restoration of struct flag in some cases ([#47](https://github.com/omry/omegaconf/issues/47))
- Fix a bug preventing dotlist values from containing '=' (foo=bar=10 -> key: foo, value: bar=10) ([#56](https://github.com/omry/omegaconf/issues/56))
- Config.merge_with_dotlist() now throws if input is not a list or tuple of strings ([#72](https://github.com/omry/omegaconf/issues/72))
- Add copy method for DictConfig and improve shallow copy support ([#82](https://github.com/omry/omegaconf/issues/82))

### Deprecations and Removals

- Deprecated Config.to_container() in favor of OmegaConf.to_container() (#[#41](https://github.com/omry/omegaconf/issues/41))
- Deprecated config.save(file) in favor of OmegaConf.save(config, file) ([#66](https://github.com/omry/omegaconf/issues/66))
- Remove OmegaConf.{empty(), from_string(), from_dict(), from_list()}. Use OmegaConf.create() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove Config.merge_from(). Use Config.merge_with() (deprecated since 1.1.0) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove OmegaConf.from_filename() and OmegaConf.from_file(). Use OmegaConf.load() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))

### Miscellaneous changes

- Switch from tox to nox for test automation ([#54](https://github.com/omry/omegaconf/issues/54))
- Formatting code with Black ([#54](https://github.com/omry/omegaconf/issues/54))
- Switch from Travis to CircleCI for CI ([#54](https://github.com/omry/omegaconf/issues/54))
