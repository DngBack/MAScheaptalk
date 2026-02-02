"""JSONL storage for episodes."""
import json
from pathlib import Path
from typing import List, Optional

import sys
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.storage import Storage
from domain.entities.episode import Episode


class JSONLStorage(Storage):
    """Store episodes in JSONL format (one JSON object per line)."""
    
    def __init__(self, filepath: str):
        """
        Initialize JSONL storage.
        
        Args:
            filepath: Path to the JSONL file
        """
        self.filepath = Path(filepath)
        
        # Create parent directory if it doesn't exist
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def save_episode(self, episode: Episode) -> None:
        """Save an episode to JSONL file (append mode)."""
        with open(self.filepath, 'a', encoding='utf-8') as f:
            json.dump(episode.to_dict(), f, ensure_ascii=False)
            f.write('\n')
    
    def load_episodes(self, limit: Optional[int] = None) -> List[Episode]:
        """Load episodes from JSONL file."""
        if not self.filepath.exists():
            return []
        
        episodes = []
        with open(self.filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                
                if line.strip():
                    try:
                        data = json.loads(line)
                        episode = Episode.from_dict(data)
                        episodes.append(episode)
                    except Exception as e:
                        print(f"Warning: Could not parse line {i+1}: {e}")
        
        return episodes
    
    def clear(self) -> None:
        """Clear all stored episodes by removing the file."""
        if self.filepath.exists():
            self.filepath.unlink()
