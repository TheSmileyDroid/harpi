from __future__ import annotations

from pathlib import Path

import pytest

from src.panel import vault_index
from src.panel.vault import Vault
from src.panel.vault_index import VaultIndex

SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def character(
    *,
    identifier: str = "chr_ana",
    status: str = "ativo",
    extra: str = "",
    body: str = "",
) -> str:
    return (
        "---\n"
        "tipo: personagem\n"
        f"harpi-id: {identifier}\n"
        "harpi-campanha: paratheos\n"
        f"harpi-status: {status}\n"
        f"{extra}"
        "---\n"
        f"{body}"
    )


def sheet(
    *,
    identifier: str = "sht_ana",
    status: str = "ativo",
    owner: str = "555",
    character_field: str = "[[Ana]]",
    character_id: str | None = "chr_ana",
) -> str:
    lines = [
        "---",
        "tipo: ficha",
        f"harpi-id: {identifier}",
        "harpi-campanha: paratheos",
        f"harpi-character: {character_field}",
    ]
    if character_id is not None:
        lines.append(f"harpi-character-id: {character_id}")
    lines.extend([
        f"harpi-owner: {owner}",
        f"harpi-status: {status}",
        "---",
        "",
    ])
    return "\n".join(lines)


@pytest.fixture(autouse=True)
def reset_index():
    yield
    vault_index.configure(vault_index.VaultIndex())


def test_the_index_reads_characters_and_sheets_at_boot(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(
            extra='imagem: "[[Arte/ana.png]]"\n',
            body="## Resumo\n\nMensageira sem memória.\n",
        ),
    )
    write(tmp_path, f"{CAMPAIGN}/sheets/Ana.md", sheet())

    index = VaultIndex(tmp_path)
    campaign = index.campaign(SLUG)

    ana = campaign.characters["chr_ana"]
    assert ana.name == "Ana"
    assert ana.status == "ativo"
    assert ana.summary == "Mensageira sem memória."
    assert ana.portrait == "Arte/ana.png"
    assert campaign.sheets[0].id == "sht_ana"
    assert campaign.sheets[0].character == "chr_ana"
    assert campaign.sheets[0].owner == "555"
    assert campaign.sheets[0].status == "ativo"


def test_the_concept_comes_from_the_concept_aspect(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(
            body="- **Conceito:** Piloto de carga\n- **Problema:** Fuga\n"
        ),
    )

    ana = VaultIndex(tmp_path).campaign(SLUG).characters["chr_ana"]

    assert ana.concept == "Piloto de carga"


def test_the_summary_falls_back_to_the_first_paragraph(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(
            body="# Ana\n\nUma médica de campo.\n\nSegundo parágrafo.\n"
        ),
    )

    ana = VaultIndex(tmp_path).campaign(SLUG).characters["chr_ana"]

    assert ana.summary == "Uma médica de campo."


def test_the_portrait_falls_back_to_the_first_embed(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(body="![[ana.png]]\n\nDepois.\n"),
    )

    ana = VaultIndex(tmp_path).campaign(SLUG).characters["chr_ana"]

    assert ana.portrait == "ana.png"


def test_the_scan_ignores_dotfiles_temporaries_and_syncthing_copies(
    tmp_path: Path,
):
    for name in (
        ".hidden.md",
        "~syncthing~Ana.md",
        "Ana.sync-conflict-20260101.md",
        "Ana.md.tmp",
    ):
        write(tmp_path, f"{CAMPAIGN}/characters/{name}", character())
    write(tmp_path, f"{CAMPAIGN}/characters/Ana.md", character())

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert list(campaign.characters) == ["chr_ana"]


def test_an_unreachable_root_is_not_available(tmp_path: Path):
    index = VaultIndex(tmp_path / "missing")

    assert index.available is False
    assert index.campaign(SLUG).characters == {}


async def test_the_periodic_scan_rebuilds_the_configured_index(tmp_path: Path):
    write(tmp_path, f"{CAMPAIGN}/characters/Ana.md", character())
    vault_index.configure(VaultIndex(tmp_path))
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Bia.md",
        character(identifier="chr_bia"),
    )

    await vault_index.refresh_once(Vault(root=tmp_path))

    assert "chr_bia" in vault_index.configured().campaign(SLUG).characters


def test_a_sheet_resolves_an_external_character_by_name(tmp_path: Path):
    write(
        tmp_path,
        "Mundo/IR1S.md",
        character(identifier="chr_ab12", body="Piloto do mundo.\n"),
    )
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/IR1S.md",
        sheet(character_field="[[IR1S]]", character_id=None),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert campaign.sheets[0].character == "chr_ab12"
    assert campaign.characters["chr_ab12"].summary == "Piloto do mundo."


