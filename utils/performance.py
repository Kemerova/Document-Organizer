"""
Performance monitoring and optimization utilities for Document Organizer.
Provides memory usage tracking, performance profiling, and resource monitoring.
"""

import gc
import logging
import os
import psutil
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
import threading
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_percent: float
    additional_metrics: Dict[str, Any]


class PerformanceMonitor:
    """Monitors system performance and resource usage."""
    
    def __init__(self, enable_detailed_monitoring: bool = True):
        """
        Initialize performance monitor.
        
        Args:
            enable_detailed_monitoring: Enable detailed CPU/memory monitoring
        """
        self.enable_detailed_monitoring = enable_detailed_monitoring
        self.metrics_history = []
        self.process = psutil.Process()
        self.monitoring_thread = None
        self.monitoring_active = False
        self.resource_samples = []
        
        logger.info("Performance monitor initialized")
    
    @contextmanager
    def monitor_operation(self, operation_name: str, **additional_metrics):
        """
        Context manager to monitor a specific operation.
        
        Args:
            operation_name: Name of the operation being monitored
            **additional_metrics: Additional metrics to track
        """
        # Start monitoring
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        if self.enable_detailed_monitoring:
            self._start_resource_monitoring()
        
        try:
            yield self
        finally:
            # Stop monitoring and collect metrics
            end_time = time.time()
            memory_after = self._get_memory_usage()
            
            if self.enable_detailed_monitoring:
                self._stop_resource_monitoring()
                memory_peak = max([sample['memory'] for sample in self.resource_samples] + [memory_after])
                cpu_percent = sum([sample['cpu'] for sample in self.resource_samples]) / len(self.resource_samples) if self.resource_samples else 0
            else:
                memory_peak = memory_after
                cpu_percent = 0
            
            # Create metrics record
            metrics = PerformanceMetrics(
                operation=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=memory_peak,
                cpu_percent=cpu_percent,
                additional_metrics=additional_metrics
            )
            
            self.metrics_history.append(metrics)
            
            # Log performance info
            logger.info(f"Operation '{operation_name}' completed in {metrics.duration:.2f}s, "
                       f"memory: {memory_before:.1f}MB -> {memory_after:.1f}MB "
                       f"(peak: {memory_peak:.1f}MB)")
            
            # Clear resource samples for next operation
            self.resource_samples.clear()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return self.process.cpu_percent()
        except Exception:
            return 0.0
    
    def _start_resource_monitoring(self):
        """Start background resource monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitoring_thread.start()
    
    def _stop_resource_monitoring(self):
        """Stop background resource monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
    
    def _monitor_resources(self):
        """Background thread function to monitor resources."""
        while self.monitoring_active:
            try:
                sample = {
                    'timestamp': time.time(),
                    'memory': self._get_memory_usage(),
                    'cpu': self._get_cpu_percent()
                }
                self.resource_samples.append(sample)
                time.sleep(0.1)  # Sample every 100ms
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                break
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_total_gb': memory.total / 1024 / 1024 / 1024,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'memory_percent': memory.percent,
                'disk_total_gb': disk.total / 1024 / 1024 / 1024,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                'disk_percent': (disk.used / disk.total) * 100,
                'process_memory_mb': self._get_memory_usage(),
                'process_cpu_percent': self._get_cpu_percent()
            }
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {}
    
    def check_resource_limits(self, memory_limit_gb: float = 8.0, 
                            cpu_limit_percent: float = 90.0) -> Dict[str, bool]:
        """
        Check if system resources are within acceptable limits.
        
        Args:
            memory_limit_gb: Maximum memory usage in GB
            cpu_limit_percent: Maximum CPU usage percentage
            
        Returns:
            Dictionary with resource status
        """
        system_info = self.get_system_info()
        
        memory_ok = system_info.get('memory_percent', 0) < (memory_limit_gb / system_info.get('memory_total_gb', 1) * 100)
        cpu_ok = system_info.get('cpu_percent', 0) < cpu_limit_percent
        disk_ok = system_info.get('disk_percent', 0) < 90.0  # 90% disk usage limit
        
        return {
            'memory_ok': memory_ok,
            'cpu_ok': cpu_ok,
            'disk_ok': disk_ok,
            'overall_ok': memory_ok and cpu_ok and disk_ok
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics."""
        if not self.metrics_history:
            return {'total_operations': 0}
        
        total_duration = sum(m.duration for m in self.metrics_history)
        avg_duration = total_duration / len(self.metrics_history)
        
        memory_usage = [m.memory_peak for m in self.metrics_history]
        max_memory = max(memory_usage)
        avg_memory = sum(memory_usage) / len(memory_usage)
        
        operations_by_type = {}
        for metric in self.metrics_history:
            if metric.operation not in operations_by_type:
                operations_by_type[metric.operation] = []
            operations_by_type[metric.operation].append(metric.duration)
        
        operation_stats = {}
        for op_type, durations in operations_by_type.items():
            operation_stats[op_type] = {
                'count': len(durations),
                'total_duration': sum(durations),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations)
            }
        
        return {
            'total_operations': len(self.metrics_history),
            'total_duration': total_duration,
            'avg_duration': avg_duration,
            'max_memory_mb': max_memory,
            'avg_memory_mb': avg_memory,
            'operations_by_type': operation_stats,
            'system_info': self.get_system_info()
        }
    
    def optimize_memory(self):
        """Perform memory optimization."""
        logger.info("Performing memory optimization...")
        
        # Force garbage collection
        collected = gc.collect()
        
        # Get memory usage after cleanup
        memory_after = self._get_memory_usage()
        
        logger.info(f"Memory optimization complete: collected {collected} objects, "
                   f"current memory usage: {memory_after:.1f}MB")
        
        return {
            'objects_collected': collected,
            'memory_after_mb': memory_after
        }
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        summary = self.get_performance_summary()
        system_info = summary.get('system_info', {})
        
        report = [
            "Performance Report",
            "=" * 50,
            f"Total Operations: {summary.get('total_operations', 0)}",
            f"Total Duration: {summary.get('total_duration', 0):.2f}s",
            f"Average Duration: {summary.get('avg_duration', 0):.2f}s",
            f"Peak Memory Usage: {summary.get('max_memory_mb', 0):.1f}MB",
            f"Average Memory Usage: {summary.get('avg_memory_mb', 0):.1f}MB",
            "",
            "System Information:",
            f"  CPU Cores: {system_info.get('cpu_count', 'Unknown')}",
            f"  CPU Usage: {system_info.get('cpu_percent', 0):.1f}%",
            f"  Total Memory: {system_info.get('memory_total_gb', 0):.1f}GB",
            f"  Available Memory: {system_info.get('memory_available_gb', 0):.1f}GB",
            f"  Memory Usage: {system_info.get('memory_percent', 0):.1f}%",
            f"  Disk Usage: {system_info.get('disk_percent', 0):.1f}%",
            ""
        ]
        
        # Add operation-specific statistics
        operations = summary.get('operations_by_type', {})
        if operations:
            report.append("Operations by Type:")
            for op_type, stats in operations.items():
                report.append(f"  {op_type}:")
                report.append(f"    Count: {stats['count']}")
                report.append(f"    Total Time: {stats['total_duration']:.2f}s")
                report.append(f"    Avg Time: {stats['avg_duration']:.2f}s")
                report.append(f"    Range: {stats['min_duration']:.2f}s - {stats['max_duration']:.2f}s")
        
        return "\n".join(report)


class MemoryOptimizer:
    """Utilities for memory optimization during processing."""
    
    @staticmethod
    def optimize_chunk_processing(chunks: List[Any], 
                                batch_size: int = 10,
                                cleanup_callback: Optional[Callable] = None) -> List[Any]:
        """
        Process chunks in batches to optimize memory usage.
        
        Args:
            chunks: List of chunks to process
            batch_size: Number of chunks to process at once
            cleanup_callback: Optional callback for cleanup between batches
            
        Returns:
            Processed results
        """
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Process batch (this would be implemented by caller)
            batch_results = batch  # Placeholder
            results.extend(batch_results)
            
            # Cleanup between batches
            if cleanup_callback:
                cleanup_callback()
            
            # Force garbage collection for large batches
            if batch_size > 50:
                gc.collect()
        
        return results
    
    @staticmethod
    def estimate_memory_requirements(file_count: int, 
                                   avg_file_size_kb: float,
                                   chunk_size_tokens: int = 8000) -> Dict[str, float]:
        """
        Estimate memory requirements for processing.
        
        Args:
            file_count: Number of files to process
            avg_file_size_kb: Average file size in KB
            chunk_size_tokens: Chunk size in tokens
            
        Returns:
            Memory estimates in MB
        """
        # Rough estimates based on typical usage
        total_content_mb = (file_count * avg_file_size_kb) / 1024
        
        # Estimate chunks (assuming ~4 chars per token)
        chars_per_chunk = chunk_size_tokens * 4
        bytes_per_chunk = chars_per_chunk * 2  # Unicode overhead
        
        estimated_chunks = (total_content_mb * 1024 * 1024) / bytes_per_chunk
        chunk_memory_mb = (estimated_chunks * bytes_per_chunk) / 1024 / 1024
        
        # Processing overhead (models, responses, etc.)
        processing_overhead = total_content_mb * 2
        
        return {
            'content_memory_mb': total_content_mb,
            'chunk_memory_mb': chunk_memory_mb,
            'processing_overhead_mb': processing_overhead,
            'total_estimated_mb': total_content_mb + chunk_memory_mb + processing_overhead,
            'recommended_ram_gb': ((total_content_mb + chunk_memory_mb + processing_overhead) * 1.5) / 1024
        }


class ConfigurationValidator:
    """Validates configuration for optimal performance."""
    
    @staticmethod
    def validate_processing_config(config: Dict[str, Any], 
                                 system_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate processing configuration against system capabilities.
        
        Args:
            config: Processing configuration
            system_info: System information
            
        Returns:
            Validation results with recommendations
        """
        recommendations = []
        warnings = []
        
        # Check concurrent requests vs CPU cores
        max_concurrent = config.get('max_concurrent_requests', 10)
        cpu_cores = system_info.get('cpu_count', 1)
        
        if max_concurrent > cpu_cores * 2:
            warnings.append(f"High concurrency ({max_concurrent}) vs CPU cores ({cpu_cores})")
            recommendations.append(f"Consider reducing max_concurrent_requests to {cpu_cores * 2}")
        
        # Check memory vs chunk size
        chunk_size = config.get('chunk_size_tokens', 8000)
        available_memory_gb = system_info.get('memory_available_gb', 0)
        
        if chunk_size > 16000 and available_memory_gb < 8:
            warnings.append("Large chunk size with limited memory")
            recommendations.append("Consider reducing chunk_size_tokens to 8000 or less")
        
        # Check disk space
        disk_free_gb = system_info.get('disk_free_gb', 0)
        if disk_free_gb < 2:
            warnings.append("Low disk space available")
            recommendations.append("Ensure at least 2GB free disk space for output files")
        
        return {
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'recommendations': recommendations,
            'optimal_settings': {
                'max_concurrent_requests': min(max_concurrent, cpu_cores * 2),
                'chunk_size_tokens': min(chunk_size, 12000 if available_memory_gb >= 8 else 8000)
            }
        }
    
    @staticmethod
    def get_recommended_settings(system_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recommended settings based on system capabilities.
        
        Args:
            system_info: System information
            
        Returns:
            Recommended configuration settings
        """
        cpu_cores = system_info.get('cpu_count', 1)
        memory_gb = system_info.get('memory_total_gb', 4)
        
        # Conservative settings for stability
        if memory_gb < 4:
            return {
                'max_concurrent_requests': max(1, cpu_cores),
                'chunk_size_tokens': 4000,
                'batch_size': 5
            }
        elif memory_gb < 8:
            return {
                'max_concurrent_requests': max(2, cpu_cores),
                'chunk_size_tokens': 6000,
                'batch_size': 10
            }
        else:
            return {
                'max_concurrent_requests': min(20, cpu_cores * 2),
                'chunk_size_tokens': 8000,
                'batch_size': 20
            }


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def monitor_performance(operation_name: str, **kwargs):
    """Decorator for monitoring function performance."""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            monitor = get_performance_monitor()
            with monitor.monitor_operation(operation_name, **kwargs):
                return func(*args, **func_kwargs)
        return wrapper
    return decorator