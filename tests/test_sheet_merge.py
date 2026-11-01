from __future__ import annotations


from src.panel import sheet_store
from src.panel.schemas import SheetPatch
from src.panel.sheet_merge import (
    SheetState,
    apply_patch,
    merge,
    patch_from_state,
    state_from_base,
)
from src.panel.sheets import sha256_text


def aspects(*items: tuple[str, str]) -> list[dict[str, str]]:
    return [{"label": label, "text": text} for label, text in items]


def state(
    *,
    history: str = "Antes.",
    notes: str = "Fim.",
    refresh: int = 7,
    fate_points: int = 3,
    status: str = "ativo",
    aspect_items: list[dict[str, str]] | None = None,
) -> SheetState:
    block = {
        "refresh": refresh,
        "fate_points": fate_points,
        "aspects": aspect_items
        if aspect_items is not None
        else aspects(("Conceito", "Piloto"), ("Problema", "Sem memória")),
        "skills": [],
        "stunts": [],
        "stress": [],
        "consequences": [],
        "extras": [],
        "inventory": [],
    }
    return SheetState({"harpi-status": status}, history, notes, block)


def conflict_paths(result) -> list[str]:
    return [conflict.field_path for conflict in result.remaining]


def test_a_vault_only_change_is_accepted():
    base = state()
    theirs = state(refresh=9)

    result = merge(base, base, theirs)

    assert result.remaining == ()
    assert result.state.block["refresh"] == 9


def test_a_panel_only_change_is_written():
    base = state()
    ours = state(refresh=5)

    result = merge(base, ours, base)

    assert result.remaining == ()
    assert result.state.block["refresh"] == 5


def test_no_change_keeps_the_base():
    base = state()

    result = merge(base, base, base)

    assert result.remaining == ()
    assert result.state == base


def test_the_same_value_on_both_sides_is_accepted():
    base = state()
    both = state(fate_points=1)

    result = merge(base, both, both)

    assert result.remaining == ()
    assert result.state.block["fate_points"] == 1


def test_different_values_conflict_on_that_field():
    base = state()
    ours = state(refresh=5)
    theirs = state(refresh=9)

    result = merge(base, ours, theirs)

    assert conflict_paths(result) == ["block.refresh"]
    conflict = result.remaining[0]
    assert (conflict.base, conflict.ours, conflict.theirs) == (7, 5, 9)
    assert result.state.block["refresh"] == 9


def test_items_are_matched_by_label_not_position():
    base = state()
    ours = state(
        aspect_items=aspects(
            ("Conceito", "Mensageira"), ("Problema", "Sem memória")
        )
    )
    theirs = state(
        aspect_items=aspects(
            ("Problema", "Sem passado"), ("Conceito", "Piloto")
        )
    )

    result = merge(base, ours, theirs)

    assert result.remaining == ()
    assert result.state.block["aspects"] == aspects(
        ("Problema", "Sem passado"), ("Conceito", "Mensageira")
    )


def test_an_item_deleted_on_one_side_is_removed():
    base = state()
    ours = state(aspect_items=aspects(("Conceito", "Piloto")))

    result = merge(base, ours, base)

    assert result.remaining == ()
    assert result.state.block["aspects"] == aspects(("Conceito", "Piloto"))


def test_an_item_changed_on_both_sides_is_a_conflict():
    base = state()
    ours = state(
        aspect_items=aspects(
            ("Conceito", "Mensageira"), ("Problema", "Sem memória")
        )
    )
    theirs = state(
        aspect_items=aspects(
            ("Conceito", "Contrabandista"), ("Problema", "Sem memória")
        )
    )

    result = merge(base, ours, theirs)

    assert conflict_paths(result) == ["block.aspects[Conceito]"]
    conflict = result.remaining[0]
    assert conflict.allow_both is True
    assert conflict.ours["text"] == "Mensageira"
    assert result.state.block["aspects"] == aspects(
        ("Conceito", "Contrabandista"), ("Problema", "Sem memória")
    )


def test_keep_both_duplicates_the_label():
    base = state()
    ours = state(aspect_items=aspects(("Conceito", "Mensageira")))
    theirs = state(aspect_items=aspects(("Conceito", "Contrabandista")))

    result = merge(
        base, ours, theirs, decisions={"block.aspects[Conceito]": "both"}
    )

    assert result.remaining == ()
    assert result.state.block["aspects"] == aspects(
        ("Conceito", "Mensageira"), ("Conceito", "Contrabandista")
    )


def test_a_prose_conflict_can_take_either_side():
    base = state()
    ours = state(history="Do painel.")
    theirs = state(history="Do vault.")

    taken_ours = merge(base, ours, theirs, decisions={"history": "ours"})
    taken_theirs = merge(base, ours, theirs, decisions={"history": "theirs"})

    assert conflict_paths(taken_ours) == []
    assert taken_ours.state.history == "Do painel."
    assert taken_theirs.state.history == "Do vault."


