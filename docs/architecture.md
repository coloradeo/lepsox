# LepSox System Architecture

## Overview

LepSox is a modular validation system for Lepidopterist Society observation data. It uses a **hybrid validation architecture** that combines deterministic Python validators with AI-powered CrewAI agents, integrated with iNaturalist via MCP (Model Context Protocol) for species and location verification.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                           │
│         (CLI Script or FastAPI Web - Future)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              LepSocValidationCrew (Orchestrator)             │
│  • Reads Excel/CSV files                                     │
│  • Coordinates 16 validation agents (11 deterministic + 5 AI)│
│  • Manages iNaturalist MCP validator with caching            │
│  • Applies corrections                                       │
│  • Generates output with metadata                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌────────────────┐  ┌──────────────────┐
│ Deterministic│  │   AI-Powered   │  │ External Services│
│  Validators  │  │   Validators   │  │                  │
│   (11 of 16) │  │   (5 of 16)    │  │ • Ollama LLM     │
│              │  │                │  │ • iNaturalist    │
│ • Geographic │  │ • Taxonomic(4) │  │   (via MCP)      │
│ • Temporal   │  │ • Comments     │  │                  │
│ • Records    │  │                │  │                  │
└──────────────┘  └────────────────┘  └──────────────────┘
```

## Hybrid Validation Architecture

### Design Philosophy

The system uses a **hybrid approach** to balance performance and intelligence:

- **Deterministic Validators (11/16)**: Simple rule-based validation (no LLM overhead)
- **AI-Powered Validators (5/16)**: Complex validation requiring intelligence or fuzzy matching

### Validator Classification

#### Deterministic Validators (use_ai=False)
No LLM initialization, pure Python logic:
- **Geographic**: Zone, Country, State, County*
- **Temporal**: First Date, Last Date, Year
- **Records**: State Record, County Record
- **Metadata**: Location, Name

*County uses iNat MCP for location verification but doesn't need AI

#### AI-Powered Validators (use_ai=True)
Initialize as CrewAI Agents with LLM access:
- **Taxonomic**: Family, Genus, Species, Subspecies (all with iNat MCP integration)
- **Metadata**: Comments (AI-powered shortening/standardization)

### BaseValidator Implementation

All validators inherit from `BaseValidator` with dynamic Agent initialization:

```python
class BaseValidator:
    def __init__(self, field_name: str, llm: Optional[Any] = None, use_ai: bool = False):
        self.field_name = field_name
        self.use_ai = use_ai

        if use_ai:
            # Only initialize as Agent when AI is needed
            self._init_as_agent(field_name, llm)
        else:
            # Simple Python class - no Agent overhead
            self.role = f'{field_name} Validator'
```

Benefits:
- **Performance**: 11 validators skip Agent initialization overhead
- **Uniform Interface**: All validators use same `validate()` method
- **Flexibility**: Easy to toggle AI on/off per validator
- **Clear Intent**: Code explicitly shows which validators need intelligence

## Component Details

### 1. Entry Point

**Location**: `scripts/run_validator.py`

Simple CLI script that:
- Accepts input/output file paths
- Creates `LepSocValidationCrew` instance
- Runs validation
- Saves results

### 2. Orchestrator

**Location**: `src/lepsox/validator.py`

**Class**: `LepSocValidationCrew`

**Responsibilities**:
- Initialize Ollama LLM (for AI validators)
- Initialize INatValidator (shared, with caching)
- Create all 16 validation agents
- Read Excel/CSV input files
- Process rows sequentially
- Collect validation results
- Apply corrections
- Add metadata columns
- Write output files
- Print summary statistics

**Key Methods**:
```python
def __init__(ollama_url, ollama_model, inat_url):
    # Initialize LLM and iNat validator

def _create_validators() -> List:
    # Create 16 validators with proper dependencies
    # Deterministic validators: no LLM
    # AI validators: get LLM
    # Taxonomic validators: get LLM + iNat validator
    # County validator: get iNat validator

def validate_row(row_index, row_data) -> Dict:
    # Validates single row with all agents

def validate_file(filepath, output_path) -> DataFrame:
    # Validates entire file and saves results
