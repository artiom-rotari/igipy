"""FBX 7.5 ASCII format model.

Provides a Pydantic-based document model for constructing FBX files
programmatically. Build an FBX instance with geometries, models,
animations, etc., then call model_dump_stream() to serialize.
"""

from __future__ import annotations

from io import BytesIO

from pydantic import BaseModel, Field

from igipy.core.base import FileModel

FBX_TIME_ONE_SECOND = 46_186_158_000
_FORMAT_FLOAT = "{:.15g}"


class IdGenerator:
    """Generate unique FBX object IDs starting from 100_000_001."""

    def __init__(self) -> None:
        self._next = 100_000_000

    def __call__(self) -> int:
        self._next += 1
        return self._next


# ---------------------------------------------------------------------------
# Internal writer
# ---------------------------------------------------------------------------


class _Writer:
    """Builds FBX 7.5 ASCII text."""

    __slots__ = ("_indent", "_lines")

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent = 0

    def line(self, text: str = "") -> None:
        self._lines.append("\t" * self._indent + text if text else "")

    def section(self, name: str) -> None:
        """Begin a section block: ``Name:  {``."""
        self._lines.append("\t" * self._indent + name + ":  {")
        self._indent += 1

    def begin(self, text: str) -> None:
        """Begin an object block: ``<text> {``."""
        self._lines.append("\t" * self._indent + text + " {")
        self._indent += 1

    def end(self) -> None:
        self._indent -= 1
        self._lines.append("\t" * self._indent + "}")

    def array(self, tag: str, count: int, values: str) -> None:
        self.line(f"{tag}: *{count} " + "{")
        self._indent += 1
        self.line(f"a: {values}")
        self._indent -= 1
        self.line("}")

    def result(self) -> str:
        return "\n".join(self._lines) + "\n"


# ---------------------------------------------------------------------------
# FBX object models
# ---------------------------------------------------------------------------


class FBXGeometry(BaseModel):
    id: int
    name: str
    positions: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]
    normals: list[tuple[float, float, float]] | None = None
    uvs: list[tuple[float, float]] | None = None


class FBXMaterial(BaseModel):
    id: int
    name: str


class FBXNodeAttribute(BaseModel):
    id: int
    name: str
    type: str
    type_flags: str


class FBXModel(BaseModel):
    id: int
    name: str
    type: str
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scaling: tuple[float, float, float] = (1.0, 1.0, 1.0)
    default_attribute_index: int | None = None
    shading: bool = False
    culling: bool = False


class FBXCluster(BaseModel):
    id: int
    name: str
    indexes: list[int] = Field(default_factory=list)
    weights: list[float] = Field(default_factory=list)
    transform: list[float]
    transform_link: list[float]


class FBXSkin(BaseModel):
    id: int
    name: str
    clusters: list[FBXCluster] = Field(default_factory=list)


class FBXPoseNode(BaseModel):
    node_id: int
    matrix: list[float]


class FBXPose(BaseModel):
    id: int
    name: str
    nodes: list[FBXPoseNode] = Field(default_factory=list)


class FBXAnimationStack(BaseModel):
    id: int
    name: str
    local_stop: int = FBX_TIME_ONE_SECOND
    reference_stop: int = FBX_TIME_ONE_SECOND


class FBXAnimationLayer(BaseModel):
    id: int
    name: str = "BaseLayer"


class FBXAnimationCurveNode(BaseModel):
    id: int
    channel: str


class FBXAnimationCurve(BaseModel):
    id: int
    key_time: list[int]
    key_value_float: list[float]


class FBXConnection(BaseModel):
    source: int
    destination: int
    property: str | None = None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_floats(values: list[float]) -> str:
    return ",".join(_FORMAT_FLOAT.format(v) for v in values)


def _format_ints(values: list[int]) -> str:
    return ",".join(str(v) for v in values)


# ---------------------------------------------------------------------------
# Root FBX document
# ---------------------------------------------------------------------------