def test_an_external_character_without_an_id_is_keyed_by_the_sheet(
    tmp_path: Path,
):
    write(tmp_path, "Mundo/IR1S.md", "---\ntipo: personagem\n---\nNeblina.\n")
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/IR1S.md",
        sheet(character_field="[[IR1S]]", character_id=None),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert campaign.sheets[0].character == "sht_ana"
    assert "sht_ana" in campaign.characters


def test_a_sheet_link_with_a_path_resolves_the_note(tmp_path: Path):
    write(tmp_path, "Mundo/IR1S.md", character(identifier="chr_ab12"))
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/Ana.md",
        sheet(character_field="[[Mundo/IR1S.md]]", character_id=None),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert campaign.sheets[0].character == "chr_ab12"


def test_a_sheet_link_can_point_at_a_campaign_character(tmp_path: Path):
    write(tmp_path, f"{CAMPAIGN}/characters/Ana.md", character())
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/Ana.md",
        sheet(character_field="[[Ana]]", character_id=None),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert campaign.sheets[0].character == "chr_ana"
    assert list(campaign.characters) == ["chr_ana"]


def test_two_sheets_sharing_an_external_character_keep_one_note(
    tmp_path: Path,
):
    write(tmp_path, "Mundo/IR1S.md", "---\ntipo: personagem\n---\nNeblina.\n")
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/A.md",
        sheet(
            identifier="sht_a", character_field="[[IR1S]]", character_id=None
        ),
    )
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/B.md",
        sheet(
            identifier="sht_b", character_field="[[IR1S]]", character_id=None
        ),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert {sheet.character for sheet in campaign.sheets} == {"sht_a"}
    assert list(campaign.characters) == ["sht_a"]


def test_a_sheet_without_a_character_link_stays_orphan(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/sheets/Ana.md",
        sheet(character_field="[[Missing]]", character_id=None),
    )

    campaign = VaultIndex(tmp_path).campaign(SLUG)

    assert campaign.sheets[0].character is None


def test_a_fenced_block_never_becomes_the_summary(tmp_path: Path):
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(body="```\ncode\n```\n\nUma médica de campo.\n"),
    )

    ana = VaultIndex(tmp_path).campaign(SLUG).characters["chr_ana"]

    assert ana.summary == "Uma médica de campo."


def portrait_vault(tmp_path: Path) -> Path:
    write(
        tmp_path,
        f"{CAMPAIGN}/characters/Ana.md",
        character(body="![[ana.png]]\n"),
    )
    (tmp_path / "Arte").mkdir(parents=True)
    (tmp_path / "Arte" / "ana.png").write_bytes(b"portrait")
    return tmp_path


def test_a_portrait_by_name_is_found_anywhere_in_the_vault(tmp_path: Path):
    index = VaultIndex(portrait_vault(tmp_path))

    path = index.portrait_path("ana.png")

    assert path == (tmp_path / "Arte" / "ana.png").resolve()


def test_a_duplicated_portrait_name_takes_the_shortest_path(tmp_path: Path):
    (tmp_path / "a" / "b" / "deep").mkdir(parents=True)
    (tmp_path / "a" / "b" / "deep" / "ana.png").write_bytes(b"deep")
    (tmp_path / "ana.png").write_bytes(b"short")
    index = VaultIndex(tmp_path)

    assert index.portrait_path("ana.png") == (tmp_path / "ana.png").resolve()


def test_a_portrait_path_is_served_relative_to_the_vault(tmp_path: Path):
    index = VaultIndex(portrait_vault(tmp_path))

    assert (
        index.portrait_path("Arte/ana.png")
        == (tmp_path / "Arte" / "ana.png").resolve()
    )


@pytest.mark.parametrize(
    "reference",
    [
        "",
        None,
        "../outside.png",
        "Arte/../../outside.png",
        "/etc/passwd.png",
        ".hidden.png",
        "~backup.png",
        "Arte/ana.svg",
        "Arte/missing.png",
    ],
)
def test_an_unsafe_or_unknown_portrait_is_refused(
    tmp_path: Path, reference: str | None
):
    index = VaultIndex(portrait_vault(tmp_path))

    assert index.portrait_path(reference) is None


def test_a_symlink_outside_the_root_is_refused(tmp_path: Path):
    root = portrait_vault(tmp_path / "vault")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"secret")
    (root / "Arte" / "link.png").symlink_to(outside)
    index = VaultIndex(root)

    assert index.portrait_path("Arte/link.png") is None


def test_a_symlink_to_a_non_raster_is_refused(tmp_path: Path):
    root = portrait_vault(tmp_path / "vault")
    (root / "Arte" / "real.svg").write_text("<svg/>", encoding="utf-8")
    (root / "Arte" / "link.png").symlink_to(root / "Arte" / "real.svg")
    index = VaultIndex(root)

    assert index.portrait_path("Arte/link.png") is None
