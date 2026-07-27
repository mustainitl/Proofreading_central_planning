from dataclasses import dataclass
from typing import Literal


TargetDocument = Literal["purchase_order", "booking_sheet"]
NormalizerName = Literal[
    "date",
    "fibre_content",
    "identifier",
    "numeric",
    "sales_order",
    "silhouette",
    "text",
]


@dataclass(frozen=True)
class ComparisonRule:
    field: str
    work_order_key: str
    target: TargetDocument
    target_key: str
    normalizer: NormalizerName


COMPARISON_RULES = (
    ComparisonRule(
        field="PO Number",
        work_order_key="vs_po_number",
        target="purchase_order",
        target_key="po_number",
        normalizer="identifier",
    ),
    ComparisonRule(
        field="Factory ID",
        work_order_key="factory_id",
        target="purchase_order",
        target_key="factory_id",
        normalizer="identifier",
    ),
    ComparisonRule(
        field="Date of MFR",
        work_order_key="date_of_mfr",
        target="purchase_order",
        target_key="date_of_mfr",
        normalizer="date",
    ),
    ComparisonRule(
        field="Item Code",
        work_order_key="item_code",
        target="purchase_order",
        target_key="item_code",
        normalizer="identifier",
    ),
    ComparisonRule(
        field="SO Number",
        work_order_key="so_number",
        target="purchase_order",
        target_key="so_number",
        normalizer="sales_order",
    ),
    ComparisonRule(
        field="Line Item",
        work_order_key="line_item",
        target="purchase_order",
        target_key="line_item",
        normalizer="identifier",
    ),
    ComparisonRule(
        field="Quantity",
        work_order_key="quantity",
        target="purchase_order",
        target_key="quantity",
        normalizer="numeric",
    ),
    ComparisonRule(
        field="Silhouette",
        work_order_key="silhouette",
        target="booking_sheet",
        target_key="silhouette",
        normalizer="silhouette",
    ),
    ComparisonRule(
        field="Garment Components",
        work_order_key="garment_components",
        target="booking_sheet",
        target_key="garment_components",
        normalizer="fibre_content",
    ),
)
