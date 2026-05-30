from collections import defaultdict
from functools import cached_property
from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self, TypeVar

from pydantic import BaseModel, Field, NonNegativeInt, model_validator

from igipy.core.base import StructModel
from igipy.core.formats import ilff
from igipy.igi2.formats.common import REIHChunk


class HSEMChunk(ilff.Chunk):
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
    reserved_09: int
    reserved_10: int
    reserved_11: int

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"HSEM")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        # noinspection PyTypeChecker
        fields = [field for field in cls.model_fields if field not in {"meta_start", "meta_end", "header"}]
        values = Struct("12I12f6If6H10I").unpack(content)
        return dict(zip(fields, values, strict=True))


class ATTAChunk(ilff.Chunk):
    class ATTAItem(StructModel):
        struct: ClassVar = Struct("<16s12f2i")

        name: bytes = Field(min_length=16, max_length=16)
        m00: float
        m01: float
        m02: float
        m10: float
        m11: float
        m12: float
        m20: float
        m21: float
        m22: float
        position_x: float
        position_y: float
        position_z: float
        attach_index: int
        bone_index: int

    content: list[ATTAItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"ATTA")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ATTAItem.unpack_many(content)}


class XTVMChunk(ilff.Chunk):
    class XTVMItem(StructModel):
        struct: ClassVar = Struct("<3fi")

        position_x: float
        position_y: float
        position_z: float
        param: int

    content: list[XTVMItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XTVM")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.XTVMItem.unpack_many(content)}


class TROPChunk(ilff.Chunk):
    class TROPItem(StructModel):
        struct: ClassVar = Struct("<5I")

        unknown_01: NonNegativeInt
        unknown_02: NonNegativeInt
        unknown_03: NonNegativeInt
        unknown_04: NonNegativeInt
        unknown_05: NonNegativeInt

    content: list[TROPItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"TROP")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.TROPItem.unpack_many(content)}


class XVTPChunk(ilff.Chunk):
    class XVTPItem(StructModel):
        struct: ClassVar = Struct("<3f")

        position_x: float
        position_y: float
        position_z: float

    content: list[XVTPItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XVTP")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.XVTPItem.unpack_many(content)}


class CFTPChunk(ilff.Chunk):
    class CFTPItem(StructModel):
        struct: ClassVar = Struct("<3I")

        index_a: NonNegativeInt
        index_b: NonNegativeInt
        index_c: NonNegativeInt

    content: list[CFTPItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"CFTP")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.CFTPItem.unpack_many(content)}


class D3DRItem0(StructModel):
    struct: ClassVar = Struct("<9I")

    flags: NonNegativeInt
    total_face_count: NonNegativeInt
    render_group_count: NonNegativeInt
    total_vertex_count: NonNegativeInt
    reserved_01: NonNegativeInt
    reserved_02: NonNegativeInt
    reserved_03: NonNegativeInt
    reserved_04: NonNegativeInt
    reserved_05: NonNegativeInt


class D3DRItem1(StructModel):
    struct: ClassVar = Struct("<10I")

    flags: NonNegativeInt
    total_face_count: NonNegativeInt
    render_group_count: NonNegativeInt
    unknown_01: NonNegativeInt
    dner_vertex_count: NonNegativeInt
    xtrv_vertex_count: NonNegativeInt
    reserved_01: NonNegativeInt
    reserved_02: NonNegativeInt
    reserved_03: NonNegativeInt
    reserved_04: NonNegativeInt


class D3DRItem3(StructModel):
    struct: ClassVar = Struct("<11I")

    flags: NonNegativeInt
    unknown_01: NonNegativeInt
    total_face_count: NonNegativeInt
    render_group_count: NonNegativeInt
    total_vertex_count: NonNegativeInt
    reserved_01: NonNegativeInt
    reserved_02: NonNegativeInt
    reserved_03: NonNegativeInt
    reserved_04: NonNegativeInt
    reserved_05: NonNegativeInt
    reserved_06: NonNegativeInt


D3DRItem = TypeVar("D3DRItem", D3DRItem0, D3DRItem1, D3DRItem3)


class D3DRChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"D3DR")

    @classmethod
    def parse_content(cls, content: bytes, item_class: type[D3DRItem]) -> D3DRItem:
        content = item_class.unpack_many(content)

        if len(content) != 1:
            raise ValueError("Expected exactly one item in content.")

        return content[0]

    @cached_property
    def content_0(self) -> D3DRItem0:
        return self.parse_content(self.content, self.D3DRItem0)

    @cached_property
    def content_1(self) -> D3DRItem1:
        return self.parse_content(self.content, self.D3DRItem1)

    @cached_property
    def content_3(self) -> D3DRItem3:
        return self.parse_content(self.content, self.D3DRItem3)


