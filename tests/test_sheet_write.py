from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest

from src.panel import notes, sheet_store, vault_write
from src.panel.notes import parse_sheet
from src.panel.schemas import SheetPatch
from src.panel.sheet_write import (
    SheetConflict,
    SheetInvalid,
    SheetReadOnly,
    SheetRecord,
    SheetRejected,
    patch_sheet,
    safe_component,
    write_sheet,
)
from src.panel.sheets import parse_config, sha256_text
from src.panel.vault_write import atomic_write, backup_text

CONFIG = """\
```harpi-campaign
name: Paratheos
ladder:
  - {rank: 4, label: Ótimo}
  - {rank: 3, label: Bom}
  - {rank: 2, label: Razoável}
  - {rank: 1, label: Regular}
stress:
  - {track: Físico, boxes: [1, 2, 3]}
  - {track: Mental, boxes: [1, 2]}
consequences:
  - {severity: Leve, value: 2}
  - {severity: Moderada, value: 4}
refresh: 7
extras:
  - Noética
```
"""

SOURCE = """\
---
tipo: ficha
harpi-id: sht_ana
harpi-campanha: paratheos
harpi-owner: "555"
harpi-status: ativo
harpi-rev: 3
aliases: []
tags:
  - ficha
# comentario do narrador
nota-livre: "fica"
---
Abertura intacta  com  dois espacos.

## História

Antiga.

```harpi-sheet
refresh: 7  # recarga
fate_points: 2
aspects:
  - {label: Conceito, text: "Piloto"}
stress:
  - track: Físico
    boxes:
      - {value: 1, checked: false}
      - {value: 2, checked: true}
house_rule: vento forte  # regra da casa
```

## Anotações

Fim.
"""


def config():
    parsed = parse_config(CONFIG)
    assert parsed is not None
    return parsed


def base_hash(text: str = SOURCE) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def patch(**changes) -> SheetPatch:
    return SheetPatch(base_hash=base_hash(), **changes)


def test_the_write_uses_a_temporary_file_then_replaces_it(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "Ana.md"
    target.write_text("antigo", encoding="utf-8")
    seen: list[tuple[Path, Path]] = []
    real_replace = Path.replace

    def spy(source, destination):
        seen.append((source, Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(Path, "replace", spy)

    atomic_write(target, "novo")

    source, destination = seen[0]
    assert destination == target
    assert source.parent == target.parent
    assert source.name == f".harpi-tmp-{vault_write.os.getpid()}"
    assert target.read_text(encoding="utf-8") == "novo"
    assert not source.exists()


def test_a_failed_replace_keeps_the_original_and_cleans_the_temporary(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "Ana.md"
    target.write_text("antigo", encoding="utf-8")

    def fail(source, destination):
        raise OSError("disco cheio")

    monkeypatch.setattr(Path, "replace", fail)

    with pytest.raises(OSError):
        atomic_write(target, "novo")

    assert target.read_text(encoding="utf-8") == "antigo"
    assert not list(tmp_path.glob(".harpi-tmp-*"))


def test_concurrent_writes_to_different_files_keep_their_own_bytes(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    payloads = {
        f"{index}.md": f"{index}:" + "x" * 200_000 for index in range(6)
    }
    paths = {name: tmp_path / name for name in payloads}

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(
            pool.map(
                lambda item: atomic_write(paths[item[0]], item[1]),
                payloads.items(),
            )
        )

    assert {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    } == payloads
    assert not list(tmp_path.glob(".harpi-tmp-*"))


def test_the_backup_and_the_replace_are_fsynced(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    calls: list[int] = []
    real_fsync = vault_write.os.fsync

    def spy(descriptor: int) -> None:
        calls.append(descriptor)
        real_fsync(descriptor)

    monkeypatch.setattr(vault_write.os, "fsync", spy)
    backup_text(tmp_path / "backups", "antigo", 1)
    assert len(calls) >= 2

    calls.clear()
    atomic_write(tmp_path / "Ana.md", "novo")
    assert len(calls) >= 2


def test_backups_keep_the_last_twenty(tmp_path):
    directory = tmp_path / "backups"

    for rev in range(25):
        backup_text(directory, f"rev {rev}", rev)

    backups = sorted(directory.glob("*.md"))
    assert len(backups) == 20
    assert any(path.name.startswith("24-") for path in backups)


def test_a_patch_rewrites_only_the_app_owned_parts():
    result = patch_sheet(
        SOURCE,
        "paratheos",
        "sht_ana",
        patch(refresh=4, history="Nova."),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 3),
    )

    text = result.text
    head, rest = text.split("## História\n", 1)
    original_head, _ = SOURCE.split("## História\n", 1)
    _, notes_after = text.split("## Anotações\n", 1)
    _, original_notes_after = SOURCE.split("## Anotações\n", 1)

    assert head == original_head.replace("harpi-rev: 3", "harpi-rev: 4")
    assert rest.startswith("\nNova.\n\n```harpi-sheet\n")
    assert notes_after == original_notes_after
    assert "refresh: 4  # recarga" in text
    assert "house_rule: vento forte  # regra da casa" in text
    assert 'nota-livre: "fica"' in text
    assert "# comentario do narrador" in text
    assert "Abertura intacta  com  dois espacos." in text


def test_a_heading_inside_a_fence_does_not_end_the_prose_section():
    source = SOURCE.replace(
        "Antiga.\n",
        "Antiga.\n\n```yaml\n## nota\nTexto depois.\n```\n\nFim da história.\n",
    )

    note = parse_sheet("Ana.md", source).note
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), history="Nova."),
        config(),
        None,
    )

    assert "## nota" in note.history
    assert "Fim da história." in note.history
    assert "## nota" not in result.text
    assert "## Anotações" in result.text
    assert "harpi-sheet" in result.text


def test_a_heading_inside_the_sheet_block_does_not_start_a_section():
    source = SOURCE.replace(
        "house_rule: vento forte  # regra da casa\n",
        "house_rule: |\n  ## História\n  perdida no bloco\n",
    )
    assert "perdida no bloco" in source
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), history="Nova."),
        config(),
        None,
    )

    assert "perdida no bloco" in result.text
    assert result.text.count("```") == 2
    assert "## Anotações" in result.text
    assert "Antiga." not in result.text
    assert "# comentario do narrador" in result.text


