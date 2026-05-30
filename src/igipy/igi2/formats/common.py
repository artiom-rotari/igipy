from collections import deque
from itertools import batched
from struct import Struct

from pydantic import BaseModel

from igipy.core.formats import ilff


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
        bone_count = (len(content) - 1) // 13
        bone_child_counts = list(content[:bone_count])
        bone_offsets_data = content[bone_count + 1 :]
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
