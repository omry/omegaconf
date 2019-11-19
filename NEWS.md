## 1.4.0 (2019-11-19)


Features
--------

- ListConfig now implements + operator (Allowing concatenation with other ListConfigs) (#36)
- OmegaConf.save() now takes a resolve flag (defaults False) (#37)
- Add OmegaConf.masked_copy(keys) function that returns a copy of a config with a subset of the keys (#42)
- Improve built-in env resolver to return properly typed values ("1" -> int, "1.0" -> float etc) (#44)
- Resolvers can now accept a list of zero or more arguments, for example: "${foo:a,b,..,n}" (#46)
- Change semantics of contains check ('x' in conf): Missing mandatory values ('???') are now considered not included and contains test returns false for them (#49)
- Allow assignment of a tuple value into a Config (#74)

Bug Fixes
---------

- Read-only list can no longer be replaced with command line override (#39)
- Fix an error when expanding an empty dictionary in PyCharm debugger (#40)
- Fix a bug in open_dict causing improper restoration of struct flag in some cases (#47)
- Fix a bug preventing dotlist values from containing '=' (foo=bar=10 -> key: foo, value: bar=10) (#56)
- Config.merge_with_dotlist() now throws if input is not a list or tuple of strings (#72)
- Add copy method for DictConfig and improve shallow copy support (#82)

Deprecations and Removals
-------------------------

- Deprecated Config.to_container() in favor of OmegaConf.to_container() (#41)
- Deprecated config.save(file) in favor of OmegaConf.save(config, file) (#66)
- Remove OmegaConf.{empty(), from_string(), from_dict(), from_list()}. Use OmegaConf.create() (deprecated since 1.1.5) (#67)
- Remove Config.merge_from(). Use Config.merge_with() (deprecated since 1.1.0) (#67)
- Remove OmegaConf.from_filename() and OmegaConf.from_file(). Use OmegaConf.load() (deprecated since 1.1.5) (#67)

Miscellaneous changes
---------------------

- Switch from tox to nox for test automation (#54)
- Formatting code with Black (#54)
- Switch from Travis to CircleCI for CI (#54)
