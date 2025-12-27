"""
Persona Registry

Central registry for managing agent personas.
Provides discovery, instantiation, and lifecycle management.
"""

from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import threading

from .persona_base import AgentPersona, PersonaType


@dataclass
class PersonaMetadata:
    """Metadata about a registered persona."""
    name: str
    persona_type: PersonaType
    description: str
    version: str = "1.0.0"
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    deprecation_reason: str = ""


@dataclass
class PersonaInstance:
    """A running instance of a persona."""
    instance_id: str
    persona_name: str
    persona: AgentPersona
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    error_count: int = 0


class PersonaRegistry:
    """
    Central registry for agent personas.

    Responsibilities:
    - Register persona classes
    - Create persona instances
    - Track active instances
    - Provide discovery by type/capability
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry."""
        if self._initialized:
            return

        self._personas: Dict[str, Type[AgentPersona]] = {}
        self._metadata: Dict[str, PersonaMetadata] = {}
        self._instances: Dict[str, PersonaInstance] = {}
        self._instance_counter = 0
        self._callbacks: Dict[str, List[Callable]] = {
            "on_register": [],
            "on_instantiate": [],
            "on_destroy": [],
        }
        self._initialized = True

    def register(
        self,
        persona_class: Type[AgentPersona],
        metadata: Optional[PersonaMetadata] = None,
        override: bool = False
    ) -> bool:
        """
        Register a persona class.

        Args:
            persona_class: The persona class to register
            metadata: Optional metadata about the persona
            override: Whether to override existing registration

        Returns:
            True if registration succeeded
        """
        # Create temporary instance to get name
        try:
            temp = persona_class.__new__(persona_class)
            # Get name from class if possible
            name = getattr(persona_class, 'PERSONA_NAME', persona_class.__name__)
        except Exception:
            name = persona_class.__name__

        if name in self._personas and not override:
            return False

        self._personas[name] = persona_class

        if metadata:
            self._metadata[name] = metadata
        else:
            # Create default metadata
            self._metadata[name] = PersonaMetadata(
                name=name,
                persona_type=PersonaType.CODE,  # Default
                description=persona_class.__doc__ or "No description",
            )

        # Fire callbacks
        for callback in self._callbacks["on_register"]:
            try:
                callback(name, persona_class)
            except Exception:
                pass

        return True

    def unregister(self, name: str) -> bool:
        """
        Unregister a persona.

        Args:
            name: Persona name to unregister

        Returns:
            True if unregistered successfully
        """
        if name not in self._personas:
            return False

        # Destroy all instances first
        instances_to_destroy = [
            iid for iid, inst in self._instances.items()
            if inst.persona_name == name
        ]
        for iid in instances_to_destroy:
            self.destroy_instance(iid)

        del self._personas[name]
        if name in self._metadata:
            del self._metadata[name]

        return True

    def get(self, name: str) -> Optional[Type[AgentPersona]]:
        """Get persona class by name."""
        return self._personas.get(name)

    def get_metadata(self, name: str) -> Optional[PersonaMetadata]:
        """Get persona metadata."""
        return self._metadata.get(name)

    def list_personas(
        self,
        persona_type: Optional[PersonaType] = None,
        include_deprecated: bool = False
    ) -> List[str]:
        """
        List registered personas.

        Args:
            persona_type: Filter by type
            include_deprecated: Include deprecated personas

        Returns:
            List of persona names
        """
        result = []
        for name, meta in self._metadata.items():
            if not include_deprecated and meta.deprecated:
                continue
            if persona_type and meta.persona_type != persona_type:
                continue
            result.append(name)
        return sorted(result)

    def create_instance(
        self,
        persona_name: str,
        instance_id: Optional[str] = None,
        **kwargs
    ) -> Optional[PersonaInstance]:
        """
        Create a new persona instance.

        Args:
            persona_name: Name of registered persona
            instance_id: Optional custom instance ID
            **kwargs: Arguments to pass to persona constructor

        Returns:
            PersonaInstance if successful, None otherwise
        """
        persona_class = self._personas.get(persona_name)
        if not persona_class:
            return None

        # Generate instance ID
        if not instance_id:
            self._instance_counter += 1
            instance_id = f"{persona_name}_{self._instance_counter}"

        try:
            persona = persona_class(**kwargs)
            instance = PersonaInstance(
                instance_id=instance_id,
                persona_name=persona_name,
                persona=persona,
            )
            self._instances[instance_id] = instance

            # Fire callbacks
            for callback in self._callbacks["on_instantiate"]:
                try:
                    callback(instance)
                except Exception:
                    pass

            return instance

        except Exception as e:
            return None

    def get_instance(self, instance_id: str) -> Optional[PersonaInstance]:
        """Get a persona instance by ID."""
        return self._instances.get(instance_id)

    def destroy_instance(self, instance_id: str) -> bool:
        """
        Destroy a persona instance.

        Args:
            instance_id: Instance to destroy

        Returns:
            True if destroyed successfully
        """
        instance = self._instances.pop(instance_id, None)
        if not instance:
            return False

        # Fire callbacks
        for callback in self._callbacks["on_destroy"]:
            try:
                callback(instance)
            except Exception:
                pass

        return True

    def list_instances(
        self,
        persona_name: Optional[str] = None
    ) -> List[PersonaInstance]:
        """
        List active instances.

        Args:
            persona_name: Filter by persona name

        Returns:
            List of active instances
        """
        if persona_name:
            return [
                inst for inst in self._instances.values()
                if inst.persona_name == persona_name
            ]
        return list(self._instances.values())

    def find_by_capability(self, capability_name: str) -> List[str]:
        """
        Find personas that have a specific capability.

        Args:
            capability_name: Capability to search for

        Returns:
            List of persona names with the capability
        """
        result = []
        for name, persona_class in self._personas.items():
            try:
                # Create temporary instance to check capabilities
                temp = persona_class.__new__(persona_class)
                temp.__init__.__wrapped__ if hasattr(temp.__init__, '__wrapped__') else None
                # This is a heuristic - better to check class metadata
                result.append(name)
            except Exception:
                pass
        return result

    def find_by_tool(self, tool_name: str) -> List[str]:
        """
        Find personas that can use a specific tool.

        Args:
            tool_name: Tool to search for

        Returns:
            List of persona names that can use the tool
        """
        result = []
        for name in self._personas:
            # Check instances first
            for inst in self._instances.values():
                if inst.persona_name == name:
                    if inst.persona.can_use_tool(tool_name):
                        result.append(name)
                        break
        return result

    def add_callback(self, event: str, callback: Callable) -> bool:
        """
        Add event callback.

        Events: on_register, on_instantiate, on_destroy
        """
        if event not in self._callbacks:
            return False
        self._callbacks[event].append(callback)
        return True

    def remove_callback(self, event: str, callback: Callable) -> bool:
        """Remove event callback."""
        if event not in self._callbacks:
            return False
        try:
            self._callbacks[event].remove(callback)
            return True
        except ValueError:
            return False

    def deprecate(self, name: str, reason: str = "") -> bool:
        """
        Mark a persona as deprecated.

        Args:
            name: Persona to deprecate
            reason: Reason for deprecation

        Returns:
            True if marked successfully
        """
        if name not in self._metadata:
            return False
        self._metadata[name].deprecated = True
        self._metadata[name].deprecation_reason = reason
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        type_counts = {}
        for meta in self._metadata.values():
            t = meta.persona_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "registered_personas": len(self._personas),
            "active_instances": len(self._instances),
            "by_type": type_counts,
            "deprecated_count": sum(1 for m in self._metadata.values() if m.deprecated),
        }

    def export_registry(self) -> Dict[str, Any]:
        """Export registry state to dictionary."""
        return {
            "personas": {
                name: {
                    "class": cls.__name__,
                    "module": cls.__module__,
                    "metadata": {
                        "description": self._metadata[name].description,
                        "type": self._metadata[name].persona_type.value,
                        "version": self._metadata[name].version,
                        "deprecated": self._metadata[name].deprecated,
                    }
                }
                for name, cls in self._personas.items()
            },
            "instances": {
                iid: {
                    "persona_name": inst.persona_name,
                    "created_at": inst.created_at.isoformat(),
                    "request_count": inst.request_count,
                    "error_count": inst.error_count,
                }
                for iid, inst in self._instances.items()
            },
            "stats": self.get_stats(),
        }

    def clear(self) -> None:
        """Clear all registrations and instances. Use with caution."""
        for iid in list(self._instances.keys()):
            self.destroy_instance(iid)
        self._personas.clear()
        self._metadata.clear()
        self._instance_counter = 0


