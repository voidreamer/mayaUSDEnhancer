from pxr import Usd, UsdGeom, Sdf
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum


class PrimPurpose(Enum):
    DEFAULT = "default"
    RENDER = "render"
    PROXY = "proxy"
    GUIDE = "guide"


@dataclass
class PrimInfo:
    name: str
    type_name: str
    kind: str
    purpose: str
    path: Sdf.Path


def get_prim_kind(prim: Usd.Prim) -> str:
    return Usd.ModelAPI(prim).GetKind() or ""


def get_prim_purpose(prim: Usd.Prim) -> str:
    return UsdGeom.Imageable(prim).GetPurposeAttr().Get() if UsdGeom.Imageable(prim) else ""


def get_prim_info(prim: Usd.Prim) -> PrimInfo:
    return PrimInfo(
        name=prim.GetName(),
        type_name=prim.GetTypeName(),
        kind=get_prim_kind(prim),
        purpose=get_prim_purpose(prim),
        path=prim.GetPath()
    )


def get_child_prims(prim: Usd.Prim) -> List[Usd.Prim]:
    return list(prim.GetFilteredChildren(predicate=Usd.PrimIsActive & ~Usd.PrimIsAbstract))


def set_prim_kind(prim: Usd.Prim, kind: str) -> None:
    Usd.ModelAPI(prim).SetKind(kind)


def set_prim_purpose(prim: Usd.Prim, purpose: PrimPurpose) -> None:
    UsdGeom.Imageable(prim).CreatePurposeAttr().Set(purpose.value)


def get_stage_as_text(stage: Usd.Stage) -> str:
    return stage.GetRootLayer().ExportToString()


def update_stage_from_text(stage: Usd.Stage, text: str) -> None:
    stage.GetRootLayer().ImportFromString(text)
