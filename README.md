# Zero-Template House Generator - AI-Assisted Blender House Synthesizer

Zero-Template House Generator is a desktop MVP I built to study how natural-language architectural briefs and structured GUI constraints can be converted into validated 3D house scenes inside Blender.

The project combines a PyQt6 desktop app, an optional AI brief interpreter, a deterministic geometry pipeline, and a compliance layer that blocks false success states. It is designed as a serious research prototype for controllable architectural generation, not as a production BIM/CAD system.

## Why I built this

Most hobby house generators break in the same way:

1. they hide a fixed template behind a few sliders
2. they ignore prompt details that do not fit the template
3. they produce scenes that "look generated" rather than architecturally coherent
4. they report success even when the scene is broken or incomplete

I wanted to build a small zero-template pipeline that can:

1. take a user brief or manual parameters
2. treat explicit user requirements as hard constraints
3. resolve them into a single authoritative scene specification
4. generate Blender geometry from that spec
5. audit the result before calling it successful

## What currently works

1. PyQt6 desktop GUI for manual house parameters and Blender execution
2. Optional AI brief interpreter with `OpenAI` or `Gemini`
3. Prompt-only hard-guard mode so unsupported extras are not silently added
4. Constraint parsing and deterministic resolution into `resolved.json`
5. Modular Blender generation pipeline for massing, openings, entrance, roof, materials, environment, props, and interior zones
6. Real boolean wall cuts for windows and doors with inset assemblies and frame depth
7. Blender 5.1-compatible background generation through `subprocess`
8. Output verification for exit code, file existence, and suspiciously small exports
9. Compliance audit against the actual built scene using `scene_report.json`
10. Export of `.blend`, `.glb`, raw input, resolved spec, scene report, and audit report

## Current supported generation behavior

The system is no longer limited to one "stretchable mansion" fallback. It currently supports multiple prompt-driven architectural directions and can route them into different geometry profiles:

1. `modern_villa`
2. `grand_estate`
3. `classic_luxury_mansion`
4. `scandinavian_barnhouse`
5. `traditional_suburban`
6. `rustic_log_cabin`
7. `cubism / shifted-block modernism`

Within those families, the pipeline already supports several important prompt-conditioned features:

1. gable, hip, and flat roofs
2. symmetry-sensitive front facades
3. L- and U-like composition logic in prompt interpretation
4. porches, lean-to porch roofs, and porch columns when explicitly requested
5. terrace, balcony, garage, fence, and selected environment props only when requested
6. material families such as stucco, brick, stone, siding, concrete, and log wood

## Implementation notes

This project was built iteratively with local debugging on Windows and repeated Blender 5.1 validation. Some important fixes already completed during development:

1. fixed multiple Blender 5.1 API compatibility issues in the materials pipeline
2. fixed false-success flow so the app no longer reports success when `.blend` / `.glb` / `scene_report.json` are missing
3. added validation so the GUI distinguishes `blender.exe` from `blender-launcher.exe`
4. fixed stale AI payload leakage by dropping AI plans that no longer match the current GUI/prompt state
5. stabilized boolean opening cuts so windows and doors are no longer simple surface decals
6. added prompt-only option gating so unrequested elements like terrace, fence, garage, pediment, or props are cleared
7. improved roof thickness, eaves/overhang handling, soffits, inset windows, and lighting so scenes stop reading like plastic mockups
8. added compliance blocking for broken scene states such as blocked openings or missing required elements

## High-level architecture

```text
[User Brief / Manual GUI Input]
            v
[Validation + Hard Constraint Capture]
            v
[AI Brief Interpreter (optional)]
            v
[Constraint Graph / Parser]
            v
[Resolver]
            v
[resolved.json = single source of truth]
            v
[Blender Runner]
            v
[Scene Builder]
 - massing
 - openings
 - entrance
 - roof
 - materials
 - environment
 - props
 - interior
            v
[scene_report.json]
            v
[Compliance Audit]
            v
[scene.blend + scene.glb + audit_report.json]
```

## Tech stack

1. Desktop app: `PyQt6`
2. Core language: `Python 3.13+`
3. 3D generation: `Blender 5.1` + `bpy`
4. AI integration: `openai`, `google-genai`
5. Validation / schemas: `pydantic`
6. Orchestration: `subprocess`, JSON artifacts