class DNERChunk(ilff.RawChunk):
    class DNERItem0(StructModel):
        struct: ClassVar = Struct("<I3f5H3h")

        material_flags: int
        center_x: float
        center_y: float
        center_z: float
        index_start: int
        face_count: int
        vertex_start: int
        vertex_count: int
        group_index: int
        sentinel: int
        unknown_01: int
        unknown_02: int

    class DNERItem1(DNERItem0):
        pass

    class DNERItem3(StructModel):
        struct: ClassVar = Struct("<3f8H")

        center_x: float
        center_y: float
        center_z: float
        unknown_01: int
        unknown_02: int
        index_start: int
        face_count: int
        vertex_start: int
        vertex_count: int
        group_index: int
        reserved: int

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"DNER")

    @cached_property
    def content_0(self) -> list[DNERItem0]:
        return self.DNERItem0.unpack_many(self.content)

    @cached_property
    def content_1(self) -> list[DNERItem1]:
        return self.DNERItem1.unpack_many(self.content)

    @cached_property
    def content_3(self) -> list[DNERItem3]:
        return self.DNERItem3.unpack_many(self.content)


class XTRVChunk(ilff.RawChunk):
    class XTRVItem0(StructModel):
        struct: ClassVar = Struct("<8f")

        position_x: float
        position_y: float
        position_z: float
        normal_x: float
        normal_y: float
        normal_z: float
        uv_u: float
        uv_v: float

    class XTRVItem1(StructModel):
        struct: ClassVar = Struct("<9fHH")

        position_x: float
        position_y: float
        position_z: float
        normal_x: float
        normal_y: float
        normal_z: float
        uv_u: float
        uv_v: float
        bone_weight: float
        vertex_index: int
        bone_index: int

    class XTRVItem3(StructModel):
        struct: ClassVar = Struct("<7f")

        position_x: float
        position_y: float
        position_z: float
        unknown_01: float
        unknown_02: float
        unknown_03: float
        unknown_04: float

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XTRV")

    @cached_property
    def content_0(self) -> list[XTRVItem0]:
        return self.XTRVItem0.unpack_many(self.content)

    @cached_property
    def content_1(self) -> list[XTRVItem1]:
        return self.XTRVItem1.unpack_many(self.content)

    @cached_property
    def content_3(self) -> list[XTRVItem3]:
        return self.XTRVItem3.unpack_many(self.content)


class PMTLChunk(ilff.Chunk):
    class PMTLItem(StructModel):
        struct: ClassVar = Struct("<4H")

        unknown_01: int
        unknown_02: int
        unknown_03: int
        unknown_04: int

    content: list[PMTLItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"PMTL")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.PMTLItem.unpack_many(content)}


class TXANChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"TXAN")


class ECAFChunk(ilff.Chunk):
    class ECAFItem(StructModel):
        struct: ClassVar = Struct("<3H")

        index_a: int
        index_b: int
        index_c: int

    content: list[ECAFItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"ECAF")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ECAFItem.unpack_many(content)}


class MANBChunk(ilff.Chunk):
    content: list[str]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"MANB")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        if len(content) % 16 != 0:
            raise ValueError("Content length must be a multiple of 16.")

        bone_names = [
            chunk.rstrip(b"\x00").decode("utf-8") for chunk in (content[i : i + 16] for i in range(0, len(content), 16))
        ]

        return {"content": bone_names}


class WOLGChunk(ilff.Chunk):
    class WOLGItem(StructModel):
        struct: ClassVar = Struct("<7fI")

        position_x: float
        position_y: float
        position_z: float
        radius: float
        color_red: float
        color_green: float
        color_blue: float
        padding: int

    content: list[WOLGItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"WOLG")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.WOLGItem.unpack_many(content)}


class HPRMChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"HPRM")


# Collision Mesh


