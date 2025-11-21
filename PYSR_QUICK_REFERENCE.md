# PySR Integration - Quick Reference Card

**Last Updated:** 2025-11-19
**Status:** ✅ Production Operational

---

## 🚨 Emergency Contacts

**Issue Severity:**
- 🔴 **Critical:** System down, rollback needed
- 🟡 **Warning:** Degraded performance, monitor closely
- 🟢 **Info:** Normal operation, FYI only

**Response:**
- Critical: Execute rollback procedure immediately
- Warning: Increase monitoring frequency, investigate within 1 hour
- Info: Document and review during next maintenance window

---

## 📊 Health Check (1-Minute Status)

```bash
# Quick health check
cd /Volumes/SSDRAID0/agentic-system/scripts

# 1. Run integration tests (should take ~10 seconds)
python3 test_pysr_integration.py

# Expected: "🎉 ALL TESTS PASSED!"
# If failed: Check error message, may need rollback
```

---

## 🔍 Monitoring Commands

### Check Equation Usage
```bash
# How many times equations were called today
grep "PySR.*estimate\|PySR.*score" /Volumes/SSDRAID0/agentic-system/logs/*.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

### Check Fallback Frequency
```bash
# Count fallback triggers (should be < 1% of calls)
grep "using fallback heuristic" /Volumes/SSDRAID0/agentic-system/logs/*.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

### Check for Errors
```bash
# Any errors related to equations?
grep -i "error.*pysr\|error.*equation" /Volumes/SSDRAID0/agentic-system/logs/*.log | \
  grep "$(date +%Y-%m-%d)"
```

### View Current Equations
```bash
# What equations are in production?
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db \
  "SELECT system_component, performance_r2, complexity_score
   FROM discovered_equations
   WHERE deprecated_at IS NULL;"
```

---

## 📈 Performance Metrics

### Expected Values
| Metric | Target | Alert If |
|--------|--------|----------|
| Inference Time | < 1ms | > 10ms |
| Fallback Rate | < 1% | > 5% |
| Error Rate | 0% | > 0.1% |
| System Latency | Baseline | +5% |

### Check Performance
```bash
# Equation inference time (from logs)
grep "PySR improvement estimate" /Volumes/SSDRAID0/agentic-system/logs/*.log | \
  tail -20
```

---

## 🔧 Common Issues and Fixes

### Issue 1: High Fallback Rate (> 5%)
**Symptoms:** Many "using fallback heuristic" messages
**Likely Cause:** Database connection issues or equation loading failure
**Fix:**
```bash
# 1. Check database accessibility
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db \
  "SELECT COUNT(*) FROM discovered_equations WHERE deprecated_at IS NULL;"

# 2. Check file permissions
ls -la /Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db

# 3. Restart equation integration layer (reload cache)
# (System-specific restart command)
```

### Issue 2: Integration Tests Failing
**Symptoms:** test_pysr_integration.py shows failures
**Likely Cause:** Database corruption or missing equations
**Fix:**
```bash
# 1. Verify database integrity
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db \
  "PRAGMA integrity_check;"

# 2. Check equation count
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db \
  "SELECT COUNT(*) FROM discovered_equations WHERE deprecated_at IS NULL;"

# Expected: 3 equations (darwin_godel, meta_learning, skill_evolution)

# 3. If < 3 equations, database may be corrupted
# Restore from backup or retrain
```

### Issue 3: System Performance Degradation
**Symptoms:** Overall system slower, equation calls taking > 10ms
**Likely Cause:** Cache invalidation or memory pressure
**Fix:**
```bash
# 1. Check system resources
top -l 1 | grep -E "^CPU|^PhysMem"

# 2. Restart equation integration (clear/reload cache)
# (System-specific restart)

# 3. If persistent, consider rollback
```

---

## 🔄 Rollback Procedure (Emergency)

### When to Rollback
- Critical errors (system down)
- Performance degradation > 20%
- Fallback rate > 50%
- Integration tests failing consistently

### Rollback Steps
```bash
# 1. Disable PySR in all three files
# Edit these files and change use_pysr=True to use_pysr=False:
# - intelligent-agents/darwin_godel_machine.py (line 416)
# - intelligent-agents/meta_learning_engine.py (line 220)

# 2. For skill evolution (always-on), comment out PySR block:
# - intelligent-agents/skill_evolution_system.py (lines 534-558)

# 3. Restart services
# (System-specific restart command)

# 4. Verify fallback active
grep "fallback heuristic" /Volumes/SSDRAID0/agentic-system/logs/*.log | tail -10

# 5. Document incident
# Create: /Volumes/SSDRAID0/agentic-system/INCIDENT_$(date +%Y%m%d).md
```

---

## 📅 Maintenance Schedule

### Daily (Automated)
- ✅ Log rotation
- ✅ Backup database
- ✅ Performance metrics collection

### Weekly (Manual)
- 📊 Review fallback frequency
- 📊 Check prediction distributions
- 📊 Analyze performance trends
- 📊 Update monitoring dashboard

### Monthly (Manual)
- 🔄 Review equation performance vs heuristics
- 🔄 Collect production data samples
- 🔄 Analyze drift and accuracy
- 🔄 Plan retraining if needed

### Quarterly (Manual)
- 🔬 Retrain equations with production data
- 🔬 Run comprehensive A/B tests
- 🔬 Update documentation
- 🔬 Review and optimize

---

## 📊 A/B Testing (Periodic Validation)

### When to Run
- After any equation changes
- Quarterly validation
- If performance concerns arise
- Before promoting new equations

### Run A/B Tests
```bash
cd /Volumes/SSDRAID0/agentic-system/scripts

# Full test suite (300 trials, ~30 seconds)
python3 ab_test_pysr_equations.py --trials 100

# Quick validation (30 trials, ~5 seconds)
python3 ab_test_pysr_equations.py --trials 10
```

### Expected Results
- PySR Win Rate: > 80% for all systems
- Error Reduction: > 50% for all systems
- Statistical Significance: p < 0.05

**If results worse:** Investigate equation behavior, may need retraining

---

## 🔄 Retraining Workflow

### When to Retrain
- Quarterly schedule
- After collecting 1000+ production samples
- If A/B tests show performance degradation
- If significant system changes occur

### Retraining Steps
```bash
cd /Volumes/SSDRAID0/agentic-system/scripts

# 1. Prepare production data
# (System-specific data export)

# 2. Update training script with real data
# Edit: train_initial_equations.py

# 3. Run training
python3 train_initial_equations.py

# 4. Validate new equations
python3 ab_test_pysr_equations.py --trials 100

# 5. If improvement > current:
#    - Deploy new equations
#    - Deprecate old equations
#    - Update deployment log

# 6. If no improvement:
#    - Keep current equations
#    - Document findings
#    - Adjust training parameters
```

---

## 📁 Important File Locations

### Code
```
/Volumes/SSDRAID0/agentic-system/intelligent-agents/
├── equation_integration.py         (Integration layer)
├── symbolic_regression_manager.py  (Training pipeline)
├── darwin_godel_machine.py         (System 1)
├── meta_learning_engine.py         (System 2)
└── skill_evolution_system.py       (System 3)
```

### Scripts
```
/Volumes/SSDRAID0/agentic-system/scripts/
├── test_pysr_integration.py              (Integration tests)
├── ab_test_pysr_equations.py             (A/B testing)
├── train_initial_equations.py            (Training)
├── retrain_darwin_godel_constrained.py   (Retraining)
└── analyze_darwin_godel_equation.py      (Analysis)
```

### Data
```
/Volumes/SSDRAID0/agentic-system/databases/
└── discovered_equations.db  (Equation storage)
```

### Documentation
```
/Volumes/SSDRAID0/agentic-system/
├── PYSR_INTEGRATION_COMPLETE.md  (Integration summary)
├── PYSR_PRODUCTION_READY.md      (Production guide)
├── PYSR_FINAL_SUMMARY.md         (Project summary)
├── PYSR_DEPLOYMENT_LOG.md        (Deployment log)
└── PYSR_QUICK_REFERENCE.md       (This file)
```

---

## 🎯 Key Performance Indicators

### System Health
- ✅ Integration Tests: 6/6 passing
- ✅ Equation Load Time: < 100ms (cached: < 1ms)
- ✅ Fallback Rate: < 1%
- ✅ Error Rate: 0%

### Business Metrics
- ✅ Error Reduction: 69.74% average
- ✅ Win Rate: 93.7% (281/300)
- ✅ Statistical Significance: p < 0.001
- ✅ Systems Operational: 3/3

---

## 🆘 Troubleshooting Decision Tree

```
Issue detected
    │
    ├─ Integration tests failing?
    │   ├─ YES → Check database integrity
    │   └─ NO → Continue
    │
    ├─ Fallback rate > 5%?
    │   ├─ YES → Check database accessibility, restart cache
    │   └─ NO → Continue
    │
    ├─ Performance degraded > 20%?
    │   ├─ YES → Execute rollback, investigate
    │   └─ NO → Continue
    │
    ├─ Errors in logs?
    │   ├─ YES → Analyze error, may need rollback
    │   └─ NO → System healthy
    │
    └─ System healthy → Continue monitoring
```

---

## 📞 Support Resources

### Documentation
- Main guide: `docs/README_PYSR.md`
- Equations: `docs/DISCOVERED_EQUATIONS.md`
- Integration plan: `docs/PYSR_INTEGRATION_PLAN.md`

### Testing
- Integration: `python3 scripts/test_pysr_integration.py`
- A/B testing: `python3 scripts/ab_test_pysr_equations.py`
- Analysis: `python3 scripts/analyze_darwin_godel_equation.py`

### Database
- Location: `databases/discovered_equations.db`
- Backup: `databases/backups/`
- Schema: See `docs/DISCOVERED_EQUATIONS.md`

---

## ✅ Daily Checklist

**Morning:**
- [ ] Run integration tests (`test_pysr_integration.py`)
- [ ] Check error logs for issues
- [ ] Verify fallback rate < 1%

**Evening:**
- [ ] Review performance metrics
- [ ] Check for any anomalies
- [ ] Update monitoring dashboard

**Weekly:**
- [ ] Run A/B tests (quick validation)
- [ ] Review prediction distributions
- [ ] Document any issues

**Monthly:**
- [ ] Analyze production data
- [ ] Review retraining needs
- [ ] Update documentation

---

**Quick Reference Version:** 1.0.0
**Last Updated:** 2025-11-19
**Next Review:** 2025-12-19 (1 month)

---

*Keep this reference handy for quick troubleshooting and maintenance.*
*All systems operational. 69.74% improvement. 93.7% win rate. p < 0.001.*
