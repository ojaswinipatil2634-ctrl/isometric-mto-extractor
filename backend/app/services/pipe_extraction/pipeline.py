"""
Pipe extraction pipeline orchestrator.

Chains: Phase 2 preprocessing -> skeletonize -> Hough line detection ->
polyline merge.

Every stage here is OpenCV/scikit-image/NumPy geometry - per project
rules, no AI/learned model is involved anywhere in this phase. Gemini
is never invoked (project-wide rule: Gemini only reviews, never
extracts).
"""
import logging
import time
from dataclasses import dataclass, field

from app.services.pipe_extraction.hough import RawLineSegment, detect_line_segments
from app.services.pipe_extraction.polyline import PipeSegment, merge_line_segments
from app.services.pipe_extraction.skeletonize import binary_to_skeleton
from app.services.preprocessing.pipeline import PreprocessingPipeline


@dataclass
class PipeExtractionResult:
    segments: list[PipeSegment] = field(default_factory=list)
    raw_segment_count: int = 0
    steps_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    skeleton_image_shape: tuple[int, int] = (0, 0)


logger = logging.getLogger(__name__)

# See the guard in run() below: a real isometric's Hough pass produces
# "dozens to low hundreds" of raw segments per polyline.py's own
# docstring. This is set well above that (and well below the ~4,900
# observed on our bundled grid-paper sample) so it only trips on
# genuinely pathological, noise-dominated input.
_GRID_NOISE_RAW_SEGMENT_THRESHOLD = 800


class PipeExtractionPipeline:
    """Orchestrates preprocessing -> skeletonize -> Hough -> polyline merge."""

    def __init__(self, preprocessing_pipeline: PreprocessingPipeline | None = None) -> None:
        self._preprocessing_pipeline = preprocessing_pipeline or PreprocessingPipeline()

    def run(self, contents: bytes, content_type: str) -> PipeExtractionResult:
        start = time.perf_counter()
        steps: list[str] = []

        preprocessed = self._preprocessing_pipeline.run(contents, content_type)
        steps.append("preprocess")

        # Skeletonize the final binarized output (not the contrast-enhanced
        # preview used by OCR/detection) - skeletonization needs a clean
        # binary foreground/background split, which is exactly what the
        # adaptive threshold stage produces.
        skeleton = binary_to_skeleton(preprocessed.processed_image)
        steps.append("skeletonize")

        raw_segments: list[RawLineSegment] = detect_line_segments(skeleton)
        steps.append("hough_transform")

        # merge_line_segments is a deliberately simple O(n^2)-per-pass
        # algorithm (see its docstring) sized for "dozens to low
        # hundreds" of raw segments from a genuine isometric. A
        # repeating background pattern - e.g. this project's own bundled
        # sample, which is printed on fine graph paper - produces
        # thousands of short, regularly-spaced raw segments instead,
        # which is both (a) not real pipe geometry and (b) enough inputs
        # to make that O(n^2) pass take many seconds for no useful
        # result. Detecting that condition immediately (a real isometric
        # essentially never produces this many raw segments) and
        # skipping the merge is faster *and* more honest than quietly
        # grinding through it and returning a topology built from grid
        # lines.
        warnings: list[str] = []
        if len(raw_segments) > _GRID_NOISE_RAW_SEGMENT_THRESHOLD:
            warnings.append(
                f"Detected {len(raw_segments)} raw line segments, far more than a genuine "
                "isometric produces - consistent with a repeating background pattern (e.g. "
                "graph/grid paper) rather than real pipe routing. Skipping pipe-topology "
                "extraction for this drawing rather than returning results built from "
                "background noise."
            )
            pipe_segments: list[PipeSegment] = []
        else:
            pipe_segments = merge_line_segments(raw_segments)
            steps.append("polyline_extraction")
            if not pipe_segments:
                warnings.append("No straight pipe runs were detected in the processed image.")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Pipe extraction pipeline complete in %.1fms: %d raw segment(s) -> %d pipe run(s)",
            elapsed_ms, len(raw_segments), len(pipe_segments),
        )

        return PipeExtractionResult(
            segments=pipe_segments,
            raw_segment_count=len(raw_segments),
            steps_applied=steps,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
            skeleton_image_shape=(skeleton.shape[0], skeleton.shape[1]),
        )