class HSMCChunk(ilff.Chunk):
    """
    Collision Meshes.
    """

    class HSMCItem(StructModel):
        struct: ClassVar = Struct("<8I")

        ecfc_length: NonNegativeInt
        xtvc_length: NonNegativeInt
        tamc_length: NonNegativeInt
        hpsc_length: NonNegativeInt
        unknown_01: Literal[0]
        unknown_02: Literal[0]
        unknown_03: Literal[0]
        unknown_04: Literal[0]

    content: list[HSMCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"HSMC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.HSMCItem.unpack_many(content)}


class XTVCChunk(ilff.Chunk):
    """
    Collision Mesh Vertices.
    """

    class XTVCItem(StructModel):
        struct: ClassVar = Struct("<5f")

        unknown_01: float
        unknown_02: float
        unknown_03: float
        unknown_04: float
        unknown_05: float

    content: list[XTVCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XTVC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.XTVCItem.unpack_many(content)}


class ECFCChunk(ilff.Chunk):
    """
    Collision Mesh Faces.
    """

    class ECFCItem(StructModel):
        struct: ClassVar = Struct("<6H")

        unknown_01: NonNegativeInt
        unknown_02: NonNegativeInt
        unknown_03: NonNegativeInt
        unknown_04: NonNegativeInt
        unknown_05: NonNegativeInt
        unknown_06: NonNegativeInt

    content: list[ECFCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"ECFC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ECFCItem.unpack_many(content)}


class TAMCChunk(ilff.Chunk):
    """
    Collision Mesh Material?
    """

    class TAMCItem(StructModel):
        struct: ClassVar = Struct("<8h")

        unknown_01: int
        unknown_02: int
        unknown_03: int
        unknown_04: int
        unknown_05: int
        unknown_06: int
        unknown_07: int
        unknown_08: int

    content: list[TAMCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"TAMC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.TAMCItem.unpack_many(content)}


class HPSCChunk(ilff.Chunk):
    """
    Collision Mesh Something?
    """

    class HPSCItem(StructModel):
        struct: ClassVar = Struct("<4f4h")

        unknown_01: float
        unknown_02: float
        unknown_03: float
        unknown_04: float
        unknown_05: int
        unknown_06: int
        unknown_07: int
        unknown_08: int

    content: list[HPSCItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"HPSC")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.HPSCItem.unpack_many(content)}


# Simplified Collision Mesh (SEMS variant)


class SEMSChunk(ilff.Chunk):
    class SEMSItem(StructModel):
        struct: ClassVar = Struct("<7i")

        cafs_start: int
        xtvs_start: int
        egde_start: int
        cafs_count: int
        xtvs_count: int
        egde_count: int
        sentinel: int

    content: list[SEMSItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"SEMS")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.SEMSItem.unpack_many(content)}


class XTVSChunk(ilff.Chunk):
    class XTVSItem(StructModel):
        struct: ClassVar = Struct("<3f")

        position_x: float
        position_y: float
        position_z: float

    content: list[XTVSItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"XTVS")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.XTVSItem.unpack_many(content)}


class CAFSChunk(ilff.Chunk):
    class CAFSItem(StructModel):
        struct: ClassVar = Struct("<3I4f")

        index_a: NonNegativeInt
        index_b: NonNegativeInt
        index_c: NonNegativeInt
        normal_x: float
        normal_y: float
        normal_z: float
        distance: float

    content: list[CAFSItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"CAFS")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.CAFSItem.unpack_many(content)}


class EGDEChunk(ilff.Chunk):
    class EGDEItem(StructModel):
        struct: ClassVar = Struct("<2I")

        index_a: NonNegativeInt
        index_b: NonNegativeInt

    content: list[EGDEItem]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"EGDE")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.EGDEItem.unpack_many(content)}


# MEF Base


class MEFItem(BaseModel):
    xtvc: XTVCChunk
    ecfc: ECFCChunk
    tamc: TAMCChunk
    hpsc: HPSCChunk


