"""Reputation storage using SQLite."""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

import sys
from pathlib import Path as PathLib
src_path = PathLib(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.reputation import Reputation, ReputationConfig


class ReputationStore:
    """
    Persistent storage for agent reputations using SQLite.
    
    Stores:
    - Current reputation scores
    - Trial counts (pass/fail)
    - Full history of updates
    - Trajectories for analysis
    """
    
    def __init__(self, db_path: str = "data/reputation.db"):
        """
        Initialize reputation store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        
        cursor = self.conn.cursor()
        
        # Main reputation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reputations (
                agent_id TEXT PRIMARY KEY,
                rep_score REAL NOT NULL,
                n_trials INTEGER NOT NULL,
                n_pass INTEGER NOT NULL,
                n_fail INTEGER NOT NULL,
                consecutive_correct INTEGER DEFAULT 0,
                consecutive_incorrect INTEGER DEFAULT 0,
                config TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reputation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                rep_before REAL NOT NULL,
                rep_after REAL NOT NULL,
                verification_result INTEGER NOT NULL,
                slashed INTEGER NOT NULL,
                redeemed INTEGER NOT NULL,
                metadata TEXT,
                FOREIGN KEY (agent_id) REFERENCES reputations(agent_id)
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_agent_id 
            ON reputation_history(agent_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_timestamp 
            ON reputation_history(timestamp)
        """)
        
        self.conn.commit()
    
    def get_reputation(
        self,
        agent_id: str,
        config: Optional[ReputationConfig] = None
    ) -> Reputation:
        """
        Get reputation for an agent.
        
        If not found, creates new reputation with initial score.
        
        Args:
            agent_id: Agent identifier
            config: Configuration (uses default if None)
            
        Returns:
            Reputation object
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT * FROM reputations WHERE agent_id = ?",
            (agent_id,)
        )
        
        row = cursor.fetchone()
        
        if row:
            # Load existing reputation
            rep_config = ReputationConfig.from_dict(json.loads(row["config"]))
            
            reputation = Reputation(
                agent_id=agent_id,
                rep_score=row["rep_score"],
                n_trials=row["n_trials"],
                n_pass=row["n_pass"],
                n_fail=row["n_fail"],
                consecutive_correct=row["consecutive_correct"],
                consecutive_incorrect=row["consecutive_incorrect"],
                config=rep_config
            )
            
            # Load history
            reputation.history = self._load_history(agent_id)
            
            return reputation
        
        else:
            # Create new reputation
            if config is None:
                config = ReputationConfig()
            
            reputation = Reputation(
                agent_id=agent_id,
                config=config
            )
            
            # Save to database
            self.save_reputation(reputation)
            
            return reputation
    
    def save_reputation(self, reputation: Reputation):
        """
        Save reputation to database.
        
        Args:
            reputation: Reputation object to save
        """
        cursor = self.conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if exists
        cursor.execute(
            "SELECT agent_id FROM reputations WHERE agent_id = ?",
            (reputation.agent_id,)
        )
        
        exists = cursor.fetchone() is not None
        
        config_json = json.dumps(reputation.config.to_dict())
        
        if exists:
            # Update existing
            cursor.execute("""
                UPDATE reputations
                SET rep_score = ?,
                    n_trials = ?,
                    n_pass = ?,
                    n_fail = ?,
                    consecutive_correct = ?,
                    consecutive_incorrect = ?,
                    config = ?,
                    updated_at = ?
                WHERE agent_id = ?
            """, (
                reputation.rep_score,
                reputation.n_trials,
                reputation.n_pass,
                reputation.n_fail,
                reputation.consecutive_correct,
                reputation.consecutive_incorrect,
                config_json,
                now,
                reputation.agent_id
            ))
        
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO reputations (
                    agent_id, rep_score, n_trials, n_pass, n_fail,
                    consecutive_correct, consecutive_incorrect,
                    config, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reputation.agent_id,
                reputation.rep_score,
                reputation.n_trials,
                reputation.n_pass,
                reputation.n_fail,
                reputation.consecutive_correct,
                reputation.consecutive_incorrect,
                config_json,
                now,
                now
            ))
        
        # Save new history entries
        self._save_history(reputation)
        
        self.conn.commit()
    
    def _load_history(self, agent_id: str) -> List:
        """Load history for an agent."""
        from domain.entities.reputation import ReputationHistory
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reputation_history
            WHERE agent_id = ?
            ORDER BY timestamp ASC
        """, (agent_id,))
        
        history = []
        for row in cursor.fetchall():
            history_entry = ReputationHistory(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                rep_before=row["rep_before"],
                rep_after=row["rep_after"],
                verification_result=bool(row["verification_result"]),
                slashed=bool(row["slashed"]),
                redeemed=bool(row["redeemed"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
            history.append(history_entry)
        
        return history
    
    def _save_history(self, reputation: Reputation):
        """Save new history entries for an agent."""
        cursor = self.conn.cursor()
        
        # Get last saved timestamp
        cursor.execute("""
            SELECT MAX(timestamp) as last_timestamp
            FROM reputation_history
            WHERE agent_id = ?
        """, (reputation.agent_id,))
        
        row = cursor.fetchone()
        last_timestamp = row["last_timestamp"] if row["last_timestamp"] else None
        
        # Save only new history entries
        for entry in reputation.history:
            entry_timestamp = entry.timestamp.isoformat()
            
            if last_timestamp is None or entry_timestamp > last_timestamp:
                cursor.execute("""
                    INSERT INTO reputation_history (
                        agent_id, timestamp, rep_before, rep_after,
                        verification_result, slashed, redeemed, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reputation.agent_id,
                    entry_timestamp,
                    entry.rep_before,
                    entry.rep_after,
                    int(entry.verification_result),
                    int(entry.slashed),
                    int(entry.redeemed),
                    json.dumps(entry.metadata)
                ))
    
    def get_all_reputations(self) -> Dict[str, Reputation]:
        """
        Get all reputations.
        
        Returns:
            Dictionary mapping agent_id to Reputation
        """
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT agent_id FROM reputations")
        
        reputations = {}
        for row in cursor.fetchall():
            agent_id = row["agent_id"]
            reputations[agent_id] = self.get_reputation(agent_id)
        
        return reputations
    
    def get_trajectory(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get reputation trajectory for an agent.
        
        Args:
            agent_id: Agent identifier
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            
        Returns:
            List of history entries as dictionaries
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM reputation_history
            WHERE agent_id = ?
        """
        params = [agent_id]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp ASC"
        
        cursor.execute(query, params)
        
        trajectory = []
        for row in cursor.fetchall():
            trajectory.append({
                "timestamp": row["timestamp"],
                "rep_before": row["rep_before"],
                "rep_after": row["rep_after"],
                "verification_result": bool(row["verification_result"]),
                "slashed": bool(row["slashed"]),
                "redeemed": bool(row["redeemed"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            })
        
        return trajectory
    
    def get_statistics(self) -> Dict:
        """
        Get overall statistics across all agents.
        
        Returns:
            Dictionary with aggregate statistics
        """
        cursor = self.conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_agents,
                AVG(rep_score) as mean_rep,
                MIN(rep_score) as min_rep,
                MAX(rep_score) as max_rep,
                SUM(n_trials) as total_trials,
                SUM(n_pass) as total_pass,
                SUM(n_fail) as total_fail
            FROM reputations
        """)
        
        row = cursor.fetchone()
        
        total_trials = row["total_trials"] or 0
        total_pass = row["total_pass"] or 0
        
        stats = {
            "total_agents": row["total_agents"],
            "mean_reputation": row["mean_rep"],
            "min_reputation": row["min_rep"],
            "max_reputation": row["max_rep"],
            "total_trials": total_trials,
            "total_pass": total_pass,
            "total_fail": row["total_fail"],
            "overall_pass_rate": total_pass / total_trials if total_trials > 0 else 0.0
        }
        
        return stats
    
    def reset_reputation(self, agent_id: str):
        """
        Reset reputation for an agent.
        
        Args:
            agent_id: Agent identifier
        """
        cursor = self.conn.cursor()
        
        # Delete history
        cursor.execute(
            "DELETE FROM reputation_history WHERE agent_id = ?",
            (agent_id,)
        )
        
        # Delete reputation
        cursor.execute(
            "DELETE FROM reputations WHERE agent_id = ?",
            (agent_id,)
        )
        
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
