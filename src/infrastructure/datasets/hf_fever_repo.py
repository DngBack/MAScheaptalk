"""FEVER dataset repository using HuggingFace datasets."""
from typing import Iterator, Optional, List
from datasets import load_dataset

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.dataset_repo import DatasetRepository
from domain.entities.task import Task
from domain.entities.evidence import Evidence
from domain.value_objects.labels import FEVERLabel


class HFFEVERRepository(DatasetRepository):
    """FEVER dataset repository using HuggingFace datasets library."""
    
    def __init__(self, split: str = "train", num_samples: int = 100, seed: int = 42):
        """
        Initialize FEVER repository.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            num_samples: Number of samples to load
            seed: Random seed for reproducibility
        """
        # Map common names to actual split names
        split_map = {
            "validation": "dev",
            "val": "dev",
            "train": "train",
            "test": "test",
            "dev": "dev"
        }
        self.split = split_map.get(split.lower(), split)
        self.num_samples = num_samples
        self.seed = seed
        
        # Load dataset - FEVER from HuggingFace (split_map: validation→dev for HF compatibility)
        print(f"Loading FEVER dataset: split={split}, num_samples={num_samples}")
        
        # Use mapped split name for load_dataset (e.g. "validation" → "dev")
        hf_split = self.split
        split_str = f"{hf_split}[:{num_samples}]" if num_samples else hf_split
        
        # Try multiple FEVER dataset sources
        dataset_sources = [
            ("lucadiliello/FEVER", None),           # Processed FEVER dataset
            ("fever", "v1.0"),                      # Original with config
            ("fever", None),                        # Original without config
        ]
        
        self.dataset = None
        last_error = None
        
        for dataset_name, config in dataset_sources:
            try:
                print(f"  Trying {dataset_name}" + (f" with config {config}" if config else ""))
                if config:
                    self.dataset = load_dataset(dataset_name, config, split=split_str)
                else:
                    self.dataset = load_dataset(dataset_name, split=split_str)
                print(f"  ✓ Successfully loaded from {dataset_name}")
                break
            except Exception as e:
                last_error = e
                print(f"  ✗ Failed: {str(e)[:100]}")
                continue
        
        if self.dataset is None:
            # If all fail, create a mock dataset for testing
            print(f"  Warning: Could not load FEVER dataset. Creating mock data for testing.")
            self.dataset = self._create_mock_dataset(num_samples if num_samples else 100)
        
        print(f"Loaded {len(self.dataset)} tasks from FEVER")
    
    def get_task(self, idx: int) -> Task:
        """Get a specific task by index."""
        if idx >= len(self.dataset):
            raise IndexError(f"Index {idx} out of range (dataset size: {len(self.dataset)})")
        
        item = self.dataset[idx]
        return self._parse_item(item, idx)
    
    def iter_tasks(self, limit: Optional[int] = None) -> Iterator[Task]:
        """Iterate over tasks."""
        max_items = min(limit, len(self.dataset)) if limit else len(self.dataset)
        for idx in range(max_items):
            yield self.get_task(idx)
    
    def get_num_tasks(self) -> int:
        """Return total number of tasks."""
        return len(self.dataset)
    
    def _parse_item(self, item: dict, idx: int) -> Task:
        """Parse a FEVER dataset item into a Task entity."""
        # FEVER dataset structure:
        # - id: unique identifier
        # - claim: the claim text
        # - label: SUPPORTS, REFUTES, or NOT ENOUGH INFO
        # - evidence_annotation_id, evidence_id, evidence_wiki_url, etc.
        
        task_id = str(item.get("id", f"fever_{idx}"))
        claim = item.get("claim", "")
        raw_label = item.get("label", "NOT ENOUGH INFO")
        # HF FEVER may use int: 0=SUPPORTS, 1=REFUTES, 2=NOT ENOUGH INFO
        label_str = raw_label if isinstance(raw_label, (str, int)) else "NOT ENOUGH INFO"
        
        # Parse label (from_string accepts str or int)
        try:
            label = FEVERLabel.from_string(label_str)
        except ValueError:
            # Default to NOT_ENOUGH_INFO if label is unknown
            label = FEVERLabel.NOT_ENOUGH_INFO
        
        # Parse evidence
        # FEVER evidence can be complex; for now, extract what's available
        evidence_list = self._extract_evidence(item)
        
        metadata = {
            "original_id": item.get("id"),
            "dataset": "FEVER",
            "split": self.split
        }
        
        return Task(
            task_id=task_id,
            claim=claim,
            label=label,
            evidence=evidence_list,
            metadata=metadata
        )
    
    def _extract_evidence(self, item: dict) -> List[Evidence]:
        """Extract evidence from FEVER item. Prefer actual sentence text when available."""
        evidence_list = []
        
        # 1) Try columns that may contain evidence *sentence text* (for evidence_match_score)
        for col in ("evidence", "evidence_sequence", "retrieved_sentences", "evidence_sentences", "sentences"):
            raw = item.get(col)
            if raw is None:
                continue
            if isinstance(raw, list):
                for i, entry in enumerate(raw):
                    if isinstance(entry, str) and len(entry.strip()) > 10:
                        evidence_list.append(Evidence(
                            evidence_id=f"{col}_{i}",
                            text=entry.strip(),
                            source=col,
                            metadata={"index": i}
                        ))
                    elif isinstance(entry, dict):
                        text = entry.get("text") or entry.get("sentence") or entry.get("content")
                        if isinstance(text, str) and len(text.strip()) > 10:
                            evidence_list.append(Evidence(
                                evidence_id=f"{col}_{i}",
                                text=text.strip(),
                                source=entry.get("source", col),
                                metadata={"index": i}
                            ))
                if evidence_list:
                    return evidence_list
            elif isinstance(raw, str) and len(raw.strip()) > 10:
                evidence_list.append(Evidence(evidence_id=col, text=raw.strip(), source=col, metadata={}))
                return evidence_list
        
        # 2) Fallback: evidence_id + evidence_wiki_url (often no sentence text, only IDs/URLs)
        if "evidence_annotation_id" in item and item["evidence_annotation_id"]:
            evidence_ids = item.get("evidence_id", [])
            evidence_wiki_urls = item.get("evidence_wiki_url", [])
            if isinstance(evidence_ids, list):
                for i, eid in enumerate(evidence_ids):
                    if eid is None or eid == "":
                        continue
                    wiki_url = evidence_wiki_urls[i] if i < len(evidence_wiki_urls) else None
                    evidence_list.append(Evidence(
                        evidence_id=str(eid),
                        text=f"Evidence from {wiki_url}" if wiki_url else "Evidence",
                        source=wiki_url,
                        metadata={"index": i}
                    ))
        
        # 3) No usable evidence: placeholder (verifier will skip match and set evidence_validity_skipped_reason)
        if not evidence_list:
            evidence_list.append(Evidence(
                evidence_id="none",
                text="No evidence available",
                source=None,
                metadata={}
            ))
        
        return evidence_list
    
    def _create_mock_dataset(self, num_samples: int) -> list:
        """Create a mock FEVER dataset for testing when real dataset is unavailable.
        Includes real evidence sentence text so evidence_match_score can be tested.
        """
        print("Creating mock FEVER dataset...")
        
        mock_data = []
        
        # (claim, label, evidence_sentences) — evidence text matches or supports/refutes claim
        sample_claims = [
            ("The sun is a star.", "SUPPORTS", ["The sun is a star.", "The Sun is the star at the center of the Solar System."]),
            ("Water freezes at 100 degrees Celsius.", "REFUTES", ["Water freezes at 0 degrees Celsius at standard pressure.", "The freezing point of water is 0 °C."]),
            ("Dragons exist in the real world.", "REFUTES", ["Dragons are mythical creatures with no scientific evidence of existence.", "No real-world evidence supports the existence of dragons."]),
            ("Python is a programming language.", "SUPPORTS", ["Python is a programming language.", "Python is an interpreted high-level programming language."]),
            ("The Earth is flat.", "REFUTES", ["The Earth is an oblate spheroid.", "Scientific evidence shows the Earth is roughly spherical."]),
            ("Photosynthesis occurs in plants.", "SUPPORTS", ["Photosynthesis occurs in plants.", "Plants use sunlight to convert CO2 and water into glucose through photosynthesis."]),
            ("Humans can breathe underwater without equipment.", "REFUTES", ["Humans cannot breathe underwater without artificial equipment.", "Human lungs are not adapted for extracting oxygen from water."]),
            ("The moon orbits the Earth.", "SUPPORTS", ["The moon orbits the Earth.", "The Moon is Earth's only natural satellite."]),
            ("Gravity pulls objects downward on Earth.", "SUPPORTS", ["Gravity pulls objects toward the center of the Earth.", "On Earth, gravity gives weight to physical objects."]),
            ("Birds are mammals.", "REFUTES", ["Birds are not mammals; they are a separate class of vertebrates.", "Birds are classified as aves, not mammals."]),
        ]
        
        for i in range(num_samples):
            claim, label, evidence_sentences = sample_claims[i % len(sample_claims)]
            
            mock_item = {
                "id": f"mock_{i}",
                "claim": claim,
                "label": label,
                "evidence": evidence_sentences,  # Real text so verifier can compute evidence_match_score
                "evidence_annotation_id": None,
                "evidence_id": [],
                "evidence_wiki_url": [],
            }
            mock_data.append(mock_item)
        
        return mock_data