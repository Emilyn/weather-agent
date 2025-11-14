"""
Reflection Engine - Implements self-evaluation and iterative refinement pattern.
The agent generates outputs, then critically evaluates them, and revises if needed.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import statistics


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class ReflectionResult:
    """Result of a reflection evaluation."""
    quality: QualityLevel
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]
    passed: bool  # Whether quality threshold is met


class ReflectionEngine:
    """
    Reflection engine that evaluates outputs and suggests improvements.
    Implements the reflection pattern: generate -> evaluate -> refine -> repeat.
    """
    
    def __init__(self, quality_threshold: float = 0.7):
        """
        Initialize reflection engine.
        
        Args:
            quality_threshold: Minimum quality score (0.0-1.0) to pass evaluation
        """
        self.quality_threshold = quality_threshold
        self.max_iterations = 3  # Maximum refinement iterations
    
    def reflect_on_weather_data(self, weather_data: Dict) -> ReflectionResult:
        """
        Reflect on weather data quality and consistency.
        
        Args:
            weather_data: Weather data dictionary
            
        Returns:
            ReflectionResult with quality assessment
        """
        issues = []
        suggestions = []
        scores = []
        
        hourly_data = weather_data.get('hourly_data', [])
        sources_used = weather_data.get('sources_used', [])
        reliability_score = weather_data.get('reliability_score', 0.0)
        
        # Check data completeness
        if len(hourly_data) < 5:
            issues.append(f"Only {len(hourly_data)} hours of data available (recommended: 10)")
            suggestions.append("Consider fetching from additional sources")
            scores.append(0.5)
        else:
            scores.append(1.0)
        
        # Check source diversity
        if len(sources_used) < 2:
            issues.append(f"Only {len(sources_used)} source(s) used (recommended: 3+)")
            suggestions.append("Add more weather API keys for better reliability")
            scores.append(0.4)
        elif len(sources_used) < 3:
            issues.append(f"Only {len(sources_used)} sources used (recommended: 3+)")
            suggestions.append("Consider adding more weather sources")
            scores.append(0.7)
        else:
            scores.append(1.0)
        
        # Check reliability score
        if reliability_score < 0.5:
            issues.append(f"Low reliability score: {reliability_score:.2f}")
            suggestions.append("Data may be inconsistent across sources")
            scores.append(reliability_score)
        else:
            scores.append(reliability_score)
        
        # Check data consistency
        if hourly_data:
            temps = [h.get('temperature', 0) for h in hourly_data]
            if temps:
                temp_range = max(temps) - min(temps)
                temp_std = statistics.stdev(temps) if len(temps) > 1 else 0
                
                # Check for unrealistic temperature jumps
                if temp_range > 30:
                    issues.append(f"Large temperature range: {temp_range:.1f}°C")
                    suggestions.append("Verify data consistency across sources")
                    scores.append(0.6)
                elif temp_std > 10:
                    issues.append(f"High temperature variability: std={temp_std:.1f}°C")
                    suggestions.append("Temperature data may be inconsistent")
                    scores.append(0.7)
                else:
                    scores.append(1.0)
        
        # Check for missing critical fields
        missing_fields = []
        for hour in hourly_data[:3]:  # Check first 3 hours
            required = ['temperature', 'precipitation', 'wind_speed', 'humidity', 'condition']
            for field in required:
                if field not in hour or hour[field] is None:
                    missing_fields.append(field)
        
        if missing_fields:
            issues.append(f"Missing fields in some hours: {set(missing_fields)}")
            suggestions.append("Ensure all sources provide complete data")
            scores.append(0.5)
        else:
            scores.append(1.0)
        
        # Calculate overall score
        overall_score = statistics.mean(scores) if scores else 0.0
        
        # Determine quality level
        if overall_score >= 0.9:
            quality = QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            quality = QualityLevel.GOOD
        elif overall_score >= 0.6:
            quality = QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            quality = QualityLevel.POOR
        else:
            quality = QualityLevel.UNACCEPTABLE
        
        passed = overall_score >= self.quality_threshold
        
        return ReflectionResult(
            quality=quality,
            score=overall_score,
            issues=issues,
            suggestions=suggestions,
            passed=passed
        )
    
    def reflect_on_recommendation(
        self,
        recommendation: str,
        weather_data: Dict
    ) -> ReflectionResult:
        """
        Reflect on AI recommendation quality and relevance.
        
        Args:
            recommendation: Generated recommendation text
            weather_data: Weather data used to generate recommendation
            
        Returns:
            ReflectionResult with quality assessment
        """
        issues = []
        suggestions = []
        scores = []
        
        # Check length
        if len(recommendation) < 20:
            issues.append("Recommendation too short (may lack detail)")
            suggestions.append("Generate more detailed recommendation")
            scores.append(0.4)
        elif len(recommendation) > 500:
            issues.append("Recommendation too long (may be verbose)")
            suggestions.append("Generate more concise recommendation")
            scores.append(0.7)
        else:
            scores.append(1.0)
        
        # Check for key weather-related terms
        recommendation_lower = recommendation.lower()
        weather_terms = ['wear', 'clothing', 'jacket', 'coat', 'umbrella', 'rain', 
                        'cold', 'warm', 'hot', 'temperature', 'weather']
        found_terms = sum(1 for term in weather_terms if term in recommendation_lower)
        
        if found_terms < 2:
            issues.append("Recommendation may not be weather-relevant")
            suggestions.append("Ensure recommendation addresses weather conditions")
            scores.append(0.5)
        else:
            scores.append(1.0)
        
        # Check for actionable advice
        action_indicators = ['should', 'recommend', 'suggest', 'wear', 'bring', 'take']
        has_action = any(indicator in recommendation_lower for indicator in action_indicators)
        
        if not has_action:
            issues.append("Recommendation may lack actionable advice")
            suggestions.append("Include specific clothing recommendations")
            scores.append(0.6)
        else:
            scores.append(1.0)
        
        # Check consistency with weather data
        hourly_data = weather_data.get('hourly_data', [])
        if hourly_data:
            avg_temp = statistics.mean([h.get('temperature', 0) for h in hourly_data])
            total_precip = sum(h.get('precipitation', 0) for h in hourly_data)
            
            # Check if recommendation matches weather conditions
            if avg_temp < 10 and 'warm' in recommendation_lower and 'cold' not in recommendation_lower:
                issues.append("Recommendation may not match cold weather conditions")
                suggestions.append("Ensure recommendation reflects actual temperature")
                scores.append(0.6)
            elif avg_temp > 25 and 'cold' in recommendation_lower and 'warm' not in recommendation_lower:
                issues.append("Recommendation may not match warm weather conditions")
                suggestions.append("Ensure recommendation reflects actual temperature")
                scores.append(0.6)
            elif total_precip > 5 and 'rain' not in recommendation_lower and 'umbrella' not in recommendation_lower:
                issues.append("Recommendation may not address expected precipitation")
                suggestions.append("Include rain protection in recommendation")
                scores.append(0.7)
            else:
                scores.append(1.0)
        
        # Check for generic/empty content
        generic_phrases = ['the weather', 'weather conditions', 'it depends']
        is_generic = any(phrase in recommendation_lower for phrase in generic_phrases)
        
        if is_generic and len(recommendation) < 50:
            issues.append("Recommendation may be too generic")
            suggestions.append("Provide more specific, actionable advice")
            scores.append(0.5)
        else:
            scores.append(1.0)
        
        # Calculate overall score
        overall_score = statistics.mean(scores) if scores else 0.0
        
        # Determine quality level
        if overall_score >= 0.9:
            quality = QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            quality = QualityLevel.GOOD
        elif overall_score >= 0.6:
            quality = QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            quality = QualityLevel.POOR
        else:
            quality = QualityLevel.UNACCEPTABLE
        
        passed = overall_score >= self.quality_threshold
        
        return ReflectionResult(
            quality=quality,
            score=overall_score,
            issues=issues,
            suggestions=suggestions,
            passed=passed
        )
    
    def reflect_on_notification(
        self,
        notification: str,
        weather_data: Dict,
        recommendation: str
    ) -> ReflectionResult:
        """
        Reflect on notification completeness and formatting.
        
        Args:
            notification: Formatted notification message
            weather_data: Weather data included in notification
            recommendation: Recommendation included in notification
            
        Returns:
            ReflectionResult with quality assessment
        """
        issues = []
        suggestions = []
        scores = []
        
        # Check length
        if len(notification) < 100:
            issues.append("Notification too short (may be incomplete)")
            suggestions.append("Ensure all sections are included")
            scores.append(0.5)
        elif len(notification) > 2000:
            issues.append("Notification too long (may be overwhelming)")
            suggestions.append("Consider condensing information")
            scores.append(0.7)
        else:
            scores.append(1.0)
        
        # Check for required sections
        required_sections = ['Temperature', 'Rain', 'Wind', 'Recommendation']
        missing_sections = []
        for section in required_sections:
            if section not in notification:
                missing_sections.append(section)
        
        if missing_sections:
            issues.append(f"Missing sections: {', '.join(missing_sections)}")
            suggestions.append("Include all required notification sections")
            scores.append(0.4)
        else:
            scores.append(1.0)
        
        # Check if recommendation is included
        if recommendation and recommendation[:50] not in notification:
            issues.append("Recommendation may not be properly included")
            suggestions.append("Ensure recommendation is in notification")
            scores.append(0.6)
        else:
            scores.append(1.0)
        
        # Check for temperature information
        if '°C' not in notification and '°F' not in notification:
            issues.append("Temperature information may be missing")
            suggestions.append("Include temperature in notification")
            scores.append(0.5)
        else:
            scores.append(1.0)
        
        # Check formatting (emojis/sections)
        has_emojis = any(emoji in notification for emoji in ['🌡️', '☁️', '🌬️', '👔'])
        if not has_emojis:
            issues.append("Notification may lack visual formatting")
            suggestions.append("Consider adding emojis for better readability")
            scores.append(0.7)
        else:
            scores.append(1.0)
        
        # Calculate overall score
        overall_score = statistics.mean(scores) if scores else 0.0
        
        # Determine quality level
        if overall_score >= 0.9:
            quality = QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            quality = QualityLevel.GOOD
        elif overall_score >= 0.6:
            quality = QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            quality = QualityLevel.POOR
        else:
            quality = QualityLevel.UNACCEPTABLE
        
        passed = overall_score >= self.quality_threshold
        
        return ReflectionResult(
            quality=quality,
            score=overall_score,
            issues=issues,
            suggestions=suggestions,
            passed=passed
        )
    
    def refine_with_feedback(
        self,
        initial_output: Any,
        reflection_result: ReflectionResult,
        refinement_func: callable
    ) -> Tuple[Any, ReflectionResult]:
        """
        Refine output based on reflection feedback.
        
        Args:
            initial_output: The initial output to refine
            reflection_result: Result from reflection evaluation
            refinement_func: Function that takes (output, issues, suggestions) and returns refined output
            
        Returns:
            Tuple of (refined_output, new_reflection_result)
        """
        if reflection_result.passed:
            return initial_output, reflection_result
        
        # Attempt refinement
        try:
            refined_output = refinement_func(
                initial_output,
                reflection_result.issues,
                reflection_result.suggestions
            )
            return refined_output, reflection_result
        except Exception as e:
            # If refinement fails, return original with warning
            return initial_output, reflection_result

