from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_DIR = ROOT / "web" / "src" / "lib" / "contract"
FIXTURES_PATH = CONTRACT_DIR / "fixtures" / "fixtures.json"


def build_fixtures() -> dict[str, object]:
    from src.panel.schemas import (
        ApprovalItem,
        ApprovalList,
        AssetDetail,
        Authenticated,
        BotStatus,
        CampaignDetail,
        CampaignList,
        CampaignSummary,
        CharacterCard,
        CharacterDetail,
        CharacterList,
        Channel,
        ChannelList,
        Connection,
        ConnectionEvent,
        Directory,
        ErrorDetail,
        ErrorEnvelope,
        Guild,
        GuildList,
        Heartbeat,
        Layer,
        PlaybackStatus,
        Position,
        Presence,
        ReloadEvent,
        SearchResults,
        SceneDetail,
        SceneGrid,
        SceneImage,
        SceneList,
        SceneRect,
        SceneSummary,
        SceneZone,
        TableScene,
        TableSummary,
        TableToken,
        SheetActionResult,
        SheetAspect,
        SheetConflictDetail,
        SheetConflictField,
        SheetConflictList,
        SheetConsequence,
        SheetDetail,
        SheetExtra,
        SheetInventoryEntry,
        SheetLadderStep,
        SheetSkill,
        SheetStressBox,
        SheetStressTrack,
        SheetStunt,
        StatusSnapshot,
        Track,
        Viewer,
    )

    track = Track(
        title="Bohemian Rhapsody",
        url="https://example.com/track",
        uploader="Queen",
        duration=354,
        thumbnail="https://example.com/thumb.jpg",
    )
    layer = Layer(
        id="layer-1",
        title="Rain",
        url="https://example.com/layer",
        volume=0.25,
        thumbnail="https://example.com/layer.jpg",
    )
    conflict_field = SheetConflictField(
        id="cnf_1",
        sheet_id="sht_ana",
        character_id="chr_ana",
        field_path="block.refresh",
        base="7",
        ours="9",
        theirs="4",
        allow_both=False,
    )
    fixtures: dict[str, BaseModel] = {
        "ApprovalList": ApprovalList(
            approvals=[
                ApprovalItem(
                    id="apr_1",
                    sheet_id="sht_ana",
                    character_id="chr_ana",
                    character_name="Ana",
                    owner="555",
                    owner_name="Harpi",
                    note="",
                    requested_at=1700000000,
                )
            ]
        ),
        "Authenticated": Authenticated(authenticated=True),
        "AssetDetail": AssetDetail(
            name=f"{'a' * 64}.png",
            path=f"Harpi/Campaigns/paratheos/assets/{'a' * 64}.png",
            url=f"/api/campaigns/paratheos/assets/{'a' * 64}.png",
            hash="a" * 64,
            size=48213,
            content_type="image/png",
            new_file=True,
        ),
        "CampaignDetail": CampaignDetail(
            slug="paratheos",
            name="Paratheos",
            system="fate",
            role="narrator",
            open_table=None,
        ),
        "CampaignList": CampaignList(
            campaigns=[
                CampaignSummary(
                    slug="paratheos",
                    name="Paratheos",
                    system="fate",
                    role="player",
                )
            ],
        ),
        "CharacterList": CharacterList(
            characters=[
                CharacterCard(
                    id="chr_ana",
                    name="Ana",
                    concept="Piloto de carga",
                    summary="Mensageira sem memória.",
                    portrait=(
                        "/api/campaigns/paratheos/characters/chr_ana/portrait"
                    ),
                )
            ],
            own_character_id="chr_ana",
        ),
        "CharacterDetail": CharacterDetail(
            kind="sheet",
            card=CharacterCard(
                id="chr_ana",
                name="Ana",
                concept="Piloto de carga",
                summary="Mensageira sem memória.",
                portrait=(
                    "/api/campaigns/paratheos/characters/chr_ana/portrait"
                ),
            ),
            sheet=SheetDetail(
                id="sht_ana",
                character_id="chr_ana",
                owner="555",
                status="active",
                state="ok",
                read_only=False,
                error=None,
                hash="a" * 64,
                rev=2,
                history="Uma piloto.",
                notes="",
                review_note=None,
                warnings=[],
                refresh=7,
                fate_points=3,
                ladder=[
                    SheetLadderStep(rank=4, label="Ótimo"),
                    SheetLadderStep(rank=3, label="Bom"),
                ],
                aspects=[
                    SheetAspect(label="Conceito", text="Piloto de carga")
                ],
                skills=[SheetSkill(name="Hackear", rank=4, label="Ótimo")],
                stunts=[
                    SheetStunt(
                        name="Escudo",
                        text="Torna um objeto indestrutível.",
                        refresh_cost=1,
                    )
                ],
                stress=[
                    SheetStressTrack(
                        track="Físico",
                        boxes=[SheetStressBox(value=1, checked=True)],
                    )
                ],
                consequences=[
                    SheetConsequence(severity="Leve", value=2, text="")
                ],
                extras=[
                    SheetExtra(
                        kind="Noética",
                        name="Constructo",
                        text="Corpo artificial.",
                        cost=0,
                    )
                ],
                inventory=[
                    SheetInventoryEntry(
                        item="[[Espada de Lancelot]]",
                        qty=1,
                        note="Relíquia",
                    )
                ],
            ),
        ),
        "Directory": Directory(
            guild_id="7",
            guilds=[Guild(id="1", name="Alpha")],
            channels=[Channel(id="10", name="Voice")],
        ),
        "Heartbeat": Heartbeat(),
        "Position": Position(progress=42.5),
        "ChannelList": ChannelList(
            channels=[Channel(id="10", name="Voice")],
        ),
        "ErrorEnvelope": ErrorEnvelope(
            error=ErrorDetail(code="not_found", message="Not found"),
        ),
        "SheetConflictList": SheetConflictList(conflicts=[conflict_field]),
        "SheetConflictDetail": SheetConflictDetail(
            error=ErrorDetail(
                code="sheet_field_conflict",
                message="The same field changed in the panel and in the vault",
            ),
            conflicts=[conflict_field],
        ),
        "SheetActionResult": SheetActionResult(
            action="restore", sheet_id="sht_ana"
        ),
        "GuildList": GuildList(guilds=[Guild(id="1", name="Alpha")]),
        "ReloadEvent": ReloadEvent(scope="shell"),
        "SearchResults": SearchResults(results=[track]),
        "SceneList": SceneList(
            scenes=[
                SceneSummary(
                    slug="cripta",
                    name="Cripta",
                    source="image",
                    thumbnail=(
                        f"/api/campaigns/paratheos/assets/{'a' * 64}.png"
                    ),
                    width=1920,
                    height=1080,
                    grid=SceneGrid(
                        cell_px=70, offset_x=0, offset_y=0, visible=True
                    ),
                    zones=[
                        SceneZone(
                            id="zon_sala",
                            label="Sala principal",
                            revealed=True,
                            rects=[SceneRect(x=1, y=2, w=3, h=2)],
                        )
                    ],
                    zone_count=1,
                    saved=True,
                    in_use=False,
                )
            ]
        ),
        "SceneDetail": SceneDetail(
            slug="cripta",
            name="Cripta",
            source="image",
            image=SceneImage(
                path=f"Harpi/Campaigns/paratheos/assets/{'a' * 64}.png",
                width=1920,
                height=1080,
            ),
            grid=SceneGrid(cell_px=70, offset_x=0, offset_y=0, visible=True),
            fog_outside=True,
            zones=[
                SceneZone(
                    id="zon_sala",
                    label="Sala principal",
                    revealed=True,
                    rects=[SceneRect(x=1, y=2, w=3, h=2)],
                )
            ],
            hash="b" * 64,
            saved=True,
        ),
        "TableSummary": TableSummary(
            id="tbl_1",
            campaign="paratheos",
            channel_id="123456789012345678",
            name="Sessão",
            viewer_id="555",
            role="narrator",
            status="open",
            round=1,
            spectators=False,
            scene=TableScene(
                id="scn_1",
                slug="cripta",
                name="Cripta",
                source="image",
                width=1920,
                height=1080,
                grid=SceneGrid(
                    cell_px=70, offset_x=0, offset_y=0, visible=True
                ),
                fog_outside=True,
                zones=[
                    SceneZone(
                        id="zon_sala",
                        label="Sala principal",
                        revealed=True,
                        rects=[SceneRect(x=1, y=2, w=3, h=2)],
                    )
                ],
                map_url="/api/tables/tbl_1/map",
                saved=True,
                fog=[],
            ),
            tokens=[
                TableToken(
                    id="tok_1",
                    character_id="chr_ana",
                    label="Ana",
                    owner_id="555",
                    x=2,
                    y=2,
                    w=1,
                    h=1,
                    color="#e9dfc7",
                    visible=True,
                    rev=1,
                )
            ],
            warning=None,
        ),
        "Presence": Presence(
            guild_id="7",
            viewers=[
                Viewer(
                    user_id="555",
                    username="harpi-user",
                    display_name="Harpi",
                    channel_id="42",
                    channel_name="Voice",
                    seen_at=1700000000,
                )
            ],
            last_connection=ConnectionEvent(
                action="connect",
                channel_id="42",
                channel_name="Voice",
                actor_id="555",
                actor_name="Harpi",
                at=1700000000,
            ),
        ),
        "StatusSnapshot": StatusSnapshot(
            bot=BotStatus(online=True),
            guild_id="7",
            connection=Connection(connected=True, channel_id="42"),
            playback=PlaybackStatus(
                guild_id="7",
                connected=True,
                is_playing=True,
                is_paused=False,
                current_music=track,
                queue=[track],
                layers=[layer],
                loop_mode="QUEUE",
                volume=0.7,
                progress=42.5,
                channel_id="42",
            ),
        ),
    }
    return {
        name: model.model_dump(mode="json") for name, model in fixtures.items()
    }


def main() -> None:
    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(build_fixtures(), indent=2, sort_keys=True)
    FIXTURES_PATH.write_text(body + "\n")


if __name__ == "__main__":
    main()
