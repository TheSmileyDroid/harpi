from __future__ import annotations

import pytest

from src.panel.sheets import (
    SheetError,
    dump_block,
    load_sheet,
    parse_config,
    read_sheet,
)

CONFIG = """\
```harpi-campaign
name: Paratheos
system: fate
ladder:
  - {rank: 4, label: Ótimo}
  - {rank: 3, label: Bom}
  - {rank: 2, label: Razoável}
  - {rank: 1, label: Regular}
  - {rank: 0, label: Medíocre}
  - {rank: -1, label: Ruim}
skills:
  - Hackear
  - Atirar
  - Luta
aspects:
  - Conceito
  - Problema
  - Aspecto
  - Aspecto
  - Aspecto
stress:
  - {track: Físico, boxes: [1, 2, 3]}
  - {track: Mental, boxes: [1, 2]}
consequences:
  - {severity: Leve, value: 2}
  - {severity: Moderada, value: 4}
  - {severity: Severa, value: 6}
refresh: 7
extras:
  - Noética
  - EGO
```
"""

SHEET = """\
---
tipo: ficha
harpi-id: sht_ana
harpi-status: ativo
---

## História

Uma piloto sem memória.

```harpi-sheet
refresh: 7
fate_points: 3
aspects:
  - label: Conceito
    text: "A Máquina Fria da Innovation"
  - label: Problema
    text: "Programada para recapturar IR1S"
skills:
  - name: Hackear
    rank: 4
  - name: Atirar
    rank: 3
  - name: Luta
    rank: 2
stunts:
  - name: "Escudo Indestrutível"
    text: "Torna um objeto indestrutível."
    refresh_cost: 1
stress:
  - track: Físico
    boxes:
      - {value: 1, checked: false}
      - {value: 2, checked: true}
  - track: Mental
    boxes:
      - {value: 1, checked: false}
consequences:
  - {severity: Leve, value: 2, text: "Casco rachado"}
  - {severity: Moderada, value: 4, text: ""}
extras:
  - kind: Noética
    name: Constructo
    text: "Corpo artificial."
    cost: 0
inventory:
  - item: "[[Espada de Lancelot]]"
    qty: 1
    note: "Relíquia"
```

## Anotações

Fim.
"""


def config():
    parsed = parse_config(CONFIG)
    assert parsed is not None
    return parsed


def test_a_sheet_block_reads_the_whole_playable_state():
    sheet = read_sheet(load_sheet(SHEET), config())

    assert sheet.refresh == 7
    assert sheet.fate_points == 3
    assert [(aspect.label, aspect.text) for aspect in sheet.aspects] == [
        ("Conceito", "A Máquina Fria da Innovation"),
        ("Problema", "Programada para recapturar IR1S"),
    ]
    assert [(skill.name, skill.rank) for skill in sheet.skills] == [
        ("Hackear", 4),
        ("Atirar", 3),
        ("Luta", 2),
    ]
    assert sheet.stunts[0].name == "Escudo Indestrutível"
    assert sheet.stunts[0].refresh_cost == 1
    assert sheet.stress[0].track == "Físico"
    assert [(box.value, box.checked) for box in sheet.stress[0].boxes] == [
        (1, False),
        (2, True),
    ]
    assert sheet.consequences[0].text == "Casco rachado"
    assert sheet.consequences[1].text == ""
    assert sheet.extras[0].kind == "Noética"
    assert sheet.extras[0].cost == 0
    assert sheet.inventory[0].item == "[[Espada de Lancelot]]"
    assert sheet.inventory[0].qty == 1
    assert sheet.inventory[0].note == "Relíquia"


def test_the_document_only_holds_the_block():
    loaded = load_sheet(SHEET)
    assert loaded.document is not None
    dumped = dump_block(loaded.document)

    assert dumped.strip().startswith("refresh: 7")
    assert "## História" not in dumped
    assert "tipo: ficha" not in dumped


def test_unknown_keys_survive_the_round_trip():
    text = SHEET.replace(
        "fate_points: 3\n",
        "fate_points: 3\nhouse_rule: vento forte\n",
    )

    sheet = read_sheet(load_sheet(text), config())

    assert sheet.unknown == {"house_rule": "vento forte"}
    assert "house_rule: vento forte" in dump_block(sheet.document)


def test_comments_survive_the_round_trip():
    text = SHEET.replace(
        "refresh: 7\n",
        "refresh: 7  # recarga da campanha\n",
    )

    sheet = read_sheet(load_sheet(text), config())

    assert "recarga da campanha" in dump_block(sheet.document)


def test_invalid_yaml_leaves_the_sheet_unreadable():
    text = SHEET.replace("refresh: 7", "refresh: [7")

    loaded = load_sheet(text)

    assert loaded.document is None
    assert loaded.error is not None
    with pytest.raises(SheetError):
        read_sheet(loaded, config())


def test_a_sheet_without_the_block_is_unreadable():
    loaded = load_sheet("---\ntipo: ficha\n---\n\nNada aqui.\n")

    assert loaded.document is None
    assert loaded.error is not None


