__all__ = ["AIInterpretationResult", "generate_house_plan"]


def __getattr__(name: str):
    if name in __all__:
        from ai.service import AIInterpretationResult, generate_house_plan

        exported = {
            "AIInterpretationResult": AIInterpretationResult,
            "generate_house_plan": generate_house_plan,
        }
        return exported[name]
    raise AttributeError(f"module 'ai' has no attribute {name!r}")