# noinspection DuplicatedCode
class MEF(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"HSEM": HSEMChunk,
        b"ATTA": ATTAChunk,
        b"XTVM": XTVMChunk,
        b"TROP": TROPChunk,
        b"XVTP": XVTPChunk,
        b"CFTP": CFTPChunk,
        b"D3DR": D3DRChunk,
        b"ECAF": ECAFChunk,
        b"DNER": DNERChunk,
        b"XTRV": XTRVChunk,
        b"PMTL": PMTLChunk,
        b"REIH": REIHChunk,
        b"MANB": MANBChunk,
        b"WOLG": WOLGChunk,
        b"HPRM": HPRMChunk,
        b"HSMC": HSMCChunk,
        b"XTVC": XTVCChunk,
        b"ECFC": ECFCChunk,
        b"TAMC": TAMCChunk,
        b"HPSC": HPSCChunk,
        b"TXAN": TXANChunk,
        b"SEMS": SEMSChunk,
        b"XTVS": XTVSChunk,
        b"CAFS": CAFSChunk,
        b"EGDE": EGDEChunk,
    }

    # Standard variant fields (HSEM-based)
    hsem: HSEMChunk | None = None
    atta: ATTAChunk | None = None
    xtvm: XTVMChunk | None = None
    trop: TROPChunk | None = None
    xvtp: XVTPChunk | None = None
    cftp: CFTPChunk | None = None
    d3dr: D3DRChunk | None = None
    ecaf: ECAFChunk | None = None
    dner: DNERChunk | None = None
    xtrv: XTRVChunk | None = None
    pmtl: PMTLChunk | None = None
    reih: REIHChunk | None = None
    manb: MANBChunk | None = None
    wolg: WOLGChunk | None = None
    hprm: HPRMChunk | None = None
    hsmc: HSMCChunk | None = None
    txan: TXANChunk | None = None

    items: list[MEFItem] = Field(default_factory=list)

    # SEMS variant fields (simplified collision mesh)
    sems: SEMSChunk | None = None
    xtvs: XTVSChunk | None = None
    cafs: CAFSChunk | None = None
    egde: EGDEChunk | None = None

    @property
    def is_sems_variant(self) -> bool:
        return self.sems is not None

    @classmethod
    def _validate_standard(cls, header: ilff.ILFFHeader, content_type: bytes, content: list[ilff.Chunk]) -> Self:
        field_mapping: dict[type[ilff.Chunk], str] = {
            HSEMChunk: "hsem",
            ATTAChunk: "atta",
            XTVMChunk: "xtvm",
            TROPChunk: "trop",
            XVTPChunk: "xvtp",
            CFTPChunk: "cftp",
            D3DRChunk: "d3dr",
            ECAFChunk: "ecaf",
            DNERChunk: "dner",
            XTRVChunk: "xtrv",
            PMTLChunk: "pmtl",
            REIHChunk: "reih",
            MANBChunk: "manb",
            WOLGChunk: "wolg",
            HPRMChunk: "hprm",
            HSMCChunk: "hsmc",
            XTVCChunk: "xtvc",
            ECFCChunk: "ecfc",
            TAMCChunk: "tamc",
            HPSCChunk: "hpsc",
            TXANChunk: "txan",
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

    @classmethod
    def _validate_sems(cls, header: ilff.ILFFHeader, content_type: bytes, content: list[ilff.Chunk]) -> Self:
        field_mapping: dict[type[ilff.Chunk], str] = {
            SEMSChunk: "sems",
            XTVSChunk: "xtvs",
            CAFSChunk: "cafs",
            EGDEChunk: "egde",
        }

        instance_values = {}

        for chunk in content:
            field = field_mapping[type(chunk)]
            if field in instance_values:
                raise ValueError(f"Multiple {field} chunks found")
            instance_values[field] = chunk

        for field in ["sems", "xtvs", "cafs", "egde"]:
            if field not in instance_values:
                raise ValueError(f"Missing required {field} chunk")

        return cls(header=header, content_type=content_type, **instance_values)

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, content = super().model_validate_chunks(stream)

        if content_type != b"OCEM":
            raise ValueError("Invalid content type")

        is_sems = content and isinstance(content[0], SEMSChunk)

        if is_sems:
            return cls._validate_sems(header, content_type, content)
        return cls._validate_standard(header, content_type, content)

    # noinspection PyNestedDecorators
    @model_validator(mode="after")
    @classmethod
    def model_validate(cls, instance: Self) -> Self:
        if instance.hsmc:
            if len(instance.hsmc.content) != len(instance.items):
                raise ValueError("hsmc chunk content length does not match items count")

            for i in range(len(instance.hsmc.content)):
                if instance.hsmc.content[i].ecfc_length != len(instance.items[i].ecfc.content):
                    raise ValueError(f"hsmc item {i} does not match ecfc {i} items count")

                if instance.hsmc.content[i].xtvc_length != len(instance.items[i].xtvc.content):
                    raise ValueError(f"hsmc item {i} does not match xtvc {i} items count")

                if instance.hsmc.content[i].tamc_length != len(instance.items[i].tamc.content):
                    raise ValueError(f"hsmc item {i} does not match tamc {i} items count")

                if instance.hsmc.content[i].hpsc_length != len(instance.items[i].hpsc.content):
                    raise ValueError(f"hsmc item {i} does not match hpsc {i} items count")

        return instance
