# LepSox Validation System - Updated Sprint Plan

**Version:** 2.0
**Last Updated:** November 2024
**Current Status:** Sprint 0 Complete, Ready for Sprint 1

---

## Sprint 0: Foundation & Setup ✅ COMPLETE

**Duration:** Completed
**Goal:** Establish proper project structure and modular codebase

### Completed Tasks:
- ✅ Created modular directory structure (`src/lepsox/`)
- ✅ Split monolithic validator into 7 organized modules
- ✅ Created all 16 validation agents
- ✅ Split requirements into core/dev/full
- ✅ Added MCP SDK dependency
- ✅ Created test framework with pytest
- ✅ Added sample test fixtures
- ✅ Created `pyproject.toml` for proper packaging
- ✅ Created utility scripts (`run_validator.py`, `test_connections.py`)
- ✅ Wrote architecture documentation
- ✅ Established code simplicity guidelines (`.claude.md`)

### Deliverables:
- Clean, modular codebase
- Proper Python package structure
- Test framework ready
- Documentation in place
- Git repository with history

---

## Sprint 1: Core Validation (Week 1)

**Goal:** Get all 16 validators working end-to-end with test data

### Day 1-2: Environment & Testing

**Tasks:**
```bash
# 1. Install core dependencies
pip install -r requirements-core.txt -r requirements-dev.txt

# 2. Test connections
python scripts/test_connections.py

# 3. Run basic validator test
python scripts/run_validator.py tests/fixtures/test_with_errors.xlsx test_output.xlsx
```

**Success Criteria:**
- All connections working (Ollama + iNat MCP)
- Validator runs without crashes
- Output file generated

### Day 3: Fix Validator Issues

**Focus Areas:**
- Debug any import errors
- Fix validation logic bugs
- Ensure all 16 agents execute
- Test with both sample files

**Tasks:**
- Run pytest: `pytest tests/test_agents.py -v`
- Fix failing tests
- Add tests for edge cases

### Day 4: Data Quality

**Tasks:**
1. Analyze `test_with_errors.xlsx` - document known errors
2. Run validation and compare results
3. Check correction logic accuracy
4. Verify metadata columns added correctly

**Success Criteria:**
- At least 80% of errors detected
- Corrections are accurate
- No false positives

### Day 5: Documentation & Polish

**Tasks:**
- Document how to run validator
- Create development guide
- Add inline code comments where needed
- Create simple user guide

**Deliverables:**
- Working validator CLI
- Test suite passing
- User documentation
- Developer guide

---

## Sprint 2: iNaturalist Integration (Week 2)

**Goal:** Connect validators to iNaturalist for species/location verification

### Day 1: iNat Integration Setup

**Tasks:**
1. Test `INatValidator` class methods independently
2. Create async test for species lookup
3. Test location validation
4. Add error handling for API timeouts

**Code:**
```python
# Test script
import asyncio
from lepsox.integrations import INatValidator

async def test():
    validator = INatValidator()
    result = await validator.check_species("Danaus", "plexippus")
    print(result)

asyncio.run(test())
```

### Day 2-3: Integrate with Taxonomic Validators

**Modify:**
- `FamilyValidator` - Check family exists in iNat
- `GenusValidator` - Validate genus
- `SpeciesValidator` - Full species validation
- `SubspeciesValidator` - Check subspecies

**Approach:**
```python
# In validator.validate():
if self.metadata.get('needs_inat_check'):
    # Make async iNat call
    inat_result = await inat_validator.check_species(genus, species)
    if not inat_result['valid']:
        result.warnings.append(f"Species not found in iNaturalist")
```

**Note:** May need to make validation async, or run iNat checks in separate pass

### Day 4: Geographic Validation

**Integrate:**
- `CountyValidator` - Verify county/state combination
- Cross-reference with iNat places API

### Day 5: Record Detection

**Implement:**
- `StateRecordValidator` - Query iNat for existing state observations
- `CountyRecordValidator` - Check county-level records
- Flag potential new records for human review

**Algorithm:**
```
1. Get taxon_id from species validation
2. Query iNat observations for [taxon_id + place]
3. If count == 0, flag as potential new record
4. Add verification URL to metadata
```

**Deliverables:**
- iNat API fully integrated
- Species/location validation working
- New record detection functional
- Caching for API responses (optional)

---

## Sprint 3: Testing & Optimization (Week 3)

**Goal:** Polish the core validator, improve performance, comprehensive testing

### Day 1-2: Comprehensive Testing

**Create Test Suites:**
1. **Unit tests** - All 16 validators
2. **Integration tests** - Full file validation
3. **Edge case tests** - Empty values, special characters, boundary conditions
4. **iNat integration tests** - Mock and real API calls

