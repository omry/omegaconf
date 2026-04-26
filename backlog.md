# Detailed Open Issues: omry/omegaconf

*Generated on: 2026-04-26 11:24:24*
*Time estimates updated for realism on: 2026-04-26*

Status legend: `not started` · `in progress` (has open PR or recent commits) · `blocked` (awaiting reporter response) · `done` (addressed by merged PR/commit)

| Issue | Title | Category | Time Estimate | Status | PR | Created | Updated | Labels |
|-------|-------|----------|---------------|--------|----|---------|---------|--------|
| #1275 | Support Union of Structured Configs (dataclasses/attr cla... | Enhancement | 32.0h | in progress | | 2026-04-24 | 2026-04-24 |  |
| #1274 | Python 3.10 minimum: remove version guards and modernize ... | Refactor | 12.0h | not started | | 2026-04-24 | 2026-04-24 |  |
| #1271 | Support Union[Literal[...], other_type] annotations in st... | Enhancement | 20.0h | not started | | 2026-04-24 | 2026-04-24 |  |
| #1263 | Revert list_merge_mode before stable 2.4 | Enhancement | 6.0h | not started | | 2026-04-24 | 2026-04-24 |  |
| #1261 | Support unions of Dict and List container types | Enhancement | 32.0h | in progress | #1262 | 2026-04-24 | 2026-04-24 |  |
| #1255 | Evaluate migrating packaging metadata and build config to... | Enhancement | 6.0h | not started | | 2026-04-22 | 2026-04-24 | enhancement |
| #1239 | RuntimeError: dictionary changed size during iteration in... | Bug | 6.0h | in progress | #1240 | 2026-03-12 | 2026-04-24 | bug, awaiting response |
| #1236 | Instantiating a class with Union-typed fields doesn't wor... | Enhancement | 12.0h | not started | | 2026-02-22 | 2026-04-24 | enhancement |
| #1230 | Allow backslash-escaping of special characters in key paths | Enhancement | 16.0h | in progress | #1279 | 2025-12-04 | 2026-04-25 | enhancement |
| #1222 | Better doc strings | Enhancement | 12.0h | in progress | #1264 | 2025-08-21 | 2026-04-24 | enhancement |
| #1221 | Suggest similar key names when a key is not found | Enhancement | 6.0h | in progress | #1265 | 2025-08-06 | 2026-04-24 | enhancement |
| #1210 | test_nodes fails for Python >= 3.12 because of changes to... | Bug | 3.0h | blocked | | 2025-03-10 | 2026-04-24 | bug, awaiting response |
| #1205 | When merging DictConfs and interpolation fails due to MIS... | Bug | 6.0h | in progress | #1249 | 2025-01-11 | 2026-04-24 | bug |
| #1191 | Controlling conflict resolution in merge_with | Enhancement | 20.0h | in progress | #917 | 2024-08-20 | 2026-04-24 | enhancement |
| #1184 | Merging Multiple Configs with Interpolation has Unexpecte... | Enhancement | 6.0h | not started | | 2024-07-18 | 2026-04-24 | enhancement, wishlist |
| #1178 | `incompatible copy of pydevd already imported` when runni... | Bug | 6.0h | done | #1257 | 2024-06-03 | 2026-04-24 | bug, awaiting response |
| #1173 | Consider adding config "blame" metadata. | Enhancement | 40.0h | not started | | 2024-04-19 | 2026-04-25 | wishlist |
| #1161 | Feature Request: Key-based readonly flag. | Enhancement | 20.0h | in progress | | 2024-02-28 | 2026-04-24 | enhancement, awaiting response |
| #1160 | Support `Boost.Python.enum` Enums as annotation and suppo... | Enhancement | 12.0h | blocked | | 2024-02-28 | 2026-04-25 | awaiting response |
| #1156 | Convert from OrderedDict? | Enhancement | 6.0h | in progress | #1278 | 2024-02-22 | 2026-04-25 |  |
| #1154 | Merge Option of update function does not merge list | Bug | 6.0h | not started | | 2024-02-21 | 2026-04-24 | bug, needs triage |
| #1148 | ImportError: cannot import name 'get_ref_type' from 'omeg... | Bug | 2.0h | not started | | 2024-01-08 | 2026-04-24 | needs triage |
| #1132 | [Feature Request] integration between omegaconf and AWS S... | Enhancement | 12.0h | not started | | 2023-10-16 | 2026-04-24 | needs triage |
| #1131 | `OmegaConf.resolve` should crash when a resolver input is... | Bug | 6.0h | not started | | 2023-10-11 | 2026-04-24 | bug |
| #1130 | Interpolations that resolve to missing value `???` don't ... | Enhancement | 6.0h | not started | | 2023-10-11 | 2026-04-24 | needs triage |
| #1129 | Add function to check if key exists | Enhancement | 3.0h | not started | | 2023-10-03 | 2026-04-24 | needs triage |
| #1127 | Make `select` and `oc.select` more robust | Enhancement | 6.0h | not started | | 2023-09-26 | 2026-04-24 | needs triage |
| #1126 | Improve error message for relative interpolations | Bug | 3.0h | not started | | 2023-09-22 | 2026-04-24 | needs triage |
| #1123 | Inconsistencies in recursive behavior in `set_readonly()` | Bug | 6.0h | in progress | #1124 | 2023-09-20 | 2026-04-24 | bug, needs triage |
| #1120 | Escaped resolver modifying `_root_` doesn't work | Bug | 10.0h | in progress | | 2023-08-30 | 2026-04-24 | bug, needs triage |
| #1118 | `OmegaConf.missing_keys(cfg)` may fail if contained custo... | Bug | 6.0h | in progress | #1117 | 2023-08-24 | 2026-04-24 | bug, needs triage |
| #1112 | Unexpected behavior for multiline-strings | Bug | 6.0h | in progress | #1113 | 2023-08-08 | 2026-04-24 | bug, needs triage |
| #1103 | One should be allowed to re-instantiate a structured obje... | Bug | 16.0h | in progress | #1104 | 2023-07-14 | 2026-04-24 | bug, needs triage |
| #1102 | Merging nested readonly structured configs doesn't work. | Bug | 12.0h | not started | | 2023-07-14 | 2026-04-24 | bug, needs triage |
| #1095 | Validation error merging structured configs containing en... | Bug | 6.0h | not started | | 2023-06-23 | 2026-04-24 | bug, needs triage |
| #1087 | `unsafe_merge` crashes with nested structured config and ... | Bug | 6.0h | in progress | #1088 | 2023-06-11 | 2026-04-24 | bug, needs triage |
| #1086 | ListConfig errors when is [:-1] applied to empty list | Bug | 2.0h | not started | | 2023-06-02 | 2026-04-24 | bug, needs triage |
| #1061 | Enum inheritance Support | Enhancement | 16.0h | not started | | 2023-03-07 | 2026-04-24 | needs triage |
| #1059 | oc.decode resolver failing to parse "???" as MISSING | Bug | 3.0h | not started | | 2023-02-21 | 2026-04-24 | bug, needs triage |
| #1058 | structured config types are discarded on list merge | Bug | 12.0h | not started | | 2023-02-19 | 2026-04-24 | bug, needs triage |
| #1056 | How to properly escape ??? | Question | 2.0h | not started | | 2023-01-31 | 2026-04-24 | needs triage, has-workaround |
| #1054 | Structured Config schema Type validation of "list[list[fl... | Bug | 12.0h | not started | | 2023-01-22 | 2026-04-24 | bug, needs triage |
| #1052 | How can I get the data type of an attribute at a depth>1? | Enhancement | 3.0h | not started | | 2023-01-06 | 2026-04-24 | needs triage |
| #1048 | [Feature Request] Use SimpleNamespace for to_container() ... | Enhancement | 6.0h | not started | | 2022-12-26 | 2026-04-24 | needs triage |
| #1037 | Structured config type coercion not working correctly for... | Bug | 6.0h | not started | | 2022-11-28 | 2026-04-24 | bug, needs triage |
| #1035 | OmegaConf.update AssertionError on key pointing into None... | Bug | 3.0h | done | #1281 | 2022-11-17 | 2026-04-24 | bug, easy, needs triage, structured config, dictconfig |
| #1028 | Add support for equals sign and other symbols in resolver... | Enhancement | 12.0h | not started | | 2022-11-09 | 2026-04-24 | needs triage |
| #1024 | Interpolations in dictionary keys | Enhancement | 24.0h | not started | | 2022-10-29 | 2026-04-24 | enhancement, needs triage, interpolation, has-workaround |
| #1020 | Failure to merge interpolation into structured config | Bug | 6.0h | not started | | 2022-10-20 | 2026-04-24 | bug, needs triage |
| #1019 | Nested structured config validation | Bug | 12.0h | in progress | #1133 | 2022-10-04 | 2026-04-24 | bug, needs triage |
| #1006 | Allow merging configs with union operator | in Python 3.9+ | Enhancement | 6.0h | in progress | #1277 | 2022-09-15 | 2026-04-24 | enhancement, dictconfig |
| #1000 | Incompatible with current versions of antlr4 | Enhancement | 12.0h | done | #1114 | 2022-09-08 | 2026-04-24 | needs triage |
| #999 | `List[Tuple[T, ...]]` not supported | Bug | 12.0h | not started | | 2022-08-29 | 2026-04-24 | bug, needs triage |
| #998 | Merging does not preserve target `ref_type` when source f... | Bug | 12.0h | not started | | 2022-08-18 | 2026-04-24 | bug, needs triage |
| #976 | Improve support for NoneType | Bug | 12.0h | not started | | 2022-07-14 | 2026-04-24 | bug, needs triage, structured config |
| #974 | fails on `Dict[Any, str]` if passed in a list of strings | Bug | 3.0h | not started | | 2022-07-13 | 2026-04-24 | needs triage, as designed |
| #969 | Follow up on deprecation of `register_resolver()` | Enhancement | 6.0h | not started | | 2022-06-21 | 2026-04-24 | maintenance, needs triage |
| #959 | Would you please consider realizing an comparing funciton... | Build | 6.0h | not started | | 2022-06-01 | 2026-04-24 | needs triage |
| #958 | ```OmegaConf.to_yaml``` adds unexpected new lines and que... | Enhancement | 6.0h | in progress | #1075 | 2022-05-31 | 2026-04-24 | needs triage |
| #945 | `get_attr_data` doesn't handle default factory correctly | Bug | 6.0h | in progress | #1134 | 2022-05-25 | 2026-04-24 | bug, needs triage |
| #936 | Generated files use obsolete typing.io import | Bug | 2.0h | not started | | 2022-05-18 | 2026-04-24 | bug, needs triage |
| #928 | `OmegaConf.get_type` inconsistent on `NoneType` | Bug | 3.0h | not started | | 2022-05-15 | 2026-04-24 | bug, needs triage |
| #910 | Allow assigning variable interpolation to structured conf... | Bug | 12.0h | not started | | 2022-05-05 | 2026-04-24 | bug, needs triage, interpolation, structured config |
| #908 | `OmegaConf.structured(...)` may mutate its input | Bug | 6.0h | not started | | 2022-05-02 | 2026-04-24 | bug, needs triage |
| #899 | [Static typing] Make DictConfig generic in the dataclass ... | Enhancement | 32.0h | not started | | 2022-04-15 | 2026-04-24 | enhancement, needs triage |
| #898 | _promote is erasing values from the config | Bug | 12.0h | not started | | 2022-04-14 | 2026-04-24 | bug, needs triage |
| #883 | Error when creating structured config with untyped Tuple | Bug | 6.0h | not started | | 2022-03-29 | 2026-04-24 | bug, needs triage |
| #882 | Interpolation to index of custom interpolation fails, dep... | Bug | 10.0h | not started | | 2022-03-29 | 2026-04-24 | bug, needs triage, has-workaround |
| #864 | Support interpolation to integer keys (or other non-strin... | Enhancement | 6.0h | not started | | 2022-02-21 | 2026-04-24 | enhancement, wishlist, needs triage, interpolation |
| #851 | Need `datetime`-typed field support | Enhancement | 16.0h | not started | | 2022-01-22 | 2026-04-24 | enhancement, needs triage |
| #846 | Nightly builds | Build | 12.0h | not started | | 2021-12-27 | 2026-04-24 | maintenance, needs triage |
| #815 | merge-readonly interatction | Enhancement | 12.0h | not started | | 2021-10-29 | 2026-04-24 | needs triage |
| #813 | OmegaConf.masked_copy does not preserve ValueNode type | Bug | 6.0h | not started | | 2021-10-28 | 2026-04-24 | bug, low priority, needs triage |
| #803 | [Question] Why hide dictconfig debugging content? | Bug | 3.0h | not started | | 2021-10-14 | 2026-04-24 | needs triage |
| #802 | Read-only flag not working during `OmegaConf.merge` | Bug | 6.0h | not started | | 2021-10-13 | 2026-04-24 | bug, needs triage |
| #801 | Feature: Read-only flag on leaf field | Enhancement | 16.0h | not started | | 2021-10-13 | 2026-04-24 | enhancement, needs triage, priority_low |
| #794 | OmegaConf is vulenrable to ddos via specially crafted yam... | Bug | 6.0h | not started | | 2021-10-05 | 2026-04-24 | bug, needs triage, priority_medium |
| #791 | consider dropping formal Python 3.6 support for OmegaConf... | Enhancement | 6.0h | done | #1109, #1225 | 2021-09-29 | 2026-04-24 |  |
| #788 | validation error when default_factory produces structured... | Bug | 6.0h | not started | | 2021-09-14 | 2026-04-24 | bug, needs triage, priority_low |
| #771 | Document special treatment of "???" by OmegaConf.merge | Documentation | 2.0h | not started | | 2021-07-21 | 2026-04-24 | documentation, needs triage |
| #762 | Dereferencing a resolver that returns "???" | Bug | 6.0h | not started | | 2021-06-28 | 2026-04-24 | bug, needs triage |
| #755 | negative list indices in variable interpolation | Enhancement | 6.0h | in progress | #1212 | 2021-06-17 | 2026-04-25 | enhancement |
| #750 | Followup: refactor ListConfig.{insert,append} | Refactor | 16.0h | not started | | 2021-06-15 | 2026-04-24 | needs triage |
| #731 | Subclasses of `Generic` cannot be used as structured configs | Bug | 20.0h | not started | | 2021-05-24 | 2026-04-25 | bug, needs triage, priority_medium |
| #726 | Consistent resolving of interpolations to random resolver... | Enhancement | 12.0h | not started | | 2021-05-20 | 2026-04-24 | needs triage |
| #725 | Support assignment of numpy floats to FloatNode | Enhancement | 6.0h | not started | | 2021-05-20 | 2026-04-24 | enhancement, needs triage, priority_low |
| #702 | Provide correct full key on nested Structured Config crea... | Bug | 6.0h | not started | | 2021-04-29 | 2026-04-24 | bug, wishlist, needs triage, priority_low |
| #651 | Interpolations can't refer to non-string keys | Bug | 12.0h | not started | | 2021-03-29 | 2026-04-24 | bug, needs triage, priority_low |
| #612 | Automatic validation of resolver arguments | Enhancement | 20.0h | not started | | 2021-03-16 | 2026-04-24 | enhancement, wishlist, needs triage, priority_low |
| #610 | Feature: nested string interpolations | Enhancement | 24.0h | not started | | 2021-03-16 | 2026-04-24 | needs triage, has-workaround, priority_low |
| #580 | _ensure_container does not set flags if target is already... | Bug | 6.0h | not started | | 2021-03-05 | 2026-04-24 | bug, needs triage, priority_medium |
| #537 | Refactor test_errors.py | Bug | 20.0h | not started | | 2021-02-11 | 2026-04-24 | maintenance, needs triage |
| #536 | Generated API docs for omegaconf | Documentation | 16.0h | in progress | #1264 | 2021-02-11 | 2026-04-24 | maintenance, needs triage |
| #519 | allow exporting to dotlist-style format | Enhancement | 6.0h | not started | | 2021-02-05 | 2026-04-25 | enhancement |
| #459 | Consider deprecating assignment of strings to non-string ... | Enhancement | 16.0h | not started | | 2020-12-15 | 2026-04-24 | needs triage, priority_low |
| #440 | Deprecate legacy_register_resolver and new_register_resolver | Enhancement | 6.0h | not started | | 2020-11-18 | 2026-04-24 | needs triage, priority_low |
| #422 | Allow the use of typing.Literal as a pythonic alternative... | Enhancement | 12.0h | in progress | #1272 | 2020-10-27 | 2026-04-24 | enhancement, wishlist, needs triage |
| #392 | Improve Tuple support | Enhancement | 20.0h | not started | | 2020-09-24 | 2026-04-24 | enhancement, needs triage |
| #265 | Attribute/KeyError can suggest matches from the available... | Enhancement | 6.0h | in progress | #1265 | 2020-06-11 | 2026-04-24 | enhancement, needs triage, priority_low |
| #182 | Config blame mode | Enhancement | 40.0h | not started | | 2020-03-27 | 2026-04-24 | enhancement, needs triage |