class FBX(FileModel):
    name: str
    time_stop: int = 0
    active_anim_stack_name: str = ""

    geometries: list[FBXGeometry] = Field(default_factory=list)
    materials: list[FBXMaterial] = Field(default_factory=list)
    node_attributes: list[FBXNodeAttribute] = Field(default_factory=list)
    models: list[FBXModel] = Field(default_factory=list)
    skins: list[FBXSkin] = Field(default_factory=list)
    poses: list[FBXPose] = Field(default_factory=list)
    animation_stacks: list[FBXAnimationStack] = Field(default_factory=list)
    animation_layers: list[FBXAnimationLayer] = Field(default_factory=list)
    animation_curve_nodes: list[FBXAnimationCurveNode] = Field(default_factory=list)
    animation_curves: list[FBXAnimationCurve] = Field(default_factory=list)
    connections: list[FBXConnection] = Field(default_factory=list)

    take_name: str = ""
    take_time_stop: int = 0

    def model_dump_stream(self) -> tuple[BytesIO, str]:  # noqa: C901
        w = _Writer()
        w.line("; FBX 7.5.0 project file")
        w.line("; Generated by igipy")
        w.line("FBXVersion: 7500")
        w.line()

        self._write_header(w)
        self._write_global_settings(w)
        self._write_documents(w)
        self._write_definitions(w)

        w.section("Objects")
        for geo in self.geometries:
            self._write_geometry(w, geo)
        for mat in self.materials:
            self._write_material(w, mat)
        for attribute in self.node_attributes:
            self._write_node_attribute(w, attribute)
        for model in self.models:
            self._write_model(w, model)
        for skin in self.skins:
            self._write_skin(w, skin)
        for pose in self.poses:
            self._write_pose(w, pose)
        for stack in self.animation_stacks:
            self._write_animation_stack(w, stack)
        for layer in self.animation_layers:
            self._write_animation_layer(w, layer)
        for curve_node in self.animation_curve_nodes:
            self._write_animation_curve_node(w, curve_node)
        for curve in self.animation_curves:
            self._write_animation_curve(w, curve)
        w.end()
        w.line()

        self._write_connections(w)
        self._write_takes(w)

        stream = BytesIO()
        stream.write(w.result().encode("ascii"))
        stream.seek(0)
        return stream, ".fbx"

    # --- Private serialization methods ---

    @staticmethod
    def _write_header(w: _Writer) -> None:
        w.section("FBXHeaderExtension")
        w.line("FBXHeaderVersion: 1003")
        w.line("FBXVersion: 7500")
        w.section("CreationTimeStamp")
        w.line("Version: 1000")
        w.line("Year: 2026")
        w.line("Month: 1")
        w.line("Day: 1")
        w.line("Hour: 0")
        w.line("Minute: 0")
        w.line("Second: 0")
        w.line("Millisecond: 0")
        w.end()
        w.line('Creator: "igipy FBX exporter"')
        w.end()
        w.line()

    def _write_global_settings(self, w: _Writer) -> None:
        w.section("GlobalSettings")
        w.line("Version: 1000")
        w.section("Properties70")
        w.line('P: "UpAxis", "int", "Integer", "",1')
        w.line('P: "UpAxisSign", "int", "Integer", "",1')
        w.line('P: "FrontAxis", "int", "Integer", "",2')
        w.line('P: "FrontAxisSign", "int", "Integer", "",1')
        w.line('P: "CoordAxis", "int", "Integer", "",0')
        w.line('P: "CoordAxisSign", "int", "Integer", "",1')
        w.line('P: "OriginalUpAxis", "int", "Integer", "",-1')
        w.line('P: "OriginalUpAxisSign", "int", "Integer", "",1')
        w.line('P: "UnitScaleFactor", "double", "Number", "",1')
        w.line('P: "OriginalUnitScaleFactor", "double", "Number", "",1')
        w.line('P: "TimeSpanStart", "KTime", "Time", "",0')
        w.line(f'P: "TimeSpanStop", "KTime", "Time", "",{self.time_stop}')
        w.end()
        w.end()
        w.line()

    def _write_documents(self, w: _Writer) -> None:
        w.section("Documents")
        w.line("Count: 1")
        w.begin('Document: 1000000000, "", "Scene"')
        w.section("Properties70")
        w.line('P: "SourceObject", "object", "", ""')
        w.line(f'P: "ActiveAnimStackName", "KString", "", "", "{self.active_anim_stack_name}"')
        w.end()
        w.line("RootNode: 0")
        w.end()
        w.end()
        w.line()

        w.section("References")
        w.end()
        w.line()

    def _write_definitions(self, w: _Writer) -> None:  # noqa: PLR0915
        geometry_count = len(self.geometries)
        material_count = len(self.materials)
        node_attribute_count = len(self.node_attributes)
        model_count = len(self.models)
        deformer_count = sum(1 + len(s.clusters) for s in self.skins)
        pose_count = len(self.poses)
        animation_stack_count = len(self.animation_stacks)
        animation_layer_count = len(self.animation_layers)
        curve_node_count = len(self.animation_curve_nodes)
        curve_count = len(self.animation_curves)

        total = 1 + geometry_count + material_count + node_attribute_count + model_count
        total += deformer_count + pose_count
        total += animation_stack_count + animation_layer_count + curve_node_count + curve_count

        w.section("Definitions")
        w.line("Version: 100")
        w.line(f"Count: {total}")

        w.begin('ObjectType: "GlobalSettings"')
        w.line("Count: 1")
        w.end()

        if geometry_count:
            w.begin('ObjectType: "Geometry"')
            w.line(f"Count: {geometry_count}")
            w.end()

        if node_attribute_count:
            w.begin('ObjectType: "NodeAttribute"')
            w.line(f"Count: {node_attribute_count}")
            w.begin('PropertyTemplate: "FbxSkeleton"')
            w.section("Properties70")
            w.line('P: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8')
            w.line('P: "Size", "double", "Number", "",100')
            w.line('P: "LimbLength", "double", "Number", "H",1')
            w.end()
            w.end()
            w.end()

        if model_count:
            w.begin('ObjectType: "Model"')
            w.line(f"Count: {model_count}")
            w.begin('PropertyTemplate: "FbxNode"')
            w.section("Properties70")
            w.line('P: "Lcl Translation", "Lcl Translation", "", "A",0,0,0')
            w.line('P: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0')
            w.line('P: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1')
            w.line('P: "RotationActive", "bool", "", "",1')
            w.end()
            w.end()
            w.end()

        if material_count:
            w.begin('ObjectType: "Material"')
            w.line(f"Count: {material_count}")
            w.end()

        if deformer_count:
            w.begin('ObjectType: "Deformer"')
            w.line(f"Count: {deformer_count}")
            w.end()

        if pose_count:
            w.begin('ObjectType: "Pose"')
            w.line(f"Count: {pose_count}")
            w.end()

        if animation_stack_count:
            w.begin('ObjectType: "AnimationStack"')
            w.line(f"Count: {animation_stack_count}")
            w.begin('PropertyTemplate: "FbxAnimStack"')
            w.section("Properties70")
            w.line('P: "LocalStart", "KTime", "Time", "",0')
            w.line(f'P: "LocalStop", "KTime", "Time", "",{self.time_stop}')
            w.line('P: "ReferenceStart", "KTime", "Time", "",0')
            w.line(f'P: "ReferenceStop", "KTime", "Time", "",{self.time_stop}')
            w.end()
            w.end()
            w.end()

            w.begin('ObjectType: "AnimationLayer"')
            w.line(f"Count: {animation_layer_count}")
            w.begin('PropertyTemplate: "FbxAnimLayer"')
            w.section("Properties70")
            w.line('P: "Weight", "Number", "", "A",100')
            w.end()
            w.end()
            w.end()

            w.begin('ObjectType: "AnimationCurveNode"')
            w.line(f"Count: {curve_node_count}")
            w.begin('PropertyTemplate: "FbxAnimCurveNode"')
            w.section("Properties70")
            w.line('P: "d", "Compound", "", ""')
            w.end()
            w.end()
            w.end()

            w.begin('ObjectType: "AnimationCurve"')
            w.line(f"Count: {curve_count}")
            w.end()

        w.end()
        w.line()

    @staticmethod
    def _write_geometry(w: _Writer, geo: FBXGeometry) -> None:  # noqa: C901, PLR0915
        w.begin(f'Geometry: {geo.id}, "Geometry::{geo.name}", "Mesh"')

        if not geo.positions or not geo.faces:
            w.array("Vertices", 0, "")
            w.array("PolygonVertexIndex", 0, "")
            w.end()
            w.line()
            return

        vert_data: list[float] = []
        for p in geo.positions:
            vert_data.extend(p)
        w.array("Vertices", len(vert_data), _format_floats(vert_data))

        poly_data: list[int] = []
        for a, b, c in geo.faces:
            poly_data.extend([a, b, -(c + 1)])
        w.array("PolygonVertexIndex", len(poly_data), _format_ints(poly_data))

        if geo.normals:
            w.begin("LayerElementNormal: 0")
            w.line("Version: 102")
            w.line('Name: ""')
            w.line('MappingInformationType: "ByPolygonVertex"')
            w.line('ReferenceInformationType: "Direct"')
            norm_data: list[float] = []
            for a, b, c in geo.faces:
                for idx in (a, b, c):
                    norm_data.extend(geo.normals[idx])
            w.array("Normals", len(norm_data), _format_floats(norm_data))
            w.end()

        if geo.uvs:
            w.begin("LayerElementUV: 0")
            w.line("Version: 101")
            w.line('Name: "map1"')
            w.line('MappingInformationType: "ByPolygonVertex"')
            w.line('ReferenceInformationType: "IndexToDirect"')
            uv_data: list[float] = []
            for uv in geo.uvs:
                uv_data.extend(uv)
            w.array("UV", len(uv_data), _format_floats(uv_data))
            uv_index: list[int] = []
            for a, b, c in geo.faces:
                uv_index.extend([a, b, c])
            w.array("UVIndex", len(uv_index), _format_ints(uv_index))
            w.end()

        w.begin("LayerElementMaterial: 0")
        w.line("Version: 101")
        w.line('Name: ""')
        w.line('MappingInformationType: "AllSame"')
        w.line('ReferenceInformationType: "IndexToDirect"')
        w.array("Materials", 1, "0")
        w.end()

        w.begin("Layer: 0")
        w.line("Version: 100")
        if geo.normals:
            w.begin("LayerElement:")
            w.line('Type: "LayerElementNormal"')
            w.line("TypedIndex: 0")
            w.end()
        w.begin("LayerElement:")
        w.line('Type: "LayerElementMaterial"')
        w.line("TypedIndex: 0")
        w.end()
        if geo.uvs:
            w.begin("LayerElement:")
            w.line('Type: "LayerElementUV"')
            w.line("TypedIndex: 0")
            w.end()
        w.end()

        w.end()
        w.line()

    @staticmethod
    def _write_material(w: _Writer, mat: FBXMaterial) -> None:
        w.begin(f'Material: {mat.id}, "Material::{mat.name}", ""')
        w.line("Version: 102")
        w.line('ShadingModel: "phong"')
        w.line("MultiLayer: 0")
        w.section("Properties70")
        w.line('P: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8')
        w.line('P: "AmbientColor", "Color", "", "A",0,0,0')
        w.line('P: "SpecularColor", "Color", "", "A",0.5,0.5,0.5')
        w.line('P: "ShininessExponent", "Number", "", "A",20')
        w.end()
        w.end()
        w.line()

    @staticmethod
    def _write_node_attribute(w: _Writer, attribute: FBXNodeAttribute) -> None:
        w.begin(f'NodeAttribute: {attribute.id}, "NodeAttribute::{attribute.name}", "{attribute.type}"')
        w.line(f'TypeFlags: "{attribute.type_flags}"')
        w.end()
        w.line()

    @staticmethod
    def _write_model(w: _Writer, model: FBXModel) -> None:
        w.begin(f'Model: {model.id}, "Model::{model.name}", "{model.type}"')
        w.line("Version: 232")
        w.section("Properties70")
        if model.default_attribute_index is not None:
            w.line(f'P: "DefaultAttributeIndex", "int", "Integer", "",{model.default_attribute_index}')
        translation_x, translation_y, translation_z = model.translation
        w.line(f'P: "Lcl Translation", "Lcl Translation", "", "A",{translation_x},{translation_y},{translation_z}')
        rotation_x, rotation_y, rotation_z = model.rotation
        w.line(f'P: "Lcl Rotation", "Lcl Rotation", "", "A",{rotation_x},{rotation_y},{rotation_z}')
        scaling_x, scaling_y, scaling_z = model.scaling
        w.line(f'P: "Lcl Scaling", "Lcl Scaling", "", "A",{scaling_x},{scaling_y},{scaling_z}')
        w.end()
        if model.shading:
            w.line("Shading: Y")
        if model.culling:
            w.line('Culling: "CullingOff"')
        w.end()
        w.line()

    @staticmethod
    def _write_skin(w: _Writer, skin: FBXSkin) -> None:
        w.begin(f'Deformer: {skin.id}, "Deformer::Skin {skin.name}", "Skin"')
        w.line("Version: 101")
        w.end()
        w.line()

        for cluster in skin.clusters:
            w.begin(f'Deformer: {cluster.id}, "SubDeformer::Cluster {cluster.name}", "Cluster"')
            w.line("Version: 100")
            w.line('UserData: "", ""')
            if cluster.indexes:
                w.array("Indexes", len(cluster.indexes), _format_ints(cluster.indexes))
                w.array("Weights", len(cluster.weights), _format_floats(cluster.weights))
            w.array("Transform", 16, _format_floats(cluster.transform))
            w.array("TransformLink", 16, _format_floats(cluster.transform_link))
            w.end()
            w.line()

    @staticmethod
    def _write_pose(w: _Writer, pose: FBXPose) -> None:
        w.begin(f'Pose: {pose.id}, "Pose::{pose.name}", "BindPose"')
        w.line('Type: "BindPose"')
        w.line("Version: 100")
        w.line(f"NbPoseNodes: {len(pose.nodes)}")
        for node in pose.nodes:
            w.begin("PoseNode:")
            w.line(f"Node: {node.node_id}")
            w.array("Matrix", 16, _format_floats(node.matrix))
            w.end()
        w.end()
        w.line()

    @staticmethod
    def _write_animation_stack(w: _Writer, stack: FBXAnimationStack) -> None:
        w.begin(f'AnimationStack: {stack.id}, "AnimStack::{stack.name}", ""')
        w.section("Properties70")
        w.line(f'P: "LocalStop", "KTime", "Time", "",{stack.local_stop}')
        w.line(f'P: "ReferenceStop", "KTime", "Time", "",{stack.reference_stop}')
        w.end()
        w.end()
        w.line()

    @staticmethod
    def _write_animation_layer(w: _Writer, layer: FBXAnimationLayer) -> None:
        w.begin(f'AnimationLayer: {layer.id}, "AnimLayer::{layer.name}", ""')
        w.end()
        w.line()

    @staticmethod
    def _write_animation_curve_node(w: _Writer, curve_node: FBXAnimationCurveNode) -> None:
        label = "T" if curve_node.channel == "T" else "R"
        w.begin(f'AnimationCurveNode: {curve_node.id}, "AnimCurveNode::{label}", ""')
        w.section("Properties70")
        w.line('P: "d|X", "Number", "", "A",0')
        w.line('P: "d|Y", "Number", "", "A",0')
        w.line('P: "d|Z", "Number", "", "A",0')
        w.end()
        w.end()
        w.line()

    @staticmethod
    def _write_animation_curve(w: _Writer, curve: FBXAnimationCurve) -> None:
        key_count = len(curve.key_value_float)
        w.begin(f'AnimationCurve: {curve.id}, "AnimCurve::", ""')
        w.line("Default: 0")
        w.line("KeyVer: 4009")
        w.array("KeyTime", key_count, ",".join(str(t) for t in curve.key_time))
        w.array("KeyValueFloat", key_count, ",".join(f"{v:.6f}" for v in curve.key_value_float))
        w.array("KeyAttrFlags", 1, "8456")
        w.array("KeyAttrDataFloat", 4, "0,0,0,0")
        w.array("KeyAttrRefCount", 1, str(key_count))
        w.end()
        w.line()

    def _write_connections(self, w: _Writer) -> None:
        w.section("Connections")
        for conn in self.connections:
            if conn.property is not None:
                w.line(f'C: "OP",{conn.source},{conn.destination}, "{conn.property}"')
            else:
                w.line(f'C: "OO",{conn.source},{conn.destination}')
        w.end()
        w.line()

    def _write_takes(self, w: _Writer) -> None:
        w.section("Takes")
        if self.take_name:
            w.line(f'Current: "{self.take_name}"')
            w.begin(f'Take: "{self.take_name}"')
            w.line(f'FileName: "{self.take_name}.tak"')
            w.line(f"LocalTime: 0,{self.take_time_stop}")
            w.line(f"ReferenceTime: 0,{self.take_time_stop}")
            w.end()
        else:
            w.line('Current: ""')
        w.end()
        w.line()
