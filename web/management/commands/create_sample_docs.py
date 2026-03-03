# Usage: python manage.py create_sample_docs


from django.core.management.base import BaseCommand
from django.utils.text import slugify

from web.models import (
    DocumentationNoteContent,
    DocumentationNoteSection,
    DocumentationNoteTopic,
)

PROJECTILE_MOTION_CONTENT = {
    "title": "Projectile Motion",
    "description": "A comprehensive guide to understanding projectile motion, from basic concepts to real-world applications.",
    "sections": [
        {
            "title": "Introduction",
            "description": "Understand what projectile motion is and its basic principles",
            "content": """# Introduction to Projectile Motion

Projectile motion is a form of motion experienced by an object or particle that is projected near Earth's surface and moves along a curved path under the influence of gravity.

## Key Concepts

- **Projectile**: An object that moves in two dimensions under the influence of gravity
- **Trajectory**: The curved path followed by the projectile
- **Initial Velocity**: The velocity at which the projectile is launched
- **Angle of Projection**: The angle at which the projectile is launched relative to the horizontal

## Assumptions

In projectile motion, we typically assume:

1. Air resistance is negligible
2. The effect of Earth's rotation is negligible
3. The acceleration due to gravity is constant (g ≈ 9.8 m/s²)
4. The motion is analyzed in a vertical plane

## Applications

Projectile motion can be observed in:
- Sports (baseball, basketball, golf)
- Military applications
- Fireworks
- Fountains
- Rocket trajectories
""",
        },
        {
            "title": "Equations of Motion",
            "description": "Mathematical representations of projectile motion",
            "content": """# Equations of Motion for Projectile Motion

## Components of Velocity

For a projectile launched with initial velocity $v_0$ at angle $\\theta$ to the horizontal:

**Horizontal component:**
$$v_x = v_0 \\cos(\\theta)$$

**Vertical component:**
$$v_y = v_0 \\sin(\\theta)$$

## Position Equations

At time $t$:

**Horizontal position:**
$$x(t) = v_0 \\cos(\\theta) \\cdot t$$

**Vertical position:**
$$y(t) = v_0 \\sin(\\theta) \\cdot t - \\frac{1}{2}gt^2$$

Where $g = 9.8 \\text{ m/s}^2$

## Velocity Equations

At time $t$:

**Horizontal velocity:**
$$v_x(t) = v_0 \\cos(\\theta)$$ (constant)

**Vertical velocity:**
$$v_y(t) = v_0 \\sin(\\theta) - gt$$

## Special Cases

### When launched horizontally ($\\theta = 0°$)
- $x(t) = v_0 t$
- $y(t) = -\\frac{1}{2}gt^2$

### When launched vertically ($\\theta = 90°$)
- $x(t) = 0$
- $y(t) = v_0 t - \\frac{1}{2}gt^2$
""",
        },
        {
            "title": "Derivation",
            "description": "Step-by-step derivation of projectile motion equations",
            "content": """# Derivation of Projectile Motion Equations

## Starting from Newton's Laws

Newton's second law states: $\\vec{F} = m\\vec{a}$

For projectile motion, the only force acting is gravity (downward):
- $F_x = 0$ → $a_x = 0$ (no acceleration in horizontal direction)
- $F_y = -mg$ → $a_y = -g$ (constant acceleration downward)

## Horizontal Motion (Uniform)

Since $a_x = 0$:

$$v_x = v_{0x} = v_0 \\cos(\\theta) = \\text{constant}$$

Integrating for position:
$$x(t) = v_{0x} \\cdot t = v_0 \\cos(\\theta) \\cdot t$$

## Vertical Motion (Uniformly Accelerated)

Since $a_y = -g$:

Using $v = u + at$:
$$v_y(t) = v_{0y} - gt = v_0 \\sin(\\theta) - gt$$

Using $s = ut + \\frac{1}{2}at^2$:
$$y(t) = v_{0y} \\cdot t - \\frac{1}{2}gt^2 = v_0 \\sin(\\theta) \\cdot t - \\frac{1}{2}gt^2$$

## Trajectory Equation

To find the equation of path, eliminate $t$:

$$t = \\frac{x}{v_0 \\cos(\\theta)}$$

Substitute in $y$ equation:

$$y = v_0 \\sin(\\theta) \\cdot \\frac{x}{v_0 \\cos(\\theta)} - \\frac{1}{2}g\\left(\\frac{x}{v_0 \\cos(\\theta)}\\right)^2$$

$$y = x \\tan(\\theta) - \\frac{gx^2}{2v_0^2 \\cos^2(\\theta)}$$

This is a **parabola**!

## Range Formula

The range $R$ is the horizontal distance when $y = 0$:

$$R = \\frac{v_0^2 \\sin(2\\theta)}{g}$$

**Maximum range** occurs at $\\theta = 45°$: $R_{max} = \\frac{v_0^2}{g}$

## Maximum Height

The maximum height $H$ occurs when $v_y = 0$:

$$H = \\frac{v_0^2 \\sin^2(\\theta)}{2g}$$
""",
        },
        {
            "title": "Graphical Interpretation",
            "description": "Visual representation of projectile motion",
            "content": """# Graphical Interpretation of Projectile Motion

## Trajectory Graph

The path of a projectile is a **parabola**. Key features:

```
         Maximum Height
                ↑
         y      │    /‾‾‾‾‾‾
         │      │   /        ‾‾\\
         │      │  /           ‾‾
         │      │ /
         │      │/
    ─────┴──────┴─────────────→ x
         0    Initial           Range
              Point
```

- The trajectory is symmetric about the maximum height
- The parabola is wider for larger launch angles (up to 45°)
- Higher initial velocities produce larger ranges

## Velocity Vector Diagram

The velocity vector changes direction throughout the flight:

```
    At Launch              At Maximum Height      At Landing
    (angle θ)             (horizontal v_y = 0)   (angle -θ)

       v ↗                    v →                  v ↘
      / │                     │                   │ /
     /  │v_y                  │v_x                │
    /   │                     │                   │
   /    │                     │                   │
  ← v_x →                     │                  ← v_x →
```

## Position vs Time Graphs

### Horizontal Position vs Time
```
x
│
│    /
│   /
│  /
│ /
└─────→ t
(Linear: x = v₀cos(θ)·t)
```

### Vertical Position vs Time
```
y
│    /‾‾‾‾‾
│   /      ‾‾
│  /         ‾‾
│ /            ‾‾\
│_______________  ‾ → t
(Parabolic: y = v₀sin(θ)·t - ½gt²)
```

### Vertical Velocity vs Time
```
v_y
│
│   ╱‾‾‾‾
│  ╱      ─── v_x (constant)
│ ╱
│         ╲
│          ╲
└──────────  ╲─ → t

(Linear: v_y = v₀sin(θ) - gt)
```
""",
        },
        {
            "title": "Real-world Applications",
            "description": "Practical applications of projectile motion",
            "content": """# Real-world Applications of Projectile Motion

## Sports

### Basketball
- Players must calculate the projection angle and initial velocity to make accurate shots
- Arc of the ball follows projectile motion
- Professional players develop intuition for the correct launch angle

### Golf
- Golfers optimize launch angle to maximize distance while accounting for spin
- Wind resistance (air drag) significantly affects the trajectory
- The 45° angle maximizes distance in ideal conditions

### Baseball
- Outfielders use projectile motion to intercept fly balls
- The angle of the hit determines whether it's a home run or an easy out
- Spin on the ball causes deviation from ideal parabolic path

## Military Applications

### Artillery
- Gunners calculate firing angle and muzzle velocity for target accuracy
- Range tables use projectile motion equations
- Wind and air resistance are critical factors

### Rocket Launches
- Initial launch angle and velocity are critical for payload delivery
- Atmospheric effects become important at high altitudes

## Other Examples

### Water Fountains
- Fountain designers use projectile motion to create aesthetic water patterns
- Multiple projectiles at different angles create complex designs

### Fireworks
- Launch angle and initial velocity determine burst location
- Multiple projectiles create coordinated explosions

### Construction
- Materials thrown during demolition follow projectile paths
- Safety zones are calculated based on projectile motion equations

## Real-world Complications

In practice, several factors complicate ideal projectile motion:

1. **Air Resistance**: Opposes motion and reduces range
2. **Wind**: Affects horizontal motion
3. **Spin**: Causes Magnus effect (curves the trajectory)
4. **Rotation of Earth**: Significant for long-range military applications
5. **Curvature of Earth**: Important for space missions
6. **Variable Gravity**: Gravity changes with altitude

## Example Calculation

A ball is thrown from ground level at 20 m/s at 45° angle:

**Given:**
- $v_0 = 20$ m/s
- $\\theta = 45°$
- $g = 9.8$ m/s²

**Maximum Height:**
$$H = \\frac{v_0^2 \\sin^2(\\theta)}{2g} = \\frac{400 \\times 0.5}{19.6} ≈ 10.2 \\text{ m}$$

**Range:**
$$R = \\frac{v_0^2 \\sin(2\\theta)}{g} = \\frac{400 \\times 1}{9.8} ≈ 40.8 \\text{ m}$$

**Flight Time:**
$$t = \\frac{2v_0 \\sin(\\theta)}{g} = \\frac{2 \\times 20 \\times 0.707}{9.8} ≈ 2.88 \\text{ s}$$
""",
        },
        {
            "title": "Practice Problems",
            "description": "Test your understanding with practice problems",
            "content": """# Practice Problems: Projectile Motion

## Difficulty Level: Easy

### Problem 1.1
A ball is thrown horizontally from a building 45 m tall with an initial velocity of 15 m/s.

**Find:**
- a) Time of flight
- b) Horizontal distance traveled
- c) Final velocity

**Solution:**

a) Using $y = h - \\frac{1}{2}gt^2$:
$$0 = 45 - \\frac{1}{2}(9.8)t^2$$
$$t = \\sqrt{\\frac{2 \\times 45}{9.8}} ≈ 3.03 \\text{ s}$$

b) $x = v_0 t = 15 \\times 3.03 ≈ 45.5 \\text{ m}$

c) $v_y = gt = 9.8 \\times 3.03 ≈ 29.7$ m/s
   $v = \\sqrt{v_x^2 + v_y^2} = \\sqrt{15^2 + 29.7^2} ≈ 33.0$ m/s

---

## Difficulty Level: Medium

### Problem 2.1
A projectile is launched at 30° with initial velocity 40 m/s.

**Find:**
- a) Maximum height
- b) Range
- c) Time to reach maximum height

**Solution:**

a) $H = \\frac{v_0^2 \\sin^2(\\theta)}{2g} = \\frac{1600 \\times 0.25}{19.6} ≈ 20.4$ m

b) $R = \\frac{v_0^2 \\sin(2\\theta)}{g} = \\frac{1600 \\times 0.866}{9.8} ≈ 141.3$ m

c) $t = \\frac{v_0 \\sin(\\theta)}{g} = \\frac{40 \\times 0.5}{9.8} ≈ 2.04$ s

---

## Difficulty Level: Hard

### Problem 3.1
A cannon fires a projectile from ground level at 50 m/s. An obstacle 2 m high is located 80 m away.

**Find the range of launch angles to clear the obstacle.**

This requires solving the trajectory equation with constraints.

---

## Challenge Problem

A basketball player shoots from 2 m away at a basket 3.05 m high (2 m above ground). The ball leaves the player's hands at 2.1 m height with speed 8 m/s.

**What launch angle(s) will result in a basket?**

This requires the ball to pass through the point (2 m, 3.05 m) relative to launch point.

---

## Answers Summary

| Problem | Part | Answer |
|---------|------|--------|
| 1.1 | a) | 3.03 s |
| 1.1 | b) | 45.5 m |
| 1.1 | c) | 33.0 m/s |
| 2.1 | a) | 20.4 m |
| 2.1 | b) | 141.3 m |
| 2.1 | c) | 2.04 s |
""",
        },
    ],
}


