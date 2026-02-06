"""Checkpoint manager for saving and resuming experiment progress."""
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime


class CheckpointManager:
    """
    Manages checkpoints for long-running experiments.
    
    Features:
    - Atomic writes (temp file + rename)
    - Resume from checkpoint
    - Auto-cleanup on completion
    - Validation on load
    """
    
    def __init__(
        self,
        checkpoint_dir: str = "results/checkpoints",
        milestone: str = "milestone2",
        seed: int = 42,
        auto_cleanup: bool = True
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
            milestone: Milestone identifier (e.g., "milestone2")
            seed: Random seed for this run
            auto_cleanup: Whether to delete checkpoint on successful completion
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.milestone = milestone
        self.seed = seed
        self.auto_cleanup = auto_cleanup
        
        # Checkpoint file path
        self.checkpoint_path = self.checkpoint_dir / f"{milestone}_seed{seed}.json"
        
        # In-memory state
        self.completed_episodes: Set[str] = set()
        self.total_episodes: int = 0
        self.metadata: Dict[str, Any] = {}
    
    def save(self, episode_ids: List[str], total_episodes: int, metadata: Optional[Dict] = None):
        """
        Save checkpoint to disk atomically.
        
        Args:
            episode_ids: List of completed episode IDs
            total_episodes: Total number of episodes to run
            metadata: Optional metadata to save
        """
        # Update in-memory state
        self.completed_episodes.update(episode_ids)
        self.total_episodes = total_episodes
        if metadata:
            self.metadata.update(metadata)
        
        # Create checkpoint data
        checkpoint_data = {
            "milestone": self.milestone,
            "seed": self.seed,
            "completed_episodes": list(self.completed_episodes),
            "total_episodes": self.total_episodes,
            "progress": len(self.completed_episodes) / max(1, total_episodes),
            "timestamp": datetime.now().isoformat(),
            "metadata": self.metadata
        }
        
        # Atomic write: write to temp file, then rename
        temp_path = self.checkpoint_path.with_suffix('.json.tmp')
        
        try:
            with open(temp_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            # Atomic rename
            shutil.move(str(temp_path), str(self.checkpoint_path))
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def load(self) -> bool:
        """
        Load checkpoint from disk.
        
        Returns:
            True if checkpoint was loaded, False if no checkpoint exists
        """
        if not self.checkpoint_path.exists():
            return False
        
        try:
            with open(self.checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Validate checkpoint
            if checkpoint_data.get("milestone") != self.milestone:
                print(f"⚠ Warning: Checkpoint milestone mismatch "
                      f"(expected {self.milestone}, got {checkpoint_data.get('milestone')})")
                return False
            
            if checkpoint_data.get("seed") != self.seed:
                print(f"⚠ Warning: Checkpoint seed mismatch "
                      f"(expected {self.seed}, got {checkpoint_data.get('seed')})")
                return False
            
            # Load state
            self.completed_episodes = set(checkpoint_data.get("completed_episodes", []))
            self.total_episodes = checkpoint_data.get("total_episodes", 0)
            self.metadata = checkpoint_data.get("metadata", {})
            
            return True
            
        except Exception as e:
            print(f"⚠ Error loading checkpoint: {e}")
            return False
    
    def is_completed(self, episode_id: str) -> bool:
        """
        Check if an episode has already been completed.
        
        Args:
            episode_id: Episode identifier
            
        Returns:
            True if episode is already completed
        """
        return episode_id in self.completed_episodes
    
    def get_progress(self) -> tuple[int, int, float]:
        """
        Get current progress.
        
        Returns:
            Tuple of (completed, total, progress_percentage)
        """
        completed = len(self.completed_episodes)
        progress = completed / max(1, self.total_episodes)
        return completed, self.total_episodes, progress
    
    def cleanup(self):
        """Delete checkpoint file."""
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()
            print(f"✓ Cleaned up checkpoint: {self.checkpoint_path}")
    
    def complete(self):
        """Mark run as complete and optionally cleanup checkpoint."""
        if self.auto_cleanup:
            self.cleanup()
    
    def print_status(self):
        """Print checkpoint status."""
        completed, total, progress = self.get_progress()
        
        print("\n" + "="*70)
        print("CHECKPOINT STATUS")
        print("="*70)
        print(f"Milestone: {self.milestone}")
        print(f"Seed: {self.seed}")
        print(f"Progress: {completed}/{total} ({progress*100:.1f}%)")
        print(f"Checkpoint file: {self.checkpoint_path}")
        print(f"Exists: {self.checkpoint_path.exists()}")
        
        if self.metadata:
            print("\nMetadata:")
            for key, value in self.metadata.items():
                print(f"  {key}: {value}")
        
        print("="*70)
    
    @classmethod
    def exists(cls, checkpoint_dir: str, milestone: str, seed: int) -> bool:
        """
        Check if a checkpoint exists.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
            milestone: Milestone identifier
            seed: Random seed
            
        Returns:
            True if checkpoint file exists
        """
        checkpoint_path = Path(checkpoint_dir) / f"{milestone}_seed{seed}.json"
        return checkpoint_path.exists()
    
    @classmethod
    def resume_or_create(
        cls,
        checkpoint_dir: str,
        milestone: str,
        seed: int,
        **kwargs
    ) -> tuple['CheckpointManager', bool]:
        """
        Resume from checkpoint if exists, otherwise create new.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
            milestone: Milestone identifier
            seed: Random seed
            **kwargs: Additional arguments for CheckpointManager
            
        Returns:
            Tuple of (CheckpointManager, was_resumed)
        """
        manager = cls(checkpoint_dir, milestone, seed, **kwargs)
        was_resumed = manager.load()
        
        if was_resumed:
            completed, total, progress = manager.get_progress()
            print(f"\n✓ Resumed from checkpoint: {completed}/{total} episodes ({progress*100:.1f}%)")
        else:
            print(f"\n✓ Starting new run (no checkpoint found)")
        
        return manager, was_resumed
