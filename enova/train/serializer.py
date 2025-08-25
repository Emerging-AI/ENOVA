from dataclasses import fields, MISSING
from typing import get_type_hints, Any, Dict, Type, List, Set, ClassVar
from pydantic import BaseModel, Field
from llamafactory.hparams import FinetuningArguments, ModelArguments


class SelectiveBaseModel(BaseModel):
    """Base class that allows field selection from a dataclass"""

    _source_dataclass: ClassVar[Type] = None
    _selected_fields: ClassVar[Set[str]] = set()
    _forbidden_fields: ClassVar[Set[str]] = set()

    def __init_subclass__(cls, source_dataclass: Type = None, selected_fields: List[str] = None, forbidden_fields: List[str] = None, **kwargs):
        super().__init_subclass__(**kwargs)

        if source_dataclass:
            cls._source_dataclass = source_dataclass
            cls._forbidden_fields = set(forbidden_fields or [])

            # If selected_fields is not specified, use all fields from source
            if selected_fields is None:
                all_fields = {f.name for f in fields(source_dataclass)}
                # Remove forbidden fields
                final_fields = all_fields - cls._forbidden_fields
            else:
                # Use selected fields but remove forbidden ones
                final_fields = set(selected_fields) - cls._forbidden_fields

            cls._selected_fields = final_fields
            # Dynamically add fields from dataclass
            cls._add_fields_from_dataclass(source_dataclass, list(final_fields))

    @classmethod
    def _add_fields_from_dataclass(cls, source_dataclass: Type, field_names: List[str]):
        """Add selected fields from dataclass to this model"""
        # Get all fields from the dataclass (including inherited ones)
        all_fields = {f.name: f for f in fields(source_dataclass)}
        type_hints = get_type_hints(source_dataclass)

        # Create model fields dictionary
        model_fields = {}
        annotations = {}

        for field_name in field_names:
            if field_name not in all_fields:
                # Skip fields that don't exist in the dataclass
                # This allows for forward compatibility
                continue

            dc_field = all_fields[field_name]
            field_type = type_hints[field_name]

            # Add to annotations
            annotations[field_name] = field_type

            # Extract default value
            if dc_field.default is not MISSING:
                default = dc_field.default
            elif dc_field.default_factory is not MISSING:
                default = dc_field.default_factory
            else:
                default = ...  # Required field

            # Extract metadata for Pydantic Field
            metadata = dc_field.metadata or {}
            description = metadata.get("help", None)

            # Create Pydantic field definition
            if default is ...:
                field_info = Field(description=description)
            else:
                field_info = Field(default=default, description=description)

            model_fields[field_name] = (field_type, field_info)

        # Update class annotations
        if not hasattr(cls, "__annotations__"):
            cls.__annotations__ = {}
        cls.__annotations__.update(annotations)

        # Set field info on the class
        for field_name, (field_type, field_info) in model_fields.items():
            setattr(cls, field_name, field_info)


class QuantizationConfig(
    SelectiveBaseModel,
    source_dataclass=ModelArguments,
    forbidden_fields=["adapter_name_or_path"],  # in quantization, model won't be
):
    """Configuration for model quantization settings"""

    class Config:
        """Pydantic model configuration"""

        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"
        use_enum_values = True

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return super().model_dump(**kwargs)


class FineTuningConfig(
    SelectiveBaseModel,
    source_dataclass=FinetuningArguments,
):
    """Configuration for fine-tuning settings"""

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"
        use_enum_values = True

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return super().model_dump(**kwargs)
