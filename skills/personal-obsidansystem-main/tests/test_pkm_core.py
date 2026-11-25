"""pkm_core.py 순수 함수·임시 볼트 시험 (T09).

- 노트 묶음·파일 이름 규칙·속성(frontmatter)·링크 갱신 함수를 시험한다.
- 실제 볼트·네트워크·비밀값은 쓰지 않는다. 모든 파일은 임시 폴더 안에서만 만든다.
- backup_file 은 원래 사용자 문서 폴더(Documents/backupvault)에 쓰므로,
  setUp 에서 DEFAULT_BACKUP_ROOT 를 임시 폴더로 바꿔 실제 폴더를 건드리지 않게 한다.
- 소스(pkm_core.py)는 고치지 않는다. 찾은 문제는 ISSUES.md 에 적고 시험은 xfail 로 둔다.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pkm_core  # noqa: E402


def meta(topics=(), tags=(), domain="", engine=""):
    return {"topics": list(topics), "tags": list(tags), "domain": domain, "engine": engine}


class TempVaultCase(unittest.TestCase):
    """임시 볼트와 임시 백업 폴더를 만들어 주는 바탕 클래스."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pkm-test-"))
        self.vault = self.tmp / "vault"
        self.vault.mkdir()
        self.backup_root = self.tmp / "backup"
        patcher = patch.object(pkm_core, "DEFAULT_BACKUP_ROOT", self.backup_root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, rel, text="", encoding="utf-8"):
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return path

    def read(self, path):
        return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------- 값 다듬기
class ValueHelperTests(unittest.TestCase):
    def test_parse_yaml_value_lists_and_quotes(self):
        parse = pkm_core.parse_yaml_value
        self.assertEqual(parse("[a, b]"), ["a", "b"])
        self.assertEqual(parse("[]"), [])
        self.assertEqual(parse('"x y"'), "x y")
        self.assertEqual(parse("'q'"), "q")
        self.assertEqual(parse("plain"), "plain")

    def test_parse_yaml_value_single_item_list_becomes_string(self):
        # 지금 동작: 항목이 하나인 목록은 글자 하나로 읽힌다(고정해 두는 시험)
        self.assertEqual(pkm_core.parse_yaml_value("[a]"), "a")

    def test_format_yaml_value(self):
        fmt = pkm_core.format_yaml_value
        self.assertEqual(fmt([]), "[]")
        self.assertEqual(fmt(["a", "b"]), "[a, b]")
        self.assertEqual(fmt("ok"), "ok")
        self.assertEqual(fmt("a:b"), '"a:b"')  # 특수문자가 있으면 따옴표
        self.assertEqual(fmt(5), "5")

    def test_escape_markdown_cell(self):
        self.assertEqual(pkm_core.escape_markdown_cell("a|b\nc"), "a\\|b c")

    def test_normalize_prop_list(self):
        norm = pkm_core.normalize_prop_list
        self.assertEqual(norm(None), [])
        self.assertEqual(norm(""), [])
        self.assertEqual(norm(["a", " ", "", " b "]), ["a", "b"])
        self.assertEqual(norm("x"), ["x"])
        self.assertEqual(norm(5), ["5"])

    def test_normalize_domain_value_uses_aliases_and_trims(self):
        norm = pkm_core.normalize_domain_value
        self.assertEqual(norm("학급경영"), "학급")
        self.assertEqual(norm("  [자기] "), "자기")
        self.assertEqual(norm("자기 "), "자기")
        self.assertEqual(norm("모르는값"), "모르는값")  # 별칭에 없으면 그대로

    def test_normalize_alias_list(self):
        self.assertEqual(pkm_core.normalize_alias_list(["a", "", " b "]), ["a", "b"])


