"""Parallel execution utility for running episodes concurrently."""
import asyncio
import time
from typing import List, Callable, Any, Optional, Dict
from datetime import datetime


class ParallelExecutor:
    """
    Executes tasks in parallel with concurrency control.
    
    Features:
    - Semaphore-based concurrency limiting
    - Batch processing with progress tracking
    - Error handling without stopping entire batch
    - Retry logic with exponential backoff
    - Rate limit detection and adaptive throttling
    """
    
    def __init__(
        self,
        max_concurrent: int = 30,
        batch_size: int = 100,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        rate_limit_backoff: float = 60.0
    ):
        """
        Initialize parallel executor.
        
        Args:
            max_concurrent: Maximum number of concurrent tasks
            batch_size: Number of tasks per batch (for checkpointing)
            retry_attempts: Number of retry attempts for failed tasks
            retry_delay: Initial delay between retries (exponential backoff)
            rate_limit_backoff: Delay when rate limit is hit (seconds)
        """
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.rate_limit_backoff = rate_limit_backoff
        
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()  # Initially not rate limited
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed": 0,
            "failed": 0,
            "retries": 0,
            "rate_limits": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.stats["start_time"] = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.stats["end_time"] = time.time()
        return False
    
    async def _execute_with_retry(
        self,
        task_func: Callable,
        *args,
        **kwargs
    ) -> tuple[bool, Any, Optional[Exception]]:
        """
        Execute a single task with retry logic.
        
        Returns:
            Tuple of (success, result, exception)
        """
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                # Wait for semaphore (concurrency control)
                async with self.semaphore:
                    # Wait if rate limited
                    await self.rate_limit_event.wait()
                    
                    # Execute task
                    result = await task_func(*args, **kwargs)
                    return True, result, None
                    
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Check if it's a rate limit error
                if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                    self.stats["rate_limits"] += 1
                    print(f"\n⚠ Rate limit hit! Backing off for {self.rate_limit_backoff}s...")
                    
                    # Block all tasks temporarily
                    self.rate_limit_event.clear()
                    await asyncio.sleep(self.rate_limit_backoff)
                    self.rate_limit_event.set()
                    
                    # Don't count rate limits as regular retries
                    continue
                
                # For other errors, use exponential backoff
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    self.stats["retries"] += 1
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    self.stats["failed"] += 1
                    return False, None, last_exception
        
        return False, None, last_exception
    
    async def run_batch(
        self,
        tasks: List[tuple],
        task_func: Callable,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        checkpoint_callback: Optional[Callable[[List[Any]], None]] = None
    ) -> tuple[List[Any], List[tuple[tuple, Exception]]]:
        """
        Run a batch of tasks in parallel.
        
        Args:
            tasks: List of task arguments (each item is a tuple of args)
            task_func: Async function to call for each task
            progress_callback: Optional callback(completed, total) for progress
            checkpoint_callback: Optional callback(results) called after each batch
            
        Returns:
            Tuple of (successful_results, failed_tasks_with_errors)
        """
        self.stats["total_tasks"] = len(tasks)
        results = []
        failures = []
        
        # Process in batches
        for batch_start in range(0, len(tasks), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(tasks))
            batch = tasks[batch_start:batch_end]
            
            print(f"[Batch {batch_start//self.batch_size + 1}] Processing episodes {batch_start+1}-{batch_end}...", flush=True)
            
            # Create coroutines for this batch
            coroutines = [
                self._execute_with_retry(task_func, *task_args)
                for task_args in batch
            ]
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(*coroutines, return_exceptions=False)
            
            # Process results
            for i, (success, result, error) in enumerate(batch_results):
                task_args = batch[i]
                
                if success:
                    results.append(result)
                    self.stats["completed"] += 1
                else:
                    failures.append((task_args, error))
                
                # Progress callback
                if progress_callback:
                    progress_callback(self.stats["completed"], self.stats["total_tasks"])
            
            # Checkpoint callback
            if checkpoint_callback and results:
                checkpoint_callback(results[-len(batch):])
        
        return results, failures
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self.stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            elapsed = stats["end_time"] - stats["start_time"]
            stats["elapsed_seconds"] = elapsed
            
            if elapsed > 0:
                stats["tasks_per_second"] = stats["completed"] / elapsed
                stats["tasks_per_minute"] = stats["completed"] / elapsed * 60
            else:
                stats["tasks_per_second"] = 0
                stats["tasks_per_minute"] = 0
        
        return stats
    
    def print_summary(self):
        """Print execution summary."""
        stats = self.get_stats()
        
        print("\n" + "="*70)
        print("PARALLEL EXECUTION SUMMARY")
        print("="*70)
        print(f"Total tasks:       {stats['total_tasks']}")
        print(f"Completed:         {stats['completed']} ({stats['completed']/max(1,stats['total_tasks'])*100:.1f}%)")
        print(f"Failed:            {stats['failed']}")
        print(f"Retries:           {stats['retries']}")
        print(f"Rate limit hits:   {stats['rate_limits']}")
        
        if stats.get("elapsed_seconds"):
            print(f"Elapsed time:      {stats['elapsed_seconds']:.1f}s")
            print(f"Throughput:        {stats['tasks_per_minute']:.1f} tasks/min")
        
        print("="*70)
