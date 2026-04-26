# Detailed Open Issues: omry/omegaconf

<!-- BEGIN GENERATED BACKLOG -->
*Generated on: 2026-04-26*

**Status legend:**
| Status | Meaning |
|--------|---------|
| ⬜ `not started` | No open PR |
| 🔄 `in progress` | Open PR by a maintainer |
| 🤝 `community PR` | Open PR by a non-maintainer |
| 🚫 `blocked` | Labelled `awaiting response`, no open PR |
| ✅ `done` | Closed or addressed by a merged PR |

**Category:** 🐛 Bug · ✨ Enhancement · 🔧 Refactor · 🏗️ Build · 📄 Documentation · ❓ Question

## Summary Statistics

### By Category (open issues only)

| Category | Count | Percentage |
|----------|-------|------------|
| 🐛 Bug | 44 | 44.0% |
| ✨ Enhancement | 49 | 49.0% |
| 🔧 Refactor | 2 | 2.0% |
| 🏗️ Build | 1 | 1.0% |
| 📄 Documentation | 2 | 2.0% |
| ❓ Question | 2 | 2.0% |
| **Total** | **100** | |

### By Status

| Status | Count |
|--------|-------|
| 🔄 in progress | 14 |
| 🤝 community PR | 7 |
| 🚫 blocked | 3 |
| ⬜ not started | 76 |
| ✅ done | 4 |