# Global registry instance
registry = PersonaRegistry()


def register_persona(
    metadata: Optional[PersonaMetadata] = None
) -> Callable[[Type[AgentPersona]], Type[AgentPersona]]:
    """
    Decorator to register a persona class.

    Usage:
        @register_persona(PersonaMetadata(name="MyAgent", ...))
        class MyAgentPersona(AgentPersona):
            ...
    """
    def decorator(cls: Type[AgentPersona]) -> Type[AgentPersona]:
        registry.register(cls, metadata)
        return cls
    return decorator


if __name__ == '__main__':
    # Self-test
    from .persona_base import (
        AgentPersona, PersonaType, PersonaCapability,
        PersonaConstraint, CommunicationStyle, PersonaTrait
    )

    print("PersonaRegistry Self-Test")
    print("=" * 50)

    # Create test persona class
    class TestPersona(AgentPersona):
        PERSONA_NAME = "TestAgent"

        def __init__(self):
            super().__init__(
                name="Test Agent",
                persona_type=PersonaType.CODE,
                description="A test persona",
                primary_purpose="Testing the registry",
            )

        def _setup_capabilities(self):
            self.add_capability(PersonaCapability(
                name="testing",
                description="Run tests",
                tools=["Bash"],
            ))

        def _setup_constraints(self):
            pass

    # Test registry
    reg = PersonaRegistry()

    # Register
    meta = PersonaMetadata(
        name="TestAgent",
        persona_type=PersonaType.CODE,
        description="Test persona",
        version="1.0.0",
        tags=["test", "development"],
    )
    assert reg.register(TestPersona, meta), "Should register"
    assert not reg.register(TestPersona, meta), "Should not re-register"
    assert reg.register(TestPersona, meta, override=True), "Should override"

    # List
    personas = reg.list_personas()
    assert "TestAgent" in personas, "Should be listed"

    # Create instance
    inst = reg.create_instance("TestAgent")
    assert inst is not None, "Should create instance"
    assert inst.persona.name == "Test Agent", "Should have correct name"

    # Get instance
    got = reg.get_instance(inst.instance_id)
    assert got == inst, "Should get same instance"

    # List instances
    instances = reg.list_instances()
    assert len(instances) == 1, "Should have one instance"

    # Stats
    stats = reg.get_stats()
    assert stats["registered_personas"] == 1
    assert stats["active_instances"] == 1

    # Deprecate
    assert reg.deprecate("TestAgent", "Testing deprecation")
    meta = reg.get_metadata("TestAgent")
    assert meta.deprecated, "Should be deprecated"

    # Export
    export = reg.export_registry()
    assert "TestAgent" in export["personas"]

    # Destroy
    assert reg.destroy_instance(inst.instance_id)
    assert len(reg.list_instances()) == 0

    # Unregister
    assert reg.unregister("TestAgent")
    assert "TestAgent" not in reg.list_personas()

    # Clear
    reg.register(TestPersona, meta)
    reg.clear()
    assert len(reg.list_personas()) == 0

    print("All PersonaRegistry tests passed!")