**Target:** 80%+ code coverage

### Day 3: Performance Optimization

**Profile & Optimize:**
```bash
# Profile validation
python -m cProfile scripts/run_validator.py test.xlsx output.xlsx
```

**Potential Improvements:**
- Remove unnecessary LLM calls (simple validators don't need AI)
- Cache common lookups
- Batch API requests
- Parallel processing (if beneficial)

### Day 4: Error Handling & Logging

**Improve:**
- Structured logging with Loguru
- Better error messages
- Graceful failure handling
- Retry logic for API calls

### Day 5: Documentation & Examples

**Create:**
- Complete user guide
- API documentation
- Example data files
- Troubleshooting guide

**Deliverables:**
- Robust, tested validator
- Performance benchmarks
- Complete documentation
- Ready for real-world use

---

## Sprint 4: Web Interface (Optional - Week 4)

**Goal:** Add simple web UI for file upload/download

**Decision Point:** Only proceed if Sprint 1-3 results look good and there's demand for web interface.

### Architecture:
```
Frontend (Simple HTML/JS)
    ↓
FastAPI Backend
    ↓
LepSoc Validator (existing)
```

### Day 1: FastAPI Setup

**Create:**
- `src/lepsox/api/main.py` - FastAPI app
- Upload endpoint
- Status endpoint
- Download endpoint

### Day 2-3: Web UI

**Build Simple Interface:**
- File upload form
- Progress indicator
- Results table
- Download button

**Tech:** Plain HTML/JS or React (keep it simple)

### Day 4: WebSocket Progress

**Add:**
- Real-time validation progress
- Row-by-row updates
- Live error display

### Day 5: Deploy & Test

**Deploy:**
- Docker container
- nginx reverse proxy
- Test on real server

**Deliverables:**
- Working web interface
- API documentation
- Deployment guide

---

## Sprint 5: Production Ready (Week 5)

**Goal:** Make it production-ready for actual LepSoc use

### Day 1-2: Real Data Testing

**Tasks:**
- Get real season summary files from LepSoc
- Run validation on historical data
- Compare with known-good data
- Tune validation rules based on feedback

### Day 3: Advanced Features

**Based on feedback, add:**
- Bulk file processing
- Contributor code validation (if master file available)
- Custom validation rules
- Export formats (Excel, CSV, JSON)

### Day 4: Deployment

**Prepare:**
- Docker compose setup
- Environment configuration
- Database for storing results (optional)
- Monitoring/alerting

### Day 5: Handoff

**Deliverables:**
- Production deployment guide
- User training materials
- Support documentation
- Maintenance guide

---

## Success Metrics

### Sprint 1:
- ✅ Validator runs without errors
- ✅ All 16 agents execute
- ✅ Output file generated with metadata
- ✅ Test suite passing

### Sprint 2:
- 🎯 95%+ species validation accuracy
- 🎯 90%+ location validation accuracy
- 🎯 New record detection working
- 🎯 < 5% false positive rate

### Sprint 3:
- 🎯 80%+ code coverage
- 🎯 < 1 minute per 100 rows
- 🎯 Complete documentation
- 🎯 Zero critical bugs

### Sprint 4 (if pursued):
- 🎯 Web UI functional
- 🎯 File upload/download working
- 🎯 Progress tracking accurate

### Sprint 5:
- 🎯 LepSoc approval
- 🎯 Production deployment successful
- 🎯 User training complete

---

## Risks & Mitigations

### Risk: iNat API Rate Limits
**Mitigation:**
- Implement caching
- Batch requests
- Add retry logic with backoff

### Risk: Validation Rules Too Strict
**Mitigation:**
- Start with warnings, not errors
- Get feedback from LepSoc
- Make rules configurable

### Risk: Performance Issues
**Mitigation:**
- Profile early
- Optimize incrementally
- Set realistic expectations (not real-time for large files)

### Risk: Scope Creep
**Mitigation:**
- Stick to sprint goals
- **Keep it simple!**
- Get feedback before building more

---

## Current Status

**✅ Sprint 0 Complete**
- Project structure established
- Codebase modular and clean
- Tests framework in place
- Ready to begin validation testing

**Next Action:** Start Sprint 1, Day 1
```bash
pip install -r requirements-core.txt -r requirements-dev.txt
python scripts/test_connections.py
python scripts/run_validator.py tests/fixtures/test_with_errors.xlsx test_output.xlsx
```

---

*Keep it simple. Build what's needed. Test thoroughly. Ship incrementally.*