# ---------------------------------------------------------------- 파일 이름 규칙
class FilenameTests(unittest.TestCase):
    def test_sanitize_filename_replaces_forbidden_characters(self):
        self.assertEqual(pkm_core.sanitize_filename('a<b>:c/d\\e|f?g*h'), "a_b_c_d_e_f_g_h")

    def test_sanitize_filename_trims_spaces_and_trailing_dots(self):
        self.assertEqual(pkm_core.sanitize_filename("  x   y.. "), "x y")

    def test_sanitize_filename_never_returns_empty(self):
        self.assertEqual(pkm_core.sanitize_filename(""), "note")
        self.assertEqual(pkm_core.sanitize_filename("   "), "note")
        self.assertEqual(pkm_core.sanitize_filename("..."), "note")

    def test_sanitize_filename_keeps_korean(self):
        self.assertEqual(pkm_core.sanitize_filename("학급 운영 메모"), "학급 운영 메모")

    def test_slugify_note_path_is_stable_and_keeps_md_extension(self):
        first = pkm_core.slugify_note_path("A/메모.md")
        self.assertEqual(first, pkm_core.slugify_note_path("A/메모.md"))
        self.assertTrue(first.endswith(".md"))
        self.assertTrue(first.startswith("메모__"))

    def test_slugify_note_path_differs_for_same_title_in_different_folders(self):
        self.assertNotEqual(
            pkm_core.slugify_note_path("A/메모.md"), pkm_core.slugify_note_path("B/메모.md")
        )

    def test_slugify_note_path_digest_is_eight_hex_chars(self):
        name = pkm_core.slugify_note_path("x/y.md")
        digest = name[:-3].split("__")[-1]
        self.assertEqual(len(digest), 8)
        int(digest, 16)  # 16진수가 아니면 오류


# ---------------------------------------------------------------- frontmatter
class FrontmatterTests(unittest.TestCase):
    SAMPLE = (
        "---\ntitle: 제목\ntopic: a, b\ndate: 2026-11-25, x\n"
        "tags:\n  - t1\n  - t2\nsingle:\n  - only\n# comment\n---\n본문\n"
    )

    def test_no_frontmatter_returns_text_unchanged(self):
        self.assertEqual(pkm_core.read_frontmatter("본문만"), ({}, [], "본문만"))

    def test_reads_simple_list_block_and_comma_values(self):
        props, blocks, body = pkm_core.read_frontmatter(self.SAMPLE)
        self.assertEqual(props["title"], "제목")
        self.assertEqual(props["topic"], ["a", "b"])  # 쉼표로 나뉨
        self.assertEqual(props["date"], "2026-11-25, x")  # 숫자로 시작하면 나누지 않음
        self.assertEqual(props["tags"], ["t1", "t2"])  # 줄 목록
        self.assertEqual(props["single"], "only")  # 항목 하나짜리 줄 목록은 글자로
        self.assertEqual(body, "본문\n")
        self.assertIn(None, [block["key"] for block in blocks])  # 주석 줄은 키 없이 보관

    def test_reads_crlf_frontmatter(self):
        props, _, body = pkm_core.read_frontmatter("---\r\na: 1\r\n---\r\nB")
        self.assertEqual(props, {"a": "1"})
        self.assertEqual(body, "B")

    def test_write_keeps_comments_and_rewrites_lists_inline(self):
        props, blocks, body = pkm_core.read_frontmatter(self.SAMPLE)
        out = pkm_core.write_frontmatter(props, blocks, body)
        self.assertIn("# comment", out)
        self.assertIn("topic: [a, b]", out)
        self.assertIn("tags: [t1, t2]", out)
        self.assertTrue(out.endswith("---\n본문\n"))

    def test_write_drops_removed_keys_and_appends_new_ones(self):
        props, blocks, body = pkm_core.read_frontmatter("---\na: 1\nb: 2\n---\nB\n")
        del props["a"]
        props["c"] = "3"
        out = pkm_core.write_frontmatter(props, blocks, body)
        self.assertNotIn("a: 1", out)
        self.assertIn("b: 2", out)
        self.assertTrue(out.index("b: 2") < out.index("c: 3"))

    def test_write_with_nothing_returns_body_only(self):
        self.assertEqual(pkm_core.write_frontmatter({}, [], ""), "")
        self.assertEqual(pkm_core.write_frontmatter({"a": 1}, [], ""), "---\na: 1\n---\n")

    def test_simple_values_survive_round_trip(self):
        for props in ({"title": "a: b"}, {"topic": ["x", "y"]}, {"t": "it's"}):
            out = pkm_core.write_frontmatter(dict(props), [], "B\n")
            self.assertEqual(pkm_core.read_frontmatter(out)[0], props, props)

    # 아래 둘은 지금 동작이 데이터를 바꾸는 문제(ISSUES ISSUE-002·003)라 xfail 로 둔다.
    @unittest.expectedFailure
    def test_list_item_containing_comma_survives_round_trip(self):
        props = {"topic": ["a, b", "c"]}
        out = pkm_core.write_frontmatter(dict(props), [], "B\n")
        self.assertEqual(pkm_core.read_frontmatter(out)[0], props)

    @unittest.expectedFailure
    def test_double_quote_in_value_survives_round_trip(self):
        props = {"title": 'say "hi"'}
        out = pkm_core.write_frontmatter(dict(props), [], "B\n")
        self.assertEqual(pkm_core.read_frontmatter(out)[0], props)


