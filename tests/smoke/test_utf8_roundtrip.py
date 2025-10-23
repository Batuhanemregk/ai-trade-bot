#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTF-8 Round-trip Test
Tests Unicode/emoji support across console, file logging, and data formats.
"""

import json
import csv
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import pytest
from loguru import logger

# Import UTF-8 configuration
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.utf8_config import setup_utf8_environment, get_emoji_setting, format_with_emoji


class TestUTF8RoundTrip:
    """Test UTF-8 encoding support across different components."""
    
    def setup_method(self):
        """Setup test environment."""
        setup_utf8_environment()
        
        # Test data with various Unicode characters
        self.test_emojis = "🚀🟢⚠️❌✅📊💾🎯📈📋🛡️📱"
        self.test_unicode = "Türkçe: ğüşıöç, Русский: йцукен, 中文: 你好世界"
        self.test_message = f"UTF-8 Test: {self.test_emojis} {self.test_unicode}"
        
    def test_console_output(self):
        """Test console output with Unicode characters."""
        print(f"Console test: {self.test_message}")
        
        # Test stdout encoding
        assert sys.stdout.encoding.lower() in ['utf-8', 'utf8'], f"Expected UTF-8, got {sys.stdout.encoding}"
        
        # Test that we can print without errors
        try:
            print(self.test_emojis)
            print(self.test_unicode)
        except UnicodeEncodeError as e:
            pytest.fail(f"Unicode encoding error in console: {e}")
    
    def test_logger_roundtrip(self):
        """Test logger with Unicode characters."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            # Configure logger to write to temp file
            logger.remove()  # Remove default handlers
            logger.add(log_file, encoding='utf-8', level='DEBUG')
            
            # Log test message
            logger.info(self.test_message)
            logger.debug(f"Debug: {self.test_emojis}")
            logger.warning(f"Warning: {self.test_unicode}")
            
            # Read back and verify
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verify content is preserved
            assert self.test_emojis in content, "Emojis not preserved in log file"
            assert self.test_unicode in content, "Unicode text not preserved in log file"
            assert self.test_message in content, "Full message not preserved in log file"
            
        finally:
            # Cleanup
            logger.remove()
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_json_roundtrip(self):
        """Test JSON serialization/deserialization with Unicode."""
        test_data = {
            "emojis": self.test_emojis,
            "unicode": self.test_unicode,
            "message": self.test_message,
            "mixed": f"Mixed: {self.test_emojis} {self.test_unicode}"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.json') as f:
            json_file = f.name
        
        try:
            # Write JSON
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # Read back
            with open(json_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Verify round-trip
            assert loaded_data == test_data, "JSON round-trip failed"
            assert loaded_data["emojis"] == self.test_emojis, "Emojis not preserved in JSON"
            assert loaded_data["unicode"] == self.test_unicode, "Unicode not preserved in JSON"
            
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)
    
    def test_csv_roundtrip(self):
        """Test CSV serialization/deserialization with Unicode."""
        test_data = [
            {"symbol": "BTC-USDT", "emoji": "🚀", "message": self.test_message},
            {"symbol": "ETH-USDT", "emoji": "📊", "message": self.test_unicode},
            {"symbol": "SOL-USDT", "emoji": "✅", "message": f"Test: {self.test_emojis}"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as f:
            csv_file = f.name
        
        try:
            # Write CSV
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["symbol", "emoji", "message"])
                writer.writeheader()
                writer.writerows(test_data)
            
            # Read back
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                loaded_data = list(reader)
            
            # Verify round-trip
            assert len(loaded_data) == len(test_data), "CSV row count mismatch"
            for i, row in enumerate(loaded_data):
                assert row["symbol"] == test_data[i]["symbol"], f"Symbol mismatch in row {i}"
                assert row["emoji"] == test_data[i]["emoji"], f"Emoji mismatch in row {i}"
                assert row["message"] == test_data[i]["message"], f"Message mismatch in row {i}"
            
        finally:
            if os.path.exists(csv_file):
                os.unlink(csv_file)
    
    def test_emoji_control_flag(self):
        """Test emoji control flag functionality."""
        # Test with emoji enabled
        os.environ['LOG_USE_EMOJI'] = 'true'
        assert get_emoji_setting() == True, "Emoji setting should be True"
        
        formatted = format_with_emoji("Test message", "🚀")
        assert "🚀" in formatted, "Emoji should be included when enabled"
        
        # Test with emoji disabled
        os.environ['LOG_USE_EMOJI'] = 'false'
        assert get_emoji_setting() == False, "Emoji setting should be False"
        
        formatted = format_with_emoji("Test message", "🚀")
        assert "🚀" not in formatted, "Emoji should not be included when disabled"
        assert "Test message" in formatted, "Message should still be included"
    
    def test_environment_variables(self):
        """Test that UTF-8 environment variables are set."""
        assert os.environ.get('PYTHONUTF8') == '1', "PYTHONUTF8 should be set to 1"
        assert os.environ.get('PYTHONIOENCODING') == 'utf-8', "PYTHONIOENCODING should be set to utf-8"
        assert os.environ.get('LANG') == 'C.UTF-8', "LANG should be set to C.UTF-8"
    
    def test_stdout_stderr_encoding(self):
        """Test stdout/stderr encoding configuration."""
        # Test that reconfigure was called (Python 3.7+)
        if sys.version_info >= (3, 7):
            assert sys.stdout.encoding.lower() in ['utf-8', 'utf8'], f"stdout encoding should be UTF-8, got {sys.stdout.encoding}"
            assert sys.stderr.encoding.lower() in ['utf-8', 'utf8'], f"stderr encoding should be UTF-8, got {sys.stderr.encoding}"
    
    def test_file_encoding_consistency(self):
        """Test that files are consistently written in UTF-8."""
        test_content = f"Test content: {self.test_emojis} {self.test_unicode}"
        
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            file_path = f.name
            f.write(test_content)
        
        try:
            # Read with different encodings to verify it's UTF-8
            with open(file_path, 'r', encoding='utf-8') as f:
                utf8_content = f.read()
            
            with open(file_path, 'r', encoding='latin-1') as f:
                latin1_content = f.read()
            
            # UTF-8 should preserve the content correctly
            assert utf8_content == test_content, "UTF-8 read should preserve content"
            
            # Latin-1 should not preserve emojis correctly
            assert utf8_content != latin1_content, "Different encodings should produce different results"
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)


def test_manual_verification():
    """Manual test that can be run to verify UTF-8 support visually."""
    setup_utf8_environment()
    
    print("\n" + "="*50)
    print("UTF-8 MANUAL VERIFICATION TEST")
    print("="*50)
    
    test_emojis = "🚀🟢⚠️❌✅📊💾🎯📈📋🛡️📱"
    test_unicode = "Türkçe: ğüşıöç, Русский: йцукен, 中文: 你好世界"
    
    print(f"Emojis: {test_emojis}")
    print(f"Unicode: {test_unicode}")
    print(f"Mixed: {test_emojis} {test_unicode}")
    
    print(f"\nEnvironment:")
    print(f"  PYTHONUTF8: {os.environ.get('PYTHONUTF8')}")
    print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
    print(f"  LANG: {os.environ.get('LANG')}")
    print(f"  stdout.encoding: {sys.stdout.encoding}")
    print(f"  stderr.encoding: {sys.stderr.encoding}")
    
    print(f"\nEmoji control:")
    print(f"  LOG_USE_EMOJI: {os.environ.get('LOG_USE_EMOJI')}")
    print(f"  get_emoji_setting(): {get_emoji_setting()}")
    
    print("\nIf you can see all emojis and Unicode characters above,")
    print("UTF-8 support is working correctly!")
    print("="*50)


if __name__ == "__main__":
    # Run manual verification
    test_manual_verification()
    
    # Run pytest
    pytest.main([__file__, "-v"])