def test_a_heading_inside_a_fence_before_the_section_is_ignored():
    source = SOURCE.replace(
        "Abertura intacta  com  dois espacos.\n",
        "Abertura intacta  com  dois espacos.\n\n"
        "```md\n## História\nexemplo de cerca\n```\n",
    )
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), history="Nova."),
        config(),
        None,
    )

    assert "exemplo de cerca" in result.text
    assert "Antiga." not in result.text
    assert "## Anotações" in result.text
    assert "harpi-sheet" in result.text


def test_duplicate_prose_sections_are_rejected():
    source = SOURCE + "\n## História\n\nOutra história.\n"

    with pytest.raises(SheetRejected, match="duplicada"):
        patch_sheet(
            source,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash=sha256_text(source), history="Nova."),
            config(),
            None,
        )


def test_a_multiline_scalar_heading_is_not_a_section(tmp_path):
    source = SOURCE.replace(
        "house_rule: vento forte  # regra da casa\n",
        "house_rule: |\n  ## História\n  perdida no bloco\n",
    )
    target = tmp_path / "Ana.md"
    target.write_text(source, encoding="utf-8")

    write_sheet(
        target,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), notes="Nova nota."),
        config(),
        None,
        tmp_path / "vault-backups",
    )

    text = target.read_text(encoding="utf-8")
    assert "perdida no bloco" in text
    assert text.count("```") == 2
    assert "## Anotações" in text


def test_the_stored_base_is_the_parsed_note():
    state = sheet_store.base_state(SOURCE)
    parsed = json.loads(state)

    assert parsed["frontmatter"]["harpi-id"] == "sht_ana"
    assert parsed["history"] == "Antiga."
    assert parsed["notes"] == "Fim."
    assert "refresh: 7" in parsed["block"]


def test_the_block_keeps_unknown_keys_and_comments():
    result = patch_sheet(
        SOURCE,
        "paratheos",
        "sht_ana",
        patch(fate_points=1),
        config(),
        None,
    )

    assert "house_rule: vento forte" in result.text
    assert "regra da casa" in result.text


def test_crlf_line_endings_survive_the_write(tmp_path):
    source = SOURCE.replace("\n", "\r\n")
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), refresh=5),
        config(),
        None,
    )

    assert "\r\n" in result.text
    assert result.text.replace("\r\n", "").count("\n") == 0
    assert "Abertura intacta  com  dois espacos.\r\n" in result.text


def test_prose_only_changes_the_two_app_sections():
    result = patch_sheet(
        SOURCE,
        "paratheos",
        "sht_ana",
        patch(history="Linha nova.  \n\n\nOutra."),
        config(),
        None,
    )

    assert "Linha nova.\n\n\nOutra." in result.text
    assert "Antiga." not in result.text
    assert "Fim." in result.text