# ---------------------------------------------------------------- 폴더 경로 속성
class PathPropTests(TempVaultCase):
    def test_build_value_for_root_and_nested_folders(self):
        root_note = self.write("root.md")
        nested = self.write("A/B/n.md")
        self.assertEqual(pkm_core.build_note_folder_path_value(self.vault, root_note), "Vault 루트")
        self.assertEqual(pkm_core.build_note_folder_path_value(self.vault, nested), "A / B")

    def test_build_value_rejects_note_outside_vault(self):
        outside = self.tmp / "outside.md"
        outside.write_text("x", encoding="utf-8")
        with self.assertRaises(ValueError):
            pkm_core.build_note_folder_path_value(self.vault, outside)

    def test_parse_value_variants(self):
        parse = pkm_core.parse_note_folder_path_value
        self.assertEqual(parse("Vault 루트"), Path())
        self.assertEqual(parse("A / B"), Path("A/B"))
        self.assertEqual(parse("A/B"), Path("A/B"))
        self.assertEqual(parse("A\\B"), Path("A/B"))
        self.assertEqual(parse('"A / B"'), Path("A/B"))  # 따옴표 제거
        self.assertEqual(parse("A / B / x.md"), Path("A/B"))  # 파일 이름은 버림
        self.assertEqual(parse("/"), Path())
        self.assertEqual(parse("root"), Path())

    def test_parse_value_rejects_empty_and_traversal(self):
        for bad in ("", "   ", "../x", "a / .. / b", "./x"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                pkm_core.parse_note_folder_path_value(bad)

    def test_build_then_parse_round_trips(self):
        note = self.write("00_Inbox/메모/n.md")
        value = pkm_core.build_note_folder_path_value(self.vault, note)
        self.assertEqual(pkm_core.parse_note_folder_path_value(value), Path("00_Inbox/메모"))

    def test_resolve_target_dir_stays_inside_vault(self):
        target = pkm_core.resolve_note_target_dir_from_path_value(self.vault, "A / B")
        self.assertEqual(target, (self.vault / "A" / "B").resolve())
        self.assertEqual(
            pkm_core.resolve_note_target_dir_from_path_value(self.vault, "Vault 루트"),
            self.vault.resolve(),
        )

    def test_resolve_target_dir_rejects_escape(self):
        with self.assertRaises(ValueError):
            pkm_core.resolve_note_target_dir_from_path_value(self.vault, "a/../../out")

    @unittest.expectedFailure
    def test_folder_name_starting_with_vault_keeps_first_part(self):
        # 기대: "Vault Notes / x" 는 'Vault Notes' 라는 실제 폴더 아래 x.
        # 지금은 'Vault ' 로 시작하면 첫 마디를 '볼트 루트' 표시로 보고 버린다 → ISSUES ISSUE-004.
        self.assertEqual(
            pkm_core.parse_note_folder_path_value("Vault Notes / x"), Path("Vault Notes/x")
        )


# ---------------------------------------------------------------- 속성 고치기(파일)
class UpdatePropsTests(TempVaultCase):
    def props_of(self, path):
        return pkm_core.read_frontmatter(self.read(path))[0]

    def test_fills_missing_and_empty_values_but_does_not_overwrite_by_default(self):
        note = self.write("n.md", "---\ndomain: 자기\nengine:\n---\nB\n")
        result = pkm_core.update_props_in_file(
            note, {"domain": "수업", "engine": "concept", "topic": ""}, make_backup=False
        )
        self.assertEqual(result, "ok")
        props = self.props_of(note)
        self.assertEqual(props["domain"], "자기")  # 이미 값이 있어 그대로
        self.assertEqual(props["engine"], "concept")  # 빈 값은 채움
        self.assertNotIn("topic", props)  # 빈 문자열 값은 쓰지 않음

    def test_overwrite_replaces_existing_value(self):
        note = self.write("n.md", "---\ndomain: 자기\n---\nB\n")
        self.assertEqual(
            pkm_core.update_props_in_file(note, {"domain": "수업"}, overwrite=True, make_backup=False),
            "ok",
        )
        self.assertEqual(self.props_of(note)["domain"], "수업")

    def test_same_value_is_skipped_and_file_untouched(self):
        note = self.write("n.md", "---\ndomain: 수업\n---\nB\n")
        before = note.read_bytes()
        result = pkm_core.update_props_in_file(note, {"domain": "수업"}, overwrite=True, make_backup=True)
        self.assertEqual(result, "skipped")
        self.assertEqual(note.read_bytes(), before)
        self.assertFalse(self.backup_root.exists())  # 바뀐 게 없으면 백업도 안 만듦

    def test_remove_props(self):
        note = self.write("n.md", "---\ndomain: 자기\nengine: concept\n---\nB\n")
        self.assertEqual(pkm_core.remove_props_from_file(note, ["engine", "nokey"], make_backup=False), "ok")
        self.assertEqual(self.props_of(note), {"domain": "자기"})
        self.assertEqual(pkm_core.remove_props_from_file(note, ["engine"], make_backup=False), "skipped")

    def test_note_without_frontmatter_gets_one_and_body_is_kept(self):
        note = self.write("m.md", "그냥 본문\n")
        self.assertEqual(pkm_core.update_props_in_file(note, {"domain": "자기"}, make_backup=False), "ok")
        self.assertEqual(self.read(note), "---\ndomain: 자기\n---\n그냥 본문\n")

    def test_missing_file_returns_error_string_instead_of_raising(self):
        result = pkm_core.update_props_in_file(self.vault / "none.md", {"a": "b"}, make_backup=False)
        self.assertTrue(result.startswith("error:"))

    def test_backup_goes_to_patched_root_not_user_documents(self):
        note = self.write("Inbox/n.md", "---\ndomain: 자기\n---\nB\n")
        pkm_core.update_props_in_file(note, {"domain": "수업"}, overwrite=True, vault_path=self.vault)
        backups = list((self.backup_root / "Inbox").glob("n_*.md.bak"))
        self.assertEqual(len(backups), 1)
        self.assertIn("domain: 자기", backups[0].read_text(encoding="utf-8"))  # 바뀌기 전 내용

    def test_get_current_props_returns_empty_for_missing_file(self):
        self.assertEqual(pkm_core.get_current_props(self.vault / "none.md"), {})

    def test_sync_path_prop_writes_folder_value(self):
        note = self.write("A/B/n.md", "---\ntitle: t\n---\nB\n")
        result, value = pkm_core.sync_path_prop_for_file(note, self.vault, make_backup=False)
        self.assertEqual((result, value), ("ok", "A / B"))
        self.assertEqual(self.props_of(note)["path"], "A / B")

    @unittest.expectedFailure
    def test_repeated_edits_do_not_pile_up_backslashes_before_quotes(self):
        # 따옴표가 든 값이 있는 노트에서 다른 속성을 고칠 때마다 역슬래시가 늘어난다 → ISSUES ISSUE-003.
        note = self.write("n.md", '---\ntitle: "say \\"hi\\""\n---\nB\n')
        before = self.props_of(note)["title"]
        for i in range(3):
            pkm_core.update_props_in_file(note, {"domain": f"d{i}"}, overwrite=True, make_backup=False)
        self.assertEqual(self.props_of(note)["title"], before)


# ---------------------------------------------------------------- 별칭
class AliasTests(unittest.TestCase):
    def test_merge_aliases_adds_new_and_ignores_case_duplicates(self):
        props = {"aliases": ["Alpha"]}
        changed = pkm_core.merge_aliases(props, ["alpha", "Beta", " beta ", ""])
        self.assertTrue(changed)
        self.assertEqual(props["aliases"], ["Alpha", "Beta"])

    def test_merge_aliases_no_change_when_all_known(self):
        props = {"aliases": ["Alpha"]}
        self.assertFalse(pkm_core.merge_aliases(props, ["ALPHA"]))
        self.assertEqual(props["aliases"], ["Alpha"])

    def test_merge_aliases_with_nothing_to_add_leaves_props_alone(self):
        props = {}
        self.assertFalse(pkm_core.merge_aliases(props, ["", "  "]))
        self.assertEqual(props, {})

    def test_merge_aliases_creates_key_when_missing(self):
        props = {}
        self.assertTrue(pkm_core.merge_aliases(props, ["새 별칭"]))
        self.assertEqual(props["aliases"], ["새 별칭"])


# ---------------------------------------------------------------- 인덱스 맞추기·찾기
class IndexAndSearchTests(TempVaultCase):
    def test_match_index_exact_and_spacing_insensitive(self):
        expected = {"domain": "학급", "engine": "principle"}
        self.assertEqual(pkm_core.match_index("학급 운영"), expected)
        self.assertEqual(pkm_core.match_index("학급운영"), expected)
        self.assertEqual(pkm_core.match_index("학급-운영"), expected)

    def test_match_index_unknown_and_too_short_return_empty(self):
        self.assertEqual(pkm_core.match_index("전혀 없는 제목입니다"), {})
        self.assertEqual(pkm_core.match_index("성장"), {})  # 너무 짧은 부분 일치는 허용 안 함

    def test_search_in_content_is_case_insensitive_and_skips_unreadable(self):
        a = self.write("a.md", "Hello World")
        b = self.write("b.md", "nothing")
        missing = self.vault / "gone.md"
        self.assertEqual(pkm_core.search_in_content([a, b, missing], "hello"), [a])

    def test_read_text_file_falls_back_to_cp949(self):
        note = self.vault / "k.md"
        note.write_bytes("한글 메모".encode("cp949"))
        self.assertEqual(pkm_core.read_text_file(note), "한글 메모")

    def test_read_text_file_strips_utf8_bom(self):
        note = self.vault / "bom.md"
        note.write_bytes("﻿본문".encode("utf-8"))
        self.assertEqual(pkm_core.read_text_file(note), "본문")

    def test_parse_obsidian_paths(self):
        self.write("Notes/ref.md")
        self.write("Notes/dup.md")
        self.write("Inbox/deep/dup.md")
        self.write("n.md")
        found, not_found = pkm_core.parse_obsidian_paths(
            "Notes/ref\n\n  Inbox\\deep\\dup.md \nnone\nn\n", self.vault
        )
        rels = [p.relative_to(self.vault).as_posix() for p in found]
        self.assertEqual(rels, ["Notes/ref.md", "Inbox/deep/dup.md", "n.md"])
        self.assertEqual(not_found, ["none"])

    def test_parse_obsidian_paths_picks_shortest_path_when_title_is_ambiguous(self):
        self.write("Notes/dup.md")
        self.write("Inbox/deep/dup.md")
        found, _ = pkm_core.parse_obsidian_paths("dup", self.vault)
        self.assertEqual([p.relative_to(self.vault).as_posix() for p in found], ["Notes/dup.md"])


# ---------------------------------------------------------------- 링크 갱신
class WikilinkTests(TempVaultCase):
    def test_split_wikilink_parts(self):
        split = pkm_core.split_wikilink_parts
        self.assertEqual(split("a#h|al"), ("a", "h", "al"))
        self.assertEqual(split("a|al#x"), ("a", "", "al#x"))
        self.assertEqual(split("a"), ("a", "", ""))

    def test_extract_wikilink_targets(self):
        text = "[[a|x]] [[b#h]] [[ ]] [[dir\\c]]"
        self.assertEqual(pkm_core.extract_wikilink_targets(text), ["a", "b", "dir/c"])

    def test_extract_markdown_targets(self):
        self.assertEqual(
            pkm_core.extract_markdown_targets("[l](x.md) [l2](<y z.md>)"), ["x.md", "<y z.md>"]
        )

    def test_wikilink_points_to_note_by_title_path_and_relative_path(self):
        old = self.write("Inbox/old.md")
        src = self.write("Notes/src.md")
        points = lambda target: pkm_core.wikilink_points_to_note(src, target, old, self.vault)
        self.assertTrue(points("old"))  # 제목만
        self.assertTrue(points("OLD"))  # 대소문자 무시
        self.assertTrue(points("Inbox/old"))  # 볼트 기준 경로
        self.assertTrue(points("Inbox/old.md"))
        self.assertTrue(points("../Inbox/old"))  # 글이 있는 폴더 기준 경로
        self.assertFalse(points("other"))
        self.assertFalse(points(""))

    def test_replace_wikilinks_keeps_heading_and_alias_and_skips_other_notes(self):
        old = self.write("Inbox/old.md")
        new = self.write("Notes/moved.md")
        src = self.write("Notes/src.md")
        text = "a [[Inbox/old#h|별칭]] b [[other]] c [[old]]"
        out, count = pkm_core.replace_wikilinks_for_note_change(text, src, old, new, self.vault)
        self.assertEqual(count, 2)
        # 경로 모양 링크는 새 경로로, 제목만 쓴 링크는 (제목이 하나뿐이면) 새 제목으로
        self.assertEqual(out, "a [[Notes/moved#h|별칭]] b [[other]] c [[moved]]")

    def test_replace_wikilinks_uses_path_when_new_title_is_not_unique(self):
        old = self.write("Inbox/old.md")
        new = self.write("Notes/dup.md")
        self.write("Other/dup.md")  # 같은 제목이 또 있어 제목만 쓰면 헷갈림
        src = self.write("Notes/src.md")
        out, count = pkm_core.replace_wikilinks_for_note_change("[[old]]", src, old, new, self.vault)
        self.assertEqual((out, count), ("[[Notes/dup]]", 1))

    def test_replace_wikilinks_keeps_title_only_link_when_title_unchanged(self):
        old = self.write("Inbox/old.md")
        new_same = self.write("Notes/old.md")  # 이름은 같고 폴더만 옮긴 경우
        src = self.write("Notes/src.md")
        out, count = pkm_core.replace_wikilinks_for_note_change("[[old]]", src, old, new_same, self.vault)
        self.assertEqual(out, "[[old]]")
        self.assertEqual(count, 1)

    def test_replace_wikilinks_path_style_link_is_rewritten_with_extension_kept(self):
        old = self.write("Inbox/old.md")
        new = self.write("Notes/moved.md")
        src = self.write("Notes/src.md")
        out, _ = pkm_core.replace_wikilinks_for_note_change("[[Inbox/old.md]]", src, old, new, self.vault)
        self.assertEqual(out, "[[Notes/moved.md]]")

    def test_replace_markdown_links(self):
        old = self.write("Inbox/old.md")
        new = self.write("Notes/moved.md")
        src = self.write("Notes/src.md")
        text = "[x](../Inbox/old.md#s) [y](https://example.com/a.md) [z](#top) [w](../Inbox/other.md)"
        out, count = pkm_core.replace_markdown_links_for_note_change(text, src, old, new, self.vault)
        self.assertEqual(count, 1)
        self.assertEqual(
            out, "[x](moved.md#s) [y](https://example.com/a.md) [z](#top) [w](../Inbox/other.md)"
        )

    def test_replace_markdown_links_wrapped_and_extensionless(self):
        old = self.write("Inbox/old.md")
        new = self.write("Notes/moved.md")
        src = self.write("Notes/src.md")
        out, count = pkm_core.replace_markdown_links_for_note_change(
            "[a](<../Inbox/old>) [b](/Inbox/old.md)", src, old, new, self.vault
        )
        self.assertEqual(count, 2)
        self.assertEqual(out, "[a](<moved>) [b](/Notes/moved.md)")


class LinkScanTests(TempVaultCase):
    def test_iter_link_update_notes_skips_excluded_folders_and_is_sorted(self):
        for rel in ("b.md", "a.md", "reports/r.md", ".obsidian/o.md", "_PKM_BACKUP/x.md", "sub/c.md", "t.txt"):
            self.write(rel)
        names = [p.relative_to(self.vault).as_posix() for p in pkm_core.iter_link_update_notes(self.vault)]
        self.assertEqual(names, ["a.md", "b.md", "sub/c.md"])

    def test_note_title_is_unique(self):
        self.write("A/dup.md")
        self.write("B/dup.md")
        self.write("A/solo.md")
        self.write("reports/solo.md")  # 제외 폴더는 세지 않음
        self.assertFalse(pkm_core.note_title_is_unique(self.vault, "dup"))
        self.assertFalse(pkm_core.note_title_is_unique(self.vault, "DUP"))
        self.assertTrue(pkm_core.note_title_is_unique(self.vault, "solo"))
        self.assertTrue(pkm_core.note_title_is_unique(self.vault, "none"))

    def test_note_title_is_unique_can_ignore_the_note_being_moved(self):
        a = self.write("A/dup.md")
        self.write("B/dup.md")
        self.assertTrue(pkm_core.note_title_is_unique(self.vault, "dup", {a}))

    def test_update_links_for_note_change_rewrites_other_notes_and_backs_them_up(self):
        old = self.write("Inbox/old.md", "본문\n")
        new = self.write("Notes/moved.md", "본문\n")
        ref = self.write("Notes/ref.md", "[[old]] [[other]] [m](../Inbox/old.md)\n")
        untouched = self.write("Notes/none.md", "[[other]]\n")
        result = pkm_core.update_links_for_note_change(self.vault, old, new)
        self.assertEqual(self.read(ref), "[[moved]] [[other]] [m](moved.md)\n")
        self.assertEqual(self.read(untouched), "[[other]]\n")
        self.assertEqual(result["updated_files"], 1)
        self.assertEqual(result["wikilinks_updated"], 1)
        self.assertEqual(result["markdown_links_updated"], 1)
        self.assertEqual(result["changed_files"], ["Notes/ref.md"])
        self.assertEqual(len(list(self.backup_root.rglob("ref_*.md.bak"))), 1)


# ---------------------------------------------------------------- 노트 옮기기
class MoveNoteTests(TempVaultCase):
    def test_moves_note_to_path_prop_and_updates_links_and_path_value(self):
        note = self.write("Inbox/old.md", "---\ntitle: T\npath: Notes\n---\n본문\n")
        ref = self.write("Notes/ref.md", "[[Inbox/old#h|al]] [x](../Inbox/old.md)\n")
        status, destination, detail = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "moved")
        self.assertEqual(destination, (self.vault / "Notes" / "old.md").resolve())
        self.assertFalse(note.exists())
        self.assertEqual(self.read(ref), "[[Notes/old#h|al]] [x](old.md)\n")
        self.assertIn("links updated: 1 files", detail)
        self.assertEqual(pkm_core.get_current_props(destination)["path"], "Notes")
        self.assertTrue(list(self.backup_root.rglob("old_*.md.bak")))  # 옮기기 전 백업

    def test_creates_missing_target_folder(self):
        note = self.write("Inbox/n.md", "---\npath: New / Deep\n---\nB\n")
        status, destination, _ = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "moved")
        self.assertTrue((self.vault / "New" / "Deep" / "n.md").exists())

    def test_skips_when_no_path_property(self):
        note = self.write("Inbox/y.md", "그냥 본문\n")
        status, _, detail = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "skipped")
        self.assertIn("path", detail)
        self.assertTrue(note.exists())

    def test_reports_conflict_and_leaves_both_files(self):
        note = self.write("Inbox/z.md", "---\npath: Notes\n---\nz\n")
        existing = self.write("Notes/z.md", "이미 있음")
        status, _, detail = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "conflict")
        self.assertTrue(note.exists())
        self.assertEqual(self.read(existing), "이미 있음")
        self.assertIn("이미 있습니다", detail)

    def test_rejects_path_that_escapes_the_vault(self):
        note = self.write("Inbox/w.md", "---\npath: ../../etc\n---\nw\n")
        status, destination, detail = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "error")
        self.assertIsNone(destination)
        self.assertIn("traversal", detail)
        self.assertTrue(note.exists())

    def test_already_in_place_is_skipped_and_path_value_is_synced(self):
        note = self.write("Notes/n.md", "---\npath: Notes\n---\nB\n")
        status, _, detail = pkm_core.move_note_to_path_prop(note, self.vault)
        self.assertEqual(status, "skipped")
        self.assertIn("이미", detail)


