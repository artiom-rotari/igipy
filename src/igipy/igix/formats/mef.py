"""MEF parser for the early/beta IGI2 ("igix") mesh format.

The igix MEF is the same ``ILFF`` / ``OCEM`` / ``HSEM`` mesh family as retail IGI2,
observed one format revision earlier. Only four chunks differ in byte layout; every
other chunk class — and all of the assembly, validation and accessor logic — is
reused from :mod:`igipy.igi2.formats.mef` by subclassing its ``MEF`` model (igi2 is
left untouched).

Format delta (igix vs igi2 retail), empirically verified across the igix corpus:

==========  ===========  ==========================  =========================
Chunk       igi2 retail  igix                        struct (igix)
==========  ===========  ==========================  =========================
HSEM        176 bytes    164 bytes                   ``12I12f6If6H7I``
XTRV type3  28 bytes     40 bytes (re-adds normal)   ``<10f``
XTVC        20 bytes     16 bytes                    ``<4f``
ECFC        12 bytes     8 bytes                     ``<4H``
==========  ===========  ==========================  =========================

Everything else (``ATTA``, ``XTVM``, ``TROP``, ``XVTP``, ``CFTP``, ``D3DR``,
``DNER``, ``ECAF``, ``PMTL``, ``REIH``, ``MANB``, ``WOLG``, ``HPRM``, ``HSMC``,
``TAMC``, ``HPSC``, ``TXAN`` and the whole ``SEMS`` collision variant) is imported
verbatim from the igi2 parser.
"""

from collections import defaultdict
from functools import cached_property
from struct import Struct
from typing import ClassVar, Self

from pydantic import BaseModel, Field, NonNegativeInt

from igipy.core.base import StructModel
from igipy.core.formats import ilff
from igipy.igi2.formats import mef as igi2_mef

# igix-specific chunk classes (the four whose byte layout differs from igi2)


class HSEMChunk(ilff.Chunk):
    """Mesh header — 164 bytes in igix (retail IGI2 grew it to 176).

    The header, creation timestamp, model type, bounding boxes and all count
    fields sit at the same offsets as the igi2 header; only the trailing reserved
    zero-padding is shorter (8 trailing ints here versus 11 in retail), so the
    count semantics carry over unchanged.
    """

    unknown_01: NonNegativeInt
    created_at_year: NonNegativeInt
    created_at_month: NonNegativeInt
    created_at_day: NonNegativeInt
    created_at_hour: NonNegativeInt
    created_at_minute: NonNegativeInt
    created_at_second: NonNegativeInt
    created_at_millisecond: NonNegativeInt
    model_type: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt
    bounding_box_min_x: float
    bounding_box_min_y: float
    bounding_box_min_z: float
    bounding_box_max_x: float
    bounding_box_max_y: float
    bounding_box_max_z: float
    bounding_box_2_min_x: float
    bounding_box_2_min_y: float
    bounding_box_2_min_z: float
    bounding_box_2_max_x: float
    bounding_box_2_max_y: float
    bounding_box_2_max_z: float
    render_face_count: NonNegativeInt
    render_vertex_count: NonNegativeInt
    unknown_05: NonNegativeInt
    collision_face_count: NonNegativeInt
    collision_vertex_count: NonNegativeInt
    unknown_06: NonNegativeInt
    bounding_radius: float
    xtvm_count: NonNegativeInt
    atta_count: NonNegativeInt
    xvtp_count: NonNegativeInt
    cftp_count: NonNegativeInt
    trop_count: NonNegativeInt
    reserved_01: int
    reserved_02: int
    reserved_03: int
    reserved_04: int
    reserved_05: int
    reserved_06: int
    reserved_07: int
    reserved_08: int

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"HSEM")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        # noinspection PyTypeChecker
        fields = [field for field in cls.model_fields if field not in {"meta_start", "meta_end", "header"}]
        values = Struct("12I12f6If6H7I").unpack(content)
        return dict(zip(fields, values, strict=True))


class XTRVChunk(igi2_mef.XTRVChunk):
    """Render vertices.

    Type-0 (32 bytes) and type-1 (40 bytes) layouts are identical to igi2, so
    their parsing is inherited. The type-3 (lightmapped/building) vertex differs:
    in igix it is 40 bytes and still carries a per-vertex normal — retail IGI2
    later dropped the normal (28 bytes) because lighting is baked into the
    lightmap. The diffuse UV is named ``uv_u``/``uv_v`` directly (as in type 0/1),
    so the inherited exporter convention applies uniformly.
    """

    class XTRVItem3(StructModel):
        struct: ClassVar = Struct("<10f")

        position_x: float
        position_y: float
        position_z: float
        normal_x: float
        normal_y: float
        normal_z: float
        uv_u: float
        uv_v: float
        lightmap_u: float
        lightmap_v: float

    @cached_property
    def content_3(self) -> list["XTRVChunk.XTRVItem3"]:
        return self.XTRVItem3.unpack_many(self.content)


class XTVCChunk(ilff.Chunk):
    """Collision-mesh vertices — 16 bytes in igix (retail IGI2 uses 20)."""

    class XTVCItem(StructModel):
        struct: ClassVar = Struct("<4f")

        unknown_01: float
        unknown_02: float
        unknown_03: float
        unknown_04: float

    content: list[XTVCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XTVC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.XTVCItem.unpack_many(content)}