def test_a_duplicated_skill_is_an_error():
    text = SHEET.replace(
        "  - name: Luta\n    rank: 2\n",
        "  - name: Luta\n    rank: 2\n  - name: Hackear\n    rank: 1\n",
    )

    with pytest.raises(SheetError, match="duplicad"):
        read_sheet(load_sheet(text), config())


def test_a_rank_outside_the_ladder_is_an_error():
    text = SHEET.replace("    rank: 4", "    rank: 9")

    with pytest.raises(SheetError, match="escada"):
        read_sheet(load_sheet(text), config())


def test_a_skill_at_rank_zero_is_an_error():
    text = SHEET.replace("    rank: 2", "    rank: 0")

    with pytest.raises(SheetError, match="rank"):
        read_sheet(load_sheet(text), config())


def test_an_unknown_stress_track_is_an_error():
    text = SHEET.replace("track: Mental", "track: Espiritual")

    with pytest.raises(SheetError, match="trilha"):
        read_sheet(load_sheet(text), config())


def test_an_unknown_consequence_slot_is_an_error():
    text = SHEET.replace("severity: Severa", "severity: Catastrófica").replace(
        "severity: Moderada", "severity: Catastrófica"
    )

    with pytest.raises(SheetError, match="consequ"):
        read_sheet(load_sheet(text), config())


def test_an_unknown_extra_kind_is_an_error():
    text = SHEET.replace("kind: Noética", "kind: Magia")

    with pytest.raises(SheetError, match="extra"):
        read_sheet(load_sheet(text), config())


def test_a_skill_outside_the_config_is_an_error():
    text = SHEET.replace("name: Luta", "name: Magia")

    with pytest.raises(SheetError, match="config"):
        read_sheet(load_sheet(text), config())


def test_a_full_stress_track_reads():
    text = SHEET.replace(
        "      - {value: 2, checked: true}\n",
        "      - {value: 2, checked: true}\n"
        "      - {value: 3, checked: false}\n",
    )

    sheet = read_sheet(load_sheet(text), config())

    assert [box.value for box in sheet.stress[0].boxes] == [1, 2, 3]


def test_more_stress_boxes_than_the_track_is_an_error():
    text = SHEET.replace(
        "      - {value: 2, checked: true}\n",
        "      - {value: 2, checked: true}\n"
        "      - {value: 3, checked: false}\n"
        "      - {value: 4, checked: false}\n"
        "      - {value: 5, checked: false}\n",
    )

    with pytest.raises(SheetError, match="caixas demais"):
        read_sheet(load_sheet(text), config())


def test_a_consequence_value_outside_the_slot_is_an_error():
    text = SHEET.replace(
        '{severity: Moderada, value: 4, text: ""}',
        '{severity: Moderada, value: 9, text: ""}',
    )

    with pytest.raises(SheetError, match="fora do slot"):
        read_sheet(load_sheet(text), config())


def test_a_missing_aspects_list_takes_the_config_labels():
    text = SHEET.replace(
        "aspects:\n"
        '  - label: Conceito\n    text: "A Máquina Fria da Innovation"\n'
        '  - label: Problema\n    text: "Programada para recapturar IR1S"\n',
        "",
    )

    sheet = read_sheet(load_sheet(text), config())

    assert [aspect.label for aspect in sheet.aspects] == [
        "Conceito",
        "Problema",
        "Aspecto",
        "Aspecto",
        "Aspecto",
    ]
    assert all(aspect.text == "" for aspect in sheet.aspects)


def test_a_missing_numeric_field_uses_a_default():
    text = SHEET.replace("refresh: 7\n", "")

    sheet = read_sheet(load_sheet(text), config())

    assert sheet.refresh == 7
    assert sheet.fate_points == 3


def test_the_config_block_reads_the_campaign_rules():
    parsed = config()

    assert parsed.name == "Paratheos"
    assert parsed.system == "fate"
    assert [(step.rank, step.label) for step in parsed.ladder][:2] == [
        (4, "Ótimo"),
        (3, "Bom"),
    ]
    assert parsed.skills == ("Hackear", "Atirar", "Luta")
    assert parsed.aspects == (
        "Conceito",
        "Problema",
        "Aspecto",
        "Aspecto",
        "Aspecto",
    )
    assert [track.track for track in parsed.stress] == ["Físico", "Mental"]
    assert parsed.stress[0].boxes == (1, 2, 3)
    assert [(slot.severity, slot.value) for slot in parsed.consequences] == [
        ("Leve", 2),
        ("Moderada", 4),
        ("Severa", 6),
    ]
    assert parsed.refresh == 7
    assert parsed.extras == ("Noética", "EGO")


def test_a_config_without_the_block_is_missing():
    assert parse_config("# sem bloco\n") is None


def test_an_invalid_config_block_is_missing():
    assert parse_config("```harpi-campaign\nname: [Paratheos\n```\n") is None