## Summary Statistics

### By Category

| Category | Count | Percentage |
|----------|-------|------------|
| Bug | 47 | 47.0% |
| Enhancement | 46 | 46.0% |
| Refactor | 2 | 2.0% |
| Build | 2 | 2.0% |
| Documentation | 2 | 2.0% |
| Question | 1 | 1.0% |

### By Status

| Status | Count |
|--------|-------|
| not started | 69 |
| in progress | 24 |
| blocked | 2 |
| done | 4 |

### Time Estimates

- **Total Estimated Time**: 883.0 hours
- **Average per Issue**: 8.8 hours
- **Median Estimate**: 6.0 hours

### Notes on Estimate Methodology

Original estimates used flat rates (8h Enhancements, 4h Bugs, 3h Build, 1h Documentation). Revised estimates account for complexity:

- **Trivial** (import fix, single edge case, docs update): 2–3h
- **Standard bug** (investigate + fix + tests): 6h
- **Complex bug** (deep cross-subsystem interaction): 10–12h
- **Small enhancement** (new API function, error message): 3–6h
- **Standard enhancement** (parser changes, type handling): 12h
- **Large enhancement** (multi-subsystem feature): 16–24h
- **Architectural** (generic typing, blame metadata, Union support): 32–40h

Issues labelled `easy` are estimated at the low end. Issues with `has-workaround` or `priority_low` retain full implementation estimates — the label reflects urgency, not effort.