def test_keep_both_keeps_both_prose_texts():
    base = state()
    ours = state(history="Do painel.")
    theirs = state(history="Do vault.")

    result = merge(base, ours, theirs)
    taken = merge(base, ours, theirs, decisions={"history": "both"})

    assert result.remaining[0].allow_both is True
    assert taken.remaining == ()
    assert taken.state.history == "Do painel.\n\nDo vault."


def stress(*marks: tuple[int, bool]) -> list[dict[str, object]]:
    return [
        {
            "track": "Físico",
            "boxes": [
                {"value": value, "checked": checked}
                for value, checked in marks
            ],
        }
    ]


def test_stress_boxes_are_matched_by_track_and_value():
    base = state()
    base.block["stress"] = stress((1, False), (2, False))
    ours = state()
    ours.block["stress"] = stress((1, True), (2, False))
    theirs = state()
    theirs.block["stress"] = stress((1, False), (2, True))

    result = merge(base, ours, theirs)

    assert result.remaining == ()
    assert result.state.block["stress"] == stress((1, True), (2, True))


def test_removing_a_box_while_the_other_side_marks_it_is_a_conflict():
    base = state()
    base.block["stress"] = stress((1, False))
    ours = state()
    ours.block["stress"] = stress((1, True))
    theirs = state()
    theirs.block["stress"] = [{"track": "Físico", "boxes": []}]

    result = merge(base, ours, theirs)

    assert conflict_paths(result) == ["block.stress[Físico].box[1]"]
    assert result.remaining[0].allow_both is False
    assert result.state.block["stress"] == [{"track": "Físico", "boxes": []}]


def test_removing_the_whole_track_while_the_other_side_marks_it_conflicts():
    base = state()
    base.block["stress"] = stress((1, False))
    ours = state()
    ours.block["stress"] = stress((1, True))
    theirs = state()

    result = merge(base, ours, theirs)
    taken = merge(
        base, ours, theirs, decisions={"block.stress[Físico]": "theirs"}
    )

    assert conflict_paths(result) == ["block.stress[Físico]"]
    assert result.state.block["stress"] == []
    assert taken.remaining == ()
    assert taken.state.block["stress"] == []


def test_the_status_changed_only_in_the_vault_is_accepted():
    base = state()
    theirs = state(status="arquivado")

    result = merge(base, base, theirs)

    assert result.remaining == ()
    assert result.state.frontmatter["harpi-status"] == "arquivado"


def test_a_status_patch_loses_to_a_hand_edited_status():
    base = state()
    ours = state(status="arquivado")
    theirs = state(status="pendente")

    result = merge(base, ours, theirs)

    assert result.remaining == ()
    assert result.state.frontmatter["harpi-status"] == "pendente"


def test_the_patch_carries_only_what_differs_from_the_disk():
    theirs = state(refresh=9)
    merged = state(refresh=9, fate_points=1, history="Nova.")

    changes = patch_from_state(theirs, merged)

    assert changes == {"fate_points": 1, "history": "Nova."}


def test_a_stale_scalar_write_leaves_unchanged_lists_alone():
    theirs = state(refresh=9)
    theirs.block.pop("skills")
    merged = state(refresh=9, fate_points=1)
    merged.block.pop("skills")

    changes = patch_from_state(theirs, merged)

    assert changes == {"fate_points": 1}


def test_disk_prose_with_a_hard_break_is_not_rewritten():
    theirs = state(history="Linha  \nOutra.")
    merged = state(history="Linha  \nOutra.", refresh=9)

    changes = patch_from_state(theirs, merged)

    assert "history" not in changes


def test_the_base_snapshot_parses_back_to_the_same_state():
    stored = sheet_store.base_state(
        "---\n"
        "tipo: ficha\n"
        "harpi-id: sht_ana\n"
        "harpi-status: ativo\n"
        "---\n\n## História\n\nAntes.\n\n"
        "```harpi-sheet\n"
        "refresh: 7\n"
        "aspects:\n"
        "  - {label: Conceito, text: Piloto}\n"
        "```\n\n## Anotações\n\nFim.\n"
    )

    parsed = state_from_base(stored)

    assert parsed.frontmatter["harpi-status"] == "ativo"
    assert parsed.history == "Antes."
    assert parsed.notes == "Fim."
    assert parsed.block["refresh"] == 7
    assert parsed.block["aspects"] == aspects(("Conceito", "Piloto"))


def test_the_panel_side_is_the_base_plus_the_patch():
    base = state()
    patch = SheetPatch(
        base_hash=sha256_text("x"),
        refresh=4,
        aspects=[{"label": "Conceito", "text": "Mensageira"}],
        history="Nova.",
    )

    ours = apply_patch(base, patch)

    assert ours.block["refresh"] == 4
    assert ours.block["aspects"] == aspects(("Conceito", "Mensageira"))
    assert ours.history == "Nova."
    assert ours.block["fate_points"] == 3
