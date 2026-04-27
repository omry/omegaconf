# Detailed Open Issues: omry/omegaconf

<!-- BEGIN GENERATED BACKLOG -->
*Generated on: 2026-04-27*

<table><tr><td>

**Status legend**

| Status | Meaning |
|--------|---------|
| ⬜ `not started` | No open PR |
| 🔄 `in progress` | Open PR by a maintainer |
| 🤝 `community PR` | Open PR by a non-maintainer |
| 🚫 `blocked` | Labelled `awaiting response`, no open PR |
| ✅ `done` | Closed or addressed by a merged PR |

</td><td>

**Category legend**

| Category |
|----------|
| 🐛 `Bug` |
| ✨ `Enhancement` |
| 🔧 `Refactor` |
| 🏗️ `Build` |
| 📄 `Documentation` |
| ❓ `Question` |

</td></tr><tr><td>

**By Category (open issues only)**

| Category | Count | Percentage |
|----------|-------|------------|
| 🐛 Bug | 41 | 45.6% |
| ✨ Enhancement | 43 | 47.8% |
| 🔧 Refactor | 2 | 2.2% |
| 🏗️ Build | 1 | 1.1% |
| 📄 Documentation | 3 | 3.3% |
| ❓ Question | 0 | 0.0% |
| **Total** | **90** | |

</td><td>

**By Status**

| Status | Count |
|--------|-------|
| 🔄 in progress | 4 |
| 🤝 community PR | 5 |
| 🚫 blocked | 4 |
| ⬜ not started | 77 |
| ✅ done | 12 |


</td></tr></table>