class ECFCChunk(ilff.Chunk):
    """Collision-mesh faces — 8 bytes in igix (retail IGI2 uses 12)."""

    class ECFCItem(StructModel):
        struct: ClassVar = Struct("<4H")

        unknown_01: NonNegativeInt
        unknown_02: NonNegativeInt
        unknown_03: NonNegativeInt
        unknown_04: NonNegativeInt

    content: list[ECFCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"ECFC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ECFCItem.unpack_many(content)}


class MEFItem(BaseModel):
    """One collision submesh — igix-typed XTVC/ECFC, reused TAMC/HPSC."""

    xtvc: XTVCChunk
    ecfc: ECFCChunk
    tamc: igi2_mef.TAMCChunk
    hpsc: igi2_mef.HPSCChunk


class MEF(igi2_mef.MEF):
    """Early/beta IGI2 ("igix") MEF model.

    Subclasses the igi2 ``MEF`` model and overrides only what differs: the chunk
    map (the four igix-specific chunk classes swapped in), the typed fields whose
    chunk type changed (``hsem``, ``xtrv``, ``items``), and ``_validate_standard``
    (which keys a class-to-field map by exact chunk type and builds the igix
    ``MEFItem``). The SEMS variant, the ILFF/OCEM stream guard, the HSMC/items
    count validator, and every ``render_*`` / ``bone_*`` accessor are inherited
    unchanged.
    """

    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"HSEM": HSEMChunk,
        b"ATTA": igi2_mef.ATTAChunk,
        b"XTVM": igi2_mef.XTVMChunk,
        b"TROP": igi2_mef.TROPChunk,
        b"XVTP": igi2_mef.XVTPChunk,
        b"CFTP": igi2_mef.CFTPChunk,
        b"D3DR": igi2_mef.D3DRChunk,
        b"ECAF": igi2_mef.ECAFChunk,
        b"DNER": igi2_mef.DNERChunk,
        b"XTRV": XTRVChunk,
        b"PMTL": igi2_mef.PMTLChunk,
        b"REIH": igi2_mef.REIHChunk,
        b"MANB": igi2_mef.MANBChunk,
        b"WOLG": igi2_mef.WOLGChunk,
        b"HPRM": igi2_mef.HPRMChunk,
        b"HSMC": igi2_mef.HSMCChunk,
        b"XTVC": XTVCChunk,
        b"ECFC": ECFCChunk,
        b"TAMC": igi2_mef.TAMCChunk,
        b"HPSC": igi2_mef.HPSCChunk,
        b"TXAN": igi2_mef.TXANChunk,
        b"SEMS": igi2_mef.SEMSChunk,
        b"XTVS": igi2_mef.XTVSChunk,
        b"CAFS": igi2_mef.CAFSChunk,
        b"EGDE": igi2_mef.EGDEChunk,
    }

    # Fields whose chunk type differs from igi2 (the rest are inherited as-is).
    hsem: HSEMChunk | None = None
    xtrv: XTRVChunk | None = None
    items: list[MEFItem] = Field(default_factory=list)

    @classmethod
    def _validate_standard(cls, header: ilff.ILFFHeader, content_type: bytes, content: list[ilff.Chunk]) -> Self:
        field_mapping: dict[type[ilff.Chunk], str] = {
            HSEMChunk: "hsem",
            igi2_mef.ATTAChunk: "atta",
            igi2_mef.XTVMChunk: "xtvm",
            igi2_mef.TROPChunk: "trop",
            igi2_mef.XVTPChunk: "xvtp",
            igi2_mef.CFTPChunk: "cftp",
            igi2_mef.D3DRChunk: "d3dr",
            igi2_mef.ECAFChunk: "ecaf",
            igi2_mef.DNERChunk: "dner",
            XTRVChunk: "xtrv",
            igi2_mef.PMTLChunk: "pmtl",
            igi2_mef.REIHChunk: "reih",
            igi2_mef.MANBChunk: "manb",
            igi2_mef.WOLGChunk: "wolg",
            igi2_mef.HPRMChunk: "hprm",
            igi2_mef.HSMCChunk: "hsmc",
            XTVCChunk: "xtvc",
            ECFCChunk: "ecfc",
            igi2_mef.TAMCChunk: "tamc",
            igi2_mef.HPSCChunk: "hpsc",
            igi2_mef.TXANChunk: "txan",
        }

        field_mapping_values: dict[str, list[ilff.Chunk]] = defaultdict(list)

        for chunk in content:
            field_mapping_values[field_mapping[type(chunk)]].append(chunk)

        instance_values = {}

        for field in ["hsem", "atta", "xtvm", "trop", "xvtp", "cftp", "d3dr", "ecaf", "dner", "xtrv"]:
            if len(field_mapping_values[field]) != 1:
                raise ValueError(f"Multiple {field} chunks found")

            instance_values[field] = field_mapping_values[field][0]

        for field in ["pmtl", "reih", "manb", "wolg", "hprm", "hsmc", "txan"]:
            if len(field_mapping_values[field]) > 1:
                raise ValueError(f"Multiple {field} chunks found")

            if len(field_mapping_values[field]) < 1:
                continue

            instance_values[field] = field_mapping_values[field][0]

        items_count_set = {len(field_mapping_values[field]) for field in ["xtvc", "ecfc", "tamc", "hpsc"]}

        if len(items_count_set) != 1:
            raise ValueError("Different count of items chunks found")

        items = []

        for i in range(items_count_set.pop()):
            # noinspection PyTypeChecker
            items.append(  # noqa: PERF401
                MEFItem(
                    xtvc=field_mapping_values["xtvc"][i],
                    ecfc=field_mapping_values["ecfc"][i],
                    tamc=field_mapping_values["tamc"][i],
                    hpsc=field_mapping_values["hpsc"][i],
                )
            )

        return cls(header=header, content_type=content_type, items=items, **instance_values)
