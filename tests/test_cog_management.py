"""Tests for cog management functionality."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.models.cog import CogInfo, CogStatusUpdate
from src.services.cog_manager import CogManagerService


class TestCogManagerService:
    """Test the CogManagerService class."""

    def test_create_default_config(self):
        """Test creating default configuration."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            manager = CogManagerService(temp_file.name)
            config = manager.config
            
            assert len(config.cogs) == 5
            assert "BasicCog" in config.cogs
            assert "DiceCog" in config.cogs
            assert "MusicCog" in config.cogs
            assert "TTSCog" in config.cogs
            assert "AiCog" in config.cogs
            
            # All should be enabled by default
            for cog in config.cogs.values():
                assert cog.enabled is True

    def test_toggle_cog(self):
        """Test toggling cog status."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            manager = CogManagerService(temp_file.name)
            
            # Initially enabled
            assert manager.is_cog_enabled("BasicCog") is True
            
            # Disable
            success = manager.toggle_cog("BasicCog", False)
            assert success is True
            assert manager.is_cog_enabled("BasicCog") is False
            
            # Re-enable
            success = manager.toggle_cog("BasicCog", True)
            assert success is True
            assert manager.is_cog_enabled("BasicCog") is True

    def test_toggle_nonexistent_cog(self):
        """Test toggling a cog that doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            manager = CogManagerService(temp_file.name)
            
            success = manager.toggle_cog("NonexistentCog", False)
            assert success is False

    def test_record_command_usage(self):
        """Test recording command usage."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            manager = CogManagerService(temp_file.name)
            
            # Record usage
            manager.record_command_usage("BasicCog", "ping", "123456789")
            
            # Check usage was recorded
            usage_stats = manager.get_command_usage("BasicCog", "ping")
            assert len(usage_stats) == 1
            assert usage_stats[0].command_name == "ping"
            assert usage_stats[0].total_uses == 1
            assert usage_stats[0].last_user == "123456789"
            
            # Record another use
            manager.record_command_usage("BasicCog", "ping", "987654321")
            
            usage_stats = manager.get_command_usage("BasicCog", "ping")
            assert len(usage_stats) == 1
            assert usage_stats[0].total_uses == 2
            assert usage_stats[0].last_user == "987654321"

    def test_persistence(self):
        """Test that configuration persists across instances."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # Create and modify configuration
            manager1 = CogManagerService(temp_path)
            manager1.toggle_cog("BasicCog", False)
            manager1.record_command_usage("DiceCog", "roll", "user123")
            
            # Create new instance and check persistence
            manager2 = CogManagerService(temp_path)
            assert manager2.is_cog_enabled("BasicCog") is False
            usage_stats = manager2.get_command_usage("DiceCog", "roll")
            assert len(usage_stats) == 1
            assert usage_stats[0].total_uses == 1
            
        finally:
            Path(temp_path).unlink(missing_ok=True)


def test_cogs_router():
    """Test the cogs API router."""
    import tempfile
    from src.services.cog_manager import CogManagerService
    from fastapi import FastAPI
    from src.routers.cogs import router
    
    # Use a temporary config file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Replace the global cog_manager with a test instance
        import src.routers.cogs
        original_manager = src.routers.cogs.cog_manager
        test_manager = CogManagerService(temp_path)
        src.routers.cogs.cog_manager = test_manager
        
        app = FastAPI()
        app.include_router(router, prefix="/api/cogs")
        
        client = TestClient(app)
        
        # Test getting all cogs
        response = client.get("/api/cogs/")
        assert response.status_code == 200
        cogs = response.json()
        assert isinstance(cogs, dict)
        assert "BasicCog" in cogs
        
        # Test getting specific cog
        response = client.get("/api/cogs/BasicCog")
        assert response.status_code == 200
        cog = response.json()
        assert cog["name"] == "BasicCog"
        assert cog["enabled"] is True  # Should be True in fresh config
        
        # Test toggling cog
        response = client.post("/api/cogs/BasicCog/toggle", json={"enabled": False})
        assert response.status_code == 200
        result = response.json()
        assert "disabled" in result["message"]
        
        # Verify cog is disabled
        response = client.get("/api/cogs/BasicCog")
        assert response.status_code == 200
        cog = response.json()
        assert cog["enabled"] is False
        
        # Test nonexistent cog
        response = client.get("/api/cogs/NonexistentCog")
        assert response.status_code == 404
        
    finally:
        # Restore original manager
        src.routers.cogs.cog_manager = original_manager
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])