| Issue | Title | Category | Status | PR | Created | Updated | Labels |
|-------|-------|----------|----|---------|---------|---------|--------|
| [#1087](https://github.com/omry/omegaconf/issues/1087) | `unsafe_merge` crashes with nested structured config an... | <span title="Bug">🐛</span> | <span title="in progress">🔄</span> | [#1285](https://github.com/omry/omegaconf/pull/1285) | 2023‑06‑11 | 2026‑04‑27 | bug |
| [#1103](https://github.com/omry/omegaconf/issues/1103) | One should be allowed to re-instantiate a structured ob... | <span title="Bug">🐛</span> | <span title="in progress">🔄</span> | [#1104](https://github.com/omry/omegaconf/pull/1104) | 2023‑07‑14 | 2026‑04‑24 | bug, needs triage |
| [#1112](https://github.com/omry/omegaconf/issues/1112) | Unexpected behavior for multiline-strings | <span title="Bug">🐛</span> | <span title="in progress">🔄</span> | [#1113](https://github.com/omry/omegaconf/pull/1113) | 2023‑08‑08 | 2026‑04‑24 | bug, needs triage |
| [#1120](https://github.com/omry/omegaconf/issues/1120) | Escaped resolver modifying `_root_` doesn't work | <span title="Bug">🐛</span> | <span title="in progress">🔄</span> | [#1113](https://github.com/omry/omegaconf/pull/1113) | 2023‑08‑30 | 2026‑04‑24 | bug, needs triage |
| [#91](https://github.com/omry/omegaconf/issues/91) | Consider supporting basic operators in interpolations o... | <span title="Enhancement">✨</span> | <span title="community PR">🤝</span> | [#1229](https://github.com/omry/omegaconf/pull/1229) | 2019‑12‑02 | 2026‑04‑26 | enhancement, has-workaround |
| [#755](https://github.com/omry/omegaconf/issues/755) | negative list indices in variable interpolation | <span title="Enhancement">✨</span> | <span title="community PR">🤝</span> | [#1212](https://github.com/omry/omegaconf/pull/1212) | 2021‑06‑17 | 2026‑04‑25 | enhancement |
| [#1118](https://github.com/omry/omegaconf/issues/1118) | `OmegaConf.missing_keys(cfg)` may fail if contained cus... | <span title="Bug">🐛</span> | <span title="community PR">🤝</span> | [#1117](https://github.com/omry/omegaconf/pull/1117) | 2023‑08‑24 | 2026‑04‑26 | bug |
| [#1123](https://github.com/omry/omegaconf/issues/1123) | Inconsistencies in recursive behavior in `set_readonly()` | <span title="Bug">🐛</span> | <span title="community PR">🤝</span> | [#1124](https://github.com/omry/omegaconf/pull/1124) | 2023‑09‑20 | 2026‑04‑24 | bug, needs triage |
| [#1239](https://github.com/omry/omegaconf/issues/1239) | RuntimeError: dictionary changed size during iteration... | <span title="Bug">🐛</span> | <span title="community PR">🤝</span> | [#1240](https://github.com/omry/omegaconf/pull/1240) | 2026‑03‑12 | 2026‑04‑24 | bug, awaiting response |
| [#1160](https://github.com/omry/omegaconf/issues/1160) | Support `Boost.Python.enum` Enums as annotation and sup... | <span title="Enhancement">✨</span> | <span title="blocked">🚫</span> |  | 2024‑02‑28 | 2026‑04‑25 | awaiting response |
| [#1161](https://github.com/omry/omegaconf/issues/1161) | Feature Request: Key-based readonly flag. | <span title="Enhancement">✨</span> | <span title="blocked">🚫</span> |  | 2024‑02‑28 | 2026‑04‑24 | enhancement, awaiting response |
| [#1178](https://github.com/omry/omegaconf/issues/1178) | `incompatible copy of pydevd already imported` when run... | <span title="Bug">🐛</span> | <span title="blocked">🚫</span> |  | 2024‑06‑03 | 2026‑04‑24 | bug, awaiting response |
| [#1210](https://github.com/omry/omegaconf/issues/1210) | test_nodes fails for Python >= 3.12 because of changes... | <span title="Bug">🐛</span> | <span title="blocked">🚫</span> |  | 2025‑03‑10 | 2026‑04‑24 | bug, awaiting response |
| [#131](https://github.com/omry/omegaconf/issues/131) | Evaluate usefulness of pep-593 for structured configs | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑01‑21 | 2026‑04‑24 | needs triage |
| [#144](https://github.com/omry/omegaconf/issues/144) | Full Union type support in structured configs | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑01‑30 | 2026‑04‑27 | enhancement, priority_high |
| [#181](https://github.com/omry/omegaconf/issues/181) | [Feature Request] Add .toJSON() method | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑03‑25 | 2026‑04‑24 | enhancement, needs triage |
| [#182](https://github.com/omry/omegaconf/issues/182) | Config blame mode | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑03‑27 | 2026‑04‑24 | enhancement, needs triage |
| [#392](https://github.com/omry/omegaconf/issues/392) | Improve Tuple support | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑09‑24 | 2026‑04‑26 | enhancement |
| [#440](https://github.com/omry/omegaconf/issues/440) | Deprecate legacy_register_resolver and new_register_res... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑11‑18 | 2026‑04‑24 | needs triage, priority_low |
| [#459](https://github.com/omry/omegaconf/issues/459) | Consider deprecating assignment of strings to non-strin... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑12‑15 | 2026‑04‑24 | needs triage, priority_low |
| [#519](https://github.com/omry/omegaconf/issues/519) | allow exporting to dotlist-style format | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑02‑05 | 2026‑04‑25 | enhancement |
| [#536](https://github.com/omry/omegaconf/issues/536) | Generated API docs for omegaconf | <span title="Documentation">📄</span> | <span title="not started">⬜</span> |  | 2021‑02‑11 | 2026‑04‑24 | maintenance, needs triage |
| [#537](https://github.com/omry/omegaconf/issues/537) | Refactor test_errors.py | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑02‑11 | 2026‑04‑24 | maintenance, needs triage |
| [#580](https://github.com/omry/omegaconf/issues/580) | _ensure_container does not set flags if target is alrea... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑03‑05 | 2026‑04‑26 | bug |
| [#610](https://github.com/omry/omegaconf/issues/610) | Feature: nested string interpolations | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑03‑16 | 2026‑04‑24 | needs triage, has-workaround, priority_low |
| [#612](https://github.com/omry/omegaconf/issues/612) | Automatic validation of resolver arguments | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑03‑16 | 2026‑04‑24 | enhancement, wishlist, needs triage, priority_low |
| [#651](https://github.com/omry/omegaconf/issues/651) | Interpolations can't refer to non-string keys | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑03‑29 | 2026‑04‑26 | bug, priority_low |
| [#702](https://github.com/omry/omegaconf/issues/702) | Provide correct full key on nested Structured Config cr... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑04‑29 | 2026‑04‑26 | bug, wishlist, priority_low |
| [#725](https://github.com/omry/omegaconf/issues/725) | Support assignment of numpy floats to FloatNode | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑05‑20 | 2026‑04‑24 | enhancement, needs triage, priority_low |
| [#726](https://github.com/omry/omegaconf/issues/726) | Consistent resolving of interpolations to random resolv... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑05‑20 | 2026‑04‑24 | needs triage |
| [#731](https://github.com/omry/omegaconf/issues/731) | Subclasses of `Generic` cannot be used as structured co... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑05‑24 | 2026‑04‑25 | bug, needs triage, priority_medium |
| [#750](https://github.com/omry/omegaconf/issues/750) | Followup: refactor ListConfig.{insert,append} | <span title="Refactor">🔧</span> | <span title="not started">⬜</span> |  | 2021‑06‑15 | 2026‑04‑24 | needs triage |
| [#762](https://github.com/omry/omegaconf/issues/762) | Dereferencing a resolver that returns "???" | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑06‑28 | 2026‑04‑24 | bug, needs triage |
| [#771](https://github.com/omry/omegaconf/issues/771) | Document special treatment of "???" by OmegaConf.merge | <span title="Documentation">📄</span> | <span title="not started">⬜</span> |  | 2021‑07‑21 | 2026‑04‑24 | documentation, needs triage |
| [#794](https://github.com/omry/omegaconf/issues/794) | OmegaConf is vulenrable to ddos via specially crafted y... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑10‑05 | 2026‑04‑24 | bug, needs triage, priority_medium |
| [#801](https://github.com/omry/omegaconf/issues/801) | Feature: Read-only flag on leaf field | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑10‑13 | 2026‑04‑24 | enhancement, needs triage, priority_low |
| [#802](https://github.com/omry/omegaconf/issues/802) | Read-only flag not working during `OmegaConf.merge` | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑10‑13 | 2026‑04‑24 | bug, needs triage |
| [#813](https://github.com/omry/omegaconf/issues/813) | OmegaConf.masked_copy does not preserve ValueNode type | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2021‑10‑28 | 2026‑04‑24 | bug, low priority, needs triage |
| [#815](https://github.com/omry/omegaconf/issues/815) | merge-readonly interatction | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2021‑10‑29 | 2026‑04‑24 | needs triage |
| [#846](https://github.com/omry/omegaconf/issues/846) | Nightly builds | <span title="Build">🏗️</span> | <span title="not started">⬜</span> |  | 2021‑12‑27 | 2026‑04‑24 | maintenance, needs triage |
| [#851](https://github.com/omry/omegaconf/issues/851) | Need `datetime`-typed field support | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑01‑22 | 2026‑04‑24 | enhancement, needs triage |
| [#864](https://github.com/omry/omegaconf/issues/864) | Support interpolation to integer keys (or other non-str... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑02‑21 | 2026‑04‑24 | enhancement, wishlist, needs triage, interpolation |
| [#882](https://github.com/omry/omegaconf/issues/882) | Interpolation to index of custom interpolation fails, d... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑03‑29 | 2026‑04‑24 | bug, needs triage, has-workaround |
| [#883](https://github.com/omry/omegaconf/issues/883) | Error when creating structured config with untyped Tuple | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑03‑29 | 2026‑04‑24 | bug, needs triage |
| [#898](https://github.com/omry/omegaconf/issues/898) | _promote is erasing values from the config | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑04‑14 | 2026‑04‑24 | bug, needs triage |
| [#899](https://github.com/omry/omegaconf/issues/899) | [Static typing] Make DictConfig generic in the dataclas... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑04‑15 | 2026‑04‑24 | enhancement, needs triage |
| [#908](https://github.com/omry/omegaconf/issues/908) | `OmegaConf.structured(...)` may mutate its input | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑05‑02 | 2026‑04‑24 | bug, needs triage |
| [#928](https://github.com/omry/omegaconf/issues/928) | `OmegaConf.get_type` inconsistent on `NoneType` | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑05‑15 | 2026‑04‑24 | bug, needs triage |
| [#936](https://github.com/omry/omegaconf/issues/936) | Generated files use obsolete typing.io import | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑05‑18 | 2026‑04‑24 | bug, needs triage |
| [#958](https://github.com/omry/omegaconf/issues/958) | ```OmegaConf.to_yaml``` adds unexpected new lines and q... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑05‑31 | 2026‑04‑24 | needs triage |
| [#959](https://github.com/omry/omegaconf/issues/959) | Would you please consider realizing an comparing funcit... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑06‑01 | 2026‑04‑24 | needs triage |
| [#969](https://github.com/omry/omegaconf/issues/969) | Follow up on deprecation of `register_resolver()` | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑06‑21 | 2026‑04‑24 | maintenance, needs triage |
| [#974](https://github.com/omry/omegaconf/issues/974) | fails on `Dict[Any, str]` if passed in a list of strings | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑07‑13 | 2026‑04‑24 | needs triage, as designed |
| [#976](https://github.com/omry/omegaconf/issues/976) | Improve support for NoneType | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑07‑14 | 2026‑04‑24 | bug, needs triage, structured config |
| [#998](https://github.com/omry/omegaconf/issues/998) | Merging does not preserve target `ref_type` when source... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑08‑18 | 2026‑04‑24 | bug, needs triage |
| [#999](https://github.com/omry/omegaconf/issues/999) | `List[Tuple[T, ...]]` not supported | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑08‑29 | 2026‑04‑24 | bug, needs triage |
| [#1020](https://github.com/omry/omegaconf/issues/1020) | Failure to merge interpolation into structured config | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑10‑20 | 2026‑04‑24 | bug, needs triage |
| [#1024](https://github.com/omry/omegaconf/issues/1024) | Interpolations in dictionary keys | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑10‑29 | 2026‑04‑24 | enhancement, needs triage, interpolation, has-workaround |
| [#1028](https://github.com/omry/omegaconf/issues/1028) | Add support for equals sign and other symbols in resolv... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑11‑09 | 2026‑04‑24 | needs triage |
| [#1037](https://github.com/omry/omegaconf/issues/1037) | Structured config type coercion not working correctly f... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑11‑28 | 2026‑04‑24 | bug, needs triage |
| [#1048](https://github.com/omry/omegaconf/issues/1048) | [Feature Request] Use SimpleNamespace for to_container(... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2022‑12‑26 | 2026‑04‑24 | needs triage |
| [#1052](https://github.com/omry/omegaconf/issues/1052) | How can I get the data type of an attribute at a depth>1? | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑01‑06 | 2026‑04‑24 | needs triage |
| [#1054](https://github.com/omry/omegaconf/issues/1054) | Structured Config schema Type validation of "list[list[... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑01‑22 | 2026‑04‑24 | bug, needs triage |
| [#1056](https://github.com/omry/omegaconf/issues/1056) | How to properly escape ??? | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑01‑31 | 2026‑04‑26 | enhancement, has-workaround |
| [#1058](https://github.com/omry/omegaconf/issues/1058) | structured config types are discarded on list merge | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑02‑19 | 2026‑04‑24 | bug, needs triage |
| [#1059](https://github.com/omry/omegaconf/issues/1059) | oc.decode resolver failing to parse "???" as MISSING | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑02‑21 | 2026‑04‑24 | bug, needs triage |
| [#1061](https://github.com/omry/omegaconf/issues/1061) | Enum inheritance Support | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑03‑07 | 2026‑04‑24 | needs triage |
| [#1086](https://github.com/omry/omegaconf/issues/1086) | ListConfig errors when is [:-1] applied to empty list | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑06‑02 | 2026‑04‑24 | bug, needs triage |
| [#1095](https://github.com/omry/omegaconf/issues/1095) | Validation error merging structured configs containing... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑06‑23 | 2026‑04‑24 | bug, needs triage |
| [#1102](https://github.com/omry/omegaconf/issues/1102) | Merging nested readonly structured configs doesn't work. | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑07‑14 | 2026‑04‑24 | bug, needs triage |
| [#1126](https://github.com/omry/omegaconf/issues/1126) | Improve error message for relative interpolations | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑09‑22 | 2026‑04‑24 | needs triage |
| [#1127](https://github.com/omry/omegaconf/issues/1127) | Make `select` and `oc.select` more robust | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑09‑26 | 2026‑04‑24 | needs triage |
| [#1129](https://github.com/omry/omegaconf/issues/1129) | Add function to check if key exists | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑10‑03 | 2026‑04‑24 | needs triage |
| [#1130](https://github.com/omry/omegaconf/issues/1130) | Interpolations that resolve to missing value `???` don'... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑10‑11 | 2026‑04‑24 | needs triage |
| [#1131](https://github.com/omry/omegaconf/issues/1131) | `OmegaConf.resolve` should crash when a resolver input... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2023‑10‑11 | 2026‑04‑24 | bug |
| [#1132](https://github.com/omry/omegaconf/issues/1132) | [Feature Request] integration between omegaconf and AWS... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2023‑10‑16 | 2026‑04‑24 | needs triage |
| [#1148](https://github.com/omry/omegaconf/issues/1148) | ImportError: cannot import name 'get_ref_type' from 'om... | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2024‑01‑08 | 2026‑04‑24 | needs triage |
| [#1154](https://github.com/omry/omegaconf/issues/1154) | Merge Option of update function does not merge list | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2024‑02‑21 | 2026‑04‑24 | bug, needs triage |
| [#1173](https://github.com/omry/omegaconf/issues/1173) | Consider adding config "blame" metadata. | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2024‑04‑19 | 2026‑04‑25 | wishlist |
| [#1184](https://github.com/omry/omegaconf/issues/1184) | Merging Multiple Configs with Interpolation has Unexpec... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2024‑07‑18 | 2026‑04‑24 | enhancement, wishlist |
| [#1191](https://github.com/omry/omegaconf/issues/1191) | Controlling conflict resolution in merge_with | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2024‑08‑20 | 2026‑04‑24 | enhancement |
| [#1236](https://github.com/omry/omegaconf/issues/1236) | Instantiating a class with Union-typed fields doesn't w... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2026‑02‑22 | 2026‑04‑24 | enhancement |
| [#1255](https://github.com/omry/omegaconf/issues/1255) | Evaluate migrating packaging metadata and build config... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2026‑04‑22 | 2026‑04‑24 | enhancement |
| [#1263](https://github.com/omry/omegaconf/issues/1263) | Revert list_merge_mode before stable 2.4 | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2026‑04‑24 | 2026‑04‑24 |  |
| [#1271](https://github.com/omry/omegaconf/issues/1271) | Support Union[Literal[...], other_type] annotations in... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2026‑04‑24 | 2026‑04‑24 |  |
| [#1274](https://github.com/omry/omegaconf/issues/1274) | Python 3.10 minimum: remove version guards and moderniz... | <span title="Refactor">🔧</span> | <span title="not started">⬜</span> |  | 2026‑04‑24 | 2026‑04‑24 |  |
| [#1282](https://github.com/omry/omegaconf/issues/1282) | Migrate Documentation from Read the docs to a GitHub ho... | <span title="Documentation">📄</span> | <span title="not started">⬜</span> |  | 2026‑04‑26 | 2026‑04‑26 | documentation |
| [#945](https://github.com/omry/omegaconf/issues/945) | `get_attr_data` doesn't handle default factory correctly | <span title="Bug">🐛</span> | <span title="not started">⬜</span> |  | 2022‑05‑25 | 2026‑04‑24 | bug, needs triage |
| [#265](https://github.com/omry/omegaconf/issues/265) | Attribute/KeyError can suggest matches from the availab... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2020‑06‑11 | 2026‑04‑24 | enhancement, needs triage, priority_low |
| [#1275](https://github.com/omry/omegaconf/issues/1275) | Support Union of Structured Configs (dataclasses/attr c... | <span title="Enhancement">✨</span> | <span title="not started">⬜</span> |  | 2026‑04‑24 | 2026‑04‑24 |  |
| [#803](https://github.com/omry/omegaconf/issues/803) | [Question] Why hide dictconfig debugging content? | <span title="Question">❓</span> | <span title="done">✅</span> |  | 2021‑10‑14 | 2026‑04‑24 | needs triage |
| [#788](https://github.com/omry/omegaconf/issues/788) | validation error when default_factory produces structur... | <span title="Bug">🐛</span> | <span title="done">✅</span> |  | 2021‑09‑14 | 2026‑04‑26 | bug, priority_low |
| [#910](https://github.com/omry/omegaconf/issues/910) | Allow assigning variable interpolation to structured co... | <span title="Bug">🐛</span> | <span title="done">✅</span> |  | 2022‑05‑05 | 2026‑04‑24 | bug, needs triage, interpolation, structured config |
| [#1156](https://github.com/omry/omegaconf/issues/1156) | Convert from OrderedDict? | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1278](https://github.com/omry/omegaconf/pull/1278) | 2024‑02‑22 | 2026‑04‑25 |  |
| [#1221](https://github.com/omry/omegaconf/issues/1221) | Suggest similar key names when a key is not found | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1265](https://github.com/omry/omegaconf/pull/1265) | 2025‑08‑06 | 2026‑04‑24 | enhancement |
| [#1222](https://github.com/omry/omegaconf/issues/1222) | Better doc strings | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1264](https://github.com/omry/omegaconf/pull/1264) | 2025‑08‑21 | 2026‑04‑24 | enhancement |
| [#422](https://github.com/omry/omegaconf/issues/422) | Allow the use of typing.Literal as a pythonic alternati... | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1272](https://github.com/omry/omegaconf/pull/1272) | 2020‑10‑27 | 2026‑04‑24 | enhancement, wishlist, needs triage |
| [#1006](https://github.com/omry/omegaconf/issues/1006) | Allow merging configs with union operator \| in Python 3.9+ | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1277](https://github.com/omry/omegaconf/pull/1277) | 2022‑09‑15 | 2026‑04‑24 | enhancement, dictconfig |
| [#1205](https://github.com/omry/omegaconf/issues/1205) | When merging DictConfs and interpolation fails due to M... | <span title="Bug">🐛</span> | <span title="done">✅</span> | [#1249](https://github.com/omry/omegaconf/pull/1249) | 2025‑01‑11 | 2026‑04‑24 | bug |
| [#1230](https://github.com/omry/omegaconf/issues/1230) | Allow backslash-escaping of special characters in key p... | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1279](https://github.com/omry/omegaconf/pull/1279) | 2025‑12‑04 | 2026‑04‑25 | enhancement |
| [#1261](https://github.com/omry/omegaconf/issues/1261) | Support unions of Dict and List container types | <span title="Enhancement">✨</span> | <span title="done">✅</span> | [#1262](https://github.com/omry/omegaconf/pull/1262) | 2026‑04‑24 | 2026‑04‑24 |  |
| [#1019](https://github.com/omry/omegaconf/issues/1019) | Nested structured config validation | <span title="Bug">🐛</span> | <span title="done">✅</span> | [#1133](https://github.com/omry/omegaconf/pull/1133) | 2022‑10‑04 | 2026‑04‑24 | bug, needs triage |
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
