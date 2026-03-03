# Contributing to Virtual Robotics Playground

Thank you for your interest in contributing to Alpha One Labs' Virtual Robotics Playground! This guide will help you get started.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the project goals
- Help others learn and grow

Harassment or discriminatory behavior will not be tolerated.

---

## 🤔 How to Contribute

### **Ways to Contribute**

1. **Report Bugs** — Found an issue? Open a bug report
2. **Suggest Features** — Have an idea? Create a feature request
3. **Fix Issues** — Browse open issues and submit PRs
4. **Improve Documentation** — Fix typos, add examples, clarify instructions
5. **Add Components** — Build new robot parts or sensors

### **Good First Issues**

Look for issues labeled `good first issue` — these are perfect for newcomers!

---

## 🛠️ Development Setup

### **Prerequisites**

- Git
- A modern web browser (Chrome, Firefox, Safari, or Edge)
- Text editor (VS Code recommended)
- Python 3 (optional, for local server)

### **Setup Steps**

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/alphaonelabs-virtual-robotics-playground.git
cd alphaonelabs-virtual-robotics-playground

# 3. Add upstream remote
git remote add upstream https://github.com/alphaonelabs/alphaonelabs-virtual-robotics-playground.git

# 4. (Optional) Start local server
python3 -m http.server 8000

# 5. Open in browser
# Direct: Open index.html in your browser
# Server: Visit http://localhost:8000
```

---

## ✏️ Making Changes

### **Step 1: Create a Branch**

```bash
# Get latest changes
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### **Step 2: Make Your Changes**

- Edit `index.html` for landing page changes
- Edit `home.html` for simulator changes
- Test thoroughly in multiple browsers

### **Step 3: Test Your Changes**

**Manual Testing Checklist:**

- [ ] Landing page loads without errors
- [ ] "Enter System" button navigates to `home.html`
- [ ] Chassis can be added
- [ ] Other components require chassis first
- [ ] WASD movement works smoothly
- [ ] Robot respects canvas boundaries
- [ ] Camera view renders correctly (if camera added)
- [ ] Arm picks and drops blocks (if arm added)
- [ ] Settings sliders update robot behavior
- [ ] No console errors (F12 → Console)
- [ ] Responsive design works (resize window)

**Browser Testing:**

Test in at least **two** of these browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

---

## 🔄 Pull Request Process

### **Before Submitting**

1. Test your changes in at least 2 browsers
2. Check for console errors (`F12` → Console)
3. Verify responsive design (resize window)
4. Write clear commit messages (see below)

### **Submit PR**

```bash
# Commit your changes
git add .
git commit -m "feat: add new robot sensor"

# Push to your fork
git push origin feature/your-feature-name
```

**Then:**

1. Go to GitHub
2. Click **"Compare & pull request"**
3. Fill out the PR template:
   - **Title:** Use conventional commit format (see below)
   - **Description:** Explain what and why
   - **Screenshots:** Add if UI changed
4. Submit!

### **PR Title Format**

```
type: brief description
```

**Examples:**
```
feat: add gripper strength control
fix: correct camera FOV rendering
docs: update installation instructions
style: format home.html consistently
refactor: simplify physics calculations
```

---

## 💻 Coding Standards

### **HTML**

```html
<!-- Use semantic HTML5 elements -->
<section class="simulator">
  <canvas id="sim-canvas"></canvas>
</section>

<!-- Add ARIA labels for accessibility -->
<canvas role="img" aria-label="Robot simulation canvas"></canvas>

<!-- Keep structure clean and indented -->
```

### **CSS (Tailwind)**

```html
<!-- Prefer Tailwind utility classes -->
<button class="bg-teal-700 hover:bg-teal-600 p-2 rounded text-white">
  Add Chassis
</button>

<!-- Custom styles in <style> tag if needed -->
<style>
  .custom-animation {
    animation: fadeIn 0.6s ease-out;
  }
</style>
```

### **JavaScript**

```javascript
// Use modern ES6+ syntax
const robot = {
  x: 0,
  y: 0,
  speed: 0
};

// Add comments for complex logic
function updatePhysics() {
  // Calculate velocity based on motor power
  const velocity = motorPower / 400;
  robot.speed += velocity;
}

// Use meaningful variable names
const isChassisAdded = robot.parts.chassis;

// Prefer const over let
const maxSpeed = 10;
let currentSpeed = 0;
```

### **General Style**

- Use **2 spaces** for indentation
- Use **single quotes** for strings
- Add **semicolons**
- Keep functions small and focused
- Comment complex logic

---

## 📝 Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### **Format**

```
type: description

[optional body]
```

### **Types**

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code formatting (no logic change) |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Adding tests |
| `chore` | Build/tooling changes |

### **Examples**

```bash
feat: add gripper strength slider
fix: correct camera FOV calculation at canvas edges
docs: update browser compatibility table
style: format home.html with consistent indentation
refactor: simplify collision detection logic
perf: reduce particle count for better mobile performance
```

---

## 🐛 Reporting Bugs

**Use this template:**

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - Browser: [e.g. Chrome 120]
 - OS: [e.g. Windows 11, macOS 14]
```

---

## 💡 Feature Requests

**Use this template:**

```markdown
**Is your feature related to a problem?**
A clear description of the problem.

**Describe the solution**
How you'd like it to work.

**Additional context**
Any other information or mockups.
```

---

## ❓ Questions?

- **GitHub Issues:** For bug reports and feature requests
- **GitHub Discussions:** For questions and general ideas
- **Email:** contact@alphaonelabs.org

---

**Thank you for contributing! 🚀**

Every contribution, no matter how small, helps make this project better.

---

*Alpha One Labs — Advancing open science through education and robotics.*