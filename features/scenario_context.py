import asyncio
import os


class ScenarioContext:
    """A storage class for scenario-specific objects.

    This class provides a way to store objects that are specific to a scenario,
    preventing cross-contamination between scenarios when using a shared context.
    """

    def __init__(self, scenario_id):
        """Initialize with a unique scenario ID."""
        self.scenario_id = scenario_id
        self.storage = {}
        self.db_file = None
        self.adapter = None
        self.async_adapter = None
        self.entities = {}
        self.entity_ids = {}

    def store(self, key, value):
        """Store an object with the given key."""
        self.storage[key] = value

    def get(self, key, default=None):
        """Get an object with the given key, returning default if not found."""
        return self.storage.get(key, default)

    def cleanup(self):
        """Clean up resources associated with this scenario."""
        # Close and dispose of database connections
        if self.adapter:
            try:
                # Check if it's a ScyllaDB adapter (has close method but no session_manager)
                if hasattr(self.adapter, "close") and not hasattr(self.adapter, "session_manager"):
                    self.adapter.close()
                elif hasattr(self.adapter, "session_manager") and hasattr(self.adapter.session_manager, "engine"):
                    # First remove any open sessions
                    self.adapter.session_manager.remove_session()
                    # Then dispose of the engine
                    self.adapter.session_manager.engine.dispose()
            except Exception as e:
                print(f"Error disposing adapter: {e}")

        # Clean up async adapter
        if self.async_adapter:
            try:
                # Try to run async cleanup if we're in an async context
                try:
                    asyncio.get_running_loop()
                    # If we have a running loop, create a task
                    asyncio.create_task(self.async_cleanup())
                except RuntimeError:
                    # No running loop, run in new loop
                    asyncio.run(self.async_cleanup())
            except Exception as e:
                print(f"Error in async cleanup: {e}")

        # Remove database file if it exists
        if self.db_file and os.path.exists(self.db_file):
            try:
                # Make sure all connections are closed before attempting to remove
                import time

                time.sleep(0.1)  # Small delay to ensure connections are fully closed
                os.remove(self.db_file)
            except Exception as e:
                print(f"Error removing database file: {e}")

    async def async_cleanup(self):
        """Clean up async resources associated with this scenario."""
        if self.async_adapter:
            try:
                # Check if it's an async ScyllaDB adapter (has close method but no session_manager)
                if hasattr(self.async_adapter, "close") and not hasattr(self.async_adapter, "session_manager"):
                    await self.async_adapter.close()
                elif hasattr(self.async_adapter, "session_manager") and hasattr(
                        self.async_adapter.session_manager, "engine",
                ):
                    # Clean up async sessions and engine
                    await self.async_adapter.session_manager.remove_session()
                    await self.async_adapter.session_manager.engine.dispose()
            except Exception as e:
                print(f"Error in async cleanup: {e}")