class Command(BaseCommand):
    help = "Create sample documentation notes for testing and demonstration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete existing sample documentation notes first",
        )

    def handle(self, *args, **options):
        if options["delete"]:
            self.stdout.write("Deleting existing sample documentation notes...")
            DocumentationNoteTopic.objects.filter(slug="projectile-motion").delete()

        self.stdout.write("Creating sample documentation notes...")
        self.create_projectile_motion_topic()

        self.stdout.write(self.style.SUCCESS("Successfully created sample documentation notes!"))

    def create_projectile_motion_topic(self):
        """Create the Projectile Motion documentation topic with all sections"""

        # Create topic
        topic, created = DocumentationNoteTopic.objects.get_or_create(
            slug="projectile-motion",
            defaults={
                "title": PROJECTILE_MOTION_CONTENT["title"],
                "description": PROJECTILE_MOTION_CONTENT["description"],
                "icon": "beaker",
                "color": "blue",
                "order": 1,
                "is_published": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created topic: {topic.title}"))
        else:
            self.stdout.write(f"  Topic already exists: {topic.title}")

        # Create sections and content
        for index, section_data in enumerate(PROJECTILE_MOTION_CONTENT["sections"]):
            section, section_created = DocumentationNoteSection.objects.get_or_create(
                topic=topic,
                slug=slugify(section_data["title"]),
                defaults={
                    "title": section_data["title"],
                    "description": section_data["description"],
                    "order": index,
                    "icon": "",
                },
            )

            if section_created:
                self.stdout.write(f"  ✓ Created section: {section.title}")
            else:
                self.stdout.write(f"    Section already exists: {section.title}")

            # Create or update content
            content, content_created = DocumentationNoteContent.objects.get_or_create(
                section=section,
                defaults={
                    "markdown_content": section_data["content"],
                },
            )

            if content_created:
                self.stdout.write(f"    ✓ Created content for: {section.title}")
            else:
                self.stdout.write(f"      Content already exists for: {section.title}")