def test_missing_prose_sections_are_appended_in_canonical_order():
    source = (
        SOURCE.split("## História")[0] + "```harpi-sheet\nrefresh: 7\n```\n"
    )
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(
            base_hash=sha256_text(source),
            history="Nova.",
            notes="Nota.",
        ),
        config(),
        None,
    )

    assert result.text.index("## História") < result.text.index("## Anotações")
    assert "Nova." in result.text
    assert "Nota." in result.text


def test_invalid_yaml_is_never_patched():
    source = SOURCE.replace("refresh: 7", "refresh: [7")

    with pytest.raises(SheetInvalid):
        patch_sheet(
            source,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash=sha256_text(source), fate_points=1),
            config(),
            None,
        )


def test_a_stale_base_hash_conflicts_without_touching_the_disk(tmp_path):
    target = tmp_path / "Ana.md"
    target.write_text(SOURCE, encoding="utf-8")
    before = target.read_bytes()

    with pytest.raises(SheetConflict):
        write_sheet(
            target,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash="velho", fate_points=1),
            config(),
            None,
            tmp_path / "vault-backups",
        )

    assert target.read_bytes() == before
    assert not (tmp_path / "vault-backups").exists()


def test_the_previous_version_goes_to_the_backup_folder(tmp_path):
    target = tmp_path / "Ana.md"
    target.write_text(SOURCE, encoding="utf-8")
    backup_root = tmp_path / "vault-backups"

    result = write_sheet(
        target,
        "paratheos",
        "sht_ana",
        patch(fate_points=1),
        config(),
        None,
        backup_root,
    )

    backups = list(backup_root.glob("paratheos/sht_ana/*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == SOURCE
    assert backups[0].name.startswith("3-")
    assert result.rev == 4
    assert target.read_text(encoding="utf-8") == result.text


def test_app_owned_keys_are_corrected_on_the_next_write():
    record = SheetRecord("sht_ana", "555", "ativo", 3)
    edited = SOURCE.replace(
        'harpi-owner: "555"', 'harpi-owner: "999"'
    ).replace("harpi-campanha: paratheos", "harpi-campanha: outro")
    result = patch_sheet(
        edited,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(edited), fate_points=1),
        config(),
        record,
    )

    assert 'harpi-owner: "555"' in result.text
    assert "harpi-campanha: paratheos" in result.text
    assert "harpi-owner editado à mão foi corrigido." in result.warnings
    assert "harpi-campanha editado à mão foi corrigido." in result.warnings


def test_the_derived_owner_name_is_rewritten_every_time():
    edited = SOURCE.replace(
        'harpi-owner: "555"',
        'harpi-owner: "555"\nharpi-owner-name: errado',
    )
    result = patch_sheet(
        edited,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(edited), fate_points=1),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 3, owner_name="leandro"),
    )

    assert "harpi-owner-name: leandro" in result.text
    assert "harpi-owner-name: errado" not in result.text


def test_an_illegal_status_transition_is_corrected_with_a_warning():
    record = SheetRecord("sht_ana", "555", "ativo", 3)
    edited = SOURCE.replace("harpi-status: ativo", "harpi-status: pendente")
    result = patch_sheet(
        edited,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(edited), fate_points=1),
        config(),
        record,
    )

    assert "harpi-status: ativo" in result.text
    assert (
        "harpi-status com transição ilegal foi corrigido." in result.warnings
    )


def test_a_status_with_a_trailing_comment_is_read_as_archived():
    source = SOURCE.replace(
        "harpi-status: ativo", "harpi-status: arquivado   # congelada"
    )

    assert notes.scalar("arquivado   # congelada") == "arquivado"
    assert parse_sheet("Ana.md", source).note.status == "arquivado"
    with pytest.raises(SheetReadOnly):
        patch_sheet(
            source,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash=sha256_text(source), fate_points=1),
            config(),
            None,
        )


def test_the_revision_never_goes_backwards():
    source = SOURCE.replace("harpi-rev: 3", "harpi-rev: 4")
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), fate_points=1),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 2),
    )

    assert result.rev == 5
    assert "harpi-rev: 5" in result.text


def test_a_utf8_bom_is_accepted_and_removed(tmp_path):
    target = tmp_path / "Ana.md"
    target.write_bytes(b"\xef\xbb\xbf" + SOURCE.encode("utf-8"))

    write_sheet(
        target,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(SOURCE), fate_points=1),
        config(),
        None,
        tmp_path / "vault-backups",
    )

    assert not target.read_bytes().startswith(b"\xef\xbb\xbf")


