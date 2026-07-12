from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pdfplumber


def _mm(points: float) -> float:
    return round(points * 25.4 / 72, 1)


def _bbox_dict(bbox: tuple[float, float, float, float]) -> dict[str, float]:
    x0, top, x1, bottom = bbox
    return {
        "x0": round(x0, 2),
        "top": round(top, 2),
        "x1": round(x1, 2),
        "bottom": round(bottom, 2),
        "width_mm": _mm(x1 - x0),
        "height_mm": _mm(bottom - top),
    }


def _dedupe_boxes(
    boxes: list[dict[str, float]],
    pos_tolerance: float = 1.0,
) -> list[dict[str, float]]:
    unique: list[dict[str, float]] = []
    for box in boxes:
        if any(
            abs(box["x0"] - other["x0"]) <= pos_tolerance
            and abs(box["y0"] - other["y0"]) <= pos_tolerance
            for other in unique
        ):
            continue
        unique.append(box)
    return unique


def get_layout_boxes(
    page: pdfplumber.page.Page,
    min_area: float = 5000,
    size_tolerance: float = 5,
) -> list[dict[str, float]]:
    """Find the repeated layout rectangles on a page."""
    candidates: list[dict[str, float]] = []

    for rect in page.rects:
        width = rect["x1"] - rect["x0"]
        height = rect["bottom"] - rect["top"]
        if width * height <= min_area:
            continue

        candidates.append(
            {
                "x0": rect["x0"],
                "y0": rect["top"],
                "x1": rect["x1"],
                "y1": rect["bottom"],
                "w": width,
                "h": height,
            }
        )

    unique = _dedupe_boxes(candidates)
    if not unique:
        return []

    size_counts = Counter((round(box["w"]), round(box["h"])) for box in unique)
    dominant_size, _ = max(
        size_counts.items(),
        key=lambda item: (item[1], item[0][0] * item[0][1]),
    )

    layout_boxes = [
        box
        for box in unique
        if abs(box["w"] - dominant_size[0]) <= size_tolerance
        and abs(box["h"] - dominant_size[1]) <= size_tolerance
    ]

    return sorted(layout_boxes, key=lambda box: (round(box["y0"] / 10) * 10, box["x0"]))


def _line_like_objects(page: pdfplumber.page.Page) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []

    for source in (page.lines, page.curves):
        for obj in source:
            if all(key in obj for key in ("x0", "x1", "top", "bottom")):
                objects.append(obj)

    for rect in page.rects:
        width = rect["x1"] - rect["x0"]
        height = rect["bottom"] - rect["top"]
        if min(width, height) <= 2 and max(width, height) >= 8:
            objects.append(rect)

    return objects


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0, min(a1, b1) - max(a0, b0))


def _cluster_positions(values: list[float], tolerance: float = 2) -> list[float]:
    clusters: list[list[float]] = []

    for value in sorted(values):
        if not clusters or abs(value - clusters[-1][-1]) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)

    return [sum(cluster) / len(cluster) for cluster in clusters]


def find_section_dividers(
    page: pdfplumber.page.Page,
    box: dict[str, float],
    min_span_ratio: float = 0.70,
    boundary_margin: float = 2,
) -> tuple[str, list[float]]:
    """Return divider axis and divider positions inside a layout box."""
    axis = "x" if box["w"] >= box["h"] else "y"
    positions: list[float] = []

    for obj in _line_like_objects(page):
        x0 = obj["x0"]
        x1 = obj["x1"]
        top = obj["top"]
        bottom = obj["bottom"]
        width = abs(x1 - x0)
        height = abs(bottom - top)

        if axis == "x":
            max_line_width = max(1.5, box["w"] * 0.02)
            if width > max_line_width:
                continue
            if _overlap(top, bottom, box["y0"], box["y1"]) < box["h"] * min_span_ratio:
                continue

            x = (x0 + x1) / 2
            if box["x0"] + boundary_margin < x < box["x1"] - boundary_margin:
                positions.append(x)
        else:
            max_line_height = max(1.5, box["h"] * 0.02)
            if height > max_line_height:
                continue
            if _overlap(x0, x1, box["x0"], box["x1"]) < box["w"] * min_span_ratio:
                continue

            y = (top + bottom) / 2
            if box["y0"] + boundary_margin < y < box["y1"] - boundary_margin:
                positions.append(y)

    return axis, _cluster_positions(positions)