```

### 3. Validation Agents

**Location**: `src/lepsox/agents/`

#### Deterministic Validators

**Geographic Validators** (`geographic.py`):
- `ZoneValidator` - Validates zones 1-12
- `CountryValidator` - Validates USA/CAN/MEX
- `StateValidator` - Validates state/province codes against lookup tables
- `CountyValidator` - Validates county names + iNat location verification

**Temporal Validators** (`temporal.py`):
- `FirstDateValidator` - Validates date format (dd-mmm-yy)
- `LastDateValidator` - Validates optional end date
- `YearValidator` - Validates observation year

**Record Validators** (`records.py`):
- `StateRecordValidator` - Validates Y/N/blank state record flag
- `CountyRecordValidator` - Validates Y/N/blank county record flag

**Metadata Validators** (`metadata.py` - partial):
- `LocationValidator` - Validates specific location text
- `NameValidator` - Validates contributor codes

#### AI-Powered Validators

**Taxonomic Validators** (`taxonomic.py`):
All use iNaturalist MCP for species verification and hierarchy validation.

- `FamilyValidator` (AI)
  - Checks against common Lepidoptera families
  - Flags uncommon families for verification

- `GenusValidator` (AI + iNat)
  - Validates genus capitalization
  - Future: iNat genus verification

- `SpeciesValidator` (AI + iNat)
  - Validates species epithet (lowercase)
  - **iNat validation**: Verifies genus+species combination
  - **Hierarchy checking**: Detects family/genus/species mismatches
  - **Suggests corrections**: Recommends correct family based on genus/species
  - Flags unknown species for human review

- `SubspeciesValidator` (AI + iNat)
  - Optional field validation
  - **iNat validation**: Verifies trinomial name (genus+species+subspecies)
  - **Hierarchy checking**: Validates family against subspecies
  - Flags unknown subspecies for human review

**Metadata Validators** (`metadata.py` - partial):
- `CommentValidator` (AI)
  - Validates comment length (max 120 chars)
  - **GPS detection**: Both decimal and DMS formats
  - **AI-powered shortening**: Uses LLM to shorten long comments
  - **Style guidelines**: Applies lepidopterist abbreviations
  - Graceful error handling for AI failures

#### Validation Flow

```python
1. Agent receives field value + full row data
2. Performs deterministic checks (format, length, required)
3. If AI-powered: Can use execute_ai_task() for complex logic
4. If taxonomic: Validates via iNat MCP (with caching)
5. Returns ValidationResult with:
   - is_valid: bool
   - errors: List[str]
   - warnings: List[str]
   - correction: Optional value
   - metadata: Dict (e.g., inat_taxon_id, suggested_family)
```

### 4. Data Models

**Location**: `src/lepsox/models/`

**ValidationResult** (`validation_result.py`):
- Standardized container for validation results
- Used by all validators
- Converted to dict for aggregation
- Includes metadata for iNat results, suggestions, etc.

### 5. External Integrations

**Location**: `src/lepsox/integrations/`

**INatValidator** (`inat.py`):
Connects to iNaturalist via MCP server for species/location validation.

**Key Features**:
- **MCP Integration**: Uses `mcp` SDK with SSE client
- **Caching**: All lookups cached during validation run
- **Independent validation**: Species and geography validated separately

**Methods**:
```python
async def check_species(genus, species, family=None) -> Dict:
    # Validates species via iNat
    # Returns taxon_id, common_name, hierarchy info
    # Detects family/genus/species mismatches
    # Suggests correct family when mismatch found

async def check_location(county, state, country) -> Dict:
    # Validates location via iNat places API
    # Returns place_id, display_name

async def check_record_status(taxon_id, place_id, ...) -> Dict:
    # Checks if observation is a new record
    # Returns is_new_record, existing_count, query_url

def clear_cache():
    # Clears all caches (for new validation runs)
