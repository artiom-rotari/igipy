import logging
from collections import deque
from itertools import batched
from struct import Struct

from pydantic import BaseModel

from igipy.core.formats import ilff

logger = logging.getLogger(__name__)

# A REIH chunk stores one uint8 child-count per bone followed by one float3 offset per
# bone, so each bone costs 1 + 12 = 13 bytes. Most models append a single trailing
# separator/terminator byte after the child-count array (total = 13 * bone_count + 1),
# but a rare variant omits it (total = 13 * bone_count exactly). Both encode the same
# bone_count, so floor division recovers it for either layout.
REIH_BYTES_PER_BONE = 13
REIH_OFFSET_BYTES_PER_BONE = 12


class REIHChunk(ilff.Chunk):
    class Bone(BaseModel):
        child_count: int
        offset_x: float
        offset_y: float
        offset_z: float

    content: list[Bone]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"REIH")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        # bone_count = len // 13 handles both the common "13 * bone_count + 1" layout and the
        # rare "13 * bone_count" layout that omits the trailing separator byte (e.g.
        # missions/.../pat_2.mef). The previous "(len - 1) // 13" hard-coded the separator and
        # computed one bone too few for the no-separator variant, misaligning the float region
        # and raising "unpack requires a buffer of N bytes". Only 0 (no separator) and 1 (with
        # separator) are valid remainders; anything else means the chunk is not a REIH layout.
        remainder = len(content) % REIH_BYTES_PER_BONE
        if remainder not in {0, 1}:
            raise ValueError(
                f"Unexpected REIH content length {len(content)} (remainder {remainder} mod {REIH_BYTES_PER_BONE})"
            )
        bone_count = len(content) // REIH_BYTES_PER_BONE
        if remainder == 0 and bone_count:
            logger.debug("[FIX] REIH no-separator variant: length=%d bones=%d", len(content), bone_count)
        bone_child_counts = list(content[:bone_count])
        # The float offsets are always the trailing bone_count * 3 floats, regardless of whether
        # a separator byte precedes them. Slicing from the tail works for both layouts.
        bone_offsets_data = content[len(content) - bone_count * REIH_OFFSET_BYTES_PER_BONE :]
        bone_offsets = list(batched(Struct(f"<{bone_count * 3}f").unpack(bone_offsets_data), 3, strict=True))
        bones = [
            cls.Bone(child_count=child_count, offset_x=offset_x, offset_y=offset_y, offset_z=offset_z)
            for child_count, (offset_x, offset_y, offset_z) in zip(bone_child_counts, bone_offsets, strict=True)
        ]
        return {"content": bones}

    @property
    def bones_child_counts(self) -> list[int]:
        return [bone.child_count for bone in self.content]

    @property
    def bones_offsets(self) -> list[tuple[float, float, float]]:
        return [(bone.offset_x, bone.offset_y, bone.offset_z) for bone in self.content]

    @property
    def bones_parents(self) -> list[int]:
        bone_count = len(self.bones_child_counts)
        parents = [-1] * bone_count
        if bone_count <= 1:
            return parents
        queue: deque[list[int]] = deque()
        queue.append([0, self.bones_child_counts[0]])
        bone_idx = 1
        while queue and bone_idx < bone_count:
            front = queue[0]
            if front[1] == 0:
                queue.popleft()
                continue
            parents[bone_idx] = front[0]
            front[1] -= 1
            if self.bones_child_counts[bone_idx] > 0:
                queue.append([bone_idx, self.bones_child_counts[bone_idx]])
            bone_idx += 1
        return parents