def _part_names(count: int) -> list[str]:
    return [f"part_{index}" for index in range(1, count + 1)]


def _section_bboxes(
    box: dict[str, float],
    axis: str,
    dividers: list[float],
    padding: float = 1,
) -> list[tuple[float, float, float, float]]:
    if axis == "x":
        bounds = [box["x0"], *dividers, box["x1"]]
        return [
            (bounds[index] + padding, box["y0"] + padding, bounds[index + 1] - padding, box["y1"] - padding)
            for index in range(len(bounds) - 1)
            if bounds[index + 1] - bounds[index] > padding * 2
        ]

    bounds = [box["y0"], *dividers, box["y1"]]
    return [
        (box["x0"] + padding, bounds[index] + padding, box["x1"] - padding, bounds[index + 1] - padding)
        for index in range(len(bounds) - 1)
        if bounds[index + 1] - bounds[index] > padding * 2
    ]


def _extract_lines(
    page: pdfplumber.page.Page,
    bbox: tuple[float, float, float, float],
) -> list[str]:
    cropped = page.crop(bbox)
    words = cropped.extract_words(x_tolerance=1.5, y_tolerance=3, use_text_flow=False)
    if not words:
        return []

    rows: defaultdict[float, list[dict[str, Any]]] = defaultdict(list)
    for word in words:
        rows[round(word["top"] / 3) * 3].append(word)

    lines: list[str] = []
    for row in sorted(rows):
        row_words = sorted(rows[row], key=lambda word: word["x0"])
        line = " ".join(word["text"] for word in row_words).strip()
        if line:
            lines.append(line)

    return lines


def split_layout_box(
    page: pdfplumber.page.Page,
    box: dict[str, float],
) -> dict[str, Any]:
    axis, dividers = find_section_dividers(page, box)
    section_direction = "left_to_right" if axis == "x" else "top_to_bottom"
    bboxes = _section_bboxes(box, axis, dividers)
    names = _part_names(len(bboxes))

    parts: dict[str, dict[str, Any]] = {}
    for index, (name, bbox) in enumerate(zip(names, bboxes), start=1):
        lines = _extract_lines(page, bbox)
        parts[name] = {
            "part": index,
            "bbox": _bbox_dict(bbox),
            "text": "\n".join(lines),
            "lines": lines,
        }

    return {
        "section_direction": section_direction,
        "divider_positions": [round(position, 2) for position in dividers],
        "part_count": len(parts),
        "parts": parts,
    }


def extract_layout_sections_from_pdf(
    pdf_path: str | Path,
    min_area: float = 5000,
    size_tolerance: float = 5,
) -> dict[str, Any]:
    pdf_path = Path(pdf_path)
    layouts: list[dict[str, Any]] = []
    layout_number = 1

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            boxes = get_layout_boxes(page, min_area=min_area, size_tolerance=size_tolerance)
            for layout_on_page, box in enumerate(boxes, start=1):
                split_data = split_layout_box(page, box)
                layouts.append(
                    {
                        "page": page_number,
                        "layout": layout_number,
                        "layout_on_page": layout_on_page,
                        "bbox": _bbox_dict((box["x0"], box["y0"], box["x1"], box["y1"])),
                        **split_data,
                    }
                )
                layout_number += 1

    return {
        "pdf": pdf_path.name,
        "layout_count": len(layouts),
        "layouts": layouts,
    }


def save_layout_sections_json(data: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
