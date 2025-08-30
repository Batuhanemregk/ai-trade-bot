"""
Unit tests for ID utilities.
Tests client ID generation, validation, and uniqueness.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from execution.id_utils import (
    generate_algo_id, 
    validate_client_id, 
    regenerate_client_id,
    is_id_used
)


@pytest.mark.core
class TestIDUtils:
    """Test ID utility functions."""
    
    def test_generate_algo_id_length(self):
        """Test that generated algo IDs have correct length."""
        # Test entry IDs
        entry_id = generate_algo_id("E")
        assert len(entry_id) <= 32
        assert entry_id.startswith("E")
        
        # Test algo IDs
        algo_id = generate_algo_id("A")
        assert len(algo_id) <= 32
        assert algo_id.startswith("A")
    
    def test_generate_algo_id_alphanumeric(self):
        """Test that generated IDs are alphanumeric."""
        entry_id = generate_algo_id("E")
        algo_id = generate_algo_id("A")
        
        # Check they only contain alphanumeric characters
        assert entry_id.replace("E", "").isalnum()
        assert algo_id.replace("A", "").isalnum()
    
    def test_generate_algo_id_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = set()
        for _ in range(100):
            entry_id = generate_algo_id("E")
            algo_id = generate_algo_id("A")
            
            assert entry_id not in ids
            assert algo_id not in ids
            
            ids.add(entry_id)
            ids.add(algo_id)
    
    def test_validate_client_id_valid(self):
        """Test validation of valid client IDs."""
        valid_ids = [
            "E1234567890abcdef",
            "A9876543210fedcba",
            "Eabc123def456",
            "Axyz789uvw012"
        ]
        
        for client_id in valid_ids:
            assert validate_client_id(client_id) == True
    
    def test_validate_client_id_invalid(self):
        """Test validation of invalid client IDs."""
        invalid_ids = [
            "1234567890abcdef",  # No prefix
            "X1234567890abcdef",  # Invalid prefix
            "E1234567890abcdefghijklmnopqrstuvwxyz",  # Too long
            "E123-456-789",  # Contains hyphens
            "E123_456_789",  # Contains underscores
            "",  # Empty string
            None  # None value
        ]
        
        for client_id in invalid_ids:
            assert validate_client_id(client_id) == False
    
    def test_regenerate_client_id(self):
        """Test client ID regeneration."""
        original_id = generate_algo_id("E")
        regenerated_id = regenerate_client_id(original_id)
        
        # Should be different
        assert regenerated_id != original_id
        
        # Should have same prefix
        assert regenerated_id.startswith("E")
        
        # Should be valid
        assert validate_client_id(regenerated_id) == True
    
    def test_is_id_used_persistence(self, tmp_path):
        """Test ID usage persistence across sessions."""
        # Create temporary state directory
        state_dir = tmp_path / "state" / "ids"
        state_dir.mkdir(parents=True)
        
        # Mock the state directory
        original_state = os.environ.get("AIBOTBS_STATE_DIR")
        os.environ["AIBOTBS_STATE_DIR"] = str(tmp_path / "state")
        
        try:
            # Test ID not used initially
            test_id = "E1234567890abcdef"
            assert is_id_used(test_id) == False
            
            # Mark ID as used
            used_ids_file = state_dir / "used_ids.json"
            used_ids_file.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(used_ids_file, 'w') as f:
                json.dump([test_id], f)
            
            # Test ID is now used
            assert is_id_used(test_id) == True
            
            # Test different ID still not used
            different_id = "E9876543210fedcba"
            assert is_id_used(different_id) == False
            
        finally:
            # Restore original state
            if original_state:
                os.environ["AIBOTBS_STATE_DIR"] = original_state
            else:
                del os.environ["AIBOTBS_STATE_DIR"]
    
    def test_is_id_used_file_creation(self, tmp_path):
        """Test that used_ids.json is created if missing."""
        # Create temporary state directory
        state_dir = tmp_path / "state" / "ids"
        
        # Mock the state directory
        original_state = os.environ.get("AIBOTBS_STATE_DIR")
        os.environ["AIBOTBS_STATE_DIR"] = str(tmp_path / "state")
        
        try:
            # File should not exist initially
            used_ids_file = state_dir / "used_ids.json"
            assert not used_ids_file.exists()
            
            # Check ID (should create file)
            test_id = "E1234567890abcdef"
            is_id_used(test_id)
            
            # File should now exist
            assert used_ids_file.exists()
            
            # Should contain empty list
            import json
            with open(used_ids_file, 'r') as f:
                data = json.load(f)
            assert data == {"used_ids": []}
            
        finally:
            # Restore original state
            if original_state:
                os.environ["AIBOTBS_STATE_DIR"] = original_state
            else:
                del os.environ["AIBOTBS_STATE_DIR"]
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test with very long ID
        long_id = "E" + "a" * 50
        assert validate_client_id(long_id) == False
        
        # Test with special characters
        special_id = "E123@456#789"
        assert validate_client_id(special_id) == False
        
        # Test with unicode characters
        unicode_id = "E123αβγδε"
        assert validate_client_id(unicode_id) == False
