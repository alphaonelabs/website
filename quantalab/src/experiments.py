"""
Experiment catalogue for QuantaLab.

Each experiment is a plain dict so it can be JSON-serialised easily.
The 'parameters' list describes the knobs students can adjust.
"""

EXPERIMENTS: dict[str, list[dict]] = {
    "physics": [
        {
            "id": "pendulum",
            "title": "Simple Pendulum",
            "description": (
                "Investigate how the length of a pendulum affects its period of oscillation. "
                "Observe simple harmonic motion and measure gravitational acceleration."
            ),
            "parameters": [
                {
                    "id": "length",
                    "label": "Length (m)",
                    "min": 0.1,
                    "max": 3.0,
                    "default": 1.0,
                    "step": 0.1,
                },
                {
                    "id": "gravity",
                    "label": "Gravity (m/s²)",
                    "min": 1.0,
                    "max": 25.0,
                    "default": 9.81,
                    "step": 0.1,
                },
                {
                    "id": "angle",
                    "label": "Release Angle (°)",
                    "min": 5,
                    "max": 45,
                    "default": 15,
                    "step": 1,
                },
            ],
            "learning_objectives": [
                "Understand the relationship between pendulum length and period.",
                "Apply the formula T = 2π√(L/g).",
                "Observe conservation of mechanical energy.",
            ],
        },
        {
            "id": "projectile",
            "title": "Projectile Motion",
            "description": (
                "Launch a projectile and explore how launch angle and initial speed "
                "determine range, maximum height, and flight time."
            ),
            "parameters": [
                {
                    "id": "speed",
                    "label": "Initial Speed (m/s)",
                    "min": 5,
                    "max": 50,
                    "default": 20,
                    "step": 1,
                },
                {
                    "id": "angle",
                    "label": "Launch Angle (°)",
                    "min": 1,
                    "max": 89,
                    "default": 45,
                    "step": 1,
                },
                {
                    "id": "gravity",
                    "label": "Gravity (m/s²)",
                    "min": 1.0,
                    "max": 25.0,
                    "default": 9.81,
                    "step": 0.1,
                },
            ],
            "learning_objectives": [
                "Decompose velocity into horizontal and vertical components.",
                "Understand why 45° maximises range under ideal conditions.",
                "Explore projectile motion on other planets by varying gravity.",
            ],
        },
        {
            "id": "ohms_law",
            "title": "Ohm's Law",
            "description": (
                "Build a virtual circuit and discover the relationship between "
                "voltage, current, and resistance: V = IR."
            ),
            "parameters": [
                {
                    "id": "voltage",
                    "label": "Voltage (V)",
                    "min": 1,
                    "max": 24,
                    "default": 9,
                    "step": 1,
                },
                {
                    "id": "resistance",
                    "label": "Resistance (Ω)",
                    "min": 10,
                    "max": 1000,
                    "default": 100,
                    "step": 10,
                },
            ],
            "learning_objectives": [
                "Understand V = IR.",
                "Read a simulated ammeter and voltmeter.",
                "Predict how changing one variable affects the others.",
            ],
        },
    ],
    "chemistry": [
        {
            "id": "acid_base",
            "title": "Acid–Base Reactions",
            "description": (
                "Add acids or bases to a solution and watch the pH change in real time. "
                "Observe the colour of universal indicator across the pH scale."
            ),
            "parameters": [
                {
                    "id": "initial_ph",
                    "label": "Initial pH",
                    "min": 1,
                    "max": 14,
                    "default": 7,
                    "step": 0.5,
                },
                {
                    "id": "drops",
                    "label": "Drops Added",
                    "min": 1,
                    "max": 20,
                    "default": 5,
                    "step": 1,
                },
                {
                    "id": "concentration",
                    "label": "Reagent Strength",
                    "min": 0.1,
                    "max": 1.0,
                    "default": 0.5,
                    "step": 0.1,
                },
            ],
            "learning_objectives": [
                "Define acids, bases, and neutral solutions.",
                "Interpret the pH scale (1–14).",
                "Predict indicator colours for a given pH.",
            ],
        },
        {
            "id": "boyles_law",
            "title": "Boyle's Law",
            "description": (
                "Compress or expand a gas syringe and observe how pressure changes "
                "at constant temperature: PV = constant."
            ),
            "parameters": [
                {
                    "id": "volume",
                    "label": "Volume (L)",
                    "min": 0.5,
                    "max": 5.0,
                    "default": 2.0,
                    "step": 0.1,
                },
                {
                    "id": "initial_pressure",
                    "label": "Initial Pressure (atm)",
                    "min": 0.5,
                    "max": 4.0,
                    "default": 1.0,
                    "step": 0.1,
                },
            ],
            "learning_objectives": [
                "State Boyle's Law and its conditions.",
                "Perform PV calculations.",
                "Plot a pressure–volume graph.",
            ],
        },
        {
            "id": "titration",
            "title": "Acid–Base Titration",
            "description": (
                "Perform a virtual titration: add a base solution drop by drop to an acid "
                "until the equivalence point is reached."
            ),
            "parameters": [
                {
                    "id": "acid_volume",
                    "label": "Acid Volume (mL)",
                    "min": 10,
                    "max": 50,
                    "default": 25,
                    "step": 5,
                },
                {
                    "id": "acid_concentration",
                    "label": "Acid Concentration (mol/L)",
                    "min": 0.1,
                    "max": 1.0,
                    "default": 0.1,
                    "step": 0.05,
                },
                {
                    "id": "base_concentration",
                    "label": "Base Concentration (mol/L)",
                    "min": 0.1,
                    "max": 1.0,
                    "default": 0.1,
                    "step": 0.05,
                },
            ],
            "learning_objectives": [
                "Define the equivalence point.",
                "Calculate the concentration of an unknown solution.",
                "Understand the use of an indicator in titration.",
            ],
        },
    ],
    "biology": [
        {
            "id": "mitosis",
            "title": "Cell Division — Mitosis",
            "description": (
                "Step through the phases of mitosis: prophase, metaphase, anaphase, "
                "and telophase. Observe chromosome behaviour at each stage."
            ),
            "parameters": [
                {
                    "id": "speed",
                    "label": "Animation Speed",
                    "min": 0.5,
                    "max": 3.0,
                    "default": 1.0,
                    "step": 0.5,
                },
            ],
            "learning_objectives": [
                "Name and describe each phase of mitosis.",
                "Explain the role of spindle fibres.",
                "Distinguish mitosis from meiosis.",
            ],
        },
        {
            "id": "natural_selection",
            "title": "Natural Selection",
            "description": (
                "Simulate a population of organisms with varying traits competing "
                "for limited resources. Watch how traits spread over generations."
            ),
            "parameters": [
                {
                    "id": "population",
                    "label": "Population Size",
                    "min": 10,
                    "max": 100,
                    "default": 40,
                    "step": 10,
                },
                {
                    "id": "mutation_rate",
                    "label": "Mutation Rate (%)",
                    "min": 0,
                    "max": 30,
                    "default": 5,
                    "step": 1,
                },
                {
                    "id": "generations",
                    "label": "Generations",
                    "min": 5,
                    "max": 50,
                    "default": 20,
                    "step": 5,
                },
            ],
            "learning_objectives": [
                "Define natural selection.",
                "Identify selective pressure in a population.",
                "Predict how allele frequencies change over generations.",
            ],
        },
        {
            "id": "photosynthesis",
            "title": "Photosynthesis",
            "description": (
                "Vary light intensity, CO₂ concentration, and temperature to see "
                "how they affect the rate of photosynthesis in a simulated aquatic plant."
            ),
            "parameters": [
                {
                    "id": "light",
                    "label": "Light Intensity (%)",
                    "min": 0,
                    "max": 100,
                    "default": 50,
                    "step": 5,
                },
                {
                    "id": "co2",
                    "label": "CO₂ Concentration (%)",
                    "min": 0.01,
                    "max": 1.0,
                    "default": 0.04,
                    "step": 0.01,
                },
                {
                    "id": "temperature",
                    "label": "Temperature (°C)",
                    "min": 5,
                    "max": 40,
                    "default": 25,
                    "step": 1,
                },
            ],
            "learning_objectives": [
                "Write the overall equation for photosynthesis.",
                "Identify limiting factors.",
                "Describe the effect of each variable on reaction rate.",
            ],
        },
    ],
}


def get_all_experiments() -> dict[str, list[dict]]:
    """Return the full experiment catalogue."""
    return EXPERIMENTS


def get_experiment(domain: str, experiment_id: str) -> dict | None:
    """Return a single experiment dict, or None if not found."""
    for exp in EXPERIMENTS.get(domain, []):
        if exp["id"] == experiment_id:
            return exp
    return None


def list_domains() -> list[str]:
    """Return the list of available science domains."""
    return list(EXPERIMENTS.keys())
