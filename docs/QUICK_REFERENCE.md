# Endpoint Analysis - Quick Reference Card

## 📊 At a Glance

```
Total Endpoints: 263

CRITICAL (9-10):  28  ████████░░░░░░░░░░░░  10.6%
IMPORTANT (7-8):  64  ████████████░░░░░░░░  24.3%
USEFUL (5-6):     98  █████████████████░░░  37.3%
OPTIONAL (1-4):   73  ██████████████░░░░░░  27.8%
```

## 🎯 Core Critical Endpoints (Must Never Remove)

| Category | Endpoints | Why Critical |
|----------|-----------|--------------|
| **Course System** | 7 | Core business: create, view, edit, enroll, search |
| **Authentication** | 4 | User access: signup, login, profile |
| **Payment** | 3 | Revenue: payment intent, webhook, cart |
| **Dashboards** | 2 | Main entry: student & teacher dashboards |
| **Core Pages** | 3 | Platform: homepage, learn, teach |
| **Admin** | 2 | Management: Django admin, admin dashboard |
| **Infrastructure** | 2 | Essential: i18n, captcha |

**Total: 23 endpoints** - These represent the absolute minimum viable platform.

## 🗑️ Immediate Removal Candidates (10 endpoints)

| Feature | Endpoints | Score | Why Remove | Impact |
|---------|-----------|-------|------------|--------|
| **Memes** | 3 | 2-3 | Not educational, off-mission | None |
| **Social Media Mgmt** | 4 | 2-3 | Better external tools exist | None |
| **Legacy Redirects** | 2 | 2 | Migration period complete | None |
| **Test Endpoints** | 1 | 2 | Development only | None |

**Savings**: 10 endpoints (~4% reduction), zero user impact

## ⚠️ Evaluate Before Deciding (30 endpoints)

| Feature | Endpoints | Score | Action Required |
|---------|-----------|-------|-----------------|
| **Merchandise System** | 15 | 3-4 | Check sales data. If <5% revenue, remove |
| **Trackers** | 6 | 3-4 | Check active trackers. If <100 users, remove |
| **Waiting Rooms** | 6 | 4-5 | Check conversion rate. Consider simplifying |
| **Avatar Customization** | 3 | 3-4 | Check usage. Nice-to-have, not essential |

**Potential Savings**: Up to 30 endpoints (~11% reduction)

## 🔄 Consolidation Opportunities

### 1. Collaboration Features (16 endpoints → 8-10 endpoints)
- **Team Goals** (10 endpoints) - General collaboration
- **Study Groups** (6 endpoints) - Course collaboration
- **Recommendation**: Merge into unified "Learning Communities"

### 2. Calendar Systems (8 endpoints → 4-5 endpoints)
- Course calendars
- Session calendars  
- Custom calendars
- Calendar feeds
- **Recommendation**: Single unified calendar with multiple views

### 3. Messaging Systems (6+ endpoints → 3-4 endpoints)
- Secure messaging
- Peer messages
- Course messages
- **Recommendation**: Consistent messaging interface

**Potential Savings**: 15-20 endpoints through consolidation

## 📈 Category Priorities

### High Value - Optimize
- ✅ **Courses** (27) - 7.3/10 - Core business logic
- ✅ **Payments** (24) - 7.1/10 - Revenue generation
- ✅ **Authentication** (6) - 8.7/10 - User management
- ✅ **Progress** (8) - 7.5/10 - Learning outcomes

### Medium Value - Maintain
- 👍 **Assessment** (29) - 6.0/10 - Quizzes & tests
- 👍 **Communication** (6) - 6.8/10 - User messaging
- 👍 **Forum** (31) - 5.5/10 - Community engagement
- 👍 **Virtual Classroom** (17) - 5.7/10 - Live teaching

### Low Value - Evaluate/Remove
- ⚠️ **Merchandise** (15) - 3.7/10 - Off-mission
- ⚠️ **Marketing** (7) - 3.7/10 - Better external tools
- ⚠️ **Content/Memes** (17) - 4.6/10 - Bloat
- ⚠️ **Tools** (7) - 3.9/10 - Niche features

## 🚀 Implementation Roadmap

### Q1 2026: Quick Wins
- [ ] Remove memes (3 endpoints)
- [ ] Remove social media management (4 endpoints)
- [ ] Remove legacy redirects (2 endpoints)
- [ ] Remove test endpoints (1 endpoint)
- **Result**: 10 endpoints removed, 0 user impact

### Q2 2026: Data Collection
- [ ] Add analytics to merchandise system
- [ ] Track tracker usage
- [ ] Monitor waiting room conversions
- [ ] Measure avatar customization rate
- **Result**: Data-driven decisions for Q3

### Q3 2026: Strategic Removals
- [ ] Decide on merchandise based on data
- [ ] Remove or simplify trackers
- [ ] Simplify waiting rooms
- [ ] Start consolidation planning
- **Result**: 15-30 endpoints removed

### Q4 2026: Consolidation
- [ ] Merge team goals + study groups
- [ ] Unify calendar systems
- [ ] Standardize messaging
- **Result**: Simplified UX, easier maintenance

## 💡 Key Insights

1. **10% of endpoints are critical** - Focus protection and optimization here
2. **28% are optional** - Low-hanging fruit for simplification
3. **40-50 endpoints can be removed/consolidated** - 15-20% reduction possible
4. **Business value concentration** - Most value in 35% of endpoints

## 📞 Decision Framework

When deciding on an endpoint:

```
HIGH USER IMPACT? ────► YES ────► KEEP & OPTIMIZE
       │
       NO
       │
       ▼
HIGH COMPLEXITY? ────► YES ────► REMOVE
       │
       NO
       │
       ▼
                      KEEP IF EASY
```

## 🎬 Next Steps

1. **Review** this analysis with product & engineering teams
2. **Gather** actual usage data for "evaluate" endpoints
3. **Start** with Phase 1 quick wins (10 endpoints)
4. **Plan** consolidation for high-complexity features
5. **Monitor** impact of changes

---

**Full Analysis**: See `docs/ENDPOINT_ANALYSIS.md` (1,900 lines)
**Executive Summary**: See `docs/ENDPOINT_SUMMARY.md`
**Data**: See `docs/endpoints.csv`

**Generated**: February 2026
**Version**: 1.0