def test_a_file_that_is_not_utf8_is_rejected_with_a_reason(tmp_path):
    target = tmp_path / "Ana.md"
    target.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(SheetInvalid, match="UTF-8"):
        write_sheet(
            target,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash="irrelevante", fate_points=1),
            config(),
            None,
            tmp_path / "vault-backups",
        )


def test_a_legal_status_transition_is_written():
    result = patch_sheet(
        SOURCE,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=base_hash(), status="archived"),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 3),
    )

    assert "harpi-status: arquivado" in result.text
    assert result.status == "arquivado"


def test_an_illegal_requested_status_is_ignored_with_a_warning():
    result = patch_sheet(
        SOURCE,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=base_hash(), status="pending"),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 3),
    )

    assert "harpi-status: ativo" in result.text
    assert (
        "harpi-status com transição ilegal foi corrigido." in result.warnings
    )


def test_missing_app_keys_are_inserted_in_the_frontmatter():
    source = SOURCE.replace("harpi-status: ativo\n", "").replace(
        "harpi-rev: 3\n", ""
    )
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), fate_points=1),
        config(),
        None,
    )

    assert "harpi-status: ativo" in result.text
    assert "harpi-rev: 1" in result.text


def test_a_sheet_without_frontmatter_is_rejected():
    source = SOURCE.split("---\n", 2)[2]

    with pytest.raises(SheetInvalid):
        patch_sheet(
            source,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash=sha256_text(source), fate_points=1),
            config(),
            None,
        )


def test_an_invalid_block_value_is_rejected():
    with pytest.raises(SheetRejected):
        patch_sheet(
            SOURCE,
            "paratheos",
            "sht_ana",
            patch(stress=[{"track": "Espiritual", "boxes": []}]),
            config(),
            None,
        )


def test_a_prose_section_added_to_a_file_without_a_final_newline():
    source = SOURCE.split("## Anotações")[0].rstrip("\n")
    result = patch_sheet(
        source,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(source), notes="Nova nota."),
        config(),
        None,
    )

    assert result.text.endswith("## Anotações\n\nNova nota.\n\n")


def test_two_writes_from_the_same_base_do_not_both_win(tmp_path):
    target = tmp_path / "Ana.md"
    target.write_text(SOURCE, encoding="utf-8")
    start = threading.Barrier(2)
    outcomes: list[str] = []

    def run(points: int) -> None:
        start.wait()
        try:
            write_sheet(
                target,
                "paratheos",
                "sht_ana",
                SheetPatch(base_hash=sha256_text(SOURCE), fate_points=points),
                config(),
                None,
                tmp_path / "vault-backups",
            )
            outcomes.append("ok")
        except SheetConflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=run, args=(value,)) for value in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["conflict", "ok"]


def test_a_comment_marker_inside_a_quoted_value_is_not_a_comment():
    edited = SOURCE.replace(
        'harpi-owner: "555"',
        'harpi-owner: "555"\nharpi-owner-name: "Ana #1"',
    )
    result = patch_sheet(
        edited,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(edited), fate_points=1),
        config(),
        SheetRecord("sht_ana", "555", "ativo", 3, owner_name="Ana #2"),
    )

    assert "Ana #1" not in result.text
    assert "Ana #2" in result.text


def test_the_disk_is_checked_again_before_the_backup(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "Ana.md"
    target.write_text(SOURCE, encoding="utf-8")
    calls = iter([SOURCE, "mudou fora"])
    from src.panel import sheet_write

    monkeypatch.setattr(sheet_write, "read_text", lambda path: next(calls))

    with pytest.raises(SheetConflict):
        sheet_write.write_sheet(
            target,
            "paratheos",
            "sht_ana",
            patch(fate_points=1),
            config(),
            None,
            tmp_path / "vault-backups",
        )

    assert not (tmp_path / "vault-backups").exists()


def test_the_backup_folder_name_is_sanitized():
    assert safe_component("../Ana") == ".._Ana"
    assert safe_component("..") == "_"
    assert safe_component("sht_ana") == "sht_ana"


def test_an_archived_sheet_rejects_field_edits_but_can_come_back():
    archived = SOURCE.replace("harpi-status: ativo", "harpi-status: arquivado")
    with pytest.raises(SheetReadOnly):
        patch_sheet(
            archived,
            "paratheos",
            "sht_ana",
            SheetPatch(base_hash=sha256_text(archived), fate_points=1),
            config(),
            None,
        )

    result = patch_sheet(
        archived,
        "paratheos",
        "sht_ana",
        SheetPatch(base_hash=sha256_text(archived), status="active"),
        config(),
        None,
    )

    assert "harpi-status: ativo" in result.text