# ---------------------------------------------------------------- 노트 관계
class RelationTests(TempVaultCase):
    def test_score_note_relation_adds_points_and_reasons(self):
        score, reasons = pkm_core.score_note_relation(
            meta(topics=["a", "b"], tags=["t"], domain="d", engine="e"),
            meta(topics=["b", "c"], tags=["t", "u"], domain="d", engine="x"),
        )
        self.assertEqual(score, 3 + 2 + 1)
        self.assertEqual(reasons, ["shared topic: b", "shared tag: t", "same domain: d"])

    def test_score_note_relation_counts_each_shared_topic_and_tag(self):
        score, _ = pkm_core.score_note_relation(
            meta(topics=["a", "b"], tags=["t", "u"]), meta(topics=["a", "b"], tags=["t", "u"])
        )
        self.assertEqual(score, 3 * 2 + 2 * 2)

    def test_score_note_relation_ignores_empty_domain_and_engine(self):
        self.assertEqual(pkm_core.score_note_relation(meta(), meta()), (0, []))

    def test_score_note_relation_lists_at_most_three_names_per_reason(self):
        many = ["a", "b", "c", "d"]
        _, reasons = pkm_core.score_note_relation(meta(topics=many), meta(topics=many))
        self.assertEqual(reasons, ["shared topic: a, b, c"])

    def test_format_related_note_line(self):
        target = {"title": "제목", "page_name": "p.md", "rel_path": "A/제목.md"}
        self.assertEqual(
            pkm_core.format_related_note_line(target), "- [제목](./p.md) `A/제목.md`"
        )
        self.assertEqual(
            pkm_core.format_related_note_line(target, "같은 주제", prefix="↩ "),
            "- ↩ [제목](./p.md) `A/제목.md` — 같은 주제",
        )

    def test_render_note_relation_page_empty_sections_say_none(self):
        page = pkm_core.render_note_relation_page(
            {
                "title": "T", "rel_path": "A/T.md", "domain": "", "engine": "", "topics": [],
                "type_value": "", "tags": [], "direct_links": [], "backlinks": [],
                "related_notes": [], "unresolved_links": [],
            }
        )
        self.assertTrue(page.startswith("# T\n"))
        self.assertIn("- source: `A/T.md`", page)
        self.assertIn("- topic: `[]`", page)
        self.assertEqual(page.count("- 없음"), 3)
        self.assertNotIn("Unresolved Links", page)
        self.assertTrue(page.endswith("\n"))

    def test_render_note_relation_page_with_content(self):
        page = pkm_core.render_note_relation_page(
            {
                "title": "T", "rel_path": "A/T.md", "domain": "자기", "engine": "concept",
                "topics": ["a", "b"], "type_value": "note", "tags": ["x"],
                "direct_links": ["- d1"], "backlinks": ["- b1"], "related_notes": ["- r1"],
                "unresolved_links": ["missing"],
            }
        )
        self.assertIn("- domain: `자기`", page)
        self.assertIn("- topic: `[a, b]`", page)
        self.assertIn("## Unresolved Links\n- `missing`", page)
        self.assertNotIn("- 없음", page)

    def test_build_note_lookup_and_resolve_wikilink_target(self):
        a = self.write("A/alpha.md")
        b = self.write("B/Beta.md")
        c1 = self.write("A/dup.md")
        c2 = self.write("B/dup.md")
        lookup = pkm_core.build_note_lookup([a, b, c1, c2], self.vault)
        self.assertEqual(set(lookup["unique_stems"]), {"alpha", "beta"})  # 겹치는 제목은 빠짐
        resolve = lambda raw: pkm_core.resolve_wikilink_target(a, raw, self.vault, lookup)
        self.assertEqual(resolve("B/beta"), b)  # 경로(대소문자 무시)
        self.assertEqual(resolve("B/Beta.md"), b)
        self.assertEqual(resolve("beta"), b)  # 제목만
        self.assertEqual(resolve("../B/Beta"), b.resolve())  # 글이 있는 폴더 기준
        self.assertEqual(resolve("dup"), c1)  # 같은 폴더(A)에 있는 글이 먼저 잡힘
        other_source = self.write("C/src.md")
        self.assertIsNone(
            pkm_core.resolve_wikilink_target(other_source, "dup", self.vault, lookup)
        )  # 다른 폴더에서는 제목이 겹치면 못 정함
        self.assertIsNone(resolve("nothing"))
        self.assertIsNone(resolve(""))

    def test_resolve_markdown_target(self):
        a = self.write("A/alpha.md")
        b = self.write("B/beta.md")
        lookup = pkm_core.build_note_lookup([a, b], self.vault)
        resolve = lambda raw: pkm_core.resolve_markdown_target(a, raw, self.vault, lookup)
        self.assertEqual(resolve("../B/beta.md"), b.resolve())
        self.assertEqual(resolve("<../B/beta#h>"), b.resolve())
        self.assertEqual(resolve("/B/beta.md"), b.resolve())
        self.assertIsNone(resolve("https://example.com/x.md"))
        self.assertIsNone(resolve("#top"))
        self.assertIsNone(resolve("../B/none.md"))


if __name__ == "__main__":
    unittest.main()
