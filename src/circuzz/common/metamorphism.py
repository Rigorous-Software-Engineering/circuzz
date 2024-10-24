
from dataclasses import dataclass
from enum import StrEnum

from ..ir.nodes import Circuit
from ..ir.rewrite.rewriter import PointOfInterest

class MetamorphicKind(StrEnum):
    EQUAL = "equal"
    WEAKER = "weaker"

@dataclass
class MetamorphicCircuitPair():
    kind: MetamorphicKind
    fst: Circuit
    snd: Circuit
    transformations: list[PointOfInterest]

@dataclass
class MetamorphicCircuitBundle():
    kinds: list[MetamorphicKind]
    origin: Circuit
    bundle: list[Circuit]
    transformations: list[list[PointOfInterest]]
