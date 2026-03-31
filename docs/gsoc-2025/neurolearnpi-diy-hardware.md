# 🧠 NeuroLearnPi: DIY Hardware Edition

## GSoC 2025 Project Idea

---

## 🔧 1. Hardware Overview

We'll build a basic EEG system using:

- Dry or gel-based scalp electrodes
- Signal amplification and filtering
- Analog-to-Digital Converter (ADC)
- Data transfer via SPI/I2C to Raspberry Pi

### 🎯 Goal

- Real-time EEG acquisition from 1–4 channels
- At least 250Hz sampling rate
- Safe, low-noise, low-voltage design
- Usable with children and students

---

## 📦 2. Bill of Materials (BOM)

| Component | Description | Qty | Est. Cost (USD) | Source |
|-----------|-------------|-----|-----------------|--------|
| Raspberry Pi 4 (4GB or 8GB) | Main processor | 1 | $55–75 | Amazon |
| microSD Card (16GB+) | OS and software | 1 | $8 | - |
| ADS1299 (EEG ADC) | 8-channel 24-bit ADC used in EEG | 1 | $60–90 | AliExpress / DIYmall |
| DRL Circuit | Right-leg drive for common noise rejection | 1 | ~$10 (can be built) | DIY |
| Electrodes (gel or dry) | EEG electrode sets | 3–4 | $10–25 | Amazon |
| INA333 or AD8232 | Instrumentation amplifier | 2–4 | $5–10 each | Digikey |
| Resistors, capacitors | For filters + gain | — | $10 | - |
| Perfboard or custom PCB | Mounting electronics | 1 | $5–20 | - |
| Battery Pack (5V) | To isolate power supply | 1 | $15 | Amazon |

💡 **Optional**: Consider ESD protection + low-pass filters if deploying to schools.

---

## 🛠️ 3. Hardware Architecture

```
[ Electrodes ]
     ↓
[ Instrumentation Amplifier (INA333 or AD8232) ]
     ↓
[ Bandpass Filter (0.5Hz – 45Hz) ]
     ↓
[ ADS1299 ADC ]
     ↓ SPI
[ Raspberry Pi ]
     ↓ WiFi/HTTP
[ Django + HTMX Platform ]
```

### EEG Signal Conditioning Chain

1. **Amplify** weak microvolt signals (gain 1000x)
2. **Filter** (bandpass 0.5–45Hz, optional notch at 50/60Hz)
3. **Digitize** with 24-bit ADC
4. **Stream** via SPI to Raspberry Pi

---

## 🧪 4. Raspberry Pi Software

### a. SPI Interface (Python)

Use `spidev` to read from the ADS1299 over SPI.

```bash
sudo apt install python3-spidev
```

**Example** `eeg_streamer.py`:

```python
import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)  # Open SPI bus 0, device 0
spi.max_speed_hz = 1000000

def read_adc():
    # Send read command (depends on ADS1299 config)
    resp = spi.xfer2([0x12])  # example command
    return resp

while True:
    data = read_adc()
    print(data)
    time.sleep(0.004)  # ~250Hz
```

### b. Preprocessing

Use `scipy` to:

- Apply digital bandpass filter
- Calculate power in alpha/beta bands
- Output attention scores

### c. Send Data to Server

Use `requests` or `aiohttp` to POST JSON to the Django backend:

```python
import requests

data = {
    "user_id": "student42",
    "engagement_score": 0.82,
    "timestamp": "2025-03-23T15:00:00Z"
}

requests.post("https://your-django-api.com/api/engagement/", json=data)
```

---

## 🌐 5. Django Backend

### Models

```python
class EEGSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    engagement_score = models.FloatField()
    content_tag = models.CharField(max_length=100)
```

### API Endpoint (Django REST Framework)

```python
@api_view(['POST'])
def record_engagement(request):
    EEGSession.objects.create(
        user=request.user,
        engagement_score=request.data['engagement_score'],
        content_tag=request.data.get('content_tag', '')
    )
    return Response({"status": "ok"})
```

