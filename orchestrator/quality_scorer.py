"""
LLM Response Quality Scorer

Evaluates LLM responses using multiple heuristics to determine quality
without requiring another LLM call. Uses pattern matching, structural
analysis, and learned indicators.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from pathlib import Path

from config.logger import get_logger

logger = get_logger("QualityScorer")


class QualityLevel(Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    ACCEPTABLE = "acceptable"  # 50-69
    POOR = "poor"  # 30-49
    UNACCEPTABLE = "unacceptable"  # 0-29


@dataclass
class QualityScore:
    """Quality assessment result"""
    overall_score: float  # 0-100
    level: QualityLevel
    component_scores: dict[str, float]
    flags: list[str]  # Issues detected
    recommendations: list[str]  # Suggestions for improvement

    def is_acceptable(self) -> bool:
        """Check if quality meets minimum threshold"""
        return self.overall_score >= 50

    def needs_retry(self) -> bool:
        """Determine if response should be retried"""
        return self.overall_score < 30


class ResponseQualityScorer:
    """
    Analyzes LLM responses for quality without calling another LLM.

    Scoring dimensions:
    1. Completeness - Does it address all aspects of the request?
    2. Coherence - Is it well-structured and logical?
    3. Accuracy - Does it contain obvious errors or hallucinations?
    4. Relevance - Is it on-topic?
    5. Format compliance - Does it follow requested format?
    6. Safety - Does it avoid dangerous or inappropriate content?
    """

    def __init__(self):
        # Indicators of poor quality
        self.error_patterns = [
            r"(?i)i (don't|do not|cannot|can't) (know|understand|have access)",
            r"(?i)i (apologize|sorry).{0,50}(unable|cannot|can't)",
            r"(?i)as an ai( language model)?",
            r"(?i)i'm (just|only) (a|an) (ai|language model|bot)",
            r"(?i)(error|exception|traceback|failed)",
            r"(?i)something went wrong",
        ]

        # Indicators of hallucination/uncertainty
        self.uncertainty_patterns = [
            r"(?i)i (think|believe|assume|guess|suspect)",
            r"(?i)(maybe|perhaps|possibly|probably|might be)",
            r"(?i)not (sure|certain|confident)",
            r"(?i)difficult to (say|tell|determine)",
        ]

        # Indicators of good quality
        self.quality_patterns = [
            r"(?i)(here'?s|here is|here are)",
            r"(?i)(specifically|precisely|exactly)",
            r"(?i)(first|second|third|finally)",  # Structured response
            r"(?i)(step \d+|phase \d+)",  # Step-by-step
        ]

        # Safety red flags
        self.safety_patterns = [
            r"(?i)(hack|exploit|vulnerability|bypass security)",
            r"(?i)(illegal|unlawful|prohibited)",
            r"(?i)(password|credential|secret key|private key)",
        ]

    def score_response(
        self,
        response: str,
        request: str,
        expected_format: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> QualityScore:
        """
        Score a response on multiple quality dimensions.

        Args:
            response: The LLM's response
            request: The original user request
            expected_format: Expected format (e.g., "json", "code", "markdown")
            context: Additional context for scoring

        Returns:
            QualityScore with detailed assessment
        """
        component_scores = {}
        flags = []
        recommendations = []

        # 1. Completeness check (0-100)
        completeness = self._score_completeness(response, request)
        component_scores["completeness"] = completeness
        if completeness < 50:
            flags.append("Response appears incomplete")
            recommendations.append("Request more detailed response")

        # 2. Coherence check (0-100)
        coherence = self._score_coherence(response)
        component_scores["coherence"] = coherence
        if coherence < 50:
            flags.append("Response lacks coherent structure")
            recommendations.append("Request better organization")

        # 3. Error detection (0-100, inverted)
        error_score = self._score_errors(response)
        component_scores["error_free"] = error_score
        if error_score < 70:
            flags.append("Response contains error indicators")
            recommendations.append("Verify accuracy or retry")

        # 4. Relevance (0-100)
        relevance = self._score_relevance(response, request)
        component_scores["relevance"] = relevance
        if relevance < 60:
            flags.append("Response may be off-topic")
            recommendations.append("Clarify request or retry")

        # 5. Format compliance (0-100)
        if expected_format:
            format_score = self._score_format(response, expected_format)
            component_scores["format_compliance"] = format_score
            if format_score < 50:
                flags.append(f"Response doesn't match expected format: {expected_format}")
                recommendations.append(f"Explicitly request {expected_format} format")

        # 6. Safety check (0-100, inverted penalty)
        safety_score = self._score_safety(response)
        component_scores["safety"] = safety_score
        if safety_score < 90:
            flags.append("Response may contain unsafe content")
            recommendations.append("Review for security concerns")

        # Calculate weighted overall score
        weights = {
            "completeness": 0.25,
            "coherence": 0.20,
            "error_free": 0.20,
            "relevance": 0.25,
            "format_compliance": 0.05 if expected_format else 0.0,
            "safety": 0.05,
        }

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        overall_score = sum(
            component_scores.get(component, 100) * weight
            for component, weight in weights.items()
        )

        # Determine quality level
        if overall_score >= 90:
            level = QualityLevel.EXCELLENT
        elif overall_score >= 70:
            level = QualityLevel.GOOD
        elif overall_score >= 50:
            level = QualityLevel.ACCEPTABLE
        elif overall_score >= 30:
            level = QualityLevel.POOR
        else:
            level = QualityLevel.UNACCEPTABLE

        return QualityScore(
            overall_score=overall_score,
            level=level,
            component_scores=component_scores,
            flags=flags,
            recommendations=recommendations,
        )

    def _score_completeness(self, response: str, request: str) -> float:
        """
        Assess if response addresses all aspects of request.

        Simple heuristics:
        - Response should be substantial
        - Should reference key terms from request
        - Should have reasonable length relative to request complexity
        """
        score = 50.0  # Baseline

        # Length check
        response_length = len(response.strip())
        if response_length < 20:
            return 10.0  # Way too short
        elif response_length < 50:
            score -= 20
        elif response_length > 100:
            score += 10

        # Extract key terms from request (nouns, important words)
        request_words = set(
            word.lower()
            for word in re.findall(r'\b\w{4,}\b', request)
            if word.lower() not in {'that', 'this', 'with', 'from', 'have', 'will'}
        )

        response_words = set(
            word.lower() for word in re.findall(r'\b\w{4,}\b', response)
        )

        # How many key terms are addressed?
        if request_words:
            coverage = len(request_words & response_words) / len(request_words)
            score += coverage * 30

        # Check for explicit completeness indicators
        if re.search(r"(?i)(in summary|to summarize|in conclusion)", response):
            score += 10

        return min(100, max(0, score))

    def _score_coherence(self, response: str) -> float:
        """
        Assess structural coherence of response.

        Looks for:
        - Proper sentence structure
        - Logical flow indicators
        - Paragraph breaks
        - Lists or numbering
        """
        score = 60.0  # Baseline

        # Sentence structure
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 1:
            return 20.0

        # Average sentence length (too short or too long indicates issues)
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if 5 <= avg_length <= 30:
            score += 10
        elif avg_length < 3 or avg_length > 50:
            score -= 20

        # Paragraph structure
        paragraphs = response.split('\n\n')
        if len(paragraphs) > 1:
            score += 10

        # Lists/numbering (structured thinking)
        if re.search(r'(?:^|\n)\s*[\d\-\*]\s*\.?', response, re.MULTILINE):
            score += 10

        # Transition words
        transition_count = len(re.findall(
            r'\b(?:however|therefore|furthermore|additionally|moreover|consequently)\b',
            response,
            re.IGNORECASE
        ))
        score += min(transition_count * 5, 15)

        # Code blocks (if present, should be properly formatted)
        code_blocks = re.findall(r'```[\s\S]*?```', response)
        if code_blocks:
            score += 5

        return min(100, max(0, score))

    def _score_errors(self, response: str) -> float:
        """
        Detect obvious errors and problems.

        Returns high score if NO errors, low score if errors detected.
        """
        score = 100.0

        # Check for error patterns
        for pattern in self.error_patterns:
            if re.search(pattern, response):
                score -= 20

        # Check for uncertainty/hallucination indicators
        uncertainty_count = 0
        for pattern in self.uncertainty_patterns:
            uncertainty_count += len(re.findall(pattern, response))

        # Some uncertainty is ok, but too much is bad
        if uncertainty_count > 3:
            score -= (uncertainty_count - 3) * 10

        # Check for contradictions (simplified)
        contradictions = [
            (r'\byes\b', r'\bno\b'),
            (r'\btrue\b', r'\bfalse\b'),
            (r'\bcan\b', r'\bcannot\b'),
        ]
        for pos, neg in contradictions:
            if re.search(pos, response, re.IGNORECASE) and re.search(neg, response, re.IGNORECASE):
                score -= 15

        return min(100, max(0, score))

    def _score_relevance(self, response: str, request: str) -> float:
        """
        Check if response is actually relevant to request.

        Uses simple keyword overlap and topic matching.
        """
        score = 50.0

        # Extract important terms
        request_terms = set(re.findall(r'\b\w{4,}\b', request.lower()))
        response_terms = set(re.findall(r'\b\w{4,}\b', response.lower()))

        if not request_terms:
            return score

        # Term overlap
        overlap = request_terms & response_terms
        overlap_ratio = len(overlap) / len(request_terms)
        score += overlap_ratio * 40

        # Check if response addresses the question type
        question_types = {
            'what': r'\b(?:is|are|was|were|definition|means)\b',
            'how': r'\b(?:by|using|through|steps?|process|method)\b',
            'why': r'\b(?:because|since|reason|due to|caused by)\b',
            'when': r'\b(?:date|time|year|day|moment|period)\b',
            'where': r'\b(?:location|place|at|in|on)\b',
        }

        for q_word, expected_pattern in question_types.items():
            if re.search(rf'\b{q_word}\b', request, re.IGNORECASE):
                if re.search(expected_pattern, response, re.IGNORECASE):
                    score += 10
                    break

        return min(100, max(0, score))

    def _score_format(self, response: str, expected_format: str) -> float:
        """
        Check if response matches expected format.
        """
        score = 50.0
        fmt = expected_format.lower()

        if fmt == "json":
            # Try to parse as JSON
            try:
                # Look for JSON in response
                json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', response)
                if json_match:
                    json.loads(json_match.group(0))
                    score = 100.0
                else:
                    score = 20.0
            except json.JSONDecodeError:
                score = 10.0

        elif fmt == "code":
            # Should have code blocks or indentation
            if '```' in response or re.search(r'^[ ]{4,}', response, re.MULTILINE):
                score = 90.0
            elif re.search(r'[{};()]', response):  # Code-like characters
                score = 60.0
            else:
                score = 20.0

        elif fmt == "markdown":
            # Check for markdown syntax
            md_indicators = [
                r'^#{1,6}\s',  # Headers
                r'\*\*.+?\*\*',  # Bold
                r'\*.+?\*',  # Italic
                r'^\s*[\-\*]\s',  # Lists
                r'```',  # Code blocks
                r'\[.+?\]\(.+?\)',  # Links
            ]
            matches = sum(1 for pattern in md_indicators if re.search(pattern, response, re.MULTILINE))
            score = min(100, 50 + matches * 10)

        elif fmt == "list":
            # Should have numbered or bulleted lists
            if re.search(r'(?:^|\n)\s*[\d\-\*•]\s*\.?', response, re.MULTILINE):
                score = 90.0
            else:
                score = 30.0

        return score

    def _score_safety(self, response: str) -> float:
        """
        Check for unsafe content.

        Returns high score if safe, low score if unsafe content detected.
        """
        score = 100.0

        # Check for safety red flags
        for pattern in self.safety_patterns:
            matches = re.findall(pattern, response)
            if matches:
                score -= len(matches) * 20

        return min(100, max(0, score))

    def compare_responses(
        self,
        responses: list[str],
        request: str,
        expected_format: Optional[str] = None,
    ) -> list[tuple[str, QualityScore]]:
        """
        Compare multiple responses and rank by quality.

        Args:
            responses: List of LLM responses to compare
            request: Original request
            expected_format: Expected format

        Returns:
            List of (response, score) tuples sorted by quality (best first)
        """
        scored_responses = [
            (response, self.score_response(response, request, expected_format))
            for response in responses
        ]

        # Sort by overall score (descending)
        scored_responses.sort(key=lambda x: x[1].overall_score, reverse=True)

        return scored_responses

    def get_best_response(
        self,
        responses: list[str],
        request: str,
        expected_format: Optional[str] = None,
        min_quality_threshold: float = 50.0,
    ) -> Optional[tuple[str, QualityScore]]:
        """
        Select best response from multiple options.

        Args:
            responses: List of responses
            request: Original request
            expected_format: Expected format
            min_quality_threshold: Minimum acceptable quality score

        Returns:
            (best_response, score) or None if all below threshold
        """
        if not responses:
            return None

        scored = self.compare_responses(responses, request, expected_format)

        # Return best if it meets threshold
        best_response, best_score = scored[0]
        if best_score.overall_score >= min_quality_threshold:
            return best_response, best_score

        logger.warning(
            f"Best response scored {best_score.overall_score:.1f}, "
            f"below threshold {min_quality_threshold}"
        )
        return None