| Issue | Title | Category | Status | PR | Created | Updated | Labels |
|-------|-------|----------|----|---------|---------|---------|--------|
| [#1275](https://github.com/omry/omegaconf/issues/1275) | Support Union of Structured Configs (dataclasses/attr c... | ✨ Enhancement | 🔄 in progress | [#1262](https://github.com/omry/omegaconf/pull/1262) | 2026-04-24 | 2026-04-24 |  |
| [#1261](https://github.com/omry/omegaconf/issues/1261) | Support unions of Dict and List container types | ✨ Enhancement | 🔄 in progress | [#1262](https://github.com/omry/omegaconf/pull/1262) | 2026-04-24 | 2026-04-24 |  |
| [#1230](https://github.com/omry/omegaconf/issues/1230) | Allow backslash-escaping of special characters in key p... | ✨ Enhancement | 🔄 in progress | [#1279](https://github.com/omry/omegaconf/pull/1279) | 2025-12-04 | 2026-04-25 | enhancement |
| [#1222](https://github.com/omry/omegaconf/issues/1222) | Better doc strings | ✨ Enhancement | 🔄 in progress | [#1264](https://github.com/omry/omegaconf/pull/1264) | 2025-08-21 | 2026-04-24 | enhancement |
| [#1221](https://github.com/omry/omegaconf/issues/1221) | Suggest similar key names when a key is not found | ✨ Enhancement | 🔄 in progress | [#1265](https://github.com/omry/omegaconf/pull/1265) | 2025-08-06 | 2026-04-24 | enhancement |
| [#1205](https://github.com/omry/omegaconf/issues/1205) | When merging DictConfs and interpolation fails due to M... | 🐛 Bug | 🔄 in progress | [#1249](https://github.com/omry/omegaconf/pull/1249) | 2025-01-11 | 2026-04-24 | bug |
| [#1156](https://github.com/omry/omegaconf/issues/1156) | Convert from OrderedDict? | ✨ Enhancement | 🔄 in progress | [#1278](https://github.com/omry/omegaconf/pull/1278) | 2024-02-22 | 2026-04-25 |  |
| [#422](https://github.com/omry/omegaconf/issues/422) | Allow the use of typing.Literal as a pythonic alternati... | ✨ Enhancement | 🔄 in progress | [#1272](https://github.com/omry/omegaconf/pull/1272), [#865](https://github.com/omry/omegaconf/pull/865) | 2020-10-27 | 2026-04-24 | enhancement, wishlist, needs triage |
| [#265](https://github.com/omry/omegaconf/issues/265) | Attribute/KeyError can suggest matches from the availab... | ✨ Enhancement | 🔄 in progress | [#1265](https://github.com/omry/omegaconf/pull/1265) | 2020-06-11 | 2026-04-24 | enhancement, needs triage, priority_low |
| [#1006](https://github.com/omry/omegaconf/issues/1006) | Allow merging configs with union operator \| in Python 3.9+ | ✨ Enhancement | 🔄 in progress | [#1277](https://github.com/omry/omegaconf/pull/1277) | 2022-09-15 | 2026-04-24 | enhancement, dictconfig |
| [#1087](https://github.com/omry/omegaconf/issues/1087) | `unsafe_merge` crashes with nested structured config an... | 🐛 Bug | 🔄 in progress | [#1088](https://github.com/omry/omegaconf/pull/1088) | 2023-06-11 | 2026-04-24 | bug, needs triage |
| [#1103](https://github.com/omry/omegaconf/issues/1103) | One should be allowed to re-instantiate a structured ob... | 🐛 Bug | 🔄 in progress | [#1104](https://github.com/omry/omegaconf/pull/1104) | 2023-07-14 | 2026-04-24 | bug, needs triage |
| [#1112](https://github.com/omry/omegaconf/issues/1112) | Unexpected behavior for multiline-strings | 🐛 Bug | 🔄 in progress | [#1113](https://github.com/omry/omegaconf/pull/1113) | 2023-08-08 | 2026-04-24 | bug, needs triage |
| [#1120](https://github.com/omry/omegaconf/issues/1120) | Escaped resolver modifying `_root_` doesn't work | 🐛 Bug | 🔄 in progress | [#1113](https://github.com/omry/omegaconf/pull/1113) | 2023-08-30 | 2026-04-24 | bug, needs triage |
| [#1239](https://github.com/omry/omegaconf/issues/1239) | RuntimeError: dictionary changed size during iteration... | 🐛 Bug | 🤝 community PR | [#1240](https://github.com/omry/omegaconf/pull/1240) | 2026-03-12 | 2026-04-24 | bug, awaiting response |
| [#1123](https://github.com/omry/omegaconf/issues/1123) | Inconsistencies in recursive behavior in `set_readonly()` | 🐛 Bug | 🤝 community PR | [#1124](https://github.com/omry/omegaconf/pull/1124) | 2023-09-20 | 2026-04-24 | bug, needs triage |
| [#1118](https://github.com/omry/omegaconf/issues/1118) | `OmegaConf.missing_keys(cfg)` may fail if contained cus... | 🐛 Bug | 🤝 community PR | [#1117](https://github.com/omry/omegaconf/pull/1117) | 2023-08-24 | 2026-04-24 | bug, needs triage |
| [#1019](https://github.com/omry/omegaconf/issues/1019) | Nested structured config validation | 🐛 Bug | 🤝 community PR | [#1133](https://github.com/omry/omegaconf/pull/1133) | 2022-10-04 | 2026-04-24 | bug, needs triage |
| [#945](https://github.com/omry/omegaconf/issues/945) | `get_attr_data` doesn't handle default factory correctly | 🐛 Bug | 🤝 community PR | [#1134](https://github.com/omry/omegaconf/pull/1134) | 2022-05-25 | 2026-04-24 | bug, needs triage |
| [#91](https://github.com/omry/omegaconf/issues/91) | Consider supporting basic operators in interpolations o... | ✨ Enhancement | 🤝 community PR | [#1229](https://github.com/omry/omegaconf/pull/1229) | 2019-12-02 | 2026-04-24 | enhancement, needs triage, has-workaround |
| [#755](https://github.com/omry/omegaconf/issues/755) | negative list indices in variable interpolation | ✨ Enhancement | 🤝 community PR | [#1212](https://github.com/omry/omegaconf/pull/1212) | 2021-06-17 | 2026-04-25 | enhancement |
| [#1210](https://github.com/omry/omegaconf/issues/1210) | test_nodes fails for Python >= 3.12 because of changes... | 🐛 Bug | 🚫 blocked |  | 2025-03-10 | 2026-04-24 | bug, awaiting response |
| [#1160](https://github.com/omry/omegaconf/issues/1160) | Support `Boost.Python.enum` Enums as annotation and sup... | ✨ Enhancement | 🚫 blocked |  | 2024-02-28 | 2026-04-25 | awaiting response |
| [#1161](https://github.com/omry/omegaconf/issues/1161) | Feature Request: Key-based readonly flag. | ✨ Enhancement | 🚫 blocked |  | 2024-02-28 | 2026-04-24 | enhancement, awaiting response |
| [#1274](https://github.com/omry/omegaconf/issues/1274) | Python 3.10 minimum: remove version guards and moderniz... | 🔧 Refactor | ⬜ not started |  | 2026-04-24 | 2026-04-24 |  |
| [#1271](https://github.com/omry/omegaconf/issues/1271) | Support Union[Literal[...], other_type] annotations in... | ✨ Enhancement | ⬜ not started |  | 2026-04-24 | 2026-04-24 |  |
| [#1263](https://github.com/omry/omegaconf/issues/1263) | Revert list_merge_mode before stable 2.4 | ✨ Enhancement | ⬜ not started |  | 2026-04-24 | 2026-04-24 |  |
| [#1255](https://github.com/omry/omegaconf/issues/1255) | Evaluate migrating packaging metadata and build config... | ✨ Enhancement | ⬜ not started |  | 2026-04-22 | 2026-04-24 | enhancement |
| [#1236](https://github.com/omry/omegaconf/issues/1236) | Instantiating a class with Union-typed fields doesn't w... | ✨ Enhancement | ⬜ not started |  | 2026-02-22 | 2026-04-24 | enhancement |
| [#1184](https://github.com/omry/omegaconf/issues/1184) | Merging Multiple Configs with Interpolation has Unexpec... | ✨ Enhancement | ⬜ not started |  | 2024-07-18 | 2026-04-24 | enhancement, wishlist |
| [#1173](https://github.com/omry/omegaconf/issues/1173) | Consider adding config "blame" metadata. | ✨ Enhancement | ⬜ not started |  | 2024-04-19 | 2026-04-25 | wishlist |
| [#1154](https://github.com/omry/omegaconf/issues/1154) | Merge Option of update function does not merge list | 🐛 Bug | ⬜ not started |  | 2024-02-21 | 2026-04-24 | bug, needs triage |
| [#1148](https://github.com/omry/omegaconf/issues/1148) | ImportError: cannot import name 'get_ref_type' from 'om... | 🐛 Bug | ⬜ not started |  | 2024-01-08 | 2026-04-24 | needs triage |
| [#1132](https://github.com/omry/omegaconf/issues/1132) | [Feature Request] integration between omegaconf and AWS... | ✨ Enhancement | ⬜ not started |  | 2023-10-16 | 2026-04-24 | needs triage |
| [#1131](https://github.com/omry/omegaconf/issues/1131) | `OmegaConf.resolve` should crash when a resolver input... | 🐛 Bug | ⬜ not started |  | 2023-10-11 | 2026-04-24 | bug |
| [#1130](https://github.com/omry/omegaconf/issues/1130) | Interpolations that resolve to missing value `???` don'... | ✨ Enhancement | ⬜ not started |  | 2023-10-11 | 2026-04-24 | needs triage |
| [#1129](https://github.com/omry/omegaconf/issues/1129) | Add function to check if key exists | ✨ Enhancement | ⬜ not started |  | 2023-10-03 | 2026-04-24 | needs triage |
| [#1127](https://github.com/omry/omegaconf/issues/1127) | Make `select` and `oc.select` more robust | ✨ Enhancement | ⬜ not started |  | 2023-09-26 | 2026-04-24 | needs triage |
| [#1126](https://github.com/omry/omegaconf/issues/1126) | Improve error message for relative interpolations | 🐛 Bug | ⬜ not started |  | 2023-09-22 | 2026-04-24 | needs triage |
| [#1102](https://github.com/omry/omegaconf/issues/1102) | Merging nested readonly structured configs doesn't work. | 🐛 Bug | ⬜ not started |  | 2023-07-14 | 2026-04-24 | bug, needs triage |
| [#1095](https://github.com/omry/omegaconf/issues/1095) | Validation error merging structured configs containing... | 🐛 Bug | ⬜ not started |  | 2023-06-23 | 2026-04-24 | bug, needs triage |
| [#1086](https://github.com/omry/omegaconf/issues/1086) | ListConfig errors when is [:-1] applied to empty list | 🐛 Bug | ⬜ not started |  | 2023-06-02 | 2026-04-24 | bug, needs triage |
| [#1061](https://github.com/omry/omegaconf/issues/1061) | Enum inheritance Support | ✨ Enhancement | ⬜ not started |  | 2023-03-07 | 2026-04-24 | needs triage |
| [#1059](https://github.com/omry/omegaconf/issues/1059) | oc.decode resolver failing to parse "???" as MISSING | 🐛 Bug | ⬜ not started |  | 2023-02-21 | 2026-04-24 | bug, needs triage |
| [#1058](https://github.com/omry/omegaconf/issues/1058) | structured config types are discarded on list merge | 🐛 Bug | ⬜ not started |  | 2023-02-19 | 2026-04-24 | bug, needs triage |
| [#1056](https://github.com/omry/omegaconf/issues/1056) | How to properly escape ??? | ❓ Question | ⬜ not started |  | 2023-01-31 | 2026-04-24 | needs triage, has-workaround |
| [#1054](https://github.com/omry/omegaconf/issues/1054) | Structured Config schema Type validation of "list[list[... | 🐛 Bug | ⬜ not started |  | 2023-01-22 | 2026-04-24 | bug, needs triage |
| [#1052](https://github.com/omry/omegaconf/issues/1052) | How can I get the data type of an attribute at a depth>1? | ✨ Enhancement | ⬜ not started |  | 2023-01-06 | 2026-04-24 | needs triage |
| [#1048](https://github.com/omry/omegaconf/issues/1048) | [Feature Request] Use SimpleNamespace for to_container(... | ✨ Enhancement | ⬜ not started |  | 2022-12-26 | 2026-04-24 | needs triage |
| [#1037](https://github.com/omry/omegaconf/issues/1037) | Structured config type coercion not working correctly f... | 🐛 Bug | ⬜ not started |  | 2022-11-28 | 2026-04-24 | bug, needs triage |
| [#1028](https://github.com/omry/omegaconf/issues/1028) | Add support for equals sign and other symbols in resolv... | ✨ Enhancement | ⬜ not started |  | 2022-11-09 | 2026-04-24 | needs triage |
| [#1024](https://github.com/omry/omegaconf/issues/1024) | Interpolations in dictionary keys | ✨ Enhancement | ⬜ not started |  | 2022-10-29 | 2026-04-24 | enhancement, needs triage, interpolation, has-workaround |
| [#1020](https://github.com/omry/omegaconf/issues/1020) | Failure to merge interpolation into structured config | 🐛 Bug | ⬜ not started |  | 2022-10-20 | 2026-04-24 | bug, needs triage |
| [#999](https://github.com/omry/omegaconf/issues/999) | `List[Tuple[T, ...]]` not supported | 🐛 Bug | ⬜ not started |  | 2022-08-29 | 2026-04-24 | bug, needs triage |
| [#998](https://github.com/omry/omegaconf/issues/998) | Merging does not preserve target `ref_type` when source... | 🐛 Bug | ⬜ not started |  | 2022-08-18 | 2026-04-24 | bug, needs triage |
| [#976](https://github.com/omry/omegaconf/issues/976) | Improve support for NoneType | 🐛 Bug | ⬜ not started |  | 2022-07-14 | 2026-04-24 | bug, needs triage, structured config |
| [#974](https://github.com/omry/omegaconf/issues/974) | fails on `Dict[Any, str]` if passed in a list of strings | 🐛 Bug | ⬜ not started |  | 2022-07-13 | 2026-04-24 | needs triage, as designed |
| [#969](https://github.com/omry/omegaconf/issues/969) | Follow up on deprecation of `register_resolver()` | ✨ Enhancement | ⬜ not started |  | 2022-06-21 | 2026-04-24 | maintenance, needs triage |
| [#959](https://github.com/omry/omegaconf/issues/959) | Would you please consider realizing an comparing funcit... | ✨ Enhancement | ⬜ not started |  | 2022-06-01 | 2026-04-24 | needs triage |
| [#936](https://github.com/omry/omegaconf/issues/936) | Generated files use obsolete typing.io import | 🐛 Bug | ⬜ not started |  | 2022-05-18 | 2026-04-24 | bug, needs triage |
| [#928](https://github.com/omry/omegaconf/issues/928) | `OmegaConf.get_type` inconsistent on `NoneType` | 🐛 Bug | ⬜ not started |  | 2022-05-15 | 2026-04-24 | bug, needs triage |
| [#910](https://github.com/omry/omegaconf/issues/910) | Allow assigning variable interpolation to structured co... | 🐛 Bug | ⬜ not started |  | 2022-05-05 | 2026-04-24 | bug, needs triage, interpolation, structured config |
| [#908](https://github.com/omry/omegaconf/issues/908) | `OmegaConf.structured(...)` may mutate its input | 🐛 Bug | ⬜ not started |  | 2022-05-02 | 2026-04-24 | bug, needs triage |
| [#899](https://github.com/omry/omegaconf/issues/899) | [Static typing] Make DictConfig generic in the dataclas... | ✨ Enhancement | ⬜ not started |  | 2022-04-15 | 2026-04-24 | enhancement, needs triage |
| [#898](https://github.com/omry/omegaconf/issues/898) | _promote is erasing values from the config | 🐛 Bug | ⬜ not started |  | 2022-04-14 | 2026-04-24 | bug, needs triage |
| [#883](https://github.com/omry/omegaconf/issues/883) | Error when creating structured config with untyped Tuple | 🐛 Bug | ⬜ not started |  | 2022-03-29 | 2026-04-24 | bug, needs triage |
| [#882](https://github.com/omry/omegaconf/issues/882) | Interpolation to index of custom interpolation fails, d... | 🐛 Bug | ⬜ not started |  | 2022-03-29 | 2026-04-24 | bug, needs triage, has-workaround |
| [#864](https://github.com/omry/omegaconf/issues/864) | Support interpolation to integer keys (or other non-str... | ✨ Enhancement | ⬜ not started |  | 2022-02-21 | 2026-04-24 | enhancement, wishlist, needs triage, interpolation |
| [#851](https://github.com/omry/omegaconf/issues/851) | Need `datetime`-typed field support | ✨ Enhancement | ⬜ not started |  | 2022-01-22 | 2026-04-24 | enhancement, needs triage |
| [#846](https://github.com/omry/omegaconf/issues/846) | Nightly builds | 🏗️ Build | ⬜ not started |  | 2021-12-27 | 2026-04-24 | maintenance, needs triage |
| [#815](https://github.com/omry/omegaconf/issues/815) | merge-readonly interatction | ✨ Enhancement | ⬜ not started |  | 2021-10-29 | 2026-04-24 | needs triage |
| [#813](https://github.com/omry/omegaconf/issues/813) | OmegaConf.masked_copy does not preserve ValueNode type | 🐛 Bug | ⬜ not started |  | 2021-10-28 | 2026-04-24 | bug, low priority, needs triage |
| [#803](https://github.com/omry/omegaconf/issues/803) | [Question] Why hide dictconfig debugging content? | ❓ Question | ⬜ not started |  | 2021-10-14 | 2026-04-24 | needs triage |
| [#802](https://github.com/omry/omegaconf/issues/802) | Read-only flag not working during `OmegaConf.merge` | 🐛 Bug | ⬜ not started |  | 2021-10-13 | 2026-04-24 | bug, needs triage |
| [#801](https://github.com/omry/omegaconf/issues/801) | Feature: Read-only flag on leaf field | ✨ Enhancement | ⬜ not started |  | 2021-10-13 | 2026-04-24 | enhancement, needs triage, priority_low |
| [#794](https://github.com/omry/omegaconf/issues/794) | OmegaConf is vulenrable to ddos via specially crafted y... | 🐛 Bug | ⬜ not started |  | 2021-10-05 | 2026-04-24 | bug, needs triage, priority_medium |
| [#788](https://github.com/omry/omegaconf/issues/788) | validation error when default_factory produces structur... | 🐛 Bug | ⬜ not started |  | 2021-09-14 | 2026-04-24 | bug, needs triage, priority_low |
| [#771](https://github.com/omry/omegaconf/issues/771) | Document special treatment of "???" by OmegaConf.merge | 📄 Documentation | ⬜ not started |  | 2021-07-21 | 2026-04-24 | documentation, needs triage |
| [#762](https://github.com/omry/omegaconf/issues/762) | Dereferencing a resolver that returns "???" | 🐛 Bug | ⬜ not started |  | 2021-06-28 | 2026-04-24 | bug, needs triage |
| [#750](https://github.com/omry/omegaconf/issues/750) | Followup: refactor ListConfig.{insert,append} | 🔧 Refactor | ⬜ not started |  | 2021-06-15 | 2026-04-24 | needs triage |
| [#731](https://github.com/omry/omegaconf/issues/731) | Subclasses of `Generic` cannot be used as structured co... | 🐛 Bug | ⬜ not started |  | 2021-05-24 | 2026-04-25 | bug, needs triage, priority_medium |
| [#726](https://github.com/omry/omegaconf/issues/726) | Consistent resolving of interpolations to random resolv... | ✨ Enhancement | ⬜ not started |  | 2021-05-20 | 2026-04-24 | needs triage |
| [#725](https://github.com/omry/omegaconf/issues/725) | Support assignment of numpy floats to FloatNode | ✨ Enhancement | ⬜ not started |  | 2021-05-20 | 2026-04-24 | enhancement, needs triage, priority_low |
| [#702](https://github.com/omry/omegaconf/issues/702) | Provide correct full key on nested Structured Config cr... | 🐛 Bug | ⬜ not started |  | 2021-04-29 | 2026-04-24 | bug, wishlist, needs triage, priority_low |
| [#651](https://github.com/omry/omegaconf/issues/651) | Interpolations can't refer to non-string keys | 🐛 Bug | ⬜ not started |  | 2021-03-29 | 2026-04-24 | bug, needs triage, priority_low |
| [#612](https://github.com/omry/omegaconf/issues/612) | Automatic validation of resolver arguments | ✨ Enhancement | ⬜ not started |  | 2021-03-16 | 2026-04-24 | enhancement, wishlist, needs triage, priority_low |
| [#610](https://github.com/omry/omegaconf/issues/610) | Feature: nested string interpolations | ✨ Enhancement | ⬜ not started |  | 2021-03-16 | 2026-04-24 | needs triage, has-workaround, priority_low |
| [#580](https://github.com/omry/omegaconf/issues/580) | _ensure_container does not set flags if target is alrea... | 🐛 Bug | ⬜ not started |  | 2021-03-05 | 2026-04-24 | bug, needs triage, priority_medium |
| [#537](https://github.com/omry/omegaconf/issues/537) | Refactor test_errors.py | 🐛 Bug | ⬜ not started |  | 2021-02-11 | 2026-04-24 | maintenance, needs triage |
| [#519](https://github.com/omry/omegaconf/issues/519) | allow exporting to dotlist-style format | ✨ Enhancement | ⬜ not started |  | 2021-02-05 | 2026-04-25 | enhancement |
| [#459](https://github.com/omry/omegaconf/issues/459) | Consider deprecating assignment of strings to non-strin... | ✨ Enhancement | ⬜ not started |  | 2020-12-15 | 2026-04-24 | needs triage, priority_low |
| [#440](https://github.com/omry/omegaconf/issues/440) | Deprecate legacy_register_resolver and new_register_res... | ✨ Enhancement | ⬜ not started |  | 2020-11-18 | 2026-04-24 | needs triage, priority_low |
| [#392](https://github.com/omry/omegaconf/issues/392) | Improve Tuple support | ✨ Enhancement | ⬜ not started |  | 2020-09-24 | 2026-04-24 | enhancement, needs triage |
| [#182](https://github.com/omry/omegaconf/issues/182) | Config blame mode | ✨ Enhancement | ⬜ not started |  | 2020-03-27 | 2026-04-24 | enhancement, needs triage |
| [#181](https://github.com/omry/omegaconf/issues/181) | [Feature Request] Add .toJSON() method | ✨ Enhancement | ⬜ not started |  | 2020-03-25 | 2026-04-24 | enhancement, needs triage |
| [#144](https://github.com/omry/omegaconf/issues/144) | Full Union type support in structured configs | ✨ Enhancement | ⬜ not started |  | 2020-01-30 | 2026-04-24 | enhancement, priority_high |
| [#131](https://github.com/omry/omegaconf/issues/131) | Evaluate usefulness of pep-593 for structured configs | ✨ Enhancement | ⬜ not started |  | 2020-01-21 | 2026-04-24 | needs triage |
| [#536](https://github.com/omry/omegaconf/issues/536) | Generated API docs for omegaconf | 📄 Documentation | ⬜ not started |  | 2021-02-11 | 2026-04-24 | maintenance, needs triage |
| [#958](https://github.com/omry/omegaconf/issues/958) | ```OmegaConf.to_yaml``` adds unexpected new lines and q... | ✨ Enhancement | ⬜ not started |  | 2022-05-31 | 2026-04-24 | needs triage |
| [#1191](https://github.com/omry/omegaconf/issues/1191) | Controlling conflict resolution in merge_with | ✨ Enhancement | ⬜ not started |  | 2024-08-20 | 2026-04-24 | enhancement |
| [#1178](https://github.com/omry/omegaconf/issues/1178) | `incompatible copy of pydevd already imported` when run... | 🐛 Bug | ✅ done | [#1257](https://github.com/omry/omegaconf/pull/1257) | 2024-06-03 | 2026-04-24 | bug, awaiting response |
| [#1035](https://github.com/omry/omegaconf/issues/1035) | OmegaConf.update AssertionError on key pointing into No... | 🐛 Bug | ✅ done | [#1281](https://github.com/omry/omegaconf/pull/1281) | 2022-11-17 | 2026-04-24 | bug, easy, needs triage, structured config, dictconfig |
| [#1000](https://github.com/omry/omegaconf/issues/1000) | Incompatible with current versions of antlr4 | ✨ Enhancement | ✅ done | [#1114](https://github.com/omry/omegaconf/pull/1114) | 2022-09-08 | 2026-04-24 | needs triage |
| [#791](https://github.com/omry/omegaconf/issues/791) | consider dropping formal Python 3.6 support for OmegaCo... | ✨ Enhancement | ✅ done | [#1109](https://github.com/omry/omegaconf/pull/1109), [#1225](https://github.com/omry/omegaconf/pull/1225) | 2021-09-29 | 2026-04-24 |  |
<!-- END GENERATED BACKLOG -->

## Manual comments
<!-- BEGIN MANUAL COMMENTS -->
```json
{
  "issues": {},
  "general": []
}
```
<!-- END MANUAL COMMENTS -->