```

**Caching Strategy**:
- Species cache: `{genus}_{species}_{family}` → result
- Location cache: `{county}_{state}_{country}` → result
- Record cache: `{taxon_id}_{place_id}_{state}_{county}` → result
- Minimizes repeated API calls for same data
- Shared across all validators in a run

**iNat Validation Logic**:
1. Check cache first
2. If miss: Query iNat MCP server via SSE
3. Parse results and extract hierarchy info
4. Detect mismatches (e.g., genus doesn't belong to family)
5. Suggest corrections based on API response
6. Cache result for future lookups
7. Return validation dict with all metadata

### 6. Configuration

**Location**: `src/lepsox/config.py`

Centralized configuration for:

**Server URLs**:
- `OLLAMA_BASE_URL` - Ollama LLM server
- `OLLAMA_MODEL` - Model name (llama2)
- `INAT_MCP_URL` - iNaturalist MCP server (SSE endpoint)

**Validation Constants**:
- `VALID_ZONES` - Zones 1-12
- `VALID_COUNTRIES` - USA/CAN/MEX
- `US_STATES` - All US state abbreviations
- `CAN_PROVINCES` - Canadian province codes
- `MEX_STATES` - Mexican state abbreviations
- `COMMON_FAMILIES` - Known Lepidoptera families
- `DATE_FORMAT` - Regex for dd-mmm-yy format

**GPS Patterns**:
- `GPS_DECIMAL_PATTERN` - Decimal coordinates (42.5834,-87.8294)
- `GPS_DMS_PATTERN` - Degrees/minutes/seconds (42°35'2.4"N)

**Lepidopterist Standards**:
- `LEPIDOPTERIST_ABBREVIATIONS` - 40+ standard abbreviations
  - Location: "nr" = near, "ca" = circa
  - Methods: "lt" = light trap, "mv" = mercury vapor
  - Behaviors: "nect" = nectaring, "ovipos" = ovipositing
  - Life stages: "L" = larva, "P" = pupa, "A" = adult
  - Sex: "M" = male, "F" = female
  - Condition: "fresh", "worn", "tattered"
  - And many more...

- `COMMENT_STYLE_GUIDE` - Guidelines for AI comment shortening
  - Max 120 characters
  - Use standard abbreviations
  - No redundant info from other fields
  - GPS coordinates in decimal or DMS
  - Separate observations with semicolons

### 7. Tests

**Location**: `tests/`

**Test Structure**:
- `test_agents.py` - Comprehensive unit tests for all validators
  - Tests for deterministic validators (no LLM needed)
  - Tests for AI-powered validators (with mock LLM)
  - Tests for iNat integration (with mock validator)
  - Integration tests for hybrid architecture

- `conftest.py` - Pytest fixtures
  - `llm` fixture: Ollama LLM for AI validators
  - `mock_inat_validator` fixture: Mock iNat for testing

- `fixtures/` - Sample data files
  - `test_with_errors.xlsx` - Known errors for testing
  - `valid_sample.xlsx` - Clean reference data

**Test Coverage**:
- All 16 validators tested individually
- Hybrid architecture verified (11 deterministic + 5 AI)
- iNat integration mocked for fast tests
- Hierarchy mismatch detection tested
- GPS format detection tested (decimal and DMS)
- Comment shortening tested
- Edge cases covered

## Data Flow

### Input
1. Excel/CSV file with 16 columns (A-P)
2. No headers (raw data only)
3. Column order must match spec

### Processing
1. Read file into Pandas DataFrame
2. Assign column names from config
3. Initialize validators (hybrid: deterministic + AI)
4. Initialize shared iNat validator with caching
5. For each row:
   - Pass to all 16 validators
   - Validators use iNat MCP as needed (cached)
   - Collect results with hierarchy suggestions
   - Flag for review if needed
6. Apply automatic corrections
7. Add 5 metadata columns (Q-U)

### Output
Original 16 columns + 5 metadata columns:
- Q: `Validation_Status` (PASS/CORRECTED/FAIL)
- R: `Validation_Notes` (error/warning messages, suggestions)
- S: `Original_Values` (what was changed)
- T: `Confidence_Score` (1.0/0.8/0.5)
- U: `Validated_By` (CrewAI Agent)

## Technology Stack

### Core
- **Python 3.9+**
- **CrewAI 0.28.8** - Agent orchestration (AI validators only)
- **Langchain** - LLM integration
- **Pandas** - Data processing
- **OpenPyXL** - Excel file handling

### AI/ML
- **Ollama** - Local LLM (llama2) at 192.168.51.99:30068
- **iNaturalist MCP** - Species/location data via MCP server at 192.168.51.99:8811
- **MCP SDK** - Model Context Protocol client

### Development
- **Pytest** - Testing
- **pytest-asyncio** - Async test support
- **unittest.mock** - Mocking for tests
- **Black** - Code formatting
- **MyPy** - Type checking
- **Loguru** - Logging (future)

## Deployment

### Current (Sprint 1)
- Run locally via CLI script
- Manual file upload/download
- Results saved to disk

### Future (Sprint 3+)
- FastAPI web service
- Browser-based file upload
- Real-time progress updates
- Docker containerization

## Performance Considerations

### Current Optimizations
1. **Hybrid Architecture** - 11/16 validators skip LLM overhead (major improvement)
2. **iNat Caching** - All API calls cached during validation run
3. **Shared iNat Validator** - Single instance across all validators

### Bottlenecks
1. **Sequential processing** - Rows processed one at a time
2. **Async-to-sync conversion** - iNat MCP calls use asyncio.run() wrapper
3. **No persistent cache** - Cache cleared between runs

### Future Optimization Opportunities (Sprint 4)
1. Batch row processing
2. Parallel validator execution per row
3. Persistent caching (Redis/SQLite)
4. Async-first validation pipeline
5. Connection pooling for iNat MCP

### Performance Expectations
- **Deterministic validators**: < 1ms per field
- **AI validators**: Variable (depends on LLM)
- **iNat lookups (cached)**: < 1ms
- **iNat lookups (uncached)**: 100-500ms via MCP
- **Target**: < 1 minute per 100 rows

## Security

### Current
- No authentication
- Local execution only
- No sensitive data handling
- MCP over HTTP (internal network)

### Future
- File upload size limits
- Input sanitization
- Rate limiting for API calls
- User authentication (if web-based)
- HTTPS for MCP connection

## Extensibility

### Adding New Validators
1. Create new validator class inheriting from `BaseValidator`
2. Set `use_ai=True` or `use_ai=False` in `__init__`
3. Implement `validate(value, row_data)` method
4. Add to agent list in `LepSocValidationCrew._create_validators()`
5. Update column names in config if needed

### Adding New Integrations
1. Create module in `src/lepsox/integrations/`
2. Implement async methods for API calls
3. Add caching if needed
4. Add configuration to `config.py`
5. Pass instance to relevant validators

### Adding iNat Validation to Existing Validator
1. Add `inat_validator` parameter to `__init__`
2. In `validate()`, check if inat_validator is provided
3. Call appropriate iNat method (e.g., `check_species()`)
4. Use `asyncio.run()` to run async call synchronously
5. Handle result and update ValidationResult metadata
6. Pass inat_validator when creating validator in orchestrator

## Monitoring & Logging

### Current
- Console output (print statements)
- Summary statistics after validation

### Planned
- Structured logging with Loguru
- Progress tracking
- Error rate monitoring
- Performance metrics
- iNat API call statistics

## Testing Strategy

### Unit Tests
- Each validator tested independently
- Mock LLM calls for AI validators
- Mock iNat validator for taxonomic validators
- Test edge cases (empty, invalid, boundary values)
- Verify `use_ai` flag correct for each validator

### Integration Tests
- Full file validation
- Multiple rows with varied data
- Error correction flow
- Hybrid architecture verification (11 deterministic + 5 AI)
- iNat integration (with mocks)

### Fixtures
- `valid_sample.xlsx` - Clean reference data
- `test_with_errors.xlsx` - Known errors for testing
- `mock_inat_validator` - Mock for fast iNat tests

## Version History

**v0.2.0** (Current)
- Hybrid validation architecture (11 deterministic + 5 AI)
- iNaturalist MCP integration with caching
- Subspecies trinomial validation
- Hierarchy validation with family suggestions
- GPS format detection (decimal and DMS)
- Lepidopterist abbreviations (40+ terms)
- AI-powered comment shortening
- Comprehensive test suite

**v0.1.0**
- Initial modular architecture
- 16 validation agents (all using CrewAI)
- Basic CLI interface
- Excel/CSV I/O
- Test framework

---

*Last Updated: January 2025*
*Sprint: 1 (Core Validation)*
*Architecture: Hybrid (Deterministic + AI)*