---

## ✨ 6. HTMX Frontend

Example: Inject retention quiz when a user has high engagement with content.

```html
<div id="quiz-placeholder" hx-get="/quiz/load/" hx-trigger="load"></div>
```

Django View:

```python
def load_quiz(request):
    if should_trigger_quiz(user=request.user):
        return render(request, "quiz-snippet.html", {...})
    return HttpResponse("")
```

---

## 🔍 7. Testing & Calibration

### Lab Tests

- Compare against a commercial EEG headset
- Use synthetic signal generator for benchmarking

### Student Trials

- Track quiz performance vs. engagement
- Use A/B testing to measure learning gains

---

## 🪪 8. Safety + Compliance

- Keep voltage < 3.3V on all analog inputs
- Isolate ADC from Pi ground if necessary
- Consider CE/FCC compliance for commercialization

---

## 🌍 9. Commercialization Strategy

### Phase 1: Open-Source Community Kit

- Publish PCB layout (KiCad)
- Provide full BOM + GitHub repo
- Offer tutorial videos + forum

### Phase 2: Classroom Kits

- Partner with STEM educators
- Bundle:
  - PCB
  - Electrodes
  - Pre-loaded Pi
- Sell via Tindie, CrowdSupply, or direct

### Licensing

- Hardware: CERN-OHL v2
- Software: MIT / Apache 2.0

---

## 📁 10. GitHub Repo Layout

```
neurolearnpi/
├── hardware/
│   ├── pcb/
│   ├── schematics/
│   └── BOM.md
├── raspberry-pi/
│   ├── eeg_streamer.py
│   ├── signal_analysis.py
│   └── post_to_server.py
├── backend/
│   ├── api/
│   ├── quizzes/
│   └── engagement/
├── frontend/
│   ├── templates/
│   └── htmx/
└── LICENSE
```

---

## 📚 Additional Resources

- [OpenBCI Documentation](https://docs.openbci.com/)
- [ADS1299 Datasheet](https://www.ti.com/product/ADS1299)
- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.org/documentation/hardware/raspberrypi/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [HTMX Documentation](https://htmx.org/docs/)

---

## 🎯 Project Scope for GSoC 2025

### Expected Outcomes

1. **Hardware Prototype**: Functional EEG acquisition system with Raspberry Pi
2. **Data Pipeline**: Real-time EEG data streaming to Django backend
3. **Web Integration**: HTMX-based frontend displaying engagement metrics
4. **Documentation**: Complete build guide and API documentation
5. **Testing Suite**: Validation against commercial EEG devices

### Skills Required

- Electronics (analog circuits, PCB design)
- Python programming
- Django web framework
- Signal processing (digital filters, FFT)
- Embedded systems (Raspberry Pi, SPI communication)

### Difficulty Level

**Advanced** - Requires knowledge of both hardware and software development

### Project Duration

**350 hours** (Large project)

### Potential Mentors

- Hardware/Electronics Expert
- Django/Backend Developer
- Signal Processing Specialist

---

## 🚀 Getting Started

Interested students should:

1. Review the [Alpha One Labs Education Platform](https://github.com/alphaonelabs/education-website)
2. Familiarize yourself with Django and HTMX
3. Study basic EEG principles and signal processing
4. Join the community discussions and introduce yourself
5. Start with small contributions to the main platform

---

## ⚠️ Important Notes

- This is a **project idea** for GSoC 2025 - implementation will begin after proposal acceptance
- Students should **not** start coding until the project is officially assigned
- Safety considerations are paramount when working with biomedical devices
- All work must comply with ethical guidelines for human subjects research

---

## 📞 Contact

For questions about this project idea:

- Open an issue in the [GitHub repository](https://github.com/alphaonelabs/education-website)
- Join our community channels
- Email: info@alphaonelabs.com
