## 2.0.0 (2020-05-04)

OmegaConf 2.0 is a major release introducing substantial new features, and introducing some incompatible changes.
The biggest new feature is Structured Configs, which extends OmegaConf into an schema validation system
as well as a configuration system.
With Structured Configs you can create OmegaConf objects from standard dataclasses or attr classes (or objects).
OmegaConf will retain the type information from the source object/class and validate that config mutations are legal.

This is the biggest OmegaConf release ever, the number of unit tests more than trippled (485 to 1571).

Features
--------

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

Bug Fixes
---------

- Disable automatic conversion of date strings in yaml decoding ([#95](https://github.com/omry/omegaconf/issues/95))
- Fixed pretty to handle strings with unicode characters correctly ([#111](https://github.com/omry/omegaconf/issues/111))
- Fix eq fails if object contains unresolveable values ([#124](https://github.com/omry/omegaconf/issues/124))
- Correctly throw MissingMandatoryValue on indirect access of missing value ([#99](https://github.com/omry/omegaconf/issues/99))
- DictConfig pop now returns the underlying value and not ValueNode ([#127](https://github.com/omry/omegaconf/issues/127))
- OmegaConf.select(key) now returns the root node when key is "" ([#135](https://github.com/omry/omegaconf/issues/135))
- Add support for loading/saving config files by using pathlib.Path objects ([#159](https://github.com/omry/omegaconf/issues/159))
- Fix AttributeError when accessing config in struct-mode with get() while providing None as default ([#174](https://github.com/omry/omegaconf/issues/174))


Deprecations and Removals
-------------------------

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

Features
--------

- ListConfig now implements + operator (Allowing concatenation with other ListConfigs) ([#36](https://github.com/omry/omegaconf/issues/36))
- OmegaConf.save() now takes a resolve flag (defaults False) ([#37](https://github.com/omry/omegaconf/issues/37))
- Add OmegaConf.masked_copy(keys) function that returns a copy of a config with a subset of the keys ([#42](https://github.com/omry/omegaconf/issues/42))
- Improve built-in env resolver to return properly typed values ("1" -> int, "1.0" -> float etc) ([#44](https://github.com/omry/omegaconf/issues/44))
- Resolvers can now accept a list of zero or more arguments, for example: "${foo:a,b,..,n}" ([#46](https://github.com/omry/omegaconf/issues/46))
- Change semantics of contains check ('x' in conf): Missing mandatory values ('???') are now considered not included and contains test returns false for them ([#49](https://github.com/omry/omegaconf/issues/49))
- Allow assignment of a tuple value into a Config ([#74](https://github.com/omry/omegaconf/issues/74))

Bug Fixes
---------

- Read-only list can no longer be replaced with command line override ([#39](https://github.com/omry/omegaconf/issues/39))
- Fix an error when expanding an empty dictionary in PyCharm debugger ([#40](https://github.com/omry/omegaconf/issues/40))
- Fix a bug in open_dict causing improper restoration of struct flag in some cases ([#47](https://github.com/omry/omegaconf/issues/47))
- Fix a bug preventing dotlist values from containing '=' (foo=bar=10 -> key: foo, value: bar=10) ([#56](https://github.com/omry/omegaconf/issues/56))
- Config.merge_with_dotlist() now throws if input is not a list or tuple of strings ([#72](https://github.com/omry/omegaconf/issues/72))
- Add copy method for DictConfig and improve shallow copy support ([#82](https://github.com/omry/omegaconf/issues/82))

Deprecations and Removals
-------------------------

- Deprecated Config.to_container() in favor of OmegaConf.to_container() (#[#41](https://github.com/omry/omegaconf/issues/41))
- Deprecated config.save(file) in favor of OmegaConf.save(config, file) ([#66](https://github.com/omry/omegaconf/issues/66))
- Remove OmegaConf.{empty(), from_string(), from_dict(), from_list()}. Use OmegaConf.create() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove Config.merge_from(). Use Config.merge_with() (deprecated since 1.1.0) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove OmegaConf.from_filename() and OmegaConf.from_file(). Use OmegaConf.load() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))

Miscellaneous changes
---------------------

- Switch from tox to nox for test automation ([#54](https://github.com/omry/omegaconf/issues/54))
- Formatting code with Black ([#54](https://github.com/omry/omegaconf/issues/54))
- Switch from Travis to CircleCI for CI ([#54](https://github.com/omry/omegaconf/issues/54))