## Project structure

```text
blender-work/
|-- main.py
|-- README.md
|-- requirements.txt
|-- ai/
|   |-- __init__.py
|   |-- schema.py
|   `-- service.py
|-- app/
|   |-- __init__.py
|   |-- controller.py
|   |-- gui.py
|   `-- validators.py
|-- blender/
|   |-- __init__.py
|   `-- run_generator.py
|-- engine/
|   |-- __init__.py
|   |-- compliance.py
|   |-- constraints.py
|   |-- parser.py
|   |-- regeneration.py
|   |-- resolver.py
|   |-- space_planner.py
|   `-- specs.py
|-- generator/
|   |-- __init__.py
|   |-- asset_registry.py
|   |-- common.py
|   |-- entrance.py
|   |-- environment.py
|   |-- facade.py
|   |-- interior.py
|   |-- massing.py
|   |-- materials.py
|   |-- openings.py
|   |-- props.py
|   |-- roof.py
|   `-- scene_builder.py
`-- output/
    |-- raw_input.json
    |-- resolved.json
    |-- scene_report.json
    |-- audit_report.json
    |-- scene.blend
    |-- scene.glb
    |-- ai_design_plan.json
    |-- ai_instruction.md
    `-- ai_space_program.json
```

## Setup (Windows / PowerShell)

### Create and activate environment

```powershell
cd YOUR_PATH\blender work
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Run the system

### Start the desktop app

```powershell
python main.py
```

Important:

1. prefer `python main.py`, not `py main.py`
2. `py` may point to a global interpreter instead of `.venv`
3. select a real `blender.exe` in the UI, not `blender-launcher.exe`

## Desktop workflow

1. launch the GUI
2. set or validate the Blender executable path
3. either fill the manual controls or use `AI Design Interpreter`
4. click `AI Analyze Brief` if you want AI to convert the brief into GUI parameters
5. click `Generate Scene`
6. inspect generated files in `output/`

## AI brief interpreter

The desktop app includes an AI layer that can analyze a natural-language house brief and convert it into real generator inputs.

Supported providers:

1. `openai`
2. `gemini`

Supported AI goals:

1. `design_and_gui`
2. `space_program`

What the AI currently writes:

1. a structured architectural concept
2. a room/space program
3. valid GUI parameter suggestions
4. a Blender-oriented technical instruction

AI outputs are saved to:

1. `output/ai_design_plan.json`
2. `output/ai_instruction.md`
3. `output/ai_space_program.json`

API keys are session-only in the GUI and are not stored in settings.

Environment variables also work:

```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:GEMINI_API_KEY="your_key_here"
```

## Generation outputs

If generation succeeds, the pipeline writes:

1. `output/raw_input.json`
2. `output/resolved.json`
3. `output/scene_report.json`
4. `output/audit_report.json`
5. `output/scene.blend`
6. `output/scene.glb`

The app only reports success after:

1. Blender exits successfully
2. required output files exist
3. output files pass minimum-size checks
4. `scene_report.json` confirms the build completed
5. compliance audit returns `PASS`

## What makes this different from a toy generator

This project is explicitly trying to avoid the usual fake-control pattern:

1. `resolved.json` is the only source of truth consumed by Blender
2. GUI controls are intended to map to real geometry decisions
3. optional elements are cleared when they are not explicitly requested
4. the generator writes a report from the built scene, not from intent alone
5. compliance runs on actual scene output before success is shown

## Known limitations

1. this is still a research MVP, not a production-grade architectural authoring system
2. prompt coverage is expanding, but not every possible architectural style has a dedicated grammar yet
3. some advanced facade systems still rely on procedural approximations rather than high-end scanned texture packs
4. room planning is functional, but not yet a full architectural layout solver
5. preview rendering/export packaging is less mature than the geometry/compliance pipeline
6. environment generation is still selective and lightweight compared to full archviz scene dressing

## Next steps

1. strengthen style grammars for more prompt families without falling back to generic boxes
2. deepen room-to-facade coupling so windows are chosen directly from room semantics
3. improve roof families, gables, dormers, and complex massing for more architectural prompt coverage
4. expand asset registry and placement rules for richer but still prompt-safe environments
5. add stronger regeneration logic for localized repair when compliance fails
6. improve preview render output and portfolio-ready presentation passes

## License

Academic / research prototype.